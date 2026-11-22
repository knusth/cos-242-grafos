// Compara o Floyd-Warshall ingênuo (sem blocos, uma thread) com o da biblioteca.
// Uso: fw_variants ARQUIVO THREADS [direcionado|nao_direcionado] [--sem-ingenuo] [--repete N]
// Compilação: c++ -O3 -std=c++20 -I include bench/fw_variants.cpp -o /tmp/fw/fw_variants
#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

using cos_graph::Direction;
using cos_graph::no_distance;
using cos_graph::no_vertex;
using cos_graph::Vertex;
using cos_graph::Weight;
using cos_graph::WeightedEdge;

struct Matrices {
    bool negative_cycle = false;
    std::unique_ptr<Weight[]> distances;
    std::unique_ptr<Vertex[]> parents;
};

// Versão de referência: o laço triplo simples, sem blocos e sem threads, com a mesma
// inicialização e a mesma saída antecipada da biblioteca. O(V³) tempo, 12V² bytes.
Matrices floyd_warshall_ingenuo(Vertex vertices, const std::vector<WeightedEdge> & edges,
                                Direction direction)
{
    const auto count = std::size_t{vertices};
    auto result = Matrices{};
    result.distances = std::make_unique_for_overwrite<Weight[]>(count * count);
    result.parents = std::make_unique_for_overwrite<Vertex[]>(count * count);
    auto * const distance = result.distances.get();
    auto * const parent = result.parents.get();

    std::fill_n(distance, count * count, no_distance);
    std::fill_n(parent, count * count, no_vertex);
    for (std::size_t v = 0; v < count; ++v) {
        distance[v * count + v] = 0;
    }
    const auto add = [&](Vertex from, Vertex to, Weight weight) {
        if (weight < distance[from * count + to]) {
            distance[from * count + to] = weight;
            parent[from * count + to] = from;
        }
    };
    for (const auto & [first, second, weight] : edges) {
        add(first, second, weight);
        if (direction == Direction::undirected) {
            add(second, first, weight);
        }
    }
    for (std::size_t v = 0; v < count; ++v) {
        if (distance[v * count + v] < 0) {
            result.negative_cycle = true;
            return result;
        }
    }

    for (std::size_t k = 0; k < count; ++k) {
        const auto * const through_row = distance + k * count;
        const auto * const through_parent = parent + k * count;
        for (std::size_t from = 0; from < count; ++from) {
            auto * const row = distance + from * count;
            auto * const row_parent = parent + from * count;
            const auto to_k = row[k];
            if (to_k == no_distance) {
                continue;
            }
            for (std::size_t to = 0; to < count; ++to) {
                const auto candidate = to_k + through_row[to];
                const auto better = candidate < row[to];
                row[to] = better ? candidate : row[to];
                row_parent[to] = better ? through_parent[to] : row_parent[to];
            }
            if (row[from] < 0) {
                result.negative_cycle = true;
                return result;
            }
        }
    }
    return result;
}

double seconds_since(std::chrono::steady_clock::time_point start)
{
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

bool close(Weight a, Weight b)
{
    if (a == b) {
        return true; // inclui infinitos iguais
    }
    // Tolerância relativa, com piso absoluto de 1e-9 para valores próximos de zero.
    return std::abs(a - b) <= 1e-9 * std::max({1.0, std::abs(a), std::abs(b)});
}

} // namespace

