#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
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
using cos_graph::Weight;

// Pai e distância de cada vértice na árvore de caminhos mínimos.
using Tree = std::vector<std::pair<Vertex, Weight>>;

// Vértice da biblioteca (base 0) ou no_vertex quando está fora do grafo.
struct Target {
    Vertex vertex;
    std::string label;
};

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

std::vector<std::string> read_names(const std::string & path, Vertex vertex_count)
{
    auto input = std::ifstream{path};
    if (!input) {
        throw std::runtime_error{"não foi possível abrir o arquivo de nomes"};
    }

    // Cada linha tem "indice,nome"; o nome pode conter vírgulas depois da primeira.
    auto names = std::vector<std::string>(vertex_count);
    auto line = std::string{};

    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty()) {
            continue;
        }

        const auto comma = std::min(line.find(','), line.size());
        auto index = Vertex{0};
        const auto [end, error] = std::from_chars(line.data(), line.data() + comma, index);

        if (comma == line.size() || error != std::errc{} || end != line.data() + comma ||
            index == 0 || index > vertex_count) {
            throw std::runtime_error{"o arquivo de nomes contém uma linha inválida"};
        }
        names[index - 1] = line.substr(comma + 1);
    }
    return names;
}

Vertex find_name(std::span<const std::string> names, std::string_view name)
{
    const auto found = std::ranges::find(names, name);
    if (found == names.end()) {
        throw std::runtime_error{"o nome \"" + std::string{name} +
                                 "\" não pertence ao arquivo de nomes"};
    }
    return Vertex(found - names.begin());
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
           << "memoria_bytes=" << graph.memory_bytes << '\n'
           << "pesos_negativos=" << (graph.negative_weight ? "sim" : "nao") << '\n';
}

std::vector<Vertex> path_to(const Tree & tree, Vertex target)
{
    // O(comprimento do caminho): sobe pelos pais e inverte a sequência.
    auto path = std::vector<Vertex>{};
    for (auto vertex = target; vertex != cos_graph::no_vertex; vertex = tree[vertex].first) {
        path.push_back(vertex);
    }
    std::ranges::reverse(path);
    return path;
}

void write_paths(std::ostream & output, const Tree & tree, Vertex source,
                 std::span<const Target> targets, std::span<const std::string> names)
{
    output << "\n[caminhos_minimos]\n"
           << "algoritmo=dijkstra_heap\n"
           << "origem=" << source + 1 << '\n';
    if (!names.empty()) {
        output << "origem_nome=" << names[source] << '\n'
               << "destino,nome,distancia,caminho,caminho_nomes\n";
    } else {
        output << "destino,distancia,caminho\n";
    }

    // 15 algarismos significativos: os pesos da rede de colaboração têm 15 e os dos
    // grafos W, 2 casas decimais; é o máximo que um double preserva em decimal.
    output << std::defaultfloat << std::setprecision(15);

    for (const auto & [target, label] : targets) {
        output << label;
        // Destinos vindos do arquivo de nomes sempre pertencem ao grafo.
        if (!names.empty()) {
            output << ',' << names[target];
        }

        if (target == cos_graph::no_vertex) {
            output << ",fora_do_grafo\n";
            continue;
        }
        if (tree[target].second == cos_graph::no_distance) {
            output << ",inalcancavel\n";
            continue;
        }

        const auto path = path_to(tree, target);
        output << ',' << tree[target].second << ',';

        auto separator = std::string_view{};
        for (const auto vertex : path) {
            output << separator << vertex + 1;
            separator = " ";
        }

        if (!names.empty()) {
            output << ',';
            separator = {};
            for (const auto vertex : path) {
                output << separator << names[vertex];
                separator = " -> ";
            }
        }
        output << '\n';
    }
}

void write_report(std::ostream & output, const Graph & graph, Vertex source,
                  std::span<const Target> targets, std::span<const std::string> names)
{
    write_summary(output, graph);

    auto tree = Tree(graph.vertex_count, {cos_graph::no_vertex, cos_graph::no_distance});
    const auto save = [&](Vertex vertex, Vertex parent, Weight distance) {
        tree[vertex] = {parent, distance};
    };

    try {
        graph.dijkstra<cos_graph::HeapFrontier>(source, save);
    } catch (const std::domain_error & error) {
        // Pesos negativos não são um erro do programa: o relatório registra a limitação.
        output << "\n[caminhos_minimos]\n"
               << "situacao=nao_implementado\n"
               << "mensagem=" << error.what() << '\n';
        return;
    }

    write_paths(output, tree, source, targets, names);
}

} // namespace

int main(int argc, char * argv[])
{
    try {
        if (argc < 3 || argc > 4) {
            throw std::invalid_argument{
                "uso: cos_part2 GRAFO.txt RELATORIO.txt [NOMES.txt]\n"
                "Sem NOMES, a origem é o vértice 10; com NOMES, é Edsger W. Dijkstra."};
        }

        const auto graph = read_graph(argv[1]);
        auto names = std::vector<std::string>{};
        auto source = Vertex{0};
        auto targets = std::vector<Target>{};

        if (argc == 4) {
            constexpr auto researchers = std::array<std::string_view, 5>{
                "Alan M. Turing", "J. B. Kruskal",        "Jon M. Kleinberg",
                "Éva Tardos",     "Daniel R. Figueiredo",
            };

            names = read_names(argv[3], graph.vertex_count);
            source = find_name(names, "Edsger W. Dijkstra");
            for (const auto name : researchers) {
                const auto vertex = find_name(names, name);
                targets.push_back({vertex, std::to_string(vertex + 1)});
            }
        } else {
            constexpr auto destinations =
                std::array{Vertex{20}, Vertex{30}, Vertex{40}, Vertex{50}, Vertex{60}};

            source = Vertex{10} - 1;
            for (const auto destination : destinations) {
                const auto inside = destination <= graph.vertex_count;
                targets.push_back(
                    {inside ? destination - 1 : cos_graph::no_vertex, std::to_string(destination)});
            }
        }

        // Com pesos negativos, o relatório só registra a limitação e não usa a origem.
        if (source >= graph.vertex_count && !graph.negative_weight) {
            throw std::out_of_range{"o vértice de origem não pertence ao grafo"};
        }

        auto output = std::ofstream{argv[2]};
        if (!output) {
            throw std::runtime_error{"não foi possível criar o arquivo de relatório"};
        }

        write_report(output, graph, source, targets, names);
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << "erro: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
