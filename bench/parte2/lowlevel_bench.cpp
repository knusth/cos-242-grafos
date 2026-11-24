// Experimentos de baixo nível que explicam os tempos de Dijkstra:
//   clock               frequência efetiva do núcleo (cadeia de somas dependentes)
//   chase               latência de memória por tamanho do conjunto de trabalho
//   scan                custo por estimativa do pop: biblioteca, 4 acumuladores e SIMD
//   pops G K P SEED     o mesmo custo dentro de Dijkstra, nas primeiras P extrações de K origens
//   order G K SEED      heap com a numeração original, aleatória e em ordem de BFS
//   layout N D K        heap em dois grafos isomorfos: numeração local e aleatória
// Compilado com COS_COUNTERS (alvo cos_counters, exige sudo), mede contadores de hardware:
//   counters G K P SEED  heap completo e P extrações do vetor em K origens do grafo G
//   counters local N D K heap nos dois grafos isomorfos de layout
#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <print>
#include <random>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#if defined(__ARM_NEON)
#include <arm_neon.h>
#endif
#if defined(__APPLE__)
#include <pthread/qos.h>
#endif
#if COS_COUNTERS
#include "kpc.hpp"
#include <filesystem>
#endif

namespace {

using cos_graph::Graph;
using cos_graph::no_distance;
using cos_graph::no_vertex;
using cos_graph::Vertex;
using cos_graph::Weight;
using Clock = std::chrono::steady_clock;
using Triples = std::vector<std::tuple<Vertex, Vertex, Weight>>;

double seconds_since(Clock::time_point start)
{
    return std::chrono::duration<double>(Clock::now() - start).count();
}

template <class Number> Number parse(std::string_view text)
{
    auto value = Number{};
    const auto [end, error] = std::from_chars(text.begin(), text.end(), value);
    if (error != std::errc{} || end != text.end()) {
        throw std::invalid_argument{"argumento inválido: " + std::string{text}};
    }
    return value;
}

// ── fronteiras alternativas (só para medir; a biblioteca segue a aula) ─────────────────────

// O vetor varre blocos; o melhor bloco é varrido de novo para achar o índice.
// Os blocos preservam a regra da biblioteca: entre estimativas iguais, vence o menor índice.
template <class BlockMin> class BlockedVectorFrontier {
  public:
    explicit BlockedVectorFrontier(Vertex vertices) : estimate_(vertices, no_distance) {}

    void push(Vertex vertex, Weight distance) { estimate_[vertex] = distance; }

    Vertex pop()
    {
        const auto * data = estimate_.data();
        const auto size = estimate_.size();
        auto best = no_distance;
        auto best_start = std::size_t{0};

        for (auto start = std::size_t{0}; start < size; start += block) {
            const auto value = BlockMin{}(data + start, std::min(block, size - start));
            if (value < best) {
                best = value;
                best_start = start;
            }
        }
        if (best == no_distance) {
            return no_vertex;
        }

        const auto first = estimate_.begin() + std::ptrdiff_t(best_start);
        const auto found = std::find(first, first + std::ptrdiff_t(std::min(block, size - best_start)), best);
        *found = no_distance;
        return Vertex(found - estimate_.begin());
    }

  private:
    static constexpr auto block = std::size_t{1024};
    std::vector<Weight> estimate_;
};

// Quatro mínimos independentes: as mesmas instruções escalares, sem uma cadeia única.
struct FourChains {
    Weight operator()(const Weight * data, std::size_t count) const
    {
        auto a = no_distance, b = no_distance, c = no_distance, d = no_distance;
        auto index = std::size_t{0};
        for (; index + 4 <= count; index += 4) {
            a = data[index] < a ? data[index] : a;
            b = data[index + 1] < b ? data[index + 1] : b;
            c = data[index + 2] < c ? data[index + 2] : c;
            d = data[index + 3] < d ? data[index + 3] : d;
        }
        for (; index < count; ++index) {
            a = data[index] < a ? data[index] : a;
        }
        return std::min({a, b, c, d});
    }
};

// NEON: quatro registradores de dois doubles, oito estimativas por iteração.
struct Simd {
    Weight operator()(const Weight * data, std::size_t count) const
    {
#if defined(__ARM_NEON)
        auto a = vdupq_n_f64(no_distance), b = a, c = a, d = a;
        auto index = std::size_t{0};
        for (; index + 8 <= count; index += 8) {
            a = vminq_f64(a, vld1q_f64(data + index));
            b = vminq_f64(b, vld1q_f64(data + index + 2));
            c = vminq_f64(c, vld1q_f64(data + index + 4));
            d = vminq_f64(d, vld1q_f64(data + index + 6));
        }
        auto best = vminvq_f64(vminq_f64(vminq_f64(a, b), vminq_f64(c, d)));
        for (; index < count; ++index) {
            best = std::min(best, data[index]);
        }
        return best;
#else
        return FourChains{}(data, count);
#endif
    }
};

using ChainsFrontier = BlockedVectorFrontier<FourChains>;
using SimdFrontier = BlockedVectorFrontier<Simd>;

// Encerra Dijkstra depois de `limit` extrações: o custo de cada pop do vetor não depende
// de quantas já ocorreram, então poucas extrações medem o custo de todas.
template <class Frontier> class Truncated {
  public:
    inline static auto limit = std::uint64_t{0};

    explicit Truncated(Vertex vertices) : frontier_{vertices} {}
    void push(Vertex vertex, Weight distance) { frontier_.push(vertex, distance); }
    Vertex pop() { return popped_++ < limit ? frontier_.pop() : no_vertex; }

  private:
    Frontier frontier_;
    std::uint64_t popped_ = 0;
};

// Conta as operações do heap e o maior tamanho que ele atinge, numa execução à parte,
// fora da medição de tempo.
class CountingHeap {
  public:
    inline static auto pushes = std::uint64_t{0};
    inline static auto pops = std::uint64_t{0};
    inline static auto peak = std::uint64_t{0};

