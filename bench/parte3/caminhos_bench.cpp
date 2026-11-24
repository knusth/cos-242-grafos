// Estudo de caso da Parte 3: tempo de Bellman-Ford (um destino e todos os pares) e de
// Floyd-Warshall (e, opcionalmente, Johnson). Bellman-Ford de um destino roda em uma thread; a amostra (--bf-amostra), Floyd-Warshall,
// o todos-pares completo e Johnson usam --threads.
// Uso: cos_bench3 GRAFO.txt direcionado|nao_direcionado RODADAS [--fw] [--fw-rodadas N]
//                 [--fw-limite-gib G] [--bf-todos] [--bf-amostra K] [--johnson]
//                 [--fronteira heap|radix] [--threads N]
#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <atomic>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

#include <sys/resource.h>
#if defined(__APPLE__)
#include <pthread/qos.h>
#endif

namespace {

using cos_graph::Direction;
using cos_graph::Graph;
using cos_graph::Vertex;
using cos_graph::Weight;
using Clock = std::chrono::steady_clock;

constexpr auto bellman_target = Vertex{99}; // vértice 100 no arquivo
constexpr auto bytes_per_gib = 1024.0 * 1024.0 * 1024.0;

struct Options {
    std::string path;
    Direction direction = Direction::directed;
    std::uint32_t runs = 0;
    bool floyd = false;
    std::uint32_t floyd_runs = 0; // 0: usa RODADAS
    double floyd_limit_gib = 16.0;
    bool all_targets = false;
    std::uint32_t sample = 0; // 0: todos os destinos
    bool johnson = false;
    bool radix = false; // fronteira de Johnson: heap (padrão) ou radix
    unsigned threads = 1;
};

[[noreturn]] void fail_usage(const std::string & detail = {})
{
    throw std::invalid_argument{
        (detail.empty() ? "" : detail + "\n") +
        "uso: cos_bench3 GRAFO.txt direcionado|nao_direcionado RODADAS [--fw] [--fw-rodadas N]\n"
        "                [--fw-limite-gib G] [--bf-todos] [--bf-amostra K]\n"
        "                [--johnson] [--fronteira heap|radix] [--threads N]"};
}

template <class Number> Number parse_number(std::string_view text, std::string_view name)
{
    auto value = Number{};
    const auto [end, error] = std::from_chars(text.begin(), text.end(), value);
    if (error != std::errc{} || end != text.end()) {
        throw std::invalid_argument{std::string{name} + " deve ser um número não negativo"};
    }
    return value;
}

double parse_double(const std::string & text, std::string_view name)
{
    char * end = nullptr;
    const auto value = std::strtod(text.c_str(), &end);
    if (text.empty() || *end != '\0' || !(value >= 0)) {
        throw std::invalid_argument{std::string{name} + " deve ser um número não negativo"};
    }
    return value;
}

Options parse_options(int argc, char * argv[])
{
    if (argc < 4) {
        fail_usage();
    }
    auto options = Options{};
    options.path = argv[1];
    const auto direction = std::string_view{argv[2]};
    if (direction == "direcionado") {
        options.direction = Direction::directed;
    } else if (direction == "nao_direcionado") {
        options.direction = Direction::undirected;
    } else {
        fail_usage();
    }
    options.runs = parse_number<std::uint32_t>(argv[3], "RODADAS");
    if (options.runs == 0) {
        fail_usage("RODADAS deve ser positivo");
    }

    for (auto index = 4; index < argc; ++index) {
        const auto name = std::string_view{argv[index]};
        const auto value = [&]() -> std::string {
            if (index + 1 >= argc) {
                fail_usage("falta o valor de " + std::string{name});
            }
            return argv[++index];
        };
        if (name == "--fw") {
            options.floyd = true;
        } else if (name == "--fw-rodadas") {
            options.floyd_runs = parse_number<std::uint32_t>(value(), name);
        } else if (name == "--fw-limite-gib") {
            options.floyd_limit_gib = parse_double(value(), name);
        } else if (name == "--bf-todos") {
            options.all_targets = true;
        } else if (name == "--bf-amostra") {
            options.sample = parse_number<std::uint32_t>(value(), name);
        } else if (name == "--johnson") {
            options.johnson = true;
        } else if (name == "--fronteira") {
            const auto kind = value();
            if (kind != "heap" && kind != "radix") {
                fail_usage("--fronteira deve ser heap ou radix");
            }
            options.radix = kind == "radix";
        } else if (name == "--threads") {
            options.threads = parse_number<unsigned>(value(), name);
            if (options.threads == 0) {
                fail_usage("--threads deve ser positivo");
            }
        } else {
            fail_usage("opção desconhecida: " + std::string{name});
        }
    }
    if (options.floyd_runs == 0) {
        options.floyd_runs = options.runs;
    }
    return options;
}

std::uint64_t peak_rss_bytes()
{
    auto usage = rusage{};
    getrusage(RUSAGE_SELF, &usage);
#ifdef __APPLE__
    // O macOS informa ru_maxrss em bytes.
    return std::uint64_t(usage.ru_maxrss);
#else
    // O Linux informa ru_maxrss em KiB.
    return std::uint64_t(usage.ru_maxrss) * 1024;
#endif
}

Graph read_graph(const std::string & path, Direction direction)
{
    auto vertex_count = Vertex{0};
    auto edges = cos_file::read_triples(path, vertex_count);

    // O arquivo começa em 1; os índices da biblioteca começam em 0.
    for (auto & [first, second, weight] : edges) {
        if (first == 0 || second == 0 || first > vertex_count || second > vertex_count) {
            throw std::out_of_range{"uma aresta usa um vértice fora do intervalo do cabeçalho"};
        }
        --first;
        --second;
    }
    return Graph{vertex_count, edges, direction};
}

double seconds_since(Clock::time_point start)
{
    return std::chrono::duration<double>(Clock::now() - start).count();
}

Weight finite_sum(const std::vector<Weight> & distances)
{
    auto sum = Weight{0};
    for (const auto distance : distances) {
        if (distance != cos_graph::no_distance) {
            sum += distance;
        }
    }
    return sum;
}

struct Stats {
    double mean = 0;
    double deviation = 0; // desvio padrão amostral
    double min = 0;
};

Stats statistics(const std::vector<double> & values)
{
    auto stats = Stats{};
    if (values.empty()) {
        return stats;
    }
    for (const auto value : values) {
        stats.mean += value;
    }
    stats.mean /= double(values.size());
    stats.min = *std::min_element(values.begin(), values.end());
    if (values.size() > 1) {
        auto squares = 0.0;
        for (const auto value : values) {
            squares += (value - stats.mean) * (value - stats.mean);
        }
        stats.deviation = std::sqrt(squares / double(values.size() - 1));
    }
    return stats;
}

void print_stats(const Stats & stats, bool with_min = true)
{
    std::cout << "media_s=" << stats.mean << '\n' << "desvio_s=" << stats.deviation << '\n';
    if (with_min) {
        std::cout << "min_s=" << stats.min << '\n';
    }
}

void run_bellman_ford(const Graph & graph, std::uint32_t runs)
{
    std::cout << "\n[bellman_ford]\n"
              << "threads=1\n"
              << "destino=" << bellman_target + 1 << '\n'
              << "rodadas_medidas=" << runs << '\n';
    if (graph.vertex_count <= bellman_target) {
        std::cout << "situacao=destino_inexistente\n";
        return;
    }
    std::cout << "execucao,tempo_s,rodadas,ciclo_negativo,soma_distancias_finitas\n";
    auto times = std::vector<double>{};
    for (auto run = std::uint32_t{0}; run < runs; ++run) {
        const auto start = Clock::now();
        const auto result = graph.bellman_ford(bellman_target);
        const auto seconds = seconds_since(start);
        times.push_back(seconds);
        // A soma fica fora da medição e mantém o resultado vivo.
        std::cout << run + 1 << ',' << seconds << ',' << result.rounds << ','
                  << (result.negative_cycle ? "sim" : "nao") << ',' << finite_sum(result.distance)
                  << '\n'
                  << std::flush;
    }
    print_stats(statistics(times));
}

void run_floyd_warshall(const Graph & graph, const Options & options)
{
    const auto vertices = double(graph.vertex_count);
    // Duas matrizes V × V: Weight (8 bytes) e Vertex (4 bytes).
    const auto needed_bytes = (sizeof(Weight) + sizeof(Vertex)) * vertices * vertices;
    std::cout << "\n[floyd_warshall]\n"
              << "memoria_necessaria_gib=" << needed_bytes / bytes_per_gib << '\n'
              << "limite_gib=" << options.floyd_limit_gib << '\n'
              << "threads=" << options.threads << '\n';
    if (needed_bytes > options.floyd_limit_gib * bytes_per_gib) {
        std::cout << "situacao=memoria_insuficiente\n";
        return;
    }
    if (graph.vertex_count == 0) {
        std::cout << "situacao=grafo_vazio\n";
        return;
    }

    std::cout << "rodadas_medidas=" << options.floyd_runs << '\n'
              << "execucao,tempo_s,ciclo_negativo,checksum\n";
    auto times = std::vector<double>{};
    const auto last = graph.vertex_count - 1;
    for (auto run = std::uint32_t{0}; run < options.floyd_runs; ++run) {
        const auto start = Clock::now();
        const auto result = graph.floyd_warshall(options.threads);
        const auto seconds = seconds_since(start);
        times.push_back(seconds);

        // Poucas células fixas: mantém o resultado vivo sem um passo O(V²) na medição.
        auto checksum = Weight{0};
        for (const auto [from, to] : {std::pair{Vertex{0}, last}, std::pair{last, Vertex{0}},
                                      std::pair{Vertex{0}, Vertex{0}},
                                      std::pair{last / 2, last / 3}, std::pair{last / 3, last / 2}}) {
            const auto distance = result.distance(from, to);
            if (distance != cos_graph::no_distance) {
                checksum += distance;
            }
        }
        std::cout << run + 1 << ',' << seconds << ',' << (result.negative_cycle ? "sim" : "nao")
                  << ',' << checksum << '\n'
                  << std::flush;
    }
    print_stats(statistics(times));
}

void run_johnson(const Graph & graph, const Options & options)
{
    const auto vertices = double(graph.vertex_count);
    const auto needed_bytes = (sizeof(Weight) + sizeof(Vertex)) * vertices * vertices;
    std::cout << "\n[johnson]\n"
              << "fronteira=" << (options.radix ? "radix" : "heap") << '\n'
              << "memoria_necessaria_gib=" << needed_bytes / bytes_per_gib << '\n'
              << "limite_gib=" << options.floyd_limit_gib << '\n'
              << "threads=" << options.threads << '\n';
    if (needed_bytes > options.floyd_limit_gib * bytes_per_gib) {
        std::cout << "situacao=memoria_insuficiente\n";
        return;
    }
    if (graph.vertex_count == 0) {
        std::cout << "situacao=grafo_vazio\n";
        return;
    }

    std::cout << "rodadas_medidas=" << options.runs << '\n'
              << "execucao,tempo_s,ciclo_negativo,checksum\n";
    auto times = std::vector<double>{};
    const auto last = graph.vertex_count - 1;
    for (auto run = std::uint32_t{0}; run < options.runs; ++run) {
        const auto start = Clock::now();
        const auto result = options.radix ? graph.johnson<cos_graph::RadixFrontier>(options.threads)
                                          : graph.johnson(options.threads);
        const auto seconds = seconds_since(start);
        times.push_back(seconds);

        // Poucas células fixas, como no Floyd-Warshall; sem matrizes com ciclo negativo.
        auto checksum = Weight{0};
        if (!result.negative_cycle) {
            for (const auto [from, to] : {std::pair{Vertex{0}, last}, std::pair{last, Vertex{0}},
                                          std::pair{Vertex{0}, Vertex{0}},
                                          std::pair{last / 2, last / 3},
                                          std::pair{last / 3, last / 2}}) {
                const auto distance = result.distance(from, to);
                if (distance != cos_graph::no_distance) {
                    checksum += distance;
                }
            }
        }
        std::cout << run + 1 << ',' << seconds << ',' << (result.negative_cycle ? "sim" : "nao")
                  << ',' << checksum << '\n'
                  << std::flush;
    }
    print_stats(statistics(times));
}

void run_all_targets(const Graph & graph, const Options & options)
{
    const auto vertices = graph.vertex_count;
    std::cout << "\n[bellman_ford_todos_pares]\n";
    if (vertices == 0) {
        std::cout << "situacao=grafo_vazio\n";
        return;
    }

    const auto measured = (options.sample == 0 || options.sample >= vertices)
                              ? vertices
                              : Vertex{options.sample};
    const auto estimated = measured < vertices;
    // Destinos igualmente espaçados em 0..V-1.
    auto targets = std::vector<Vertex>(measured);
    for (auto index = std::size_t{0}; index < targets.size(); ++index) {
        targets[index] = Vertex(std::uint64_t{index} * vertices / measured);
    }

    // Completo: all_pairs_bellman_ford(threads). Amostra: bellman_ford por destino, com os
    // destinos repartidos entre as threads por um contador atômico; tempo_s é o relógio de
    // parede dos K destinos (a soma de distâncias de cada destino entra na medição).
    const auto threads = std::max(1u, options.threads);
    std::cout << "threads=" << threads << '\n'
              << "vertices=" << vertices << '\n'
              << "destinos_medidos=" << measured << '\n'
              << "estimado=" << (estimated ? "sim" : "nao") << '\n'
              << "rodadas_medidas=" << options.runs << '\n'
              << "execucao,tempo_s,tempo_medio_por_destino_s,ciclos_negativos,soma_distancias\n";

    auto totals = std::vector<double>{};
    for (auto run = std::uint32_t{0}; run < options.runs; ++run) {
        auto total = 0.0;
        auto negative = std::uint64_t{0};
        auto sum = Weight{0};
        if (!estimated) {
            const auto start = Clock::now();
            const auto result = graph.all_pairs_bellman_ford(options.threads);
            total = seconds_since(start);
            negative = result.negative_cycle ? 1 : 0;
            // A soma fica fora da medição e mantém o resultado vivo.
            if (!result.negative_cycle) {
                const auto cells = std::size_t{vertices} * vertices;
                for (auto cell = std::size_t{0}; cell < cells; ++cell) {
                    const auto distance = result.distances[cell];
                    sum += distance == cos_graph::no_distance ? 0 : distance;
                }
            }
        } else {
            auto sums = std::vector<Weight>(measured);
            auto cycles = std::vector<std::uint8_t>(measured);
            auto ticket = std::atomic<std::size_t>{0};
            const auto worker = [&] {
                for (auto index = ticket.fetch_add(1); index < measured;
                     index = ticket.fetch_add(1)) {
                    const auto result = graph.bellman_ford(targets[index]);
                    cycles[index] = result.negative_cycle ? 1 : 0;
                    sums[index] = finite_sum(result.distance);
                }
            };
            const auto start = Clock::now();
            {
                auto pool = std::vector<std::jthread>{};
                for (auto id = 1u; id < std::min<std::size_t>(threads, measured); ++id) {
                    pool.emplace_back(worker);
                }
                worker();
            }
            total = seconds_since(start);
            // Soma em ordem de destino: o checksum não depende do número de threads.
            for (auto index = std::size_t{0}; index < measured; ++index) {
                negative += cycles[index];
                sum += sums[index];
            }
        }
        const auto per_target = total / double(measured);
        totals.push_back(total);
        std::cout << run + 1 << ',' << total << ',' << per_target << ',' << negative << ',' << sum
                  << '\n'
                  << std::flush;
    }
    print_stats(statistics(totals), false);
}

} // namespace

