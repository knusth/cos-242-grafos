#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

namespace {

using cos_graph::AllPairsPaths;
using cos_graph::Direction;
using cos_graph::Graph;
using cos_graph::PathsToTarget;
using cos_graph::Vertex;
using cos_graph::Weight;

constexpr auto bellman_target = Vertex{100};
constexpr auto bellman_sources = std::array{Vertex{10}, Vertex{20}, Vertex{30}};
constexpr auto floyd_vertices =
    std::array{Vertex{10}, Vertex{20}, Vertex{30}, Vertex{40}, Vertex{50}};

constexpr auto default_limit_gib = 16.0;
constexpr auto bytes_per_gib = 1024.0 * 1024.0 * 1024.0;

Graph read_graph(const std::string & path, Direction direction)
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
    return Graph{vertex_count, edges, direction};
}

[[noreturn]] void fail_usage()
{
    throw std::invalid_argument{
        "uso: cos_part3 GRAFO.txt RELATORIO.txt direcionado|nao_direcionado\n"
        "Variável opcional: COS_FW_LIMITE_GIB (limite de memória do Floyd-Warshall, padrão 16)."};
}

Direction parse_direction(std::string_view argument)
{
    if (argument == "direcionado") {
        return Direction::directed;
    }
    if (argument == "nao_direcionado") {
        return Direction::undirected;
    }
    fail_usage();
}

double read_limit_gib()
{
    const auto * text = std::getenv("COS_FW_LIMITE_GIB");
    if (text == nullptr || *text == '\0') {
        return default_limit_gib;
    }

    char * end = nullptr;
    const auto value = std::strtod(text, &end);
    if (*end != '\0' || !(value >= 0)) {
        throw std::invalid_argument{"COS_FW_LIMITE_GIB deve ser um número não negativo"};
    }
    return value;
}

// 12·V² bytes, saturando em vez de estourar o uint64.
std::uint64_t floyd_bytes(Vertex vertex_count)
{
    const auto count = std::uint64_t{vertex_count};
    if (count != 0 && count > std::numeric_limits<std::uint64_t>::max() / 12 / count) {
        return std::numeric_limits<std::uint64_t>::max();
    }
    return 12 * count * count;
}

void write_summary(std::ostream & output, const Graph & graph)
{
    output << "[grafo]\n"
           << "representacao=" << (COS_MATRIX ? "matriz" : "csr") << '\n'
           << "direcionado=" << (graph.directed ? "sim" : "nao") << '\n'
           << "vertices=" << graph.vertex_count << '\n'
           << "arestas=" << graph.edge_count << '\n'
           << "grau_minimo=" << graph.min_degree << '\n'
           << "grau_maximo=" << graph.max_degree << '\n'
           << std::fixed << std::setprecision(6) << "grau_medio=" << graph.mean_degree << '\n'
           << "grau_mediano=" << graph.median_degree << '\n'
           << "memoria_bytes=" << graph.memory_bytes << '\n'
           << "pesos_negativos=" << (graph.negative_weight ? "sim" : "nao") << '\n';
}

void write_path(std::ostream & output, const std::vector<Vertex> & path)
{
    auto separator = std::string_view{};
    for (const auto vertex : path) {
        output << separator << vertex + 1;
        separator = " ";
    }
}

// Segue os sucessores até o destino; o limite de V passos evita laço infinito.
std::vector<Vertex> path_by_next(const PathsToTarget & paths, Vertex source)
{
    auto path = std::vector<Vertex>{source};
    for (auto vertex = source; paths.next[vertex] != cos_graph::no_vertex;) {
        if (path.size() > paths.next.size()) {
            throw std::logic_error{"os sucessores de Bellman-Ford formam um laço"};
        }
        vertex = paths.next[vertex];
        path.push_back(vertex);
    }
    return path;
}

// Sobe pelos pais da árvore com raiz em `from` e inverte; limite de V passos contra laços.
std::vector<Vertex> path_by_parent(const AllPairsPaths & paths, Vertex from, Vertex to)
{
    auto path = std::vector<Vertex>{to};
    for (auto vertex = to; vertex != from;) {
        vertex = paths.parent(from, vertex);
        if (vertex == cos_graph::no_vertex || path.size() > paths.vertex_count) {
            throw std::logic_error{"a árvore de Floyd-Warshall não chega à origem"};
        }
        path.push_back(vertex);
    }
    return {path.rbegin(), path.rend()};
}

void write_bellman_ford(std::ostream & output, const Graph & graph)
{
    output << "\n[bellman_ford]\n"
           << "destino=" << bellman_target << '\n';
    if (bellman_target > graph.vertex_count) {
        output << "situacao=fora_do_grafo\n";
        return;
    }

    const auto paths = graph.bellman_ford(bellman_target - 1);
    output << "rodadas=" << paths.rounds << '\n'
           << "ciclo_negativo_alcanca_destino=" << (paths.negative_cycle ? "sim" : "nao") << '\n'
           << "ciclo_negativo_no_grafo=" << (graph.has_negative_cycle() ? "sim" : "nao") << '\n';
    // Um ciclo que não alcança o destino não invalida as distâncias até ele.
    if (paths.negative_cycle) {
        output << "situacao=ciclo_negativo\n";
        return;
    }

    output << "origem,distancia,caminho\n" << std::defaultfloat << std::setprecision(15);
    for (const auto source : bellman_sources) {
        output << source;
        if (source > graph.vertex_count) {
            output << ",fora_do_grafo\n";
        } else if (paths.distance[source - 1] == cos_graph::no_distance) {
            output << ",inalcancavel\n";
        } else {
            output << ',' << paths.distance[source - 1] << ',';
            write_path(output, path_by_next(paths, source - 1));
            output << '\n';
        }
    }
}

