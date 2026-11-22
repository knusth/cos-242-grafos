#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <random>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

using cos_graph::Vertex;
using cos_graph::Weight;
using cos_graph::WeightedEdge;

auto checks = 0u;

void check(bool condition, std::string_view expression)
{
    ++checks;
    if (!condition) {
        throw std::runtime_error{"verificação falhou: " + std::string{expression}};
    }
}

#define CHECK(expression) check((expression), #expression)

constexpr auto edges = std::array{
    cos_graph::Edge{0, 1}, cos_graph::Edge{1, 2}, cos_graph::Edge{2, 0},
    cos_graph::Edge{2, 3}, cos_graph::Edge{4, 5}, cos_graph::Edge{5, 4},
    cos_graph::Edge{4, 4}, cos_graph::Edge{4, 4}, cos_graph::Edge{6, 6},
};

cos_graph::Graph make_graph() { return cos_graph::Graph{8, edges}; }

void test_info()
{
    const auto graph = make_graph();
    CHECK(graph.vertex_count == 8);
    CHECK(graph.edge_count == 9);
    CHECK(graph.min_degree == 0);
    CHECK(graph.max_degree == 6);
    CHECK(std::abs(graph.mean_degree - 2.25) < 1e-12);
    CHECK(std::abs(graph.median_degree - 2.0) < 1e-12);

    constexpr auto storage_bytes =
        COS_MATRIX ? std::uint64_t{8 * 8} : std::uint64_t{(8 + 1 + 2 * edges.size()) * 4};
    CHECK(graph.memory_bytes == sizeof(cos_graph::Graph) + storage_bytes);
}

void test_traversals()
{
    const auto graph = make_graph();
    auto bfs = std::vector<std::pair<cos_graph::Vertex, cos_graph::Vertex>>(
        graph.vertex_count, {cos_graph::no_vertex, cos_graph::no_vertex});
    auto dfs = bfs;

    graph.bfs(0, [&](auto vertex, auto parent, auto level) { bfs[vertex] = {parent, level}; });
    graph.dfs(0, [&](auto vertex, auto parent, auto level) { dfs[vertex] = {parent, level}; });

    constexpr auto bfs_expected = std::array{
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{cos_graph::no_vertex, 0},
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{0, 1},
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{0, 1},
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{2, 2},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
    };
    constexpr auto dfs_expected = std::array{
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{cos_graph::no_vertex, 0},
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{0, 1},
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{1, 2},
        std::pair<cos_graph::Vertex, cos_graph::Vertex>{2, 3},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
        std::pair{cos_graph::no_vertex, cos_graph::no_vertex},
    };
    constexpr auto bfs_level = std::array{
        cos_graph::Vertex{0}, cos_graph::Vertex{1}, cos_graph::Vertex{1}, cos_graph::Vertex{2},
        cos_graph::no_vertex, cos_graph::no_vertex, cos_graph::no_vertex, cos_graph::no_vertex,
    };

    CHECK(std::ranges::equal(bfs, bfs_expected));
    CHECK(std::ranges::equal(dfs, dfs_expected));
    CHECK(std::ranges::equal(graph.distances(0), bfs_level));
}

void test_analysis()
{
    const auto graph = make_graph();
    const auto components = graph.components();

    constexpr auto expected_sizes = std::array{
        std::size_t{4},
        std::size_t{2},
        std::size_t{1},
        std::size_t{1},
    };

    CHECK(graph.diameter() == 2);
    CHECK(components.size() == expected_sizes.size());
    for (auto component = std::size_t{0}; component < components.size(); ++component) {
        CHECK(components[component].size() == expected_sizes[component]);
    }
    CHECK(std::ranges::equal(components.front(), std::array{
                                                     cos_graph::Vertex{0},
                                                     cos_graph::Vertex{1},
                                                     cos_graph::Vertex{2},
                                                     cos_graph::Vertex{3},
                                                 }));
}

void test_matrix_row_boundary()
{
    constexpr auto one_edge = std::array{cos_graph::Edge{2, 3}};
    const cos_graph::Graph graph{4, one_edge};
    auto level = std::vector<cos_graph::Vertex>(graph.vertex_count, cos_graph::no_vertex);
    graph.bfs(0, [&](auto vertex, auto, auto current_level) { level[vertex] = current_level; });
    constexpr auto expected = std::array{
        cos_graph::Vertex{0},
        cos_graph::no_vertex,
        cos_graph::no_vertex,
        cos_graph::no_vertex,
    };
    for (auto vertex = std::size_t{0}; vertex < expected.size(); ++vertex) {
        CHECK(level[vertex] == expected[vertex]);
    }
}

void test_bitmap_word_boundary()
{
    auto path = std::vector<cos_graph::Edge>{};
    for (auto vertex = cos_graph::Vertex{0}; vertex < 69; ++vertex) {
        path.emplace_back(vertex, vertex + 1);
    }

    const cos_graph::Graph graph{70, path};
    CHECK(graph.diameter() == 69);
}

void test_text_adapter()
{
    auto header = std::uint32_t{0};
    const auto pairs = cos_file::read_pairs(COS_FIXTURE, header);
    CHECK(header == 8);
    CHECK(pairs.size() == 9);
    CHECK(pairs.front().first == 1 && pairs.front().second == 2);
}

// Distância e pai de cada vértice produzidos pelo visitante de Dijkstra.
struct ShortestPaths {
    std::vector<Weight> distance;
    std::vector<Vertex> parent;
};

template <class Frontier> ShortestPaths run_dijkstra(const cos_graph::Graph & graph, Vertex source)
{
    auto result = ShortestPaths{std::vector<Weight>(graph.vertex_count, cos_graph::no_distance),
                                std::vector<Vertex>(graph.vertex_count, cos_graph::no_vertex)};
    auto previous = Weight{0};

    graph.dijkstra<Frontier>(source, [&](Vertex vertex, Vertex parent, Weight distance) {
        // Cada vértice é fechado uma vez, em ordem não decrescente de distância.
        check(result.distance[vertex] == cos_graph::no_distance, "vértice fechado duas vezes");
        check(distance >= previous, "distâncias fora de ordem");
        previous = distance;
        result.distance[vertex] = distance;
        result.parent[vertex] = parent;
    });
    return result;
}

bool close(Weight first, Weight second)
{
    if (first == cos_graph::no_distance || second == cos_graph::no_distance) {
        return first == second;
    }
    return std::abs(first - second) <= 1e-9 * std::max({1.0, std::abs(first), std::abs(second)});
}

// Exemplo da Figura 1 do enunciado, já com índices começando em 0.
std::vector<WeightedEdge> figure_edges(Weight weight_3_4)
{
    return {
        {0, 1, 0.1}, {1, 4, 0.2}, {4, 2, 5.0}, {2, 3, weight_3_4}, {3, 4, 2.3}, {0, 4, 1.0},
    };
}

void test_negative_weight()
{
    const auto edges = figure_edges(-9.5);
    const cos_graph::Graph graph{5, edges};
    CHECK(graph.negative_weight);

    auto thrown = false;
    try {
        graph.dijkstra<cos_graph::HeapFrontier>(0, [](Vertex, Vertex, Weight) {});
    } catch (const std::domain_error &) {
        thrown = true;
    }
    CHECK(thrown);

    constexpr auto nan_edge =
        std::array{WeightedEdge{0, 1, std::numeric_limits<Weight>::quiet_NaN()}};
    CHECK(cos_graph::Graph(2, nan_edge).negative_weight);
}