    static void reset() { pushes = pops = peak = 0; }

    explicit CountingHeap(Vertex vertices) : heap_{vertices}, queued_(vertices, false) {}
    void push(Vertex vertex, Weight distance)
    {
        ++pushes;
        if (!queued_[vertex]) {
            queued_[vertex] = true;
            peak = std::max(peak, ++size_);
        }
        heap_.push(vertex, distance);
    }
    Vertex pop()
    {
        const auto vertex = heap_.pop();
        if (vertex != cos_graph::no_vertex) {
            ++pops;
            --size_;
        }
        return vertex;
    }

  private:
    cos_graph::HeapFrontier heap_;
    std::vector<bool> queued_;
    std::uint64_t size_ = 0;
};

// ── grafos ────────────────────────────────────────────────────────────────────────────────

Triples read_edges(const std::string & path, Vertex & vertices)
{
    auto edges = cos_file::read_triples(path, vertices);
    for (auto & [first, second, weight] : edges) {
        if (first == 0 || second == 0 || first > vertices || second > vertices) {
            throw std::out_of_range{"uma aresta usa um vértice fora do intervalo do cabeçalho"};
        }
        --first;
        --second;
    }
    return edges;
}

// As mesmas origens de dijkstra_bench: as K primeiras da sequência da semente.
std::vector<Vertex> pick_sources(Vertex vertices, std::uint32_t count, std::uint64_t seed)
{
    auto random = std::mt19937_64{seed};
    auto pick = std::uniform_int_distribution<Vertex>{0, vertices - 1};
    auto sources = std::vector<Vertex>(count);
    for (auto & source : sources) {
        source = pick(random);
    }
    return sources;
}

struct Run {
    double seconds;
    Weight distance_sum;
    std::uint64_t reached;
};

template <class Frontier> Run timed(const Graph & graph, Vertex source)
{
    auto run = Run{0, 0, 0};
    const auto start = Clock::now();
    graph.dijkstra<Frontier>(source, [&](Vertex, Vertex, Weight distance) {
        run.distance_sum += distance;
        ++run.reached;
    });
    run.seconds = seconds_since(start);
    return run;
}

// Nova numeração: label[v] é o novo índice de v.
std::vector<Vertex> random_order(Vertex vertices, std::uint64_t seed)
{
    auto label = std::vector<Vertex>(vertices);
    std::iota(label.begin(), label.end(), Vertex{0});
    std::ranges::shuffle(label, std::mt19937_64{seed});
    return label;
}

std::vector<Vertex> bfs_order(const Graph & graph)
{
    // Vértices numerados na ordem de descoberta; cada componente segue a anterior.
    auto label = std::vector<Vertex>(graph.vertex_count, no_vertex);
    auto next = Vertex{0};
    for (auto start = Vertex{0}; start < graph.vertex_count; ++start) {
        if (label[start] == no_vertex) {
            graph.bfs(start, [&](Vertex vertex, Vertex, Vertex) {
                if (label[vertex] == no_vertex) {
                    label[vertex] = next++;
                }
            });
        }
    }
    return label;
}

Graph relabeled(Vertex vertices, Triples edges, std::span<const Vertex> label)
{
    for (auto & [first, second, weight] : edges) {
        first = label[first];
        second = label[second];
    }
    return Graph{vertices, edges};
}

// Distância média entre os índices das pontas, em fração de n: mede a localidade.
double mean_gap(const Triples & edges, Vertex vertices, std::span<const Vertex> label)
{
    auto sum = 0.0;
    for (const auto & [first, second, weight] : edges) {
        const auto a = label.empty() ? first : label[first];
        const auto b = label.empty() ? second : label[second];
        sum += a > b ? a - b : b - a;
    }
    return sum / double(edges.size()) / vertices;
}

// ── experimentos ──────────────────────────────────────────────────────────────────────────

void measure_clock()
{
#if defined(__aarch64__)
    // Oito somas dependentes por iteração: oito ciclos; subs e b.ne correm em paralelo.
    constexpr auto iterations = std::uint64_t{500'000'000};
    auto value = std::uint64_t{0};
    auto remaining = iterations;
    const auto start = Clock::now();
    asm volatile("1:\n"
                 "add %0, %0, #1\n add %0, %0, #1\n add %0, %0, #1\n add %0, %0, #1\n"
                 "add %0, %0, #1\n add %0, %0, #1\n add %0, %0, #1\n add %0, %0, #1\n"
                 "subs %1, %1, #1\n"
                 "b.ne 1b\n"
                 : "+r"(value), "+r"(remaining));
    std::println("[clock]\nghz={:.3f}", 8.0 * iterations / seconds_since(start) / 1e9);
#else
    std::println("[clock]\nghz=nan");
#endif
}

void measure_chase()
{
    // Cada linha de cache aponta para a próxima de um ciclo aleatório (Sattolo):
    // toda carga depende da anterior e o prefetcher não adivinha o endereço.
    struct alignas(64) Line {
        Line * next;
    };
    std::println("[chase]\nbytes,ns_por_carga");
    for (auto bytes = std::size_t{16} << 10; bytes <= std::size_t{2} << 30; bytes *= 2) {
        for (const auto scale : {1.0, 1.5}) {
            const auto lines = std::size_t(double(bytes) * scale) / sizeof(Line);
            if (lines * sizeof(Line) > (std::size_t{2} << 30)) {
                continue;
            }
            auto memory = std::vector<Line>(lines);
            auto order = std::vector<std::uint32_t>(lines);
            std::iota(order.begin(), order.end(), 0u);
            auto random = std::mt19937_64{lines};
            for (auto i = lines - 1; i > 0; --i) {
                std::swap(order[i], order[std::uniform_int_distribution<std::size_t>{0, i - 1}(random)]);
            }
            for (auto i = std::size_t{0}; i < lines; ++i) {
                memory[i].next = &memory[order[i]];
            }

            constexpr auto loads = std::size_t{20'000'000};
            auto * cursor = &memory[0];
            for (auto i = std::size_t{0}; i < std::min(lines, loads); ++i) {
                cursor = cursor->next; // aquece a TLB e os caches
            }
            const auto start = Clock::now();
            for (auto i = std::size_t{0}; i < loads; ++i) {
                cursor = cursor->next;
            }
            const auto elapsed = seconds_since(start);
            asm volatile("" ::"r"(cursor));
            std::println("{},{:.3f}", lines * sizeof(Line), elapsed / loads * 1e9);
        }
    }
}

// ns por estimativa examinada: P extrações de um vetor com n estimativas finitas.
template <class Frontier> double scan_cost(Vertex vertices)
{
    auto frontier = Frontier{vertices};
    auto random = std::mt19937_64{vertices};
    auto value = std::uniform_real_distribution<Weight>{0, 1000};
    for (auto vertex = Vertex{0}; vertex < vertices; ++vertex) {
        frontier.push(vertex, value(random));
    }
    // Cerca de 2·10⁹ estimativas examinadas, ao menos três extrações.
    const auto pops = std::max<std::uint64_t>(3, std::min<std::uint64_t>(vertices, 2'000'000'000 / vertices));
    auto checksum = Vertex{0};
    const auto start = Clock::now();
    for (auto pop = std::uint64_t{0}; pop < pops; ++pop) {
        checksum ^= frontier.pop();
    }
    const auto elapsed = seconds_since(start);
    asm volatile("" ::"r"(checksum));
    return elapsed / double(pops) / vertices * 1e9;
}

void measure_scan()
{
    std::println("[scan]\nn,biblioteca_ns,quatro_cadeias_ns,simd_ns");
    for (const auto vertices : {1'000u, 3'000u, 10'000u, 30'000u, 100'000u, 300'000u, 1'000'000u,
                                3'000'000u, 10'000'000u, 30'000'000u, 50'000'000u}) {
        std::println("{},{:.4f},{:.4f},{:.4f}", vertices, scan_cost<cos_graph::VectorFrontier>(vertices),
                     scan_cost<ChainsFrontier>(vertices), scan_cost<SimdFrontier>(vertices));
    }
}

// As três fronteiras de vetor devolvem a mesma sequência de vértices.
void check_frontiers()
{
    constexpr auto vertices = Vertex{5'000};
    auto library = cos_graph::VectorFrontier{vertices};
    auto chains = ChainsFrontier{vertices};
    auto simd = SimdFrontier{vertices};
    auto random = std::mt19937_64{7};
    auto value = std::uniform_int_distribution<int>{0, 50}; // muitos empates de propósito
    for (auto vertex = Vertex{0}; vertex < vertices; vertex += 3) {
        const auto distance = Weight(value(random));
        library.push(vertex, distance);
        chains.push(vertex, distance);
        simd.push(vertex, distance);
    }
    while (true) {
        const auto expected = library.pop();
        if (chains.pop() != expected || simd.pop() != expected) {
            throw std::logic_error{"as fronteiras de vetor divergem"};
        }
        if (expected == no_vertex) {
            break;
        }
    }
}

template <class Frontier>
void report_pops(std::string_view name, const Graph & graph, std::span<const Vertex> sources,
                 std::uint64_t limit)
{
    Truncated<Frontier>::limit = limit;
    for (const auto source : sources) {
        const auto run = timed<Truncated<Frontier>>(graph, source);
        std::println("{},{},{},{:.6f},{:.4f}", name, source + 1, run.reached, run.seconds,
                     run.seconds / double(run.reached) / graph.vertex_count * 1e9);
    }
}

void measure_pops(const std::string & path, std::uint32_t count, std::uint64_t limit,
                  std::uint64_t seed)
{
    auto vertices = Vertex{0};
    const auto edges = read_edges(path, vertices);
    const auto graph = Graph{vertices, edges};
    const auto sources = pick_sources(vertices, count, seed);

    std::println("[pops]\narquivo={}\nvertices={}\narestas={}\nlimite={}\n"
                 "fronteira,origem,extracoes,s,ns_por_estimativa",
                 path, graph.vertex_count, graph.edge_count, limit);
    report_pops<cos_graph::VectorFrontier>("biblioteca", graph, sources, limit);
    report_pops<ChainsFrontier>("quatro_cadeias", graph, sources, limit);
    report_pops<SimdFrontier>("simd", graph, sources, limit);

    // Execução completa com as três fronteiras no W_3: confere distâncias contra o heap.
    if (limit >= vertices) {
        for (const auto source : sources) {
            const auto heap = timed<cos_graph::HeapFrontier>(graph, source);
            const auto simd = timed<SimdFrontier>(graph, source);
            if (heap.reached != simd.reached ||
                std::abs(heap.distance_sum - simd.distance_sum) > 1e-9 * heap.distance_sum) {
                throw std::logic_error{"SIMD e heap divergem"};
            }
        }
        std::println("conferencia_simd_heap=ok");
    }
}

void report_order(std::string_view name, const Graph & graph, std::span<const Vertex> sources,
                  std::span<const Vertex> label, double gap)
{
    for (const auto source : sources) {
        const auto mapped = label.empty() ? source : label[source];
        const auto run = timed<cos_graph::HeapFrontier>(graph, mapped);
        std::println("{},{},{:.4f},{},{:.6f},{:.6f}", name, source + 1, gap, run.reached,
                     run.seconds, run.distance_sum);
    }
}

void measure_order(const std::string & path, std::uint32_t count, std::uint64_t seed)
{
    auto vertices = Vertex{0};
    const auto edges = read_edges(path, vertices);
    const auto sources = pick_sources(vertices, count, seed);

    auto bfs_label = std::vector<Vertex>{};
    {
        const auto graph = Graph{vertices, edges};
        CountingHeap::reset();
        graph.dijkstra<CountingHeap>(sources.front(), [](Vertex, Vertex, Weight) {});
        std::println("[ordem]\narquivo={}\nvertices={}\narestas={}\npushes={}\npops={}\npico_heap={}\n"
                     "numeracao,origem,distancia_media_indices,alcancados,s,soma_distancias",
                     path, vertices, graph.edge_count, CountingHeap::pushes, CountingHeap::pops,
                     CountingHeap::peak);
        report_order("original", graph, sources, {}, mean_gap(edges, vertices, {}));
        bfs_label = bfs_order(graph);
    }
    {
        const auto label = random_order(vertices, seed);
        const auto graph = relabeled(vertices, edges, label);
        report_order("aleatoria", graph, sources, label, mean_gap(edges, vertices, label));
    }
    const auto graph = relabeled(vertices, edges, bfs_label);
    report_order("bfs", graph, sources, bfs_label, mean_gap(edges, vertices, bfs_label));
}

// Cada vértice liga-se a d/2 vértices escolhidos entre os 64 seguintes (em anel):
// vizinhos têm índices próximos, e o grafo é conexo com alta probabilidade.
Triples local_graph(Vertex vertices, std::uint32_t degree, std::uint64_t seed)
{
    auto random = std::mt19937_64{seed};
    auto step = std::uniform_int_distribution<Vertex>{1, 64};
    auto weight = std::uniform_real_distribution<Weight>{0, 1};
    auto edges = Triples{};
    edges.reserve(std::size_t{vertices} * degree / 2);
    for (auto vertex = Vertex{0}; vertex < vertices; ++vertex) {
        for (auto edge = 0u; edge < degree / 2; ++edge) {
            edges.emplace_back(vertex, Vertex((std::uint64_t{vertex} + step(random)) % vertices),
                               weight(random));
        }
    }
    return edges;
}

void report_layout(std::string_view name, const Graph & graph, std::span<const Vertex> sources,
                   std::span<const Vertex> label)
{
    const auto operations = double(graph.vertex_count + graph.edge_count) *
                            std::log2(double(graph.vertex_count));
    CountingHeap::reset();
    graph.dijkstra<CountingHeap>(label.empty() ? sources.front() : label[sources.front()],
                                 [](Vertex, Vertex, Weight) {});
    std::println("# {} {}: pushes={} pops={} pico_heap={}", graph.vertex_count, name,
                 CountingHeap::pushes, CountingHeap::pops, CountingHeap::peak);
    for (const auto source : sources) {
        const auto run = timed<cos_graph::HeapFrontier>(graph, label.empty() ? source : label[source]);
        std::println("{},{},{},{},{:.6f},{:.4f},{:.6f}", graph.vertex_count, graph.edge_count, name,
                     run.reached, run.seconds, run.seconds / operations * 1e9, run.distance_sum);
    }
}

// Os dois grafos são isomorfos: mesmas operações do heap, só os endereços mudam.
void measure_layout(Vertex vertices, std::uint32_t degree, std::uint32_t count)
{
    auto edges = local_graph(vertices, degree, vertices);
    const auto sources = pick_sources(vertices, count, 2026);
    {
        const auto graph = Graph{vertices, edges};
        report_layout("local", graph, sources, {});
    }
    const auto label = random_order(vertices, 2026);
    for (auto & [first, second, weight] : edges) {
        first = label[first];
        second = label[second];
    }
    const auto graph = Graph{vertices, edges};
    edges = {};
    report_layout("aleatoria", graph, sources, label);
}

#if COS_COUNTERS
// ── contadores de hardware ────────────────────────────────────────────────────────────────

// Não há evento de falta no L2 nestes processadores; a espera por uma falta no L1 inclui o
// tempo de buscar o dado no L2 ou na memória.
const auto counter_events = std::vector<std::string>{
    "FIXED_CYCLES", "FIXED_INSTRUCTIONS", "INST_LDST", "L1D_CACHE_MISS_LD_NONSPEC",
    "L1D_TLB_MISS_NONSPEC", "L2_TLB_MISS_DATA", "LDST_UNIT_OLD_L1D_CACHE_MISS"};

void counters_header()
{
    std::println("[contadores]\ngrafo,numeracao,fronteira,vertices,arestas,extracoes,ciclos,"
                 "instrucoes,acessos_memoria,faltas_l1d,faltas_tlb_l1d,faltas_tlb_l2,ciclos_espera_l1d");
}

template <class Frontier>
void report_counters(cos_kpc::Counters & counters, std::string_view graph_name,
                     std::string_view labeling, std::string_view frontier, const Graph & graph,
                     Vertex source)
{
    auto popped = std::uint64_t{0};
    const auto before = counters.read();
    graph.dijkstra<Frontier>(source, [&](Vertex, Vertex, Weight) { ++popped; });
    const auto after = counters.read();
    std::print("{},{},{},{},{},{}", graph_name, labeling, frontier, graph.vertex_count,
               graph.edge_count, popped);
    for (auto index = std::size_t{0}; index < after.size(); ++index) {
        std::print(",{}", after[index] - before[index]);
    }
    std::println();
}

void measure_counters(const std::string & path, std::uint32_t count, std::uint64_t limit,
                      std::uint64_t seed)
{
    auto vertices = Vertex{0};
    const auto edges = read_edges(path, vertices);
    const auto graph = Graph{vertices, edges};
    const auto sources = pick_sources(vertices, count, seed);
    const auto name = std::filesystem::path{path}.stem().string();
    auto counters = cos_kpc::Counters{counter_events};
    Truncated<cos_graph::VectorFrontier>::limit = limit;
    for (const auto source : sources) {
        report_counters<cos_graph::HeapFrontier>(counters, name, "original", "heap", graph, source);
        report_counters<Truncated<cos_graph::VectorFrontier>>(counters, name, "original", "vetor",
                                                              graph, source);
    }
}

void measure_counters_layout(Vertex vertices, std::uint32_t degree, std::uint32_t count)
{
    auto edges = local_graph(vertices, degree, vertices);
    const auto sources = pick_sources(vertices, count, 2026);
    const auto name = "local_" + std::to_string(vertices);
    auto counters = cos_kpc::Counters{counter_events};
    {
        const auto graph = Graph{vertices, edges};
        for (const auto source : sources) {
            report_counters<cos_graph::HeapFrontier>(counters, name, "local", "heap", graph, source);
        }
    }
    const auto label = random_order(vertices, 2026);
    const auto graph = relabeled(vertices, std::move(edges), label);
    for (const auto source : sources) {
        report_counters<cos_graph::HeapFrontier>(counters, name, "aleatoria", "heap", graph,
                                                 label[source]);
    }
}
#endif

} // namespace

int main(int argc, char * argv[])
{
#if defined(__APPLE__)
    // Sem isso o macOS pode rodar o processo nos núcleos de eficiência e os tempos variam 2x.
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
#endif
    try {
        const auto mode = std::string_view{argc > 1 ? argv[1] : ""};
        if (mode == "clock" && argc == 2) {
            measure_clock();
        } else if (mode == "chase" && argc == 2) {
            measure_chase();
        } else if (mode == "scan" && argc == 2) {
            check_frontiers();
            measure_scan();
        } else if (mode == "pops" && argc == 6) {
            check_frontiers();
            measure_pops(argv[2], parse<std::uint32_t>(argv[3]), parse<std::uint64_t>(argv[4]),
                         parse<std::uint64_t>(argv[5]));
        } else if (mode == "order" && argc == 5) {
            measure_order(argv[2], parse<std::uint32_t>(argv[3]), parse<std::uint64_t>(argv[4]));
        } else if (mode == "layout" && argc == 5) {
            if (argv[2] == std::string_view{"cabecalho"}) {
                std::println("[layout]\nvertices,arestas,numeracao,alcancados,s,ns_por_op,soma_distancias");
                return EXIT_SUCCESS;
            }
            measure_layout(parse<Vertex>(argv[2]), parse<std::uint32_t>(argv[3]),
                           parse<std::uint32_t>(argv[4]));
#if COS_COUNTERS
        } else if (mode == "counters" && argc == 3 && argv[2] == std::string_view{"cabecalho"}) {
            counters_header();
        } else if (mode == "counters" && argc == 6 && argv[2] == std::string_view{"local"}) {
            measure_counters_layout(parse<Vertex>(argv[3]), parse<std::uint32_t>(argv[4]),
                                    parse<std::uint32_t>(argv[5]));
        } else if (mode == "counters" && argc == 6) {
            measure_counters(argv[2], parse<std::uint32_t>(argv[3]), parse<std::uint64_t>(argv[4]),
                             parse<std::uint64_t>(argv[5]));
#endif
        } else {
            throw std::invalid_argument{"uso: cos_lowlevel clock | chase | scan | "
                                        "pops GRAFO K EXTRACOES SEMENTE | order GRAFO K SEMENTE | "
                                        "layout N GRAU K"};
        }
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << "erro: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