// Consulta de distância e caminho (índices 0-based, ambos dentro do grafo), compartilhada
// pela saída do Floyd-Warshall e pela alternativa com Bellman-Ford.
struct PairLookup {
    std::function<Weight(Vertex, Vertex)> distance;
    std::function<std::vector<Vertex>(Vertex, Vertex)> path;
};

void write_floyd_matrix(std::ostream & output, const Graph & graph, const PairLookup & lookup)
{
    output << "origem\\destino";
    for (const auto vertex : floyd_vertices) {
        output << ',' << vertex;
    }
    output << '\n' << std::defaultfloat << std::setprecision(15);

    for (const auto from : floyd_vertices) {
        output << from;
        for (const auto to : floyd_vertices) {
            output << ',';
            if (from > graph.vertex_count || to > graph.vertex_count) {
                output << '-';
            } else if (const auto distance = lookup.distance(from - 1, to - 1);
                       distance == cos_graph::no_distance) {
                output << "inf";
            } else {
                output << distance;
            }
        }
        output << '\n';
    }
}

void write_floyd_paths(std::ostream & output, const Graph & graph, const PairLookup & lookup)
{
    output << "origem,destino,caminho\n";
    for (const auto from : floyd_vertices) {
        for (const auto to : floyd_vertices) {
            if (from == to) {
                continue;
            }
            output << from << ',' << to << ',';
            if (from > graph.vertex_count || to > graph.vertex_count) {
                output << "fora_do_grafo\n";
            } else if (lookup.distance(from - 1, to - 1) == cos_graph::no_distance) {
                output << "inalcancavel\n";
            } else {
                write_path(output, lookup.path(from - 1, to - 1));
                output << '\n';
            }
        }
    }
}

// Sem memória para Floyd-Warshall: um Bellman-Ford por destino (cada um dá d(s, t) para todo s
// e a árvore de sucessores rumo a t), só para os destinos da tabela que existem no grafo.
void write_floyd_by_bellman_ford(std::ostream & output, const Graph & graph)
{
    output << "\n[distancias_por_bellman_ford]\n"
           << "motivo=floyd_warshall_sem_memoria\n";

    auto by_target = std::array<PathsToTarget, floyd_vertices.size()>{};
    for (auto index = std::size_t{0}; index < floyd_vertices.size(); ++index) {
        if (floyd_vertices[index] > graph.vertex_count) {
            continue;
        }
        by_target[index] = graph.bellman_ford(floyd_vertices[index] - 1);
        if (by_target[index].negative_cycle) {
            output << "situacao=ciclo_negativo\n";
            return;
        }
    }

    const auto target_index = [](Vertex to) {
        return std::size_t(std::find(floyd_vertices.begin(), floyd_vertices.end(), to + 1) -
                           floyd_vertices.begin());
    };
    const auto lookup = PairLookup{
        [&](Vertex from, Vertex to) { return by_target[target_index(to)].distance[from]; },
        [&](Vertex from, Vertex to) { return path_by_next(by_target[target_index(to)], from); }};

    write_floyd_matrix(output, graph, lookup);
    output << "\n[distancias_por_bellman_ford_caminhos]\n";
    write_floyd_paths(output, graph, lookup);
}

void write_floyd_warshall(std::ostream & output, const Graph & graph)
{
    output << "\n[floyd_warshall]\n";

    const auto needed = floyd_bytes(graph.vertex_count);
    if (double(needed) > read_limit_gib() * bytes_per_gib) {
        output << "situacao=memoria_insuficiente\n"
               << "memoria_necessaria_bytes=" << needed << '\n';
        write_floyd_by_bellman_ford(output, graph);
        return;
    }

    // Esta saída não é cronometrada: todas as threads só encurtam a espera (resultado idêntico).
    const auto paths = graph.floyd_warshall(std::max(1u, std::thread::hardware_concurrency()));
    output << "ciclo_negativo=" << (paths.negative_cycle ? "sim" : "nao") << '\n';
    if (paths.negative_cycle) {
        output << "situacao=ciclo_negativo\n";
        return;
    }

    const auto lookup =
        PairLookup{[&](Vertex from, Vertex to) { return paths.distance(from, to); },
                   [&](Vertex from, Vertex to) { return path_by_parent(paths, from, to); }};
    write_floyd_matrix(output, graph, lookup);
    output << "\n[floyd_warshall_caminhos]\n";
    write_floyd_paths(output, graph, lookup);
}

} // namespace

int main(int argc, char * argv[])
{
    try {
        if (argc != 4) {
            fail_usage();
        }
        const auto direction = parse_direction(argv[3]);

        const auto graph = read_graph(argv[1], direction);

        auto output = std::ofstream{argv[2]};
        if (!output) {
            throw std::runtime_error{"não foi possível criar o arquivo de relatório"};
        }

        write_summary(output, graph);
        write_bellman_ford(output, graph);
        write_floyd_warshall(output, graph);
        return EXIT_SUCCESS;
    } catch (const std::exception & error) {
        std::cerr << "erro: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