template <class Frontier> void check_figure(const cos_graph::Graph & graph)
{
    const auto paths = run_dijkstra<Frontier>(graph, 0);
    constexpr auto distance = std::array{0.0, 0.1, 5.3, 2.6, 0.3};
    constexpr auto parent =
        std::array{cos_graph::no_vertex, Vertex{0}, Vertex{4}, Vertex{4}, Vertex{1}};

    for (auto vertex = std::size_t{0}; vertex < distance.size(); ++vertex) {
        CHECK(close(paths.distance[vertex], distance[vertex]));
        CHECK(paths.parent[vertex] == parent[vertex]);
    }
}

void test_positive_figure()
{
    const auto edges = figure_edges(9.5);
    const cos_graph::Graph graph{5, edges};
    CHECK(!graph.negative_weight);

    check_figure<cos_graph::VectorFrontier>(graph);
    check_figure<cos_graph::HeapFrontier>(graph);
    check_figure<cos_graph::RadixFrontier>(graph);

    constexpr auto storage_bytes =
        COS_MATRIX ? std::uint64_t{5 * 5 * (1 + sizeof(Weight))}
                   : std::uint64_t{(5 + 1 + 2 * 6) * 4 + 2 * 6 * sizeof(Weight)};
    CHECK(graph.memory_bytes == sizeof(cos_graph::Graph) + storage_bytes);
}

void test_unweighted_dijkstra()
{
    const auto graph = make_graph();
    CHECK(!graph.negative_weight);

    auto thrown = false;
    try {
        graph.dijkstra<cos_graph::VectorFrontier>(0, [](Vertex, Vertex, Weight) {});
    } catch (const std::logic_error &) {
        thrown = true;
    }
    CHECK(thrown);
}

void test_repeated_edge_minimum()
{
    // A matriz guarda o menor peso; a CSR guarda as duas arestas e Dijkstra escolhe a menor.
    constexpr auto repeated = std::array{
        WeightedEdge{0, 1, 5.0},
        WeightedEdge{1, 0, 2.0},
        WeightedEdge{0, 1, 3.0},
        WeightedEdge{1, 1, 0.0},
    };
    const cos_graph::Graph graph{2, repeated};
    CHECK(run_dijkstra<cos_graph::HeapFrontier>(graph, 0).distance[1] == 2.0);
    CHECK(run_dijkstra<cos_graph::VectorFrontier>(graph, 1).distance[0] == 2.0);
    CHECK(run_dijkstra<cos_graph::RadixFrontier>(graph, 0).distance[1] == 2.0);
}

std::vector<Weight> bellman_ford(Vertex vertices, std::span<const WeightedEdge> edges,
                                 Vertex source)
{
    // Referência O(VE) usada apenas nos testes.
    auto distance = std::vector<Weight>(vertices, cos_graph::no_distance);
    distance[source] = 0;

    for (auto round = Vertex{0}; round < vertices; ++round) {
        for (const auto [first, second, weight] : edges) {
            distance[second] = std::min(distance[second], distance[first] + weight);
            distance[first] = std::min(distance[first], distance[second] + weight);
        }
    }
    return distance;
}

void check_tree(const ShortestPaths & paths, std::span<const Weight> expected,
                std::span<const WeightedEdge> edges, Vertex source)
{
    for (auto vertex = Vertex{0}; vertex < expected.size(); ++vertex) {
        CHECK(close(paths.distance[vertex], expected[vertex]));

        const auto parent = paths.parent[vertex];
        if (vertex == source || parent == cos_graph::no_vertex) {
            CHECK(vertex == source || expected[vertex] == cos_graph::no_distance);
            continue;
        }

        // Alguma aresta entre o pai e o vértice explica a distância obtida.
        CHECK(std::ranges::any_of(edges, [&](const WeightedEdge & edge) {
            const auto [first, second, weight] = edge;
            const auto joins =
                (first == parent && second == vertex) || (first == vertex && second == parent);
            return joins && close(paths.distance[vertex], paths.distance[parent] + weight);
        }));
    }
}

void test_random_graphs()
{
    auto random = std::mt19937_64{20261029};

    for (auto round = 0; round < 200; ++round) {
        const auto vertices = std::uniform_int_distribution<Vertex>{1, 40}(random);
        const auto edge_count = std::uniform_int_distribution<std::size_t>{0, 3 * vertices}(random);
        auto pick = std::uniform_int_distribution<Vertex>{0, vertices - 1};
        auto weight = std::uniform_real_distribution<Weight>{0.0, 10.0};

        // Arestas sorteadas incluem laços, repetições, pesos nulos e partes desconexas.
        auto edges = std::vector<WeightedEdge>{};
        for (auto edge = std::size_t{0}; edge < edge_count; ++edge) {
            const auto first = pick(random);
            const auto second = random() % 8 == 0 ? first : pick(random);
            const auto value = random() % 5 == 0 ? 0.0 : weight(random);
            edges.emplace_back(first, second, value);
            if (random() % 6 == 0) {
                edges.emplace_back(second, first, weight(random));
            }
        }

        const cos_graph::Graph graph{vertices, edges};
        const auto source = pick(random);
        const auto expected = bellman_ford(vertices, edges, source);

        check_tree(run_dijkstra<cos_graph::VectorFrontier>(graph, source), expected, edges, source);
        check_tree(run_dijkstra<cos_graph::HeapFrontier>(graph, source), expected, edges, source);
        check_tree(run_dijkstra<cos_graph::RadixFrontier>(graph, source), expected, edges, source);
    }
}


// RadixFrontier isolada: cada extração devolve um vértice de chave mínima entre os vivos,
// com -0.0, reduções de chave, magnitudes muito diferentes, infinito e reutilização.
void test_radix_frontier()
{
    auto random = std::mt19937_64{20261120};
    constexpr auto vertices = Vertex{200};
    auto radix = cos_graph::RadixFrontier{vertices};

    for (auto round = 0; round < 50; ++round) {
        // Simula Dijkstra: chaves novas sempre >= à última extraída.
        auto live = std::vector<Weight>(vertices, cos_graph::no_distance);
        auto last = Weight{0};
        const auto offer = [&](Vertex vertex, Weight key) {
            if (key < live[vertex]) {
                live[vertex] = key;
                radix.push(vertex, key);
            }
        };
        const auto extract = [&] {
            const auto vertex = radix.pop();
            const auto smallest = *std::ranges::min_element(live);
            if (smallest == cos_graph::no_distance) {
                CHECK(vertex == cos_graph::no_vertex);
                return false;
            }
            CHECK(vertex != cos_graph::no_vertex && live[vertex] == smallest);
            CHECK(smallest >= last);
            last = smallest;
            live[vertex] = cos_graph::no_distance;
            return true;
        };

        offer(0, round % 2 == 0 ? -0.0 : 0.0);
        for (auto step = 0; step < 2000; ++step) {
            if (random() % 3 != 0) {
                const auto scale = std::array{1e-12, 1.0, 1e3, 1e12}[random() % 4];
                const auto offset = random() % 4 == 0 ? 0.0 : double(random() % 1000) * scale / 7;
                offer(Vertex(random() % vertices), last + offset);
            }
            if (random() % 2 == 0) {
                extract();
            }
        }
        while (extract()) {
        }
        CHECK(radix.pop() == cos_graph::no_vertex);
    }

    // +infinito é uma chave válida; -0.0 equivale a +0.0.
    auto small = cos_graph::RadixFrontier{3};
    small.push(0, cos_graph::no_distance);
    small.push(1, -0.0);
    small.push(2, 5.0);
    CHECK(small.pop() == 1 && small.pop() == 2 && small.pop() == 0);
    CHECK(small.pop() == cos_graph::no_vertex);
}

