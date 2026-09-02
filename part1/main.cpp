#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <array>
#include <charconv>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

using cos_graph::Graph;
using cos_graph::Vertex;

Vertex parse_source(std::string_view text)
{
    auto source = Vertex{0};
    const auto [end, error] = std::from_chars(text.begin(), text.end(), source);

    if (error != std::errc{} || end != text.end() || source == 0) {
        throw std::invalid_argument{"a origem deve ser um inteiro positivo"};
    }
    return source - 1;
}

Graph read_graph(const std::string & path)
{
    auto vertex_count = Vertex{0};
    auto edges = cos_file::read_pairs(path, vertex_count);

    // O arquivo começa em 1; os índices da biblioteca começam em 0.
    for (auto & [first, second] : edges) {
        --first;
        --second;
    }
    return Graph{vertex_count, edges};
}

void write_summary(std::ostream & output, const Graph & graph)
{
    output << "[grafo]\n"
           << "representacao=" << (COS_MATRIX ? "matriz" : "csr") << '\n'
           << "vertices=" << graph.vertex_count << '\n'
           << "arestas=" << graph.edge_count << '\n'
           << "grau_minimo=" << graph.min_degree << '\n'
           << "grau_maximo=" << graph.max_degree << '\n'
           << std::fixed << std::setprecision(6) << "grau_medio=" << graph.mean_degree << '\n'
           << "grau_mediano=" << graph.median_degree << '\n'
           << "memoria_bytes=" << graph.memory_bytes << '\n';
}

void write_traversal(std::ostream & output, std::string_view name, Vertex source,
                     std::span<const std::pair<Vertex, Vertex>> traversal)
{
    output << '\n'
           << '[' << name << "]\n"
           << "origem=" << source + 1 << '\n'
           << "vertice,pai,nivel\n";

    auto vertex = std::size_t{0};
    for (const auto [parent, level] : traversal) {
        output << vertex + 1 << ',';

        if (parent == cos_graph::no_vertex) {
            output << "nenhum,";
        } else {
            output << parent + 1 << ',';
        }

        if (level == cos_graph::no_vertex) {
            output << "nenhum\n";
        } else {
            output << level << '\n';
        }
        ++vertex;
    }
}

void write_distances(std::ostream & output, const Graph & graph)
{
    constexpr auto queries = std::array{
        std::pair{Vertex{10}, Vertex{20}},
        std::pair{Vertex{10}, Vertex{30}},
        std::pair{Vertex{20}, Vertex{30}},
    };

    output << "\n[consultas_distancia]\n"
           << "primeiro_vertice,segundo_vertice,distancia\n";

    auto previous_source = cos_graph::no_vertex;
    auto distances = std::vector<Vertex>{};

    for (const auto [first, second] : queries) {
        output << first << ',' << second << ',';

        if (first > graph.vertex_count || second > graph.vertex_count) {
            output << "fora_do_grafo\n";
            continue;
        }

        const auto source = first - 1;
        if (source != previous_source) {
            // Consultas consecutivas com a mesma origem compartilham uma BFS.
            distances = graph.distances(source);
            previous_source = source;
        }

        const auto distance = distances[second - 1];
        if (distance == cos_graph::no_vertex) {
            output << "inalcancavel\n";
        } else {
            output << distance << '\n';
        }
    }
}

void write_components(std::ostream & output, std::span<const std::vector<Vertex>> components)
{
    output << "\n[componentes]\n"
           << "quantidade=" << components.size() << '\n'
           << "maior_tamanho=" << components.front().size() << '\n'
           << "menor_tamanho=" << components.back().size() << '\n'
           << "componente,tamanho,vertices\n";

    for (auto index = std::size_t{0}; index < components.size(); ++index) {
        output << index + 1 << ',' << components[index].size() << ',';

        auto separator = std::string_view{};
        for (const auto vertex : components[index]) {
            output << separator << vertex + 1;
            separator = " ";
        }
        output << '\n';
    }
}

void write_report(std::ostream & output, const Graph & graph, Vertex source)
{
    write_summary(output, graph);

    auto tree = std::vector<std::pair<Vertex, Vertex>>(
        graph.vertex_count, {cos_graph::no_vertex, cos_graph::no_vertex});
    const auto save = [&](Vertex vertex, Vertex parent, Vertex level) {
        tree[vertex] = {parent, level};
    };

    graph.bfs(source, save);
    write_traversal(output, "bfs", source, tree);

    graph.dfs(source, save);
    write_traversal(output, "dfs", source, tree);

    write_distances(output, graph);

    const auto components = graph.components();
    write_components(output, components);

    output << "\n[diametro]\n"
           << "tipo=exato\n"
           << "valor=" << graph.diameter() << '\n';
}

} // namespace

int main(int argc, char * argv[])
{
    try {
        if (argc < 3 || argc > 4) {
            throw std::invalid_argument{
                "uso: cos_part1 GRAFO.txt RELATORIO.txt [ORIGEM]\n"
                "ORIGEM deve ser um inteiro positivo; quando omitida, vale 1."};
        }

        const auto source = argc == 4 ? parse_source(argv[3]) : Vertex{0};
        const auto graph = read_graph(argv[1]);

        if (source >= graph.vertex_count) {
            throw std::out_of_range{"o vértice de origem não pertence ao grafo"};
        }

        auto output = std::ofstream{argv[2]};
        if (!output) {
            throw std::runtime_error{"não foi possível criar o arquivo de relatório"};
        }

        write_report(output, graph, source);
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << "erro: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
