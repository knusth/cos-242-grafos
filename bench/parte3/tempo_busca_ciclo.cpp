// Tempo da busca de ciclo em `next` no Bellman-Ford até o destino 100.
// Repete relax_rounds (include/cos/graph.hpp) como bench/contagem_bf.cpp, com uma chave que
// pula a busca de ciclo. Por grafo e repetição mede (a) a réplica completa, (b) a réplica sem
// a busca, (c) o tempo dentro da busca em (a), e a biblioteca para conferir (a). Uma thread.
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
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
using Clock = std::chrono::steady_clock;

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

    double search_s = 0;
    std::uint64_t examined_total = 0, visits_total = 0;

    void run(Vertex target, bool do_search)
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
        search_s = 0; examined_total = 0; visits_total = 0;
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
            const auto t0 = do_search ? Clock::now() : Clock::time_point{};
            const auto first_stamp = stamp + 1;
            if (do_search) for (const auto start : upcoming) {
                const auto walk = ++stamp;
                for (auto v = start; v != no_vertex; v = next[v]) {
                    ++round.visits;
                    if (stamps[v] == walk) { cycle_vertex = v; break; }
                    if (stamps[v] >= first_stamp) break; // já percorrido, sem ciclo
                    stamps[v] = walk;
                }
                if (cycle_vertex != no_vertex) break;
            }
            if (do_search) search_s += std::chrono::duration<double>(Clock::now() - t0).count();
            examined_total += round.examined; visits_total += round.visits;
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


// Profundidade da árvore de `next`: maior número de arestas de um vértice alcançável até o destino.
static std::uint32_t tree_depth(const std::vector<Vertex> & next, const std::vector<Weight> & distance, Vertex target)
{
    const auto n = next.size();
    std::vector<std::uint32_t> d(n, 0);
    std::vector<bool> done(n, false);
    done[target] = true;
    std::vector<Vertex> path;
    std::uint32_t best = 0;
    for (Vertex s = 0; s < n; ++s) {
        if (distance[s] == cos_graph::no_distance || done[s]) continue;
        path.clear();
        auto v = s;
        while (!done[v]) { path.push_back(v); v = next[v]; }
        auto k = d[v];
        for (auto it = path.rbegin(); it != path.rend(); ++it) { d[*it] = ++k; done[*it] = true; }
        best = std::max(best, d[s]);
    }
    return best;
}

int main(int argc, char ** argv)
{
    if (argc < 4 || argc % 2 != 0) {
        std::println(stderr, "uso: tempo_busca_ciclo REPETICOES NOME ARQUIVO [NOME ARQUIVO ...] > tempo_busca_ciclo.json");
        return 2;
    }
    const int reps = std::atoi(argv[1]);
    constexpr auto target = Vertex{100 - 1};
    auto stat = [](const std::vector<double> & v) {
        return std::pair{std::accumulate(v.begin(), v.end(), 0.0) / double(v.size()), *std::ranges::min_element(v)};
    };
    std::print("{{\"destino\":100,\"rodadas_medidas\":{},\"grafos\":[", reps);
    for (int arg = 2; arg < argc; arg += 2) {
        const std::string name = argv[arg], path = argv[arg + 1];
        Vertex n = 0;
        auto edges = cos_file::read_triples(path, n);
        for (auto & [a, b, w] : edges) { --a; --b; }
        const auto g = cos_graph::Graph{n, edges, cos_graph::Direction::directed};
        Replay rp{g, n};
        std::vector<double> full, nosearch, search, lib;
        std::uint64_t examined = 0, visits = 0;
        Vertex count = 0;
        std::uint32_t depth = 0;
        for (int i = 0; i < reps; ++i) {
            auto t0 = Clock::now();
            rp.run(target, true);
            full.push_back(std::chrono::duration<double>(Clock::now() - t0).count());
            search.push_back(rp.search_s);
            examined = rp.examined_total; visits = rp.visits_total; count = rp.count;
            if (rp.negative) { std::println(stderr, "{}: ciclo negativo", name); return 1; }
            if (i == 0) depth = tree_depth(rp.next, rp.distance, target);
            t0 = Clock::now();
            rp.run(target, false);
            nosearch.push_back(std::chrono::duration<double>(Clock::now() - t0).count());
            if (rp.count != count || rp.examined_total != examined) { std::println(stderr, "{}: sem busca diverge", name); return 1; }
            t0 = Clock::now();
            const auto r = g.bellman_ford(target);
            lib.push_back(std::chrono::duration<double>(Clock::now() - t0).count());
            if (r.rounds != count) { std::println(stderr, "{}: rodadas divergem da biblioteca", name); return 1; }
        }
        const auto [fm, fn] = stat(full);
        const auto [nm, nn] = stat(nosearch);
        const auto [sm, sn] = stat(search);
        const auto [lm, ln] = stat(lib);
        std::println(stderr, "{}: rodadas={} profundidade={} arestas={} visitas={} completo={:.3f}/{:.3f} sem_busca={:.3f}/{:.3f} busca={:.3f}/{:.3f} lib={:.3f}/{:.3f} (media/min)",
                     name, count, depth, examined, visits, fm, fn, nm, nn, sm, sn, lm, ln);
        std::print("{}{{\"nome\":\"{}\",\"rodadas\":{},\"profundidade_arvore\":{},\"arestas_examinadas\":{},\"visitas_busca_ciclo\":{},"
                   "\"completo_s\":{{\"media\":{:.4f},\"min\":{:.4f}}},\"sem_busca_s\":{{\"media\":{:.4f},\"min\":{:.4f}}},"
                   "\"busca_s\":{{\"media\":{:.4f},\"min\":{:.4f}}},\"fracao_busca\":{:.4f},"
                   "\"biblioteca_s\":{{\"media\":{:.4f},\"min\":{:.4f}}},"
                   "\"ns_por_aresta_sem_busca\":{:.2f},\"ns_por_visita_busca\":{:.2f}}}",
                   arg > 2 ? "," : "", name, count, depth, examined, visits, fm, fn, nm, nn, sm, sn, sn / fn, lm, ln,
                   nn * 1e9 / double(examined), sn * 1e9 / double(visits));
    }
    std::print("]}}\n");
}