template <class Frontier>
void check_levels(const cos_graph::Graph & weighted, std::span<const Vertex> levels, Vertex source)
{
    const auto paths = run_dijkstra<Frontier>(weighted, source);
    for (auto vertex = Vertex{0}; vertex < levels.size(); ++vertex) {
        const auto level = levels[vertex];
        CHECK(paths.distance[vertex] ==
              (level == cos_graph::no_vertex ? cos_graph::no_distance : Weight(level)));
    }
}

void test_unit_weights_match_bfs()
{
    // Com todo peso igual a 1, a ordem de distância é a ordem de nível: Dijkstra vira a BFS.
    auto random = std::mt19937_64{20261030};

    for (auto round = 0; round < 100; ++round) {
        const auto vertices = std::uniform_int_distribution<Vertex>{1, 60}(random);
        auto pick = std::uniform_int_distribution<Vertex>{0, vertices - 1};

        auto pairs = std::vector<cos_graph::Edge>{};
        auto unit = std::vector<WeightedEdge>{};
        for (auto edge = Vertex{0}; edge < 2 * vertices; ++edge) {
            const auto first = pick(random);
            const auto second = pick(random);
            pairs.emplace_back(first, second);
            unit.emplace_back(first, second, 1.0);
        }

        const auto source = pick(random);
        const auto levels = cos_graph::Graph{vertices, pairs}.distances(source);
        const cos_graph::Graph weighted{vertices, unit};
        check_levels<cos_graph::VectorFrontier>(weighted, levels, source);
        check_levels<cos_graph::HeapFrontier>(weighted, levels, source);
        check_levels<cos_graph::RadixFrontier>(weighted, levels, source);
    }
}

std::string write_temporary(std::string_view name, std::string_view content)
{
    const auto path = std::filesystem::temp_directory_path() / name;
    auto output = std::ofstream{path, std::ios::binary};
    output << content;
    return path.string();
}

bool read_fails(std::string_view content, std::size_t block = 1 << 20)
{
    const auto path = write_temporary("cos_tests_invalid.txt", content);
    auto header = std::uint32_t{0};
    try {
        cos_file::read_triples(path, header, block);
    } catch (const std::runtime_error &) {
        return true;
    }
    return false;
}

void test_triple_reader()
{
    auto header = std::uint32_t{0};
    const auto expected = cos_file::read_triples(COS_WEIGHTED_FIXTURE, header);
    CHECK(header == 5);
    CHECK(expected.size() == 8);
    CHECK((expected[3] == std::tuple{3u, 4u, -9.5}));
    CHECK((expected[5] == std::tuple{1u, 5u, 1.000000000000001}));
    CHECK((expected[7] == std::tuple{4u, 1u, 1e-300}));

    // Blocos pequenos obrigam linhas a atravessar o limite do buffer.
    for (const auto block : {std::size_t{24}, std::size_t{29}, std::size_t{64}}) {
        auto other_header = std::uint32_t{0};
        CHECK(cos_file::read_triples(COS_WEIGHTED_FIXTURE, other_header, block) == expected);
        CHECK(other_header == header);
    }

    // Linhas de até 7 bytes cabem num bloco de 8 mesmo sem a quebra de linha.
    const auto short_path =
        write_temporary("cos_tests_short.txt", "3\n1 2 1\n2 3 0.5\n\n3 1 2e1\n1 1 0\n2 3 7");
    auto short_header = std::uint32_t{0};
    const auto short_expected = cos_file::read_triples(short_path, short_header);
    CHECK(short_header == 3 && short_expected.size() == 5);
    CHECK((short_expected[2] == std::tuple{3u, 1u, 20.0}));
    for (const auto block : {std::size_t{8}, std::size_t{13}, std::size_t{64}}) {
        auto other_header = std::uint32_t{0};
        CHECK(cos_file::read_triples(short_path, other_header, block) == short_expected);
    }

    auto crlf_header = std::uint32_t{0};
    const auto crlf = cos_file::read_triples(
        write_temporary("cos_tests_crlf.txt", "2\r\n1 2 0.5\r\n2 1 1.5"), crlf_header, 9);
    CHECK(crlf_header == 2);
    CHECK(crlf.size() == 2);
    CHECK((crlf[1] == std::tuple{2u, 1u, 1.5}));

    CHECK(read_fails(""));
    CHECK(read_fails("x\n"));
    CHECK(read_fails("3\n1 2\n"));
    CHECK(read_fails("3\n1 2 abc\n"));
    CHECK(read_fails("3\n1 2 3 4\n"));
    CHECK(read_fails("3\n1 -2 3\n"));
    CHECK(read_fails("3\n1 2.5 3\n"));
    CHECK(read_fails("3\n1 2 0.123456789\n", 8));
}

using cos_graph::Direction;

constexpr auto inf = cos_graph::no_distance;

// Menor peso entre as arestas de `from` para `to`; sem direção, as arestas valem nos dois
// sentidos. Devolve infinito quando não há aresta.
Weight min_weight(std::span<const WeightedEdge> edges, Vertex from, Vertex to, Direction direction)
{
    auto best = inf;
    for (const auto [first, second, weight] : edges) {
        const auto forward = first == from && second == to;
        const auto backward = direction == Direction::undirected && first == to && second == from;
        if (forward || backward) {
            best = std::min(best, weight);
        }
    }
    return best;
}

// Segue os ponteiros `next` de cada vértice até o destino e confere que a soma dos pesos
// reproduz a distância.
void check_next_walks(const cos_graph::PathsToTarget & paths, std::span<const WeightedEdge> edges,
                      Direction direction, Vertex target)
{
    CHECK(paths.next[target] == cos_graph::no_vertex);
    for (auto start = Vertex{0}; start < paths.distance.size(); ++start) {
        if (paths.distance[start] == inf) {
            CHECK(paths.next[start] == cos_graph::no_vertex);
            continue;
        }

        auto sum = Weight{0};
        auto vertex = start;
        auto steps = std::size_t{0};
        while (vertex != target) {
            const auto following = paths.next[vertex];
            CHECK(following != cos_graph::no_vertex);
            sum += min_weight(edges, vertex, following, direction);
            vertex = following;
            CHECK(++steps <= paths.distance.size());
        }
        CHECK(close(sum, paths.distance[start]));
    }
}

// Segue os pais da árvore de cada origem de volta até ela e confere a soma dos pesos.
void check_parent_walks(const cos_graph::AllPairsPaths & paths,
                        std::span<const WeightedEdge> edges, Direction direction)
{
    const auto count = paths.vertex_count;
    for (auto from = Vertex{0}; from < count; ++from) {
        CHECK(paths.distance(from, from) == 0);
        CHECK(paths.parent(from, from) == cos_graph::no_vertex);

        for (auto to = Vertex{0}; to < count; ++to) {
            if (to == from) {
                continue;
            }
            if (paths.distance(from, to) == inf) {
                CHECK(paths.parent(from, to) == cos_graph::no_vertex);
                continue;
            }

            auto sum = Weight{0};
            auto vertex = to;
            auto steps = Vertex{0};
            while (vertex != from) {
                const auto parent = paths.parent(from, vertex);
                CHECK(parent != cos_graph::no_vertex);
                sum += min_weight(edges, parent, vertex, direction);
                vertex = parent;
                CHECK(++steps <= count);
            }
            CHECK(close(sum, paths.distance(from, to)));
        }
    }
}