int main(int argc, char ** argv)
{
    if (argc < 3) {
        std::cerr << "uso: fw_variants ARQUIVO THREADS [direcionado|nao_direcionado] "
                     "[--sem-ingenuo] [--repete N]\n";
        return 2;
    }
    const std::string path = argv[1];
    const auto threads = unsigned(std::atoi(argv[2]));
    auto direction = Direction::directed;
    auto naive = true;
    auto repeat = 1;
    for (auto i = 3; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "nao_direcionado") {
            direction = Direction::undirected;
        } else if (arg == "--sem-ingenuo") {
            naive = false;
        } else if (arg == "--repete" && i + 1 < argc) {
            repeat = std::atoi(argv[++i]);
        }
    }

    auto vertices = Vertex{0};
    auto edges = cos_file::read_triples(path, vertices);
    for (auto & [first, second, weight] : edges) {
        --first;
        --second;
    }
    const cos_graph::Graph graph{vertices, edges, direction};
    const auto count = double(vertices);
    const auto relaxations = count * count * count;
    std::cout << "V=" << vertices << " E=" << edges.size() << " threads=" << threads << '\n';

    auto best = 1e300;
    cos_graph::AllPairsPaths lib;
    for (auto round = 0; round < repeat; ++round) {
        lib = {};
        const auto start = std::chrono::steady_clock::now();
        lib = graph.floyd_warshall(threads);
        const auto elapsed = seconds_since(start);
        best = std::min(best, elapsed);
        std::cout << "biblioteca: " << elapsed << " s, " << relaxations / elapsed / 1e9
                  << " G relaxacoes/s, ciclo negativo=" << lib.negative_cycle << '\n';
    }

    if (naive) {
        const auto start = std::chrono::steady_clock::now();
        const auto ref = floyd_warshall_ingenuo(vertices, edges, direction);
        const auto elapsed = seconds_since(start);
        std::cout << "ingenuo: " << elapsed << " s, " << relaxations / elapsed / 1e9
                  << " G relaxacoes/s, ciclo negativo=" << ref.negative_cycle
                  << ", aceleracao=" << elapsed / best << "x\n";
        if (ref.negative_cycle != lib.negative_cycle) {
            std::cout << "FALHA: ciclo negativo difere\n";
            return 1;
        }
        if (!lib.negative_cycle) {
            const auto total = std::size_t{vertices} * vertices;
            auto max_diff = 0.0;
            auto bad = std::size_t{0};
            for (std::size_t i = 0; i < total; ++i) {
                const auto a = lib.distances[i];
                const auto b = ref.distances[i];
                if (!close(a, b)) {
                    ++bad;
                }
                if (a != b && std::isfinite(a) && std::isfinite(b)) {
                    max_diff = std::max(max_diff, std::abs(a - b));
                }
            }
            std::cout << "matrizes: " << bad << " celulas fora da tolerancia 1e-9, "
                      << "maior diferenca absoluta=" << max_diff << '\n';
            if (bad != 0) {
                return 1;
            }
        }
    }

    if (!lib.negative_cycle) {
        // Peso mínimo por aresta (u, v) para conferir os pais.
        auto minimum = std::unordered_map<std::uint64_t, Weight>{};
        const auto key = [](Vertex a, Vertex b) { return (std::uint64_t{a} << 32) | b; };
        const auto add = [&](Vertex a, Vertex b, Weight w) {
            const auto [it, fresh] = minimum.try_emplace(key(a, b), w);
            if (!fresh) {
                it->second = std::min(it->second, w);
            }
        };
        for (const auto & [first, second, weight] : edges) {
            add(first, second, weight);
            if (direction == Direction::undirected) {
                add(second, first, weight);
            }
        }

        auto failures = std::size_t{0};
        // Todos os pares: d(i, j) = d(i, pai) + w(pai, j).
        for (Vertex from = 0; from < vertices; ++from) {
            for (Vertex to = 0; to < vertices; ++to) {
                if (to == from) {
                    failures += lib.parent(from, to) != no_vertex || lib.distance(from, to) != 0;
                } else if (lib.distance(from, to) == no_distance) {
                    failures += lib.parent(from, to) != no_vertex;
                } else {
                    const auto p = lib.parent(from, to);
                    const auto found = p == no_vertex ? minimum.end() : minimum.find(key(p, to));
                    failures +=
                        found == minimum.end() ||
                        !close(lib.distance(from, to), lib.distance(from, p) + found->second);
                }
            }
        }
        // Percursos completos de 32 origens sorteadas: a soma dos pesos reconstrói a distância.
        auto random = std::mt19937_64{1};
        for (auto sample = 0; sample < 32; ++sample) {
            const auto from = std::uniform_int_distribution<Vertex>{0, vertices - 1}(random);
            for (Vertex to = 0; to < vertices; ++to) {
                if (lib.distance(from, to) == no_distance) {
                    continue;
                }
                auto sum = 0.0;
                auto vertex = to;
                auto steps = std::size_t{0};
                while (vertex != from && steps <= vertices) {
                    const auto p = lib.parent(from, vertex);
                    const auto found =
                        p == no_vertex ? minimum.end() : minimum.find(key(p, vertex));
                    if (found == minimum.end()) {
                        break;
                    }
                    sum += found->second;
                    vertex = p;
                    ++steps;
                }
                failures += vertex != from || !close(sum, lib.distance(from, to));
            }
        }
        std::cout << "pais: " << failures << " falhas\n";
        if (failures != 0) {
            return 1;
        }
    }
    return 0;
}
