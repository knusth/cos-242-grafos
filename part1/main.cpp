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

cos_graph::Vertex parse_source(std::string_view text)
{
    auto source = cos_graph::Vertex{0};
    const auto [end, error] = std::from_chars(text.begin(), text.end(), source);
    if (error != std::errc{} || end != text.end() || source == 0) {
        throw std::invalid_argument{"ORIGEM inválida"};
    }
    return source - 1;
}

cos_graph::Graph read_graph(const std::string & path)
{
    auto vertex_count = cos_graph::Vertex{0};
    auto edges = cos_file::read_pairs(path, vertex_count);

    // O arquivo usa índices a partir de 1; o grafo usa índices a partir de 0.
    for (auto & [first, second] : edges) {
        --first;
        --second;
    }
    return cos_graph::Graph{vertex_count, edges};
}

void write_graph_info(std::ostream & output, const cos_graph::Graph & graph)
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

void write_traversal(std::ostream & output, std::string_view name, cos_graph::Vertex source,
                     std::span<const std::pair<cos_graph::Vertex, cos_graph::Vertex>> traversal)
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

void write_distances(std::ostream & output, const cos_graph::Graph & graph)
{
    constexpr auto queries = std::array{
        std::pair{cos_graph::Vertex{10}, cos_graph::Vertex{20}},
        std::pair{cos_graph::Vertex{10}, cos_graph::Vertex{30}},
        std::pair{cos_graph::Vertex{20}, cos_graph::Vertex{30}},
    };

    output << "\n[consultas_distancia]\n"
           << "primeiro_vertice,segundo_vertice,distancia\n";

    auto previous_source = cos_graph::no_vertex;
    auto distances = std::vector<cos_graph::Vertex>{};

    for (const auto [first, second] : queries) {
        output << first << ',' << second << ',';

        if (first > graph.vertex_count || second > graph.vertex_count) {
            output << "fora_do_grafo\n";
            continue;
        }

        const auto source = first - 1;
        if (source != previous_source) {
            // Consultas consecutivas com a mesma origem reutilizam uma BFS.
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

void write_components(std::ostream & output,
                      std::span<const std::vector<cos_graph::Vertex>> components)
{
    const auto count = components.size();
    output << "\n[componentes]\n"
           << "quantidade=" << count << '\n'
           << "maior_tamanho=" << components.front().size() << '\n'
           << "menor_tamanho=" << components.back().size() << '\n'
           << "componente,tamanho,vertices\n";

    for (auto component = std::size_t{0}; component < count; ++component) {
        output << component + 1 << ',' << components[component].size() << ',';

        auto separator = std::string_view{};
        for (const auto vertex : components[component]) {
            output << separator << vertex + 1;
            separator = " ";
        }
        output << '\n';
    }
}

void write_report(std::ostream & output, const cos_graph::Graph & graph, cos_graph::Vertex source)
{
    write_graph_info(output, graph);

    auto tree = std::vector<std::pair<cos_graph::Vertex, cos_graph::Vertex>>(
        graph.vertex_count, {cos_graph::no_vertex, cos_graph::no_vertex});
    const auto save = [&](cos_graph::Vertex vertex, cos_graph::Vertex parent,
                          cos_graph::Vertex level) { tree[vertex] = {parent, level}; };

    graph.bfs(source, save);
    write_traversal(output, "bfs", source, tree);

    graph.dfs(source, save);
    write_traversal(output, "dfs", source, tree);

    write_distances(output, graph);
    write_components(output, graph.components());

    output << "\n[diametro]\n"
           << "tipo=exato\n"
           << "valor=" << graph.diameter() << '\n';
}

} // namespace

int main(int argument_count, char ** arguments)
{
    try {
        if (argument_count < 3 || argument_count > 4) {
            throw std::invalid_argument{
                "uso: cos_part1 GRAFO.txt SAIDA.txt [ORIGEM]\n"
                "ORIGEM é um número de vértice iniciado em 1; o padrão é 1."};
        }

        const auto source = argument_count == 4 ? parse_source(arguments[3]) : cos_graph::Vertex{0};
        const auto graph = read_graph(arguments[1]);

        if (source >= graph.vertex_count) {
            throw std::out_of_range{"ORIGEM está fora do grafo"};
        }

        auto output = std::ofstream{arguments[2]};
        if (!output) {
            throw std::runtime_error{"não foi possível abrir o arquivo de saída"};
        }

        write_report(output, graph, source);
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