void test_directed_semantics()
{
    constexpr auto pairs = std::array{
        cos_graph::Edge{0, 1}, cos_graph::Edge{1, 2}, cos_graph::Edge{2, 0}, cos_graph::Edge{3, 0},
    };
    const cos_graph::Graph directed{4, pairs, Direction::directed};
    const cos_graph::Graph undirected{4, pairs};
    CHECK(directed.directed && !undirected.directed);

    // BFS e DFS só seguem as arestas no sentido da entrada.
    CHECK(std::ranges::equal(directed.distances(0), std::array{Vertex{0}, Vertex{1}, Vertex{2},
                                                               cos_graph::no_vertex}));
    CHECK(std::ranges::equal(directed.distances(3),
                             std::array{Vertex{1}, Vertex{2}, Vertex{3}, Vertex{0}}));
    CHECK(std::ranges::equal(undirected.distances(0),
                             std::array{Vertex{0}, Vertex{1}, Vertex{1}, Vertex{1}}));

    auto parent = std::vector<Vertex>(4, cos_graph::no_vertex);
    directed.dfs(3, [&](Vertex vertex, Vertex from, Vertex) { parent[vertex] = from; });
    CHECK(std::ranges::equal(parent, std::array{Vertex{3}, Vertex{0}, Vertex{1},
                                                cos_graph::no_vertex}));
    auto reached = 0;
    directed.dfs(0, [&](Vertex, Vertex, Vertex) { ++reached; });
    CHECK(reached == 3);

    // Dijkstra: 2 -> 0 custa 0,5 no grafo direcionado e vale nos dois sentidos no outro.
    const auto weighted = std::vector<WeightedEdge>{
        {0, 1, 1.0}, {1, 2, 1.0}, {2, 0, 0.5}, {3, 0, 1.0},
    };
    const cos_graph::Graph weighted_directed{4, weighted, Direction::directed};
    const cos_graph::Graph weighted_undirected{4, weighted};
    const auto from_directed = run_dijkstra<cos_graph::HeapFrontier>(weighted_directed, 0);
    const auto from_undirected = run_dijkstra<cos_graph::HeapFrontier>(weighted_undirected, 0);
    CHECK(close(from_directed.distance[1], 1.0) && close(from_directed.distance[2], 2.0));
    CHECK(from_directed.distance[3] == inf);
    CHECK(close(from_undirected.distance[1], 1.0) && close(from_undirected.distance[2], 0.5));
    CHECK(close(from_undirected.distance[3], 1.0));

    // Memória: a CSR direcionada guarda as listas de saída e de entrada; a matriz não muda.
    constexpr auto V = std::uint64_t{4};
    constexpr auto E = std::uint64_t{4};
    constexpr auto plain = COS_MATRIX ? V * V : 2 * (V + 1) * 4 + 2 * E * 4;
    constexpr auto with_weights = COS_MATRIX ? V * V * (1 + sizeof(Weight))
                                             : 2 * (V + 1) * 4 + 2 * E * 4 + 2 * E * sizeof(Weight);
    CHECK(directed.memory_bytes == sizeof(cos_graph::Graph) + plain);
    CHECK(weighted_directed.memory_bytes == sizeof(cos_graph::Graph) + with_weights);

    // Os graus são totais (entrada mais saída), iguais aos do grafo sem direção.
    const cos_graph::Graph big_directed{8, edges, Direction::directed};
    const auto big_undirected = make_graph();
    CHECK(big_directed.edge_count == big_undirected.edge_count);
    CHECK(big_directed.min_degree == big_undirected.min_degree);
    CHECK(big_directed.max_degree == big_undirected.max_degree);
    CHECK(big_directed.mean_degree == big_undirected.mean_degree);
    CHECK(big_directed.median_degree == big_undirected.median_degree);
}

// Grafo de 7 vértices com pesos negativos e sem ciclo negativo; o vértice 6 só é alcançado.
const std::vector<WeightedEdge> hand_edges = {
    {0, 1, 4.0}, {0, 2, 2.0}, {2, 1, -1.0}, {1, 3, 3.0},
    {2, 3, 6.0}, {3, 4, -2.0}, {5, 0, 1.0}, {4, 6, 1.0},
};

void test_bellman_ford_hand()
{
    const cos_graph::Graph graph{7, hand_edges, Direction::directed};
    const auto paths = graph.bellman_ford(4);
    constexpr auto no = cos_graph::no_vertex;

    CHECK(!paths.negative_cycle);
    CHECK(paths.rounds >= 1 && paths.rounds <= 7);
    constexpr auto distance = std::array{2.0, 1.0, 0.0, -2.0, 0.0, 3.0, inf};
    constexpr auto next = std::array{Vertex{2}, Vertex{3}, Vertex{1}, Vertex{4}, no, Vertex{0}, no};
    for (auto vertex = std::size_t{0}; vertex < 7; ++vertex) {
        CHECK(paths.distance[vertex] == distance[vertex]);
        CHECK(paths.next[vertex] == next[vertex]);
    }
    check_next_walks(paths, hand_edges, Direction::directed, 4);
}

void test_negative_cycles()
{
    // Ciclo 1 <-> 2 de peso -4 que alcança o destino 3.
    const auto reachable = std::vector<WeightedEdge>{
        {0, 1, 1.0}, {1, 2, 1.0}, {2, 1, -5.0}, {2, 3, 1.0}};
    const cos_graph::Graph graph{4, reachable, Direction::directed};
    CHECK(graph.bellman_ford(3).negative_cycle);
    CHECK(graph.floyd_warshall().negative_cycle);
    CHECK(graph.has_negative_cycle());

    // Ciclo 2 <-> 3 negativo, mas que não alcança o destino 1: as distâncias seguem corretas.
    // O vértice 1 alcança o ciclo, o que não importa para as distâncias até 1.
    const auto unreachable = std::vector<WeightedEdge>{
        {0, 1, 1.0}, {1, 2, 1.0}, {2, 3, -1.0}, {3, 2, -1.0}};
    const cos_graph::Graph other{4, unreachable, Direction::directed};
    const auto paths = other.bellman_ford(1);
    CHECK(!paths.negative_cycle);
    CHECK(paths.distance[0] == 1.0 && paths.distance[1] == 0.0);
    CHECK(paths.distance[2] == inf && paths.distance[3] == inf);
    CHECK(other.floyd_warshall().negative_cycle);
    CHECK(other.has_negative_cycle());
    CHECK(other.bellman_ford(2).negative_cycle && other.bellman_ford(3).negative_cycle);

    // Aresta negativa sem direção é um ciclo negativo (ida e volta).
    const auto single = std::vector<WeightedEdge>{{0, 1, -1.0}, {1, 2, 3.0}};
    const cos_graph::Graph undirected{3, single};
    CHECK(undirected.bellman_ford(2).negative_cycle);
    CHECK(undirected.bellman_ford(0).negative_cycle);
    CHECK(undirected.floyd_warshall().negative_cycle);
    CHECK(undirected.has_negative_cycle());
    const cos_graph::Graph one_way{3, single, Direction::directed};
    CHECK(!one_way.has_negative_cycle());
    CHECK(!one_way.bellman_ford(2).negative_cycle);
    CHECK(!one_way.floyd_warshall().negative_cycle);

    // Laço negativo.
    const auto loop = std::vector<WeightedEdge>{{0, 1, 1.0}, {1, 1, -0.5}};
    const cos_graph::Graph looped{2, loop, Direction::directed};
    CHECK(looped.floyd_warshall().negative_cycle);
    CHECK(looped.has_negative_cycle());
    CHECK(looped.bellman_ford(1).negative_cycle);
    CHECK(!looped.bellman_ford(0).negative_cycle);

    // Ciclo negativo de dois vértices perto do destino num grafo de V = 1000: a busca de
    // ciclos em `next` o encontra em poucas rodadas, sem esperar a rodada V.
    constexpr auto count = Vertex{1000};
    auto chain = std::vector<WeightedEdge>{};
    for (auto vertex = Vertex{0}; vertex + 1 < count; ++vertex) {
        chain.emplace_back(vertex, vertex + 1, 1.0);
    }
    chain.emplace_back(count - 2, count - 3, -5.0);
    const cos_graph::Graph large{count, chain, Direction::directed};
    const auto detected = large.bellman_ford(count - 1);
    CHECK(detected.negative_cycle);
    CHECK(detected.rounds <= 10);
    CHECK(large.has_negative_cycle());

    // Sem o ciclo negativo, a mesma cadeia leva V - 1 rodadas de mudanças.
    chain.pop_back();
    const auto clean = cos_graph::Graph{count, chain, Direction::directed}.bellman_ford(count - 1);
    CHECK(!clean.negative_cycle);
    CHECK(clean.rounds == count);
    CHECK(clean.distance[0] == double(count - 1));
    CHECK(!(cos_graph::Graph{count, chain, Direction::directed}.has_negative_cycle()));
}

