// Contagem por rodada do Bellman-Ford até o destino 100 e extração do ciclo negativo.
// Repete relax_rounds (include/cos/graph.hpp) com a mesma lista de ativos, a mesma saída
// antecipada e a mesma contagem de rodadas; confere rodadas, distâncias e sucessores com
// Graph::bellman_ford e termina com erro se divergirem.
#include <algorithm>
#include <array>
#include <atomic>
#include <barrier>
#include <bit>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <format>
#include <fstream>
#include <limits>
#include <map>
#include <memory>
#include <numeric>
#include <print>
#include <span>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

#include <cos/file_reader.hpp>
// Acesso aos métodos privados de adjacência, para percorrer os predecessores na mesma ordem
// da biblioteca. Só este programa de bancada faz isso.
#define private public
#include <cos/graph.hpp>
#undef private

using cos_graph::Vertex;
using cos_graph::Weight;
using cos_graph::no_vertex;

struct Round {
    std::uint64_t active, examined, changed, visits;
};

// Réplica de relax_rounds com buffers reutilizáveis. `visits` conta os vértices em que a
// busca de ciclo em `next` entra no laço (inclui o que fecha o ciclo ou encontra um selo).
struct Replay {
    const cos_graph::Graph & g;
    Vertex n;
    std::vector<Weight> distance;
    std::vector<Vertex> next;
    std::vector<std::uint32_t> stamps;
    std::vector<bool> queued;
    std::vector<Vertex> active, upcoming;
    std::vector<Round> rounds;
    std::uint32_t stamp = 0;
    Vertex cycle_vertex = no_vertex;
    bool negative = false;
    Vertex count = 0;

    explicit Replay(const cos_graph::Graph & graph, Vertex vertices)
        : g(graph), n(vertices), distance(vertices), next(vertices), stamps(vertices, 0),
          queued(vertices, false) {}

    void run(Vertex target, bool keep_rounds)
    {
        std::ranges::fill(distance, cos_graph::no_distance);
        std::ranges::fill(next, no_vertex);
        std::ranges::fill(stamps, 0);
        std::ranges::fill(queued, false);
        active.assign(1, target);
        upcoming.clear();
        rounds.clear();
        stamp = 0;
        cycle_vertex = no_vertex;
        negative = false;
        count = 0;
        distance[target] = 0;

        while (!active.empty()) {
            if (count == n) { negative = true; break; }
            ++count;
            auto round = Round{active.size(), 0, 0, 0};
            bool stop = false;
            for (const auto vertex : active) {
                auto position = g.first_predecessor(vertex);
                while (true) {
                    const auto previous = g.next_predecessor(vertex, position);
                    if (previous == no_vertex) break;
                    ++round.examined;
                    const auto candidate = distance[vertex] + g.weight_before_predecessor(vertex, position);
                    if (candidate < distance[previous] - g.tolerance) {
                        if (previous == target) { negative = true; stop = true; break; }
                        distance[previous] = candidate;
                        next[previous] = vertex;
                        if (!queued[previous]) { queued[previous] = true; upcoming.push_back(previous); }
                    }
                }
                if (stop) break;
            }
            if (stop) { rounds.push_back(round); break; }
            round.changed = upcoming.size();
            for (const auto v : upcoming) queued[v] = false;
            // Mesma busca de ciclo em `next` que Graph::has_cycle, guardando o vértice achado.
            const auto first_stamp = stamp + 1;
            for (const auto start : upcoming) {
                const auto walk = ++stamp;
                for (auto v = start; v != no_vertex; v = next[v]) {
                    ++round.visits;
                    if (stamps[v] == walk) { cycle_vertex = v; break; }
                    if (stamps[v] >= first_stamp) break; // já percorrido, sem ciclo
                    stamps[v] = walk;
                }
                if (cycle_vertex != no_vertex) break;
            }
            rounds.push_back(round);
            if (cycle_vertex != no_vertex) { negative = true; break; }
            active.swap(upcoming);
            upcoming.clear();
        }
    }

