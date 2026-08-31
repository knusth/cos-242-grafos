#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

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

        std::cout << checks << " verificações passaram\n";
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