void test_floyd_warshall_hand()
{
    const cos_graph::Graph graph{7, hand_edges, Direction::directed};
    const auto paths = graph.floyd_warshall();
    CHECK(!paths.negative_cycle && paths.vertex_count == 7);
    CHECK(!graph.has_negative_cycle());

    constexpr auto expected = std::array{
        std::array{0.0, 1.0, 2.0, 4.0, 2.0, inf, 3.0},
        std::array{inf, 0.0, inf, 3.0, 1.0, inf, 2.0},
        std::array{inf, -1.0, 0.0, 2.0, 0.0, inf, 1.0},
        std::array{inf, inf, inf, 0.0, -2.0, inf, -1.0},
        std::array{inf, inf, inf, inf, 0.0, inf, 1.0},
        std::array{1.0, 2.0, 3.0, 5.0, 3.0, 0.0, 4.0},
        std::array{inf, inf, inf, inf, inf, inf, 0.0},
    };
    for (auto from = Vertex{0}; from < 7; ++from) {
        for (auto to = Vertex{0}; to < 7; ++to) {
            CHECK(paths.distance(from, to) == expected[from][to]);
        }
    }
    check_parent_walks(paths, hand_edges, Direction::directed);
}

std::vector<WeightedEdge> random_weighted(std::mt19937_64 & random, Vertex vertices, int low,
                                          int high)
{
    auto pick = std::uniform_int_distribution<Vertex>{0, vertices - 1};
    auto weight = std::uniform_int_distribution<int>{low, high};
    const auto count = std::uniform_int_distribution<std::size_t>{0, 3 * vertices}(random);

    // Inclui laços, arestas repetidas com pesos diferentes e partes desconexas.
    auto result = std::vector<WeightedEdge>{};
    for (auto edge = std::size_t{0}; edge < count; ++edge) {
        const auto first = pick(random);
        const auto second = random() % 8 == 0 ? first : pick(random);
        result.emplace_back(first, second, Weight(weight(random)));
        if (random() % 6 == 0) {
            result.emplace_back(first, second, Weight(weight(random)));
        }
    }
    return result;
}

// Referência O(V·E) usada apenas nos testes: relaxa todas as arestas por V rodadas e acusa
// ciclo negativo se a última ainda mudar algo. Com `target`, calcula as distâncias até ele
// (arestas percorridas ao contrário); sem alvo, parte de todos os vértices com distância 0.
struct Reference {
    std::vector<Weight> distance;
    bool negative_cycle = false;
};

Reference reference_bellman_ford(Vertex vertices, std::span<const WeightedEdge> edges,
                                 Direction direction, Vertex target, bool use_target)
{
    auto result = Reference{std::vector<Weight>(vertices, use_target ? inf : 0.0), false};
    if (use_target) {
        result.distance[target] = 0;
    }
    for (auto round = Vertex{0}; round < vertices; ++round) {
        auto changed = false;
        const auto relax = [&](Vertex from, Vertex to, Weight weight) {
            if (result.distance[to] + weight < result.distance[from]) {
                result.distance[from] = result.distance[to] + weight;
                changed = true;
            }
        };
        for (const auto [first, second, weight] : edges) {
            relax(first, second, weight);
            if (direction == Direction::undirected) {
                relax(second, first, weight);
            }
        }
        result.negative_cycle = changed && round + 1 == vertices;
        if (!changed) {
            break;
        }
    }
    return result;
}

// Bellman-Ford de todos os pares, com 1, 2 e 4 threads: distâncias iguais às do Floyd-Warshall
// (dentro da tolerância), caminhadas por `next` que reproduzem as distâncias, e o mesmo
// resultado independentemente do número de threads. `all` é o Floyd-Warshall do mesmo grafo.
void check_all_pairs_bellman_ford(const cos_graph::Graph & graph,
                                  std::span<const WeightedEdge> edges, Direction direction,
                                  const cos_graph::AllPairsPaths & all)
{
    const auto count = graph.vertex_count;
    const auto total = std::size_t{count} * count;
    auto first = cos_graph::AllPairsToTargets{};
    for (const auto threads : {1u, 2u, 4u}) {
        auto paths = graph.all_pairs_bellman_ford(threads);
        CHECK(paths.vertex_count == count);
        CHECK(!paths.negative_cycle && !all.negative_cycle);
        for (auto to = Vertex{0}; to < count; ++to) {
            CHECK(paths.distance(to, to) == 0);
            CHECK(paths.next(to, to) == cos_graph::no_vertex);
            for (auto from = Vertex{0}; from < count; ++from) {
                CHECK(close(paths.distance(from, to), all.distance(from, to)));
                if (paths.distance(from, to) == inf) {
                    CHECK(paths.next(from, to) == cos_graph::no_vertex);
                    continue;
                }
                auto sum = Weight{0};
                auto vertex = from;
                auto steps = Vertex{0};
                while (vertex != to) {
                    const auto following = paths.next(vertex, to);
                    CHECK(following != cos_graph::no_vertex);
                    sum += min_weight(edges, vertex, following, direction);
                    vertex = following;
                    CHECK(++steps <= count);
                }
                CHECK(close(sum, paths.distance(from, to)));
            }
        }
        if (threads == 1) {
            first = std::move(paths);
        } else {
            CHECK(std::equal(first.distances.get(), first.distances.get() + total,
                             paths.distances.get()));
        }
    }
}