    std::uint64_t total_examined() const
    {
        std::uint64_t t = 0;
        for (const auto & r : rounds) t += r.examined;
        return t;
    }
    std::uint64_t total_visits() const
    {
        std::uint64_t t = 0;
        for (const auto & r : rounds) t += r.visits;
        return t;
    }
};

struct PerTarget {
    std::uint64_t rounds = 0, examined = 0, visits = 0;
};

int main(int argc, char ** argv)
{
    if (argc < 3 || argc % 2 == 0) {
        std::println(stderr, "uso: contagem_bf NOME ARQUIVO [NOME ARQUIVO ...] > contagens.json");
        return 2;
    }
    constexpr auto target = Vertex{100 - 1};
    std::print("{{\n \"gerado_por\": \"bench/contagem_bf.cpp\",\n \"destino\": 100,\n \"grafos\": [");
    for (int arg = 1; arg < argc; arg += 2) {
        const std::string name = argv[arg], path = argv[arg + 1];
        Vertex n = 0;
        auto edges = cos_file::read_triples(path, n);
        for (auto & [a, b, w] : edges) { --a; --b; }
        const auto g = cos_graph::Graph{n, edges, cos_graph::Direction::directed};

        Replay rp{g, n};
        rp.run(target, true);
        auto & distance = rp.distance;
        auto & next = rp.next;
        auto & rounds = rp.rounds;
        const auto count = rp.count;
        const auto negative = rp.negative;
        const auto cycle_vertex = rp.cycle_vertex;

        // Conferência com a biblioteca.
        const auto lib = g.bellman_ford(target);
        if (lib.rounds != count || lib.negative_cycle != negative) {
            std::println(stderr, "{}: rodadas/ciclo divergem (lib {} {}, aqui {} {})", name,
                         lib.rounds, lib.negative_cycle, count, negative);
            return 1;
        }
        if (!negative) {
            for (Vertex v = 0; v < n; ++v)
                if (lib.distance[v] != distance[v] || lib.next[v] != next[v]) {
                    std::println(stderr, "{}: distância/sucessor diverge em {}", name, v + 1);
                    return 1;
                }
            for (const auto s : {10, 20, 30})
                std::println(stderr, "{} d({},100)={}", name, s, distance[s - 1]);
        }
        std::println(stderr, "{}: rodadas={} ciclo_negativo={}", name, count, negative);

        const auto total = rp.total_examined();
        const auto total_visits = rp.total_visits();
        std::print("{}\n  {{\"nome\": \"{}\", \"vertices\": {}, \"arestas\": {},\n   \"rodadas\": [", arg > 1 ? "," : "",
                   name, n, edges.size());
        for (std::size_t i = 0; i < rounds.size(); ++i)
            std::print("{}{{\"rodada\": {}, \"ativos\": {}, \"arestas_examinadas\": {}, \"mudaram\": {}, \"visitas_busca_ciclo\": {}}}",
                       i ? ",\n    " : "\n    ", i + 1, rounds[i].active, rounds[i].examined, rounds[i].changed,
                       rounds[i].visits);
        std::print("],\n   \"total_arestas_examinadas\": {},\n   \"total_visitas_busca_ciclo\": {},\n   \"ciclo_negativo\": ",
                   total, total_visits);

        if (cycle_vertex == no_vertex) {
            std::print("null");
        } else {
            std::vector<Vertex> cycle{cycle_vertex};
            for (auto v = next[cycle_vertex]; ; v = next[v]) {
                cycle.push_back(v);
                if (v == cycle_vertex) break;
            }
            std::vector<Weight> weights;
            double sum = 0;
            for (std::size_t i = 0; i + 1 < cycle.size(); ++i) {
                // Menor peso entre arestas paralelas u -> v; erro se a aresta não existe.
                auto best = std::numeric_limits<Weight>::infinity();
                for (const auto & [a, b, w] : edges)
                    if (a == cycle[i] && b == cycle[i + 1]) best = std::min(best, w);
                if (best == std::numeric_limits<Weight>::infinity()) {
                    std::println(stderr, "aresta do ciclo ausente no arquivo");
                    return 1;
                }
                weights.push_back(best);
                sum += best;
            }
            if (!(sum < 0)) { std::println(stderr, "soma do ciclo não é negativa"); return 1; }
            std::print("{{\"vertices\": [");
            for (std::size_t i = 0; i < cycle.size(); ++i) std::print("{}{}", i ? ", " : "", cycle[i] + 1);
            std::print("], \"pesos\": [");
            for (std::size_t i = 0; i < weights.size(); ++i) std::print("{}{:.2f}", i ? ", " : "", weights[i]);
            std::print("], \"soma\": {:.2f}}}", sum);
        }
        std::print(",\n   \"todos_os_pares\": ");
        if (negative) {
            std::print("null");
        } else {
            // W_2 (25 000 vértices): todos os destinos; demais: K destinos index * V / K,
            // como em bench/caminhos_bench.cpp.
            const std::uint64_t V = n;
            const std::uint64_t K = n <= 25000 ? V : (n <= 100000 ? 200 : (n <= 1000000 ? 30 : 10));
            auto targets = std::vector<Vertex>(K);
            for (std::uint64_t i = 0; i < K; ++i) targets[i] = Vertex(i * V / K);
            auto per = std::vector<PerTarget>(K);
            auto sums = std::vector<double>(K, 0.0);
            std::atomic<std::uint64_t> cursor{0};
            const auto nthreads = std::max(1u, std::thread::hardware_concurrency());
            {
                auto pool = std::vector<std::jthread>{};
                for (unsigned t = 0; t < nthreads; ++t)
                    pool.emplace_back([&] {
                        Replay r{g, n};
                        for (auto i = cursor.fetch_add(1); i < K; i = cursor.fetch_add(1)) {
                            r.run(targets[i], false);
                            double sum = 0;
                            for (Vertex v = 0; v < n; ++v)
                                if (r.distance[v] != cos_graph::no_distance) sum += r.distance[v];
                            per[i] = {r.count, r.total_examined(), r.total_visits()};
                            sums[i] = r.negative ? std::nan("") : sum;
                        }
                    });
            }
            // Conferência por amostragem contra a biblioteca: rodadas e soma das distâncias.
            for (const auto t : {targets[0], targets[K / 2], targets[K - 1]}) {
                const auto i = std::size_t(std::ranges::find(targets, t) - targets.begin());
                const auto lib = g.bellman_ford(t);
                double sum = 0;
                for (Vertex v = 0; v < n; ++v)
                    if (lib.distance[v] != cos_graph::no_distance) sum += lib.distance[v];
                if (lib.negative_cycle || lib.rounds != per[i].rounds || sum != sums[i]) {
                    std::println(stderr, "{}: destino {} diverge da biblioteca", name, t + 1);
                    return 1;
                }
            }
            std::uint64_t sr = 0, se = 0, sv = 0, mr = 0;
            for (const auto & p : per) {
                sr += p.rounds; se += p.examined; sv += p.visits; mr = std::max(mr, p.rounds);
            }
            const double mean_e = double(se) / K;
            std::print("{{\"destinos\": {}, \"amostra\": {}, \"rodadas_media\": {:.4f}, \"rodadas_max\": {},\n"
                       "    \"arestas_examinadas_media\": {:.2f}, \"arestas_examinadas_total_extrapolado\": {},\n"
                       "    \"visitas_busca_ciclo_media\": {:.2f}, \"passagens_por_E_media\": {:.4f}}}",
                       K, K < V ? "true" : "false", double(sr) / K, mr, mean_e,
                       K == V ? std::to_string(se) : std::format("{:.0f}", mean_e * double(V)),
                       double(sv) / K, mean_e / double(edges.size()));
            std::println(stderr, "{}: todos_os_pares K={} rodadas_media={:.2f} arestas_media={:.0f}", name, K,
                         double(sr) / K, mean_e);
        }
        std::print("\n  }}");
    }
    std::print("\n ]\n}}\n");
}
