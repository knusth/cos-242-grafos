#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <span>
#include <utility>
#include <vector>

namespace cos_graph {

using Vertex = std::uint32_t;
using Edge = std::pair<Vertex, Vertex>;

inline constexpr auto no_vertex = std::numeric_limits<Vertex>::max();

class Graph {
  public:
    Vertex vertex_count;
    std::uint64_t edge_count;
    Vertex min_degree;
    Vertex max_degree;
    double mean_degree;
    double median_degree;
    std::uint64_t memory_bytes;

    // Tempo esperado: CSR O(V + E); matriz O(V² + E).
    Graph(Vertex vertices, std::span<const Edge> edges)
        : vertex_count{vertices}, edge_count{edges.size()}
    {
        build(edges);
    }

    // Visitante O(1): CSR O(V + E); matriz O(V²); memória O(V).
    void bfs(Vertex source, auto visit) const
    {
        // Capacidade O(V) sem inicialização; as marcas zeram V/64 palavras.
        auto queue = std::make_unique_for_overwrite<Vertex[]>(vertex_count);
        auto visited = std::vector<std::uint64_t>(word_count());
        bfs(source, visited, std::span{queue.get(), std::size_t{vertex_count}}, visit);
    }

    // Visitante O(1): CSR O(V + E); matriz O(V²); memória O(V).
    void dfs(Vertex source, auto visit) const
    {
        // Pilha O(V) e marcas O(V/64); nenhum vértice entra duas vezes.
        auto stack = std::vector<std::pair<Vertex, Vertex>>{};
        auto visited = std::vector<std::uint64_t>(word_count());

        stack.reserve(vertex_count);
        stack.emplace_back(source, first_neighbor(source));
        mark(visited, source);
        visit(source, no_vertex, Vertex{0});

        // Cada incidência é examinada uma vez: O(V + E) na CSR.
        // Na matriz, cada vértice alcançado examina uma linha de V células.
        while (!stack.empty()) {
            auto & [current, position] = stack.back();
            const auto next = next_neighbor(current, position);

            if (next == no_vertex) {
                stack.pop_back();
            } else if (mark(visited, next)) {
                visit(next, current, Vertex(stack.size()));
                // A posição salva reproduz a DFS recursiva sem arriscar a pilha.
                stack.emplace_back(next, first_neighbor(next));
            }
        }
    }

    // CSR O(V + E); matriz O(V²); memória e saída O(V).
    auto distances(Vertex source) const
    {
        // O(V) para inicializar a saída e representar vértices inalcançáveis.
        auto distance = std::vector<Vertex>(vertex_count, no_vertex);
        // A lambda é incorporada à BFS; não há chamada indireta no laço.
        bfs(source, [&](Vertex vertex, Vertex, Vertex level) { distance[vertex] = level; });

        return distance;
    }

    // CSR O(V + E + C log C); matriz O(V²); memória O(V), saída O(V + C).
    auto components() const
    {
        // Fila e marcas são alocadas uma vez: memória auxiliar O(V).
        auto result = std::vector<std::vector<Vertex>>{};
        auto visited = std::vector<std::uint64_t>(word_count());
        auto queue = std::make_unique_for_overwrite<Vertex[]>(vertex_count);
        const auto queue_view = std::span{queue.get(), std::size_t{vertex_count}};

        // O(V) fontes; a marca evita percorrer novamente um componente.
        for (auto start = Vertex{0}; start < vertex_count; ++start) {
            if (marked(visited, start)) {
                continue;
            }

            auto & component = result.emplace_back();
            // No conjunto das chamadas: CSR O(V + E), matriz O(V²).
            bfs(start, visited, queue_view,
                [&](Vertex vertex, Vertex, Vertex) { component.push_back(vertex); });
        }

        // C componentes: O(C log C); seus membros não são reordenados.
        std::ranges::sort(result, [](const auto & first, const auto & second) {
            return first.size() > second.size();
        });
        return result;
    }

    // Exato: CSR O(V(V + E)); matriz O(V³); memória O(V).
    Vertex diameter() const
    {
        // O(V) de memória, reutilizada por todas as fontes.
        auto visited = std::vector<std::uint64_t>(word_count());
        auto queue = std::make_unique_for_overwrite<Vertex[]>(vertex_count);
        const auto queue_view = std::span{queue.get(), std::size_t{vertex_count}};
        auto diameter = Vertex{0};

        // V buscas: O(V(V + E)) na CSR e O(V³) na matriz.
        for (auto source = Vertex{0}; source < vertex_count; ++source) {
            // O(V/64); a fila só redefine seus índices dentro da BFS.
            std::ranges::fill(visited, 0);
            diameter =
                std::max(diameter, bfs(source, visited, queue_view, [](Vertex, Vertex, Vertex) {}));
        }

        return diameter;
    }

  private:
    static std::vector<Vertex> count_degrees(Vertex vertices, std::span<const Edge> edges)
    {
        // Inicialização O(V), seguida por duas incidências por aresta: O(E).
        auto degrees = std::vector<Vertex>(vertices, 0);
        for (const auto [first, second] : edges) {
            ++degrees[first];
            ++degrees[second];
        }
        return degrees;
    }