// Johnson com 1, 2 e 4 threads e as duas fronteiras: distâncias iguais às do Floyd-Warshall
// (`all`, dentro da tolerância), caminhadas pelos pais que reproduzem as distâncias e o mesmo
// resultado para qualquer número de threads.
void check_johnson(const cos_graph::Graph & graph, std::span<const WeightedEdge> edges,
                   Direction direction, const cos_graph::AllPairsPaths & all)
{
    const auto count = graph.vertex_count;
    CHECK(!all.negative_cycle);
    auto first = cos_graph::AllPairsPaths{};
    for (const auto threads : {1u, 2u, 4u}) {
        auto paths = graph.johnson(threads);
        const auto radix = graph.johnson<cos_graph::RadixFrontier>(threads);
        CHECK(!paths.negative_cycle && !radix.negative_cycle);
        CHECK(paths.vertex_count == count);
        for (auto from = Vertex{0}; from < count; ++from) {
            for (auto to = Vertex{0}; to < count; ++to) {
                CHECK(close(paths.distance(from, to), all.distance(from, to)));
                CHECK(close(radix.distance(from, to), all.distance(from, to)));
            }
        }
        check_parent_walks(paths, edges, direction);
        check_parent_walks(radix, edges, direction);
        if (threads == 1) {
            first = std::move(paths);
        } else {
            const auto total = std::size_t{count} * count;
            CHECK(std::equal(first.distances.get(), first.distances.get() + total,
                             paths.distances.get()));
            CHECK(std::equal(first.parents.get(), first.parents.get() + total,
                             paths.parents.get()));
        }
    }
}

// Floyd-Warshall com várias threads deve devolver exatamente as mesmas matrizes que com uma
// thread: os blocos de cada fase são disjuntos e só leem blocos já prontos.
void check_threads_agree(const cos_graph::Graph & graph, const cos_graph::AllPairsPaths & single)
{
    for (const auto threads : {2u, 4u}) {
        const auto many = graph.floyd_warshall(threads);
        CHECK(many.negative_cycle == single.negative_cycle);
        if (single.negative_cycle) {
            continue;
        }
        const auto total = std::size_t{single.vertex_count} * single.vertex_count;
        CHECK(std::equal(single.distances.get(), single.distances.get() + total,
                         many.distances.get()));
        CHECK(std::equal(single.parents.get(), single.parents.get() + total, many.parents.get()));
    }
}

// Grafos maiores que um bloco do Floyd-Warshall em blocos, com V múltiplo ou não do bloco e
// com V menor que ele: o caminho 0 -> 1 -> ... -> V-1 obriga as rotas a cruzar os blocos.
// A distância confere com Dijkstra (pesos não negativos), com Bellman-Ford (negativos
// sem ciclo, por potenciais) e a detecção de ciclo negativo, com Bellman-Ford.
void test_floyd_warshall_blocks()
{
    auto random = std::mt19937_64{20261114};

    for (const auto vertices : {Vertex{1}, Vertex{2}, Vertex{63}, Vertex{64}, Vertex{65},
                                Vertex{127}, Vertex{128}, Vertex{129}, Vertex{200}, Vertex{257}}) {
        for (const auto direction : {Direction::directed, Direction::undirected}) {
            auto chain = std::vector<WeightedEdge>{};
            for (auto vertex = Vertex{0}; vertex + 1 < vertices; ++vertex) {
                chain.emplace_back(vertex, vertex + 1, Weight(1 + random() % 9));
            }
            auto weighted = chain;
            auto extra = random_weighted(random, vertices, 0, 10);
            weighted.insert(weighted.end(), extra.begin(), extra.end());

            // Pesos não negativos: confere com Dijkstra de cada origem.
            const cos_graph::Graph graph{vertices, weighted, direction};
            const auto all = graph.floyd_warshall();
            CHECK(!all.negative_cycle);
            check_parent_walks(all, weighted, direction);
            for (auto source = Vertex{0}; source < vertices; source += 3) {
                const auto dijkstra = run_dijkstra<cos_graph::HeapFrontier>(graph, source);
                for (auto to = Vertex{0}; to < vertices; ++to) {
                    CHECK(all.distance(source, to) == dijkstra.distance[to]);
                }
            }
            check_threads_agree(graph, all);

            // Pesos negativos por potenciais, só no grafo direcionado: sem ciclo negativo.
            if (direction == Direction::directed) {
                auto potential = std::vector<Weight>(vertices);
                for (auto & value : potential) {
                    value = Weight(std::uniform_int_distribution<int>{-20, 20}(random));
                }
                auto shifted = weighted;
                for (auto & [first, second, weight] : shifted) {
                    weight += potential[first] - potential[second];
                }
                const cos_graph::Graph shifted_graph{vertices, shifted, direction};
                const auto shifted_all = shifted_graph.floyd_warshall();
                CHECK(!shifted_all.negative_cycle);
                CHECK(!shifted_graph.has_negative_cycle());
                check_parent_walks(shifted_all, shifted, direction);
                for (auto source = Vertex{0}; source < vertices; source += 3) {
                    const auto dijkstra = run_dijkstra<cos_graph::HeapFrontier>(graph, source);
                    for (auto to = Vertex{0}; to < vertices; ++to) {
                        const auto expected =
                            dijkstra.distance[to] == inf
                                ? inf
                                : dijkstra.distance[to] + potential[source] - potential[to];
                        CHECK(shifted_all.distance(source, to) == expected);
                    }
                }
                check_threads_agree(shifted_graph, shifted_all);
                check_johnson(shifted_graph, shifted, direction, shifted_all);
            }

            // Pesos negativos arbitrários: a detecção coincide com Bellman-Ford.
            auto negative = random_weighted(random, vertices, -3, 12);
            negative.insert(negative.end(), chain.begin(), chain.end());
            const cos_graph::Graph negative_graph{vertices, negative, direction};
            const auto negative_all = negative_graph.floyd_warshall();
            CHECK(negative_all.negative_cycle == negative_graph.has_negative_cycle());
            check_threads_agree(negative_graph, negative_all);
            for (const auto threads : {1u, 3u}) {
                CHECK(negative_graph.johnson(threads).negative_cycle ==
                      negative_all.negative_cycle);
            }
            if (!negative_all.negative_cycle) {
                check_johnson(negative_graph, negative, direction, negative_all);
            }
        }

        // Ciclo negativo nos últimos vértices: só aparece na última fase.
        if (vertices >= 3) {
            auto late = std::vector<WeightedEdge>{};
            for (auto vertex = Vertex{0}; vertex + 1 < vertices; ++vertex) {
                late.emplace_back(vertex, vertex + 1, 1.0);
            }
            late.emplace_back(vertices - 1, vertices - 2, -2.0);
            const cos_graph::Graph graph{vertices, late, Direction::directed};
            CHECK(graph.floyd_warshall().negative_cycle);
            CHECK(graph.floyd_warshall(3).negative_cycle);
            CHECK(graph.johnson().negative_cycle && graph.johnson(3).negative_cycle);
        }
    }
}