int main(int argc, char * argv[])
{
#if defined(__APPLE__)
    // Sem isso o macOS pode rodar o processo nos núcleos de eficiência e os tempos variam 2x.
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
#endif
    try {
        const auto options = parse_options(argc, argv);

        const auto load_start = Clock::now();
        const auto graph = read_graph(options.path, options.direction);
        const auto load_seconds = seconds_since(load_start);

        std::cout << std::setprecision(9) << std::fixed << "[grafo]\n"
                  << "arquivo=" << options.path << '\n'
                  << "representacao=" << (COS_MATRIX ? "matriz" : "csr") << '\n'
                  << "direcionado=" << (graph.directed ? "sim" : "nao") << '\n'
                  << "vertices=" << graph.vertex_count << '\n'
                  << "arestas=" << graph.edge_count << '\n'
                  << "pesos_negativos=" << (graph.negative_weight ? "sim" : "nao") << '\n'
                  << "leitura_s=" << load_seconds << '\n'
                  << "memoria_bytes=" << graph.memory_bytes << '\n'
                  << "pico_rss_apos_leitura_bytes=" << peak_rss_bytes() << '\n'
                  << std::flush;

        run_bellman_ford(graph, options.runs);
        if (options.floyd) {
            run_floyd_warshall(graph, options);
        }
        if (options.all_targets) {
            run_all_targets(graph, options);
        }
        if (options.johnson) {
            run_johnson(graph, options);
        }

        std::cout << "\n[resumo]\npico_rss_bytes=" << peak_rss_bytes() << '\n';
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << "erro: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
