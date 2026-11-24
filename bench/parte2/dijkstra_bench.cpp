#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include <sys/resource.h>
#if defined(__APPLE__)
#include <pthread/qos.h>
#endif

namespace {

using cos_graph::Graph;
using cos_graph::Vertex;
using cos_graph::Weight;
using Clock = std::chrono::steady_clock;

// Soma das distâncias e quantidade de vértices fechados: impede que a busca seja descartada.
struct Checksum {
    Weight distance_sum = 0;
    std::uint64_t reached = 0;
};

template <class Number> Number parse_number(std::string_view text, std::string_view name)
{
    auto value = Number{};
    const auto [end, error] = std::from_chars(text.begin(), text.end(), value);
    if (error != std::errc{} || end != text.end()) {
        throw std::invalid_argument{std::string{name} + " deve ser um inteiro não negativo"};
    }
    return value;
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

Graph read_graph(const std::string & path)
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
    return Graph{vertex_count, edges};
}

template <class Frontier> double timed_dijkstra(const Graph & graph, Vertex source, Checksum & sum)
{
    // Só a chamada de Dijkstra é medida; o visitante acumula a verificação em O(1).
    sum = {};
    const auto start = Clock::now();
    graph.dijkstra<Frontier>(source, [&](Vertex, Vertex, Weight distance) {
        sum.distance_sum += distance;
        ++sum.reached;
    });
    return std::chrono::duration<double>(Clock::now() - start).count();
}

bool same_checksum(const Checksum & heap, const Checksum & vector)
{
    const auto scale = std::max({std::abs(heap.distance_sum), std::abs(vector.distance_sum), 1.0});
    return heap.reached == vector.reached &&
           std::abs(heap.distance_sum - vector.distance_sum) <= 1e-9 * scale;
}

} // namespace

int main(int argc, char * argv[])
{
#if defined(__APPLE__)
    // Sem isso o macOS pode rodar o processo nos núcleos de eficiência e os tempos variam 2x.
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
#endif
    try {
        if (argc != 5) {
            throw std::invalid_argument{"uso: cos_bench2 GRAFO.txt K SEMENTE EXECUCOES_VETOR"};
        }

        const auto runs = parse_number<std::uint32_t>(argv[2], "K");
        const auto seed = parse_number<std::uint64_t>(argv[3], "SEMENTE");
        const auto vector_runs =
            std::min(runs, parse_number<std::uint32_t>(argv[4], "EXECUCOES_VETOR"));

        const auto load_start = Clock::now();
        const auto graph = read_graph(argv[1]);
        const auto load_seconds = std::chrono::duration<double>(Clock::now() - load_start).count();

        std::cout << std::setprecision(6) << std::fixed << "[grafo]\n"
                  << "arquivo=" << argv[1] << '\n'
                  << "representacao=" << (COS_MATRIX ? "matriz" : "csr") << '\n'
                  << "vertices=" << graph.vertex_count << '\n'
                  << "arestas=" << graph.edge_count << '\n'
                  << "pesos_negativos=" << (graph.negative_weight ? "sim" : "nao") << '\n'
                  << "leitura_s=" << load_seconds << '\n'
                  << "memoria_bytes=" << graph.memory_bytes << '\n'
                  << "pico_rss_apos_leitura_bytes=" << peak_rss_bytes() << '\n';

        if (graph.negative_weight || graph.vertex_count == 0) {
            std::cout << "situacao=dijkstra_nao_executado\n";
            return EXIT_SUCCESS;
        }

        auto random = std::mt19937_64{seed};
        auto pick = std::uniform_int_distribution<Vertex>{0, graph.vertex_count - 1};
        auto sources = std::vector<Vertex>(runs);
        for (auto & source : sources) {
            source = pick(random);
        }

        std::cout << "k=" << runs << '\n'
                  << "semente=" << seed << '\n'
                  << "execucoes_vetor=" << vector_runs << '\n'
                  << "\n[execucoes]\n"
                  << "execucao,origem,alcancados,heap_s,vetor_s,soma_distancias,radix_s\n";

        auto mismatches = 0u;
        auto heap_total = 0.0;
        auto vector_total = 0.0;
        auto radix_total = 0.0;

        // K execuções com heap; as primeiras execuções também usam o vetor para conferência.
        for (auto run = std::uint32_t{0}; run < runs; ++run) {
            const auto source = sources[run];
            auto heap = Checksum{};
            const auto heap_seconds = timed_dijkstra<cos_graph::HeapFrontier>(graph, source, heap);
            heap_total += heap_seconds;

            std::cout << run + 1 << ',' << source + 1 << ',' << heap.reached << ',' << heap_seconds
                      << ',';

            if (run < vector_runs) {
                auto vector = Checksum{};
                const auto vector_seconds =
                    timed_dijkstra<cos_graph::VectorFrontier>(graph, source, vector);
                vector_total += vector_seconds;
                std::cout << vector_seconds;

                if (!same_checksum(heap, vector)) {
                    ++mismatches;
                    std::cerr << "ERRO: heap e vetor divergem na origem " << source + 1 << " (heap "
                              << heap.distance_sum << '/' << heap.reached << ", vetor "
                              << vector.distance_sum << '/' << vector.reached << ")\n";
                }
            }
            std::cout << ',' << heap.distance_sum << ',';

            // Fronteira radix em todas as execuções; a soma deve igualar a do heap.
            auto radix = Checksum{};
            const auto radix_seconds = timed_dijkstra<cos_graph::RadixFrontier>(graph, source, radix);
            radix_total += radix_seconds;
            std::cout << radix_seconds << '\n' << std::flush;
            if (!same_checksum(heap, radix)) {
                ++mismatches;
                std::cerr << "ERRO: heap e radix divergem na origem " << source + 1 << " (heap "
                          << heap.distance_sum << '/' << heap.reached << ", radix "
                          << radix.distance_sum << '/' << radix.reached << ")\n";
            }
        }

        std::cout << "\n[resumo]\n"
                  << "heap_total_s=" << heap_total << '\n'
                  << "vetor_total_s=" << vector_total << '\n'
                  << "radix_total_s=" << radix_total << '\n'
                  << "divergencias=" << mismatches << '\n'
                  << "pico_rss_bytes=" << peak_rss_bytes() << '\n';

        return mismatches == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
    } catch (const std::exception & error) {
        std::cerr << "erro: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