void test_random_nonnegative()
{
    auto random = std::mt19937_64{20261111};

    for (const auto direction : {Direction::directed, Direction::undirected}) {
        for (auto round = 0; round < 150; ++round) {
            const auto vertices = std::uniform_int_distribution<Vertex>{1, 40}(random);
            const auto weighted = random_weighted(random, vertices, 0, 10);
            const cos_graph::Graph graph{vertices, weighted, direction};

            const auto all = graph.floyd_warshall();
            CHECK(!all.negative_cycle);
            CHECK(!graph.has_negative_cycle());
            check_parent_walks(all, weighted, direction);
            check_threads_agree(graph, all);
            check_all_pairs_bellman_ford(graph, weighted, direction, all);
            check_johnson(graph, weighted, direction, all);

            for (auto source = Vertex{0}; source < vertices; ++source) {
                const auto dijkstra = run_dijkstra<cos_graph::HeapFrontier>(graph, source);
                for (auto to = Vertex{0}; to < vertices; ++to) {
                    CHECK(close(all.distance(source, to), dijkstra.distance[to]));
                }
            }

            for (auto target = Vertex{0}; target < vertices; ++target) {
                const auto paths = graph.bellman_ford(target);
                CHECK(!paths.negative_cycle);
                CHECK(paths.rounds <= vertices);
                for (auto from = Vertex{0}; from < vertices; ++from) {
                    CHECK(close(paths.distance[from], all.distance(from, target)));
                }
                check_next_walks(paths, weighted, direction, target);
            }
        }
    }
}

void test_random_potentials()
{
    // Pesos w' = w + p(u) - p(v) com w >= 0 e p inteiro: negativos, sem ciclo negativo, e
    // d'(s, t) = d(s, t) + p(s) - p(t). Tudo inteiro, então as somas são exatas.
    auto random = std::mt19937_64{20261112};

    for (auto round = 0; round < 200; ++round) {
        const auto vertices = std::uniform_int_distribution<Vertex>{1, 40}(random);
        const auto original = random_weighted(random, vertices, 0, 10);
        auto potential = std::vector<Weight>(vertices);
        for (auto & value : potential) {
            value = Weight(std::uniform_int_distribution<int>{-20, 20}(random));
        }

        auto shifted = original;
        for (auto & [first, second, weight] : shifted) {
            weight += potential[first] - potential[second];
        }

        const cos_graph::Graph base{vertices, original, Direction::directed};
        const cos_graph::Graph graph{vertices, shifted, Direction::directed};
        const auto all = graph.floyd_warshall();
        CHECK(!all.negative_cycle);
        CHECK(!graph.has_negative_cycle());
        check_parent_walks(all, shifted, Direction::directed);
        check_threads_agree(graph, all);
        check_all_pairs_bellman_ford(graph, shifted, Direction::directed, all);
        check_johnson(graph, shifted, Direction::directed, all);

        for (auto source = Vertex{0}; source < vertices; ++source) {
            const auto dijkstra = run_dijkstra<cos_graph::HeapFrontier>(base, source);
            for (auto to = Vertex{0}; to < vertices; ++to) {
                const auto expected = dijkstra.distance[to] == inf
                                          ? inf
                                          : dijkstra.distance[to] + potential[source] - potential[to];
                CHECK(all.distance(source, to) == expected);
            }
        }

        for (auto target = Vertex{0}; target < vertices; ++target) {
            const auto paths = graph.bellman_ford(target);
            CHECK(!paths.negative_cycle);
            for (auto from = Vertex{0}; from < vertices; ++from) {
                CHECK(paths.distance[from] == all.distance(from, target));
            }
            check_next_walks(paths, shifted, Direction::directed, target);
        }
    }
}

void test_random_negative_cycles()
{
    // Pesos negativos arbitrários: a detecção de ciclo negativo deve coincidir com a
    // referência sem otimizações, e as distâncias com a referência quando não há ciclo.
    auto random = std::mt19937_64{20261113};
    auto found = 0;

    for (const auto direction : {Direction::directed, Direction::undirected}) {
        for (auto round = 0; round < 300; ++round) {
            const auto vertices = std::uniform_int_distribution<Vertex>{1, 40}(random);
            const auto weighted = random_weighted(random, vertices, -3, 12);
            const cos_graph::Graph graph{vertices, weighted, direction};

            const auto any = reference_bellman_ford(vertices, weighted, direction, 0, false);
            CHECK(graph.floyd_warshall().negative_cycle == any.negative_cycle);
            CHECK(graph.floyd_warshall(2).negative_cycle == any.negative_cycle);
            CHECK(graph.floyd_warshall(4).negative_cycle == any.negative_cycle);
            CHECK(graph.has_negative_cycle() == any.negative_cycle);
            for (const auto threads : {1u, 2u, 4u}) {
                CHECK(graph.johnson(threads).negative_cycle == any.negative_cycle);
            }
            for (const auto threads : {1u, 2u, 4u}) {
                CHECK(graph.all_pairs_bellman_ford(threads).negative_cycle == any.negative_cycle);
            }

            const auto target = std::uniform_int_distribution<Vertex>{0, vertices - 1}(random);
            const auto expected = reference_bellman_ford(vertices, weighted, direction, target, true);
            const auto paths = graph.bellman_ford(target);
            CHECK(paths.negative_cycle == expected.negative_cycle);
            found += paths.negative_cycle;

            if (!paths.negative_cycle) {
                for (auto from = Vertex{0}; from < vertices; ++from) {
                    CHECK(paths.distance[from] == expected.distance[from]);
                }
                check_next_walks(paths, weighted, direction, target);
            }
        }
    }
    // O sorteio precisa exercitar os dois resultados.
    CHECK(found > 50 && found < 500);
}

// Ciclos de soma decimal exatamente 0 com pesos não inteiros: em ponto flutuante,
// 0,1 + 0,2 - 0,3 e 3,07 - 3,07 somados em outra ordem podem sobrar 1 ulp negativo, e sem a
// tolerância isso vira um ciclo negativo falso. Nenhum grafo abaixo tem ciclo negativo.
void check_no_negative_cycle(Vertex vertices, const std::vector<WeightedEdge> & weighted)
{
    const cos_graph::Graph graph{vertices, weighted, Direction::directed};
    CHECK(!graph.has_negative_cycle());
    for (auto target = Vertex{0}; target < vertices; target += std::max<Vertex>(1, vertices / 7)) {
        const auto paths = graph.bellman_ford(target);
        CHECK(!paths.negative_cycle);
        check_next_walks(paths, weighted, Direction::directed, target);
    }
    const auto all = graph.floyd_warshall();
    CHECK(!all.negative_cycle);
    check_parent_walks(all, weighted, Direction::directed);
    check_threads_agree(graph, all);
    check_all_pairs_bellman_ford(graph, weighted, Direction::directed, all);
    check_johnson(graph, weighted, Direction::directed, all);
}