    void compute_statistics(std::vector<Vertex> degrees)
    {
        // Extremos e soma: O(V).
        auto sum = std::uint64_t{0};
        min_degree = degrees.front();
        max_degree = degrees.front();

        for (const auto degree : degrees) {
            sum += degree;
            min_degree = std::min(min_degree, degree);
            max_degree = std::max(max_degree, degree);
        }

        mean_degree = double(sum) / vertex_count;

        // Seleção esperada O(V); não ordena graus que nunca serão exibidos.
        const auto middle = degrees.begin() + degrees.size() / 2;
        std::ranges::nth_element(degrees, middle);
        median_degree = *middle;

        if (degrees.size() % 2 == 0) {
            const auto lower = std::ranges::max_element(degrees.begin(), middle);
            median_degree = (double(*lower) + *middle) / 2;
        }
    }

    std::size_t word_count() const { return (std::size_t{vertex_count} + 63) / 64; }

    static bool mark(std::span<std::uint64_t> visited, Vertex vertex)
    {
        // Uma divisão, uma máscara e uma atualização: O(1).
        auto & word = visited[vertex / 64];
        const auto bit = std::uint64_t{1} << (vertex % 64);
        const auto first_visit = (word & bit) == 0;
        word |= bit;
        return first_visit;
    }

    static bool marked(std::span<const std::uint64_t> visited, Vertex vertex)
    {
        // Consulta de uma palavra e um bit: O(1).
        const auto bit = std::uint64_t{1} << (vertex % 64);
        return (visited[vertex / 64] & bit) != 0;
    }

    Vertex bfs(Vertex source, std::span<std::uint64_t> visited, std::span<Vertex> queue,
               auto visit) const
    {
        // Apenas índices são reiniciados; fila e marcas pertencem ao chamador.
        auto head = Vertex{0};
        auto tail = Vertex{0};
        auto level_end = Vertex{1};
        auto level = Vertex{0};

        mark(visited, source);
        queue[tail++] = source;
        visit(source, no_vertex, Vertex{0});

        // Cada vértice alcançado entra uma vez e chama o visitante uma vez.
        // CSR examina cada incidência alcançada; matriz examina V células por linha.
        while (head < tail) {
            const auto current = queue[head++];
            auto position = first_neighbor(current);

            while (true) {
                const auto next = next_neighbor(current, position);
                if (next == no_vertex) {
                    break;
                }
                if (mark(visited, next)) {
                    queue[tail++] = next;
                    visit(next, current, level + 1);
                }
            }

            if (head == level_end && head < tail) {
                // O limite da fila separa níveis sem armazenar V distâncias.
                level_end = tail;
                ++level;
            }
        }

        return level;
    }

#if COS_MATRIX

    void build(std::span<const Edge> edges)
    {
        // O temporário O(V) é liberado antes da matriz O(V²).
        compute_statistics(count_degrees(vertex_count, edges));

        const auto count = std::size_t{vertex_count};
        // A matriz fixa precisa começar zerada: O(V²) tempo e memória.
        matrix_ = std::make_unique<std::uint8_t[]>(count * count);

        // Duas escritas por aresta: O(E).
        for (const auto [first, second] : edges) {
            matrix_[std::size_t{first} * count + second] = 1;
            matrix_[std::size_t{second} * count + first] = 1;
        }
        memory_bytes = sizeof(Graph) + count * count;
    }

    static Vertex first_neighbor(Vertex) { return 0; }

    Vertex next_neighbor(Vertex vertex, Vertex & position) const
    {
        const auto count = std::size_t{vertex_count};
        const auto * row = matrix_.get() + std::size_t{vertex} * count;
        // As buscas sucessivas cobrem trechos disjuntos: O(V) por linha completa.
        const auto * found =
            static_cast<const std::uint8_t *>(std::memchr(row + position, 1, count - position));

        if (found == nullptr) {
            return no_vertex;
        }

        const auto next = Vertex(found - row);
        position = next + 1;
        return next;
    }

    std::unique_ptr<std::uint8_t[]> matrix_;

#else

    void build(std::span<const Edge> edges)
    {
        // O(V + E); a estatística usa uma cópia e preserva os graus.
        auto cursor = count_degrees(vertex_count, edges);
        compute_statistics(cursor);

        // Os arrays fixos serão completamente escritos durante a construção.
        offsets_ = std::make_unique_for_overwrite<Vertex[]>(std::size_t{vertex_count} + 1);
        neighbors_ = std::make_unique_for_overwrite<Vertex[]>(edges.size() * 2);
        offsets_[0] = 0;

        // Soma prefixada e inicialização dos cursores: O(V).
        for (auto vertex = Vertex{0}; vertex < vertex_count; ++vertex) {
            offsets_[vertex + 1] = offsets_[vertex] + cursor[vertex];
            cursor[vertex] = offsets_[vertex];
        }

        // Preenchimento O(E); os graus viram cursores e preservam a ordem.
        for (const auto [first, second] : edges) {
            neighbors_[cursor[first]++] = second;
            neighbors_[cursor[second]++] = first;
        }
        memory_bytes =
            sizeof(Graph) + (std::size_t{vertex_count} + 1 + edges.size() * 2) * sizeof(Vertex);
    }

    Vertex first_neighbor(Vertex vertex) const { return offsets_[vertex]; }

    Vertex next_neighbor(Vertex vertex, Vertex & position) const
    {
        // Consulta e avanço O(1) por incidência armazenada.
        if (position == offsets_[vertex + 1]) {
            return no_vertex;
        }
        return neighbors_[position++];
    }

    std::unique_ptr<Vertex[]> offsets_;
    std::unique_ptr<Vertex[]> neighbors_;

#endif
};

} // namespace cos_graph