void test_decimal_zero_cycles()
{
    // Triângulo 0,1 / 0,2 / -0,3 em cada rotação, e um quadrado de pares 3,07 / -3,07 cuja
    // volta soma 3,07 + 0,1 + 0,2 - 3,37 = 0.
    check_no_negative_cycle(3, {{0, 1, 0.1}, {1, 2, 0.2}, {2, 0, -0.3}});
    check_no_negative_cycle(3, {{0, 1, 0.2}, {1, 2, -0.3}, {2, 0, 0.1}});
    check_no_negative_cycle(3, {{0, 1, -0.3}, {1, 2, 0.1}, {2, 0, 0.2}});
    check_no_negative_cycle(4, {{0, 1, 3.07}, {1, 0, -3.07}, {1, 2, 0.1}, {2, 1, -0.1},
                                {2, 3, 0.2}, {3, 2, -0.2}, {3, 0, -3.37}, {0, 3, 3.37}});

    // Grafos de 2 casas decimais com potenciais: pesos não negativos reduzidos, com ciclos
    // longos e curtos de peso reduzido 0, que viram ciclos de soma decimal 0 e pesos negativos.
    auto random = std::mt19937_64{20261115};
    for (const auto vertices : {Vertex{5}, Vertex{64}, Vertex{65}, Vertex{130}, Vertex{200}}) {
        auto potential = std::vector<long>(vertices);
        for (auto & value : potential) {
            value = long(random() % 1001) - 500;
        }
        const auto weight_of = [&](Vertex from, Vertex to, long reduced) {
            return WeightedEdge{from, to, double(reduced + potential[from] - potential[to]) / 100};
        };
        auto weighted = std::vector<WeightedEdge>{};
        // Ciclo geral por todos os vértices, e cada aresta tem um retorno de mesmo peso reduzido.
        for (auto vertex = Vertex{0}; vertex < vertices; ++vertex) {
            const auto next = Vertex((vertex + 1) % vertices);
            weighted.push_back(weight_of(vertex, next, 0));
            weighted.push_back(weight_of(next, vertex, 0));
        }
        for (auto count = vertices * 4; count > 0; --count) {
            const auto from = Vertex(random() % vertices);
            const auto to = Vertex(random() % vertices);
            if (from != to) {
                weighted.push_back(weight_of(from, to, long(random() % 4) * (random() % 2)));
            }
        }
        check_no_negative_cycle(vertices, weighted);
    }
}

// components e diameter só têm sentido sem direção; no grafo direcionado, lançam logic_error.
void test_directed_analysis_throws()
{
    const auto pairs = std::array{cos_graph::Edge{0, 1}, cos_graph::Edge{1, 2}};
    const cos_graph::Graph directed{3, pairs, Direction::directed};
    auto thrown = 0;
    try {
        static_cast<void>(directed.components());
    } catch (const std::logic_error & error) {
        thrown += std::string_view{error.what()}.find("components") != std::string_view::npos;
    }
    try {
        static_cast<void>(directed.diameter());
    } catch (const std::logic_error & error) {
        thrown += std::string_view{error.what()}.find("diameter") != std::string_view::npos;
    }
    CHECK(thrown == 2);

    // Sem direção, continuam funcionando.
    const cos_graph::Graph undirected{3, pairs, Direction::undirected};
    CHECK(undirected.components().size() == 1 && undirected.diameter() == 2);
}

void test_path_edge_cases()
{
    // V = 1, sem arestas.
    const auto none = std::vector<WeightedEdge>{};
    const cos_graph::Graph single{1, none, Direction::directed};
    const auto one = single.bellman_ford(0);
    CHECK(!one.negative_cycle && one.distance[0] == 0 && one.next[0] == cos_graph::no_vertex);
    CHECK(!single.has_negative_cycle());
    const auto one_all = single.floyd_warshall();
    CHECK(!one_all.negative_cycle && one_all.distance(0, 0) == 0);
    // V = 1 e V < threads: as threads em excesso não fazem nada.
    for (const auto threads : {1u, 4u, 64u}) {
        const auto bf_one = single.all_pairs_bellman_ford(threads);
        CHECK(!bf_one.negative_cycle && bf_one.distance(0, 0) == 0);
        CHECK(bf_one.next(0, 0) == cos_graph::no_vertex);

        const auto few = std::vector<WeightedEdge>{{0, 1, 2.0}, {1, 2, -1.0}};
        const cos_graph::Graph three{3, few, Direction::directed};
        const auto bf_three = three.all_pairs_bellman_ford(threads);
        CHECK(!bf_three.negative_cycle);
        CHECK(bf_three.distance(0, 2) == 1.0 && bf_three.next(0, 2) == 1);
        CHECK(bf_three.distance(2, 0) == inf && bf_three.next(2, 0) == cos_graph::no_vertex);

        // Johnson: pesos negativos, potenciais h = (0, -1, 0) e d = d' - h(t) + h(s).
        const auto jo_three = three.johnson(threads);
        CHECK(!jo_three.negative_cycle && jo_three.distance(0, 2) == 1.0);
        CHECK(jo_three.parent(0, 2) == 1 && jo_three.distance(1, 2) == -1.0);
        CHECK(jo_three.distance(2, 0) == inf && jo_three.parent(2, 0) == cos_graph::no_vertex);
        const auto jo_one = single.johnson(threads);
        CHECK(!jo_one.negative_cycle && jo_one.distance(0, 0) == 0);
    }

    // V = 1 com laços: o positivo é ignorado e o negativo é um ciclo negativo.
    const auto positive_loop = std::vector<WeightedEdge>{{0, 0, 2.0}};
    const auto negative_loop = std::vector<WeightedEdge>{{0, 0, -2.0}};
    for (const auto direction : {Direction::directed, Direction::undirected}) {
        const cos_graph::Graph harmless{1, positive_loop, direction};
        CHECK(!harmless.bellman_ford(0).negative_cycle && !harmless.floyd_warshall().negative_cycle);
        const cos_graph::Graph harmful{1, negative_loop, direction};
        CHECK(harmful.bellman_ford(0).negative_cycle && harmful.floyd_warshall().negative_cycle);
        CHECK(harmful.has_negative_cycle() && !harmless.has_negative_cycle());
        CHECK(harmful.all_pairs_bellman_ford(3).negative_cycle);
        CHECK(harmful.johnson(3).negative_cycle && !harmless.johnson(3).negative_cycle);
        CHECK(!harmless.all_pairs_bellman_ford(3).negative_cycle);
    }

    // Destino sem arestas de entrada: só ele tem distância finita.
    const auto outgoing = std::vector<WeightedEdge>{{0, 1, 1.0}, {0, 2, 1.0}};
    const cos_graph::Graph source_only{3, outgoing, Direction::directed};
    const auto isolated = source_only.bellman_ford(0);
    CHECK(!isolated.negative_cycle && isolated.rounds == 1);
    CHECK(isolated.distance[0] == 0 && isolated.distance[1] == inf && isolated.distance[2] == inf);
    CHECK(isolated.next[1] == cos_graph::no_vertex);

    // Arestas repetidas com pesos diferentes: vale a menor, em qualquer sentido.
    const auto repeated = std::vector<WeightedEdge>{{0, 1, 5.0}, {0, 1, 3.0}, {0, 1, 4.0}};
    for (const auto direction : {Direction::directed, Direction::undirected}) {
        const cos_graph::Graph graph{2, repeated, direction};
        CHECK(graph.bellman_ford(1).distance[0] == 3.0);
        CHECK(graph.floyd_warshall().distance(0, 1) == 3.0);
        CHECK(graph.bellman_ford(0).distance[1] == (direction == Direction::directed ? inf : 3.0));
    }
}

} // namespace

int main()
{
    try {
        test_info();
        test_traversals();
        test_analysis();
        test_matrix_row_boundary();
        test_bitmap_word_boundary();
        test_text_adapter();
        test_negative_weight();
        test_positive_figure();
        test_unweighted_dijkstra();
        test_repeated_edge_minimum();
        test_radix_frontier();
        test_random_graphs();
        test_unit_weights_match_bfs();
        test_triple_reader();
        test_directed_semantics();
        test_bellman_ford_hand();
        test_negative_cycles();
        test_floyd_warshall_hand();
        test_random_nonnegative();
        test_random_potentials();
        test_random_negative_cycles();
        test_floyd_warshall_blocks();
        test_decimal_zero_cycles();
        test_path_edge_cases();
        test_directed_analysis_throws();

        std::cout << checks << " verificações passaram\n";
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
