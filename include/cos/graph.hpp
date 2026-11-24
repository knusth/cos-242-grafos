#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <barrier>
#include <bit>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <numeric>
#include <span>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace cos_graph {

using Vertex = std::uint32_t;
using Edge = std::pair<Vertex, Vertex>;
using Weight = double;
using WeightedEdge = std::tuple<Vertex, Vertex, Weight>;

inline constexpr auto no_vertex = std::numeric_limits<Vertex>::max();
inline constexpr auto no_distance = std::numeric_limits<Weight>::infinity();

// No grafo direcionado, cada aresta vai do primeiro para o segundo vértice da entrada.
enum class Direction : bool { undirected, directed };

// Resultado de Bellman-Ford até um destino fixo.
struct PathsToTarget {
    // distance[u] é a distância de u até o destino; no_distance quando u não o alcança.
    std::vector<Weight> distance;
    // next[u] é o sucessor de u no caminho mínimo; os ponteiros formam uma árvore enraizada
    // no destino. Vale no_vertex nos vértices que não o alcançam e, só quando negative_cycle
    // é falso, também no destino.
    std::vector<Vertex> next;
    // Rodadas executadas; sem ciclo negativo, no máximo V.
    Vertex rounds = 0;
    // Existe ciclo negativo que alcança o destino; as distâncias deixam de ser mínimas.
    bool negative_cycle = false;
};

// Resultado de Floyd-Warshall: duas matrizes V × V, com uma linha por origem.
struct AllPairsPaths {
    Vertex vertex_count = 0;
    bool negative_cycle = false;
    std::unique_ptr<Weight[]> distances;
    std::unique_ptr<Vertex[]> parents;

    // Distância de `from` até `to`; no_distance quando `to` não é alcançável.
    Weight distance(Vertex from, Vertex to) const { return distances[cell(from, to)]; }

    // Pai de `to` na árvore de caminhos mínimos com raiz `from`; no_vertex na raiz e nos
    // vértices inalcançáveis.
    Vertex parent(Vertex from, Vertex to) const { return parents[cell(from, to)]; }

    std::size_t cell(Vertex from, Vertex to) const { return std::size_t{from} * vertex_count + to; }
};

// Resultado de Bellman-Ford para todos os destinos: uma linha por destino.
// Por que não reutilizar AllPairsPaths: Bellman-Ford devolve, para cada destino t, o sucessor
// `next` de cada origem rumo a t (árvore enraizada em t), enquanto AllPairsPaths guarda pais em
// árvores enraizadas na origem. Converter exigiria transpor duas matrizes V × V (acessos com
// passo V, mais O(V²) de tempo e memória extra) e misturaria duas semânticas sob o mesmo nome
// `parent`. Um tipo próprio, armazenado por destino, deixa cada execução escrever uma linha
// contígua e custa os mesmos 12V² bytes do Floyd-Warshall.
struct AllPairsToTargets {
    Vertex vertex_count = 0;
    bool negative_cycle = false;
    std::unique_ptr<Weight[]> distances;
    std::unique_ptr<Vertex[]> nexts;

    // Distância de `from` até `to`; no_distance quando `to` não é alcançável.
    Weight distance(Vertex from, Vertex to) const { return distances[cell(from, to)]; }

    // Sucessor de `from` no caminho mínimo até `to`; no_vertex em `to` e nos vértices que
    // não o alcançam.
    Vertex next(Vertex from, Vertex to) const { return nexts[cell(from, to)]; }

    // Linha do destino `to`, contígua: índice da origem dentro da linha.
    std::size_t cell(Vertex from, Vertex to) const { return std::size_t{to} * vertex_count + from; }
};

// Memória de trabalho de uma execução de Bellman-Ford (listas de ativos, marcas e selos).
// Pode ser reutilizada entre destinos pela mesma thread: O(V) de memória, alocada uma vez.
struct BellmanFordWorkspace {
    explicit BellmanFordWorkspace(Vertex vertices)
        : queued((std::size_t{vertices} + 63) / 64), stamps(vertices, 0)
    {
    }

    std::vector<Vertex> active;
    std::vector<Vertex> upcoming;
    std::vector<std::uint64_t> queued;
    // Selos da busca de ciclos em `next`; o contador cresce entre execuções sem limpeza.
    std::vector<std::uint32_t> stamps;
    std::uint32_t stamp = 0;
};

// Fronteira em vetor de estimativas: inserção O(1) e extração O(V).
class VectorFrontier {
  public:
    // O(V) para inicializar todas as estimativas como infinitas.
    explicit VectorFrontier(Vertex vertices) : estimate_(vertices, no_distance) {}

    // Inserção ou redução da estimativa: O(1).
    void push(Vertex vertex, Weight distance) { estimate_[vertex] = distance; }

    // Varredura completa: O(V); devolve no_vertex quando nenhuma estimativa é finita.
    Vertex pop()
    {
        const auto found = std::ranges::min_element(estimate_);
        if (found == estimate_.end() || *found == no_distance) {
            return no_vertex;
        }

        // A estimativa volta a ser infinita e o vértice sai da fronteira.
        *found = no_distance;
        return Vertex(found - estimate_.begin());
    }

  private:
    std::vector<Weight> estimate_;
};

// Heap binário indexado: inserção, redução de chave e extração O(log V).
class HeapFrontier {
  public:
    // Capacidade O(V) sem inicialização; as posições começam ausentes em O(V).
    explicit HeapFrontier(Vertex vertices)
        : heap_{std::make_unique_for_overwrite<Entry[]>(vertices)}, position_(vertices, no_vertex)
    {
    }

    // Insere o vértice ou reduz sua chave: O(log V).
    void push(Vertex vertex, Weight distance)
    {
        auto index = position_[vertex];
        if (index == no_vertex) {
            index = size_++;
        }
        // A chave só diminui; subir a partir da posição atual restaura o heap.
        sift_up(index, Entry{distance, vertex});
    }

    // Remove a menor chave: O(log V); devolve no_vertex quando o heap está vazio.
    Vertex pop()
    {
        if (size_ == 0) {
            return no_vertex;
        }

        const auto top = heap_[0].vertex;
        position_[top] = no_vertex;
        --size_;

        if (size_ > 0) {
            // O último elemento ocupa a raiz vaga e desce até sua posição.
            sift_down(0, heap_[size_]);
        }
        return top;
    }

  private:
    struct Entry {
        Weight key;
        Vertex vertex;
    };

    void place(Vertex index, Entry entry)
    {
        // Toda movimentação atualiza a posição do vértice: O(1).
        heap_[index] = entry;
        position_[entry.vertex] = index;
    }

    void sift_up(Vertex index, Entry entry)
    {
        // No máximo log V trocas até a raiz.
        while (index > 0) {
            const auto parent = (index - 1) / 2;
            if (heap_[parent].key <= entry.key) {
                break;
            }
            place(index, heap_[parent]);
            index = parent;
        }
        place(index, entry);
    }

    void sift_down(Vertex index, Entry entry)
    {
        // No máximo log V níveis até uma folha.
        while (true) {
            auto child = std::size_t{index} * 2 + 1;
            if (child >= size_) {
                break;
            }
            if (child + 1 < size_ && heap_[child + 1].key < heap_[child].key) {
                ++child;
            }
            if (!(heap_[child].key < entry.key)) {
                break;
            }
            place(index, heap_[child]);
            index = Vertex(child);
        }
        place(index, entry);
    }

    std::unique_ptr<Entry[]> heap_;
    std::vector<Vertex> position_;
    Vertex size_ = 0;
};

// Heap radix monótono, com chave igual ao padrão de bits IEEE-754 da distância lida como
// uint64 (std::bit_cast). Para doubles não negativos (inclusive +infinito), a ordem dos bits
// coincide com a ordem numérica, então todas as comparações são exatas e feitas com inteiros.
// -0.0 tem o bit de sinal ligado e viraria uma chave enorme; push o normaliza para +0.0.
// NaN e valores negativos não são aceitos.
//
// Requisito de monotonicidade: toda chave inserida é >= a última chave extraída. Dijkstra
// cumpre isso, pois extrai em ordem não decrescente e só insere distance[current] + w, com
// w >= 0. O balde de uma chave é o índice do bit mais alto em que ela difere da última
// extraída (0 quando são iguais): 65 baldes. Quando o balde 0 esvazia, o primeiro balde não
// vazio é redistribuído em torno de sua menor chave, e cada entrada só desce de balde.
//
// Redução de chave preguiçosa: push insere uma entrada nova e best_[vertex] guarda a chave
// vigente; entradas com outra chave são obsoletas e pop as descarta. Escolhida em vez de
// posições indexadas porque os baldes são vetores desordenados, onde remover uma entrada
// exigiria manter o índice dela dentro do balde a cada redistribuição. O custo é até
// uma entrada por relaxação (O(E) de memória no pior caso) em vez de O(V).
// Extração amortizada O(1) por entrada em baldes + O(64) movimentos no pior caso; inserção O(1).
// Reutilizável por várias buscas, desde que cada uma esvazie a fronteira (pop até no_vertex).
class RadixFrontier {
  public:
    // O(V) para marcar todos os vértices como ausentes.
    explicit RadixFrontier(Vertex vertices) : best_(vertices, absent) {}

    // Insere o vértice ou reduz sua chave: O(1). Chaves que não melhoram são ignoradas.
    void push(Vertex vertex, Weight distance)
    {
        if (distance == 0) {
            distance = 0; // normaliza -0.0
        }
        const auto key = std::bit_cast<std::uint64_t>(distance);
        assert(key >= last_ && "RadixFrontier exige chaves monótonas");
        if (key >= best_[vertex]) {
            return;
        }
        best_[vertex] = key;
        buckets_[bucket_of(key)].push_back(Entry{key, vertex});
    }

    // Remove a menor chave; no_vertex quando vazio. Amortizado O(log C), C = 64 bits.
    Vertex pop()
    {
        while (true) {
            auto & zero = buckets_[0];
            while (!zero.empty()) {
                const auto entry = zero.back();
                zero.pop_back();
                if (best_[entry.vertex] == entry.key) {
                    best_[entry.vertex] = absent;
                    return entry.vertex;
                }
            }

            // Primeiro balde com entradas vigentes; as obsoletas são descartadas aqui.
            auto index = std::size_t{1};
            for (; index < buckets_.size(); ++index) {
                std::erase_if(buckets_[index], [&](const Entry & entry) {
                    return best_[entry.vertex] != entry.key;
                });
                if (!buckets_[index].empty()) {
                    break;
                }
            }
            if (index == buckets_.size()) {
                last_ = 0; // vazio: a fronteira pode servir a outra busca
                return no_vertex;
            }

            // A menor chave vira a referência; as entradas descem para baldes menores.
            auto & source = buckets_[index];
            last_ = std::ranges::min_element(source, {}, &Entry::key)->key;
            for (const auto & entry : source) {
                buckets_[bucket_of(entry.key)].push_back(entry);
            }
            source.clear();
        }
    }

  private:
    struct Entry {
        std::uint64_t key;
        Vertex vertex;
    };

    static constexpr auto absent = std::numeric_limits<std::uint64_t>::max();

    std::size_t bucket_of(std::uint64_t key) const { return std::bit_width(key ^ last_); }

    std::vector<std::uint64_t> best_;
    std::array<std::vector<Entry>, 65> buckets_;
    std::uint64_t last_ = 0;
};

class Graph {
  public:
    Vertex vertex_count;
    std::uint64_t edge_count;
    Vertex min_degree;
    Vertex max_degree;
    double mean_degree;
    double median_degree;
    std::uint64_t memory_bytes;
    bool negative_weight = false;
    // Margem absoluta de arredondamento: uma relaxação só vale se melhora a distância em mais
    // que `tolerance`. Calculada uma vez, na construção, como 8 · ε · V · max|w|.
    //   - Um caminho tem até V - 1 arestas, e cada soma em double erra no máximo ε/2 do valor
    //     da soma (ε = 2,2e-16). Com somas parciais da ordem de max|w| (pesos com potenciais
    //     limitados, como nos dados), o erro de um caminho fica abaixo de (ε/2) · V · max|w|.
    //   - O fator 8 cobre somas parciais até 16 vezes maiores que max|w| e a comparação de
    //     dois caminhos (dois erros).
    // Sem ela, um ciclo de soma decimal exatamente 0 (0,1 + 0,2 - 0,3) pode virar uma
    // "melhora" de 1 ulp, e então um ciclo negativo falso ou um ciclo nos pais. Para pesos
    // com 2 casas decimais a menor melhora real é 0,01, muito acima (6,6e-10 com V = 25000 e
    // max|w| = 15). Pesos com diferenças reais menores que `tolerance` não são distinguidos.
    Weight tolerance = 0;
    bool directed;

    // Tempo esperado: CSR O(V + E); matriz O(V² + E).
    Graph(Vertex vertices, std::span<const Edge> edges, Direction direction = Direction::undirected)
        : vertex_count{vertices}, edge_count{edges.size()},
          directed{direction == Direction::directed}
    {
        build(edges);
    }

    // Tempo esperado: CSR O(V + E); matriz O(V² + E); arestas repetidas são preservadas.
    Graph(Vertex vertices, std::span<const WeightedEdge> edges,
          Direction direction = Direction::undirected)
        : vertex_count{vertices}, edge_count{edges.size()},
          directed{direction == Direction::directed}
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
        require_undirected("components");
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
        require_undirected("diameter");
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

    // Visitante O(1): CSR O((V + E) log V) com HeapFrontier e O(V² + E) com VectorFrontier;
    // matriz O(V² + E log V) com HeapFrontier e O(V²) com VectorFrontier.
    // Memória O(V) além da fronteira.
    template <class Frontier> void dijkstra(Vertex source, auto visit) const
    {
        require_weights();
        if (negative_weight) {
            throw std::domain_error{
                "Dijkstra exige pesos não negativos; use Bellman-Ford ou Floyd-Warshall"};
        }

        // Distâncias e pais O(V); a fronteira decide como guardar e extrair estimativas.
        auto distance = std::vector<Weight>(vertex_count, no_distance);
        auto parent = std::vector<Vertex>(vertex_count, no_vertex);
        auto frontier = Frontier{vertex_count};
        // A transformação identidade some na inlinação.
        dijkstra_search(source, distance, parent, frontier, visit,
                        [](Vertex, Vertex, Weight weight) { return weight; });
    }

    // Distâncias de todos os vértices até `target`, que aceitam pesos negativos.
    // Pior caso: CSR O(V·E); matriz O(V³). Sem mudanças, a busca para antes: com
    // R rodadas, o custo é o das arestas que entram nos vértices ativos em cada rodada.
    // Memória O(V). Cada rodada ainda custa O(V) extra na busca de ciclos de `next`;
    // com ciclo negativo, a busca costuma encerrar muito antes da rodada V.
    // negative_cycle só cobre ciclos negativos que alcançam `target`.
    PathsToTarget bellman_ford(Vertex target) const { return relax_rounds(target); }

    // Indica se o grafo possui algum ciclo negativo, alcance ou não um destino dado.
    // Mesmo núcleo de bellman_ford, partindo de uma origem virtual com aresta de peso 0 para
    // cada vértice: todas as distâncias valem 0 e todos os vértices começam ativos.
    // Pior caso: CSR O(V·E); matriz O(V³); memória O(V). Sem ciclo negativo, para assim que
    // uma rodada não muda nada; com ele, costuma parar na busca de ciclos de `next`.
    bool has_negative_cycle() const { return relax_rounds(no_vertex).negative_cycle; }

  private:
    // Corpo único de Dijkstra. `distance` e `parent` (V posições) são do chamador e são
    // inicializados aqui em O(V); a fronteira deve estar vazia. `reweigh(from, to, w)` devolve
    // o peso usado na aresta e deve ser >= 0 (identidade na dijkstra pública, peso
    // reponderado em Johnson); como é um parâmetro de template, é incorporado ao laço.
    template <class Frontier>
    void dijkstra_search(Vertex source, std::span<Weight> distance, std::span<Vertex> parent,
                         Frontier & frontier, auto visit, auto reweigh) const
    {
        std::ranges::fill(distance, no_distance);
        std::ranges::fill(parent, no_vertex);

        distance[source] = 0;
        frontier.push(source, 0);

        // Cada vértice alcançado sai uma vez da fronteira, em distância não decrescente.
        // CSR examina cada incidência alcançada; matriz examina V células por linha.
        while (true) {
            const auto current = frontier.pop();
            if (current == no_vertex) {
                break;
            }
            visit(current, parent[current], distance[current]);

            auto position = first_neighbor(current);
            while (true) {
                const auto next = next_neighbor(current, position);
                if (next == no_vertex) {
                    break;
                }

                // Aqui os pesos não negativos são usados: um vértice já extraído tem
                // distância <= distance[current] <= candidate, então a comparação estrita
                // nunca o devolve à fronteira e nenhuma marca de visita é necessária.
                const auto candidate =
                    distance[current] + reweigh(current, next, weight_before(current, position));
                if (candidate < distance[next]) {
                    distance[next] = candidate;
                    parent[next] = current;
                    frontier.push(next, candidate);
                }
            }
        }
    }

    // Resumo de uma execução de relax_rounds; os vetores pertencem ao chamador.
    struct RoundsSummary {
        Vertex rounds = 0;
        bool negative_cycle = false;
    };

    // Núcleo único de Bellman-Ford. Com `target` válido, as distâncias são até ele; com
    // no_vertex, é a origem virtual de has_negative_cycle e nenhum vértice é destino.
    // `distance` e `next` (V posições cada) e `work` são do chamador, que pode reutilizá-los
    // entre destinos: a inicialização é O(V) por chamada, mas nada é alocado aqui.
    RoundsSummary relax_rounds(Vertex target, std::span<Weight> distance, std::span<Vertex> next,
                               BellmanFordWorkspace & work) const
    {
        require_weights();

        auto summary = RoundsSummary{};
        auto & active = work.active;
        auto & upcoming = work.upcoming;
        auto & queued = work.queued;
        auto & stamps = work.stamps;

        // Uma execução anterior pode ter saído no meio de uma rodada, deixando marcas em
        // `upcoming`; limpá-las custa O(vértices pendentes).
        for (const auto vertex : upcoming) {
            unmark(queued, vertex);
        }
        upcoming.clear();
        active.clear();

        std::ranges::fill(distance, no_distance);
        std::ranges::fill(next, no_vertex);

        // Otimização 2: só os vértices cuja distância mudou na rodada anterior podem
        // melhorar outros; a rodada seguinte examina apenas as arestas que chegam neles.
        if (target == no_vertex) {
            // A rodada da aresta virtual já foi feita: distâncias 0 e todos ativos. O(V).
            std::ranges::fill(distance, 0.0);
            active.resize(vertex_count);
            std::iota(active.begin(), active.end(), Vertex{0});
        } else {
            distance[target] = 0;
            active.push_back(target);
        }

        // Otimização 1: uma rodada sem mudanças deixa `active` vazio e encerra o laço.
        while (!active.empty()) {
            // Sem ciclo negativo, um caminho mínimo simples tem até V - 1 arestas, e a
            // rodada i fixa os vértices cujo caminho tem i arestas. Se a rodada V ainda
            // mudou alguma distância, há um ciclo negativo que alcança o destino.
            if (summary.rounds == vertex_count) {
                summary.negative_cycle = true;
                break;
            }
            ++summary.rounds;

            for (const auto vertex : active) {
                auto position = first_predecessor(vertex);
                while (true) {
                    const auto previous = next_predecessor(vertex, position);
                    if (previous == no_vertex) {
                        break;
                    }

                    // A aresta previous -> vertex melhora o caminho de previous até o destino.
                    const auto candidate =
                        distance[vertex] + weight_before_predecessor(vertex, position);
                    if (candidate < distance[previous] - tolerance) {
                        // O destino só melhora se existe um passeio negativo que sai e volta
                        // a ele, e esse passeio contém um ciclo negativo.
                        if (previous == target) {
                            summary.negative_cycle = true;
                            return summary;
                        }
                        distance[previous] = candidate;
                        next[previous] = vertex;
                        if (mark(queued, previous)) {
                            upcoming.push_back(previous);
                        }
                    }
                }
            }

            // As marcas só valem para a próxima rodada: O(vértices ativos).
            for (const auto vertex : upcoming) {
                unmark(queued, vertex);
            }

            // Saída antecipada: um ciclo nos ponteiros `next` prova um ciclo negativo.
            if (has_cycle(next, upcoming, stamps, work.stamp)) {
                summary.negative_cycle = true;
                break;
            }
            active.swap(upcoming);
            upcoming.clear();
        }

        return summary;
    }

    // Versão com buffers próprios, para chamadas isoladas: O(V) de alocação por chamada.
    PathsToTarget relax_rounds(Vertex target) const
    {
        require_weights();

        auto result =
            PathsToTarget{std::vector<Weight>(vertex_count), std::vector<Vertex>(vertex_count)};
        auto work = BellmanFordWorkspace{vertex_count};
        const auto summary = relax_rounds(target, result.distance, result.next, work);
        result.rounds = summary.rounds;
        result.negative_cycle = summary.negative_cycle;
        return result;
    }

    // Lado dos blocos do Floyd-Warshall em blocos. Três blocos de 64 × 64 (distâncias em
    // double e pais em 32 bits) ocupam 144 KiB, e os dois lidos pela fase 3 cabem no cache L1.
    static constexpr std::size_t fw_block = 64;
    // Blocos de uma tarefa da fase 3: tarefas menores balanceiam melhor núcleos de
    // eficiência e de desempenho; a linha de blocos da tarefa reaproveita o bloco da coluna k.
    static constexpr std::size_t fw_group = 4;

    // Relaxa um trecho de linha por k: row[to] = min(row[to], to_k + through[to]), e o pai
    // acompanha a melhora. Sem desvios, o compilador vetoriza o laço (NEON, SSE ou AVX, sem
    // intrínsecas), com uma checagem de alias em tempo de execução. O(width).
    static void relax_segment(Weight * row, Vertex * row_parent, const Weight * through,
                              const Vertex * through_parent, Weight to_k, Weight tolerance,
                              std::size_t width)
    {
        for (auto to = std::size_t{0}; to < width; ++to) {
            // Todas as leituras vêm antes dos seleções: com leituras dentro do `?:`, o
            // compilador as transforma em escritas condicionais e desiste de vetorizar.
            const auto current = row[to];
            const auto current_parent = row_parent[to];
            const auto through_to_parent = through_parent[to];
            const auto candidate = to_k + through[to];
            const auto better = candidate < current - tolerance;
            row[to] = better ? candidate : current;
            // O pai de `to` no caminho de k até `to` continua sendo seu pai.
            row_parent[to] = better ? through_to_parent : current_parent;
        }
    }

    // As duas matrizes V × V, de distâncias e de pais, com `count` = V.
    struct FwMatrices {
        Weight * distance;
        Vertex * parent;
        std::size_t count;
        Weight tolerance;
    };

    // Aplica o passo k (linha k da janela de colunas [col, col + width)) às linhas
    // [row_begin, row_end), exceto a própria linha k. Pula a linha cujo d[i][k] é infinito.
    // O((row_end - row_begin) · width).
    static void relax_rows(const FwMatrices & m, std::size_t row_begin, std::size_t row_end,
                           std::size_t k, std::size_t col, std::size_t width)
    {
        const auto * const through = m.distance + k * m.count + col;
        const auto * const through_parent = m.parent + k * m.count + col;
        for (auto i = row_begin; i < row_end; ++i) {
            if (i == k) {
                continue;
            }
            const auto to_k = m.distance[i * m.count + k];
            // Se `i` não alcança k, nenhum caminho por k melhora a linha.
            if (to_k == no_distance) {
                continue;
            }
            relax_segment(m.distance + i * m.count + col, m.parent + i * m.count + col, through,
                          through_parent, to_k, m.tolerance, width);
        }
    }

    // Atualiza o bloco (linhas [i0, i1), colunas [j0, j1)) com todos os k em [k0, k1):
    // O((i1 - i0)(j1 - j0)(k1 - k0)). `in_place` indica que a linha k ou a coluna k
    // pertence ao próprio bloco, e então k é o laço externo (ordem do algoritmo clássico).
    // Caso contrário, a linha k e a coluna k já estão prontas e i é o laço externo, o que
    // mantém o trecho da linha i no cache enquanto k a percorre.
    static void update_block(const FwMatrices & m, std::size_t i0, std::size_t i1, std::size_t j0,
                             std::size_t j1, std::size_t k0, std::size_t k1, bool in_place)
    {
        if (in_place) {
            for (auto k = k0; k < k1; ++k) {
                relax_rows(m, i0, i1, k, j0, j1 - j0);
            }
            return;
        }
        for (auto i = i0; i < i1; ++i) {
            for (auto k = k0; k < k1; ++k) {
                relax_rows(m, i, i + 1, k, j0, j1 - j0);
            }
        }
    }

    // A ordem das relaxações em blocos difere da ordem clássica: quando dois caminhos de mesmo
    // peso passam por um ciclo de peso zero, empates podem ser resolvidos em sentidos
    // opostos, e os pais de uma linha formam um ciclo em vez de uma árvore (também com pesos
    // inteiros, logo não é erro de arredondamento; o laço triplo simples não tem o problema).
    // As distâncias continuam corretas. Esta passagem procura ciclos nos pais de cada linha,
    // O(V) por linha, e refaz as linhas afetadas com uma busca em largura pelas arestas justas
    // (d[i][a] + w = d[i][j]), que sempre produz uma árvore: O(V + E) por linha afetada.
    // Linhas são independentes e divididas entre as threads. As arestas justas aceitam erro
    // de arredondamento: o maior entre 1e-9 relativo e 2 · tolerance.
    void repair_zero_cycles(const Weight * distance, Vertex * parent, std::size_t count,
                            unsigned threads) const
    {
        auto next_row = std::atomic<std::size_t>{0};
        const auto worker = [&] {
            auto mark = std::vector<std::uint32_t>(count);
            auto queue = std::vector<Vertex>(count);
            for (auto row = next_row.fetch_add(1); row < count; row = next_row.fetch_add(1)) {
                auto * const tree = parent + row * count;
                const auto * const from = distance + row * count;

                // Caminhadas pelos pais: cada vértice recebe o número da caminhada que o
                // visitou; alcançar um vértice da caminhada atual fecha um ciclo.
                std::ranges::fill(mark, 0);
                auto cyclic = false;
                for (auto start = std::size_t{0}; start < count && !cyclic; ++start) {
                    auto vertex = Vertex(start);
                    while (vertex != no_vertex && mark[vertex] == 0) {
                        mark[vertex] = std::uint32_t(start + 1);
                        vertex = tree[vertex];
                    }
                    cyclic = vertex != no_vertex && mark[vertex] == start + 1;
                }
                if (!cyclic) {
                    continue;
                }

                // Busca em largura a partir da origem pelas arestas justas.
                std::ranges::fill(mark, 0);
                std::ranges::fill_n(tree, count, no_vertex);
                auto head = std::size_t{0};
                auto tail = std::size_t{0};
                queue[tail++] = Vertex(row);
                mark[row] = 1;
                while (head < tail) {
                    const auto vertex = queue[head++];
                    auto position = first_neighbor(vertex);
                    while (true) {
                        const auto next = next_neighbor(vertex, position);
                        if (next == no_vertex) {
                            break;
                        }
                        const auto gap =
                            from[vertex] + weight_before(vertex, position) - from[next];
                        if (mark[next] == 0 &&
                            std::abs(gap) <= std::max(1e-9 * std::max(1.0, std::abs(from[next])),
                                                      2 * tolerance)) {
                            mark[next] = 1;
                            tree[next] = vertex;
                            queue[tail++] = next;
                        }
                    }
                }
            }
        };

        auto pool = std::vector<std::jthread>{};
        for (auto id = 1u; id < threads; ++id) {
            pool.emplace_back(worker);
        }
        worker();
    }

    // Floyd-Warshall em blocos sobre as matrizes já inicializadas, no lugar. Para cada
    // bloco-diagonal kb: fase 1 atualiza o bloco (kb, kb); fase 2, a linha e a coluna de
    // blocos kb (usam o bloco diagonal pronto); fase 3, os demais blocos (usam a linha e a
    // coluna prontas). Cada fase termina numa barreira. Tempo O(V³) dividido entre as
    // threads, mais O((V / B) · threads) em sincronização; memória extra O(V / B).
    // Devolve verdadeiro, abandonando as matrizes inválidas, se algum d[i][i] ficar negativo
    // (ciclo negativo); a checagem ocorre após a fase 1 e após cada bloco diagonal da fase 3,
    // as únicas que escrevem na diagonal.
    static bool blocked_floyd_warshall(Weight * distance, Vertex * parent, std::size_t count,
                                       Weight tolerance, unsigned threads)
    {
        const auto matrices = FwMatrices{distance, parent, count, tolerance};
        const auto blocks = (count + fw_block - 1) / fw_block;
        threads = std::max(
            1u, std::min<unsigned>(threads, unsigned(std::max<std::size_t>(blocks - 1, 1))));

        // Tarefas de cada fase, reivindicadas por contador atômico (balanceia núcleos de
        // desempenho e de eficiência): fase 2 tem 2(nb - 1) blocos; fase 3, nb - 1 linhas.
        auto tickets = std::vector<std::atomic<std::size_t>>(2 * blocks);
        auto negative = std::atomic<bool>{false};
        auto stop = false;
        std::barrier sync{std::ptrdiff_t(threads),
                          [&]() noexcept { stop = negative.load(std::memory_order_relaxed); }};

        const auto span = [&](std::size_t block) {
            return std::pair{block * fw_block, std::min(count, (block + 1) * fw_block)};
        };
        const auto diagonal_negative = [&](std::size_t block) {
            const auto [begin, end] = span(block);
            for (auto i = begin; i < end; ++i) {
                if (distance[i * count + i] < -tolerance) {
                    return true;
                }
            }
            return false;
        };

        const auto worker = [&](unsigned id) {
            for (auto kb = std::size_t{0}; kb < blocks; ++kb) {
                const auto [k0, k1] = span(kb);

                if (id == 0) {
                    update_block(matrices, k0, k1, k0, k1, k0, k1, true);
                    if (diagonal_negative(kb)) {
                        negative.store(true, std::memory_order_relaxed);
                    }
                }
                sync.arrive_and_wait();
                if (stop) {
                    return;
                }

                // Fase 2: tarefa t < nb - 1 é um bloco da linha kb; as demais, da coluna kb.
                const auto others = blocks - 1;
                for (auto task = tickets[2 * kb].fetch_add(1); task < 2 * others;
                     task = tickets[2 * kb].fetch_add(1)) {
                    const auto other = task % others;
                    const auto block = other < kb ? other : other + 1;
                    const auto [b0, b1] = span(block);
                    if (task < others) {
                        update_block(matrices, k0, k1, b0, b1, k0, k1, true);
                    } else {
                        update_block(matrices, b0, b1, k0, k1, k0, k1, true);
                    }
                }
                sync.arrive_and_wait();

                // Fase 3: cada tarefa é um grupo de `fw_group` blocos de uma linha ib != kb.
                const auto groups = (blocks + fw_group - 1) / fw_group;
                for (auto task = tickets[2 * kb + 1].fetch_add(1); task < others * groups;
                     task = tickets[2 * kb + 1].fetch_add(1)) {
                    const auto row = task / groups;
                    const auto ib = row < kb ? row : row + 1;
                    const auto [i0, i1] = span(ib);
                    const auto first = (task % groups) * fw_group;
                    const auto last = std::min(blocks, first + fw_group);
                    for (auto jb = first; jb < last; ++jb) {
                        if (jb == kb) {
                            continue;
                        }
                        const auto [j0, j1] = span(jb);
                        update_block(matrices, i0, i1, j0, j1, k0, k1, false);
                        if (jb == ib && diagonal_negative(ib)) {
                            negative.store(true, std::memory_order_relaxed);
                        }
                    }
                }
                sync.arrive_and_wait();
                if (stop) {
                    return;
                }
            }
        };

        {
            auto pool = std::vector<std::jthread>{};
            for (auto id = 1u; id < threads; ++id) {
                pool.emplace_back(worker, id);
            }
            worker(0);
        }
        return stop;
    }

  public:
    // Distâncias e árvores de caminhos mínimos entre todos os pares: O(V³) tempo e
    // 12V² bytes de memória (distâncias em double e pais em 32 bits). O algoritmo é em
    // blocos de 64 × 64 e usa `threads` threads (a chamadora é uma delas); com 1, nenhuma
    // thread é criada. O resultado não depende do número de threads.
    // Com ciclo negativo, a função retorna assim que o detecta (ao fim de uma fase em blocos),
    // e as matrizes ficam incompletas: distâncias e pais são inválidos quando negative_cycle
    // é verdadeiro.
    AllPairsPaths floyd_warshall(unsigned threads = 1) const
    {
        require_weights();

        const auto count = std::size_t{vertex_count};
        auto result = AllPairsPaths{};
        result.vertex_count = vertex_count;
        result.distances = std::make_unique_for_overwrite<Weight[]>(count * count);
        result.parents = std::make_unique_for_overwrite<Vertex[]>(count * count);
        auto * const distance = result.distances.get();
        auto * const parent = result.parents.get();

        // Inicialização O(V² + E): só as arestas diretas; entre repetidas, a de menor peso.
        std::fill_n(distance, count * count, no_distance);
        std::fill_n(parent, count * count, no_vertex);
        auto smallest = no_distance;
        for (auto vertex = Vertex{0}; vertex < vertex_count; ++vertex) {
            auto * const row = distance + vertex * count;
            row[vertex] = 0;

            auto position = first_neighbor(vertex);
            while (true) {
                const auto next = next_neighbor(vertex, position);
                if (next == no_vertex) {
                    break;
                }
                const auto weight = weight_before(vertex, position);
                smallest = std::min(smallest, weight);
                if (weight < row[next]) {
                    row[next] = weight;
                    parent[vertex * count + next] = vertex;
                }
            }

            // Um laço negativo é um ciclo negativo: dispensa as V iterações.
            if (row[vertex] < 0) {
                result.negative_cycle = true;
                return result;
            }
        }

        // Otimização de memória: uma única matriz V × V atualizada no lugar, em vez de
        // uma matriz por valor de k. Na iteração k, a linha e a coluna k não mudam, pois
        // d[i][k] + d[k][k] = d[i][k] quando d[k][k] = 0; ler valores já atualizados
        // equivale a ler os da iteração anterior.
        result.negative_cycle = blocked_floyd_warshall(distance, parent, count, tolerance, threads);

        // Sem ciclo de peso zero, os pais já formam árvores. Com todos os pesos positivos, não
        // existe ciclo de peso zero.
        if (!result.negative_cycle && !(smallest > 0)) {
            repair_zero_cycles(distance, parent, count, threads);
        }

        return result;
    }

    // Distâncias de todos os pares por Bellman-Ford: V execuções, uma por destino, em
    // O(V·E) no pior caso com CSR e O(V³) com matriz; memória 12V² bytes (como Floyd-Warshall)
    // mais O(V) por thread. Cada thread reutiliza um BellmanFordWorkspace e escreve a linha do
    // destino que reivindicou (por contador atômico, em blocos); o grafo é só lido.
    // A chamadora é uma das `threads` (com 1, nenhuma thread é criada). O resultado não
    // depende do número de threads. Se alguma execução achar um ciclo negativo, as demais
    // param cedo e negative_cycle é verdadeiro; distâncias e sucessores são então inválidos
    // (como em floyd_warshall). Cada execução só vê ciclos que alcançam seu destino, mas um
    // ciclo alcança os próprios vértices, então a união dos V destinos cobre todos.
    AllPairsToTargets all_pairs_bellman_ford(unsigned threads = 1) const
    {
        require_weights();

        const auto count = std::size_t{vertex_count};
        auto result = AllPairsToTargets{};
        result.vertex_count = vertex_count;
        result.distances = std::make_unique_for_overwrite<Weight[]>(count * count);
        result.nexts = std::make_unique_for_overwrite<Vertex[]>(count * count);
        if (count == 0) {
            return result;
        }

        threads =
            std::max(1u, std::min<unsigned>(threads, unsigned(std::min<std::size_t>(count, 1024))));
        // Blocos pequenos balanceiam destinos de custo desigual sem disputar o contador.
        const auto chunk = std::clamp<std::size_t>(count / (std::size_t{threads} * 16), 1, 16);
        auto ticket = std::atomic<std::size_t>{0};
        auto negative = std::atomic<bool>{false};

        const auto worker = [&] {
            auto work = BellmanFordWorkspace{vertex_count};
            while (!negative.load(std::memory_order_relaxed)) {
                const auto first = ticket.fetch_add(chunk);
                if (first >= count) {
                    return;
                }
                const auto last = std::min(count, first + chunk);
                for (auto target = first; target < last; ++target) {
                    const auto summary = relax_rounds(
                        Vertex(target), std::span{result.distances.get() + target * count, count},
                        std::span{result.nexts.get() + target * count, count}, work);
                    if (summary.negative_cycle) {
                        negative.store(true, std::memory_order_relaxed);
                        return;
                    }
                }
            }
        };

        {
            auto pool = std::vector<std::jthread>{};
            for (auto id = 1u; id < threads; ++id) {
                pool.emplace_back(worker);
            }
            worker();
        }
        result.negative_cycle = negative.load();
        return result;
    }

    // Distâncias e árvores de todos os pares por Johnson: um Bellman-Ford com origem virtual
    // (potenciais) e V buscas de Dijkstra com pesos reponderados. CSR O(V·E + V(V + E) log V)
    // no pior caso; memória 12V² bytes (como floyd_warshall) mais O(V) por thread. Mesmo
    // resultado e semântica de pais de floyd_warshall (árvores enraizadas na origem), dentro
    // da tolerância de arredondamento.
    //
    // Potenciais: relax_rounds em modo virtual (todas as distâncias começam em 0) devolve
    //   h(u) = min(0, menor peso de um passeio que começa em u).
    // Para cada aresta u -> v, h(u) <= w(u, v) + h(v) (um passeio de v estendido por u -> v é
    // um passeio de u, e 0 também vale para h(u)), logo w'(u, v) = w(u, v) + h(v) - h(u) >= 0.
    // Num caminho s -> t, os h dos vértices intermediários se cancelam:
    //   d'(s, t) = d(s, t) + h(t) - h(s)   e portanto   d(s, t) = d'(s, t) - h(t) + h(s).
    // Os h são arredondados (erro até `tolerance`), então w' pode sair -tolerance; vale
    // max(0, w'), o que altera as distâncias em no máximo V · tolerance. Sem pesos negativos,
    // h = 0 e o Bellman-Ford é dispensado.
    // Com ciclo negativo, devolve logo após os potenciais, com negative_cycle verdadeiro e
    // sem matrizes alocadas. `threads` reparte as origens (contador atômico, em blocos); a
    // chamadora é uma delas, e o resultado não depende do número de threads.
    template <class Frontier = HeapFrontier> AllPairsPaths johnson(unsigned threads = 1) const
    {
        require_weights();

        const auto count = std::size_t{vertex_count};
        auto result = AllPairsPaths{};
        result.vertex_count = vertex_count;

        auto potential = std::vector<Weight>(count, 0.0);
        if (negative_weight) {
            auto next = std::vector<Vertex>(count);
            auto work = BellmanFordWorkspace{vertex_count};
            if (relax_rounds(no_vertex, potential, next, work).negative_cycle) {
                result.negative_cycle = true;
                return result;
            }
        }
        if (count == 0) {
            return result;
        }

        result.distances = std::make_unique_for_overwrite<Weight[]>(count * count);
        result.parents = std::make_unique_for_overwrite<Vertex[]>(count * count);

        threads =
            std::max(1u, std::min<unsigned>(threads, unsigned(std::min<std::size_t>(count, 1024))));
        const auto chunk = std::clamp<std::size_t>(count / (std::size_t{threads} * 16), 1, 16);
        auto ticket = std::atomic<std::size_t>{0};

        const auto worker = [&] {
            auto frontier = Frontier{vertex_count};
            for (auto first = ticket.fetch_add(chunk); first < count;
                 first = ticket.fetch_add(chunk)) {
                const auto last = std::min(count, first + chunk);
                for (auto source = first; source < last; ++source) {
                    const auto row = std::span{result.distances.get() + source * count, count};
                    dijkstra_search(
                        Vertex(source), row,
                        std::span{result.parents.get() + source * count, count}, frontier,
                        [](Vertex, Vertex, Weight) {},
                        [&](Vertex from, Vertex to, Weight weight) {
                            return std::max(0.0, weight + potential[to] - potential[from]);
                        });
                    // d = d' - h(t) + h(s); inalcançáveis continuam infinitos.
                    for (auto target = std::size_t{0}; target < count; ++target) {
                        if (row[target] != no_distance) {
                            row[target] += potential[source] - potential[target];
                        }
                    }
                }
            }
        };

        {
            auto pool = std::vector<std::jthread>{};
            for (auto id = 1u; id < threads; ++id) {
                pool.emplace_back(worker);
            }
            worker();
        }
        return result;
    }

    // Procura um ciclo na floresta de sucessores `next` a partir dos vértices alterados.
    // Lema: sempre vale distance[p] >= distance[next[p]] + w(p, next[p]), pois as distâncias
    // só diminuem. Quando a última aresta p -> v de um ciclo foi gravada, a melhora foi
    // estrita (distance[p] antigo > distance[v] + w + tolerance); somando as desigualdades ao
    // longo do ciclo, 0 > soma dos pesos (as demais valem a menos de erros muito menores que
    // `tolerance`). Logo, qualquer ciclo em `next` é negativo. Um ciclo novo
    // contém algum vértice alterado na rodada, então basta partir deles.
    // O(V) por chamada: cada vértice é selado no máximo uma vez, e um selo desta chamada
    // encerra a caminhada. Selos de chamadas anteriores não valem, pois `next` mudou. O destino
    // tem next == no_vertex enquanto não melhora, e então encerra a caminhada.
    static bool has_cycle(std::span<const Vertex> next, std::span<const Vertex> changed,
                          std::vector<std::uint32_t> & stamps, std::uint32_t & stamp)
    {
        // Antes de estourar o contador, os selos são zerados: O(V) amortizado.
        if (changed.size() >= std::numeric_limits<std::uint32_t>::max() - stamp) {
            std::ranges::fill(stamps, 0);
            stamp = 0;
        }

        const auto first_stamp = stamp + 1;
        for (const auto start : changed) {
            const auto walk = ++stamp;
            for (auto vertex = start; vertex != no_vertex; vertex = next[vertex]) {
                if (stamps[vertex] == walk) {
                    return true;
                }
                if (stamps[vertex] >= first_stamp) {
                    break; // já percorrido nesta chamada, sem ciclo
                }
                stamps[vertex] = walk;
            }
        }
        return false;
    }

    // components e diameter assumem arestas simétricas (componentes conexos e distância
    // em ambos os sentidos); em grafo direcionado, a BFS alcançável não os define.
    void require_undirected(const char * operation) const
    {
        if (directed) {
            throw std::logic_error{std::string{operation} +
                                   " só está definido para grafos não direcionados"};
        }
    }

    void require_weights() const
    {
        if (!weights_) {
            throw std::logic_error{"o grafo não possui pesos"};
        }
    }

    template <class Item> std::vector<Vertex> count_degrees(std::span<const Item> edges)
    {
        // Inicialização O(V) e uma passagem O(E): graus e, com pesos, a marca negative_weight.
        auto degrees = std::vector<Vertex>(vertex_count, 0);
        auto largest = Weight{0};
        for (const auto & edge : edges) {
            ++degrees[std::get<0>(edge)];
            ++degrees[std::get<1>(edge)];

            if constexpr (weighted<Item>) {
                // A negação também classifica NaN como peso inválido para Dijkstra.
                negative_weight = negative_weight || !(std::get<2>(edge) >= 0);
                largest = std::max(largest, std::abs(std::get<2>(edge)));
            }
        }
        if constexpr (weighted<Item>) {
            tolerance = 8 * std::numeric_limits<Weight>::epsilon() * vertex_count * largest;
        }
        return degrees;
    }

    template <class Item> static constexpr bool weighted = std::is_same_v<Item, WeightedEdge>;

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

    static void unmark(std::span<std::uint64_t> visited, Vertex vertex)
    {
        visited[vertex / 64] &= ~(std::uint64_t{1} << (vertex % 64));
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

    template <class Item> void build(std::span<const Item> edges)
    {
        // O temporário O(V) é liberado antes da matriz O(V²).
        compute_statistics(count_degrees(edges));

        const auto count = std::size_t{vertex_count};
        // A matriz fixa precisa começar zerada: O(V²) tempo e memória.
        matrix_ = std::make_unique<std::uint8_t[]>(count * count);
        if constexpr (weighted<Item>) {
            // Cada peso só é lido depois que o byte correspondente indica a aresta.
            weights_ = std::make_unique_for_overwrite<Weight[]>(count * count);
        }

        // Até duas escritas por aresta: O(E). No grafo direcionado, só a célula (u, v).
        for (const auto & edge : edges) {
            const auto forward = std::size_t{std::get<0>(edge)} * count + std::get<1>(edge);
            const auto backward = std::size_t{std::get<1>(edge)} * count + std::get<0>(edge);

            if constexpr (weighted<Item>) {
                // Entre arestas repetidas, a célula guarda o menor peso.
                const auto weight = std::get<2>(edge);
                if (matrix_[forward] == 0 || weight < weights_[forward]) {
                    weights_[forward] = weight;
                    if (!directed) {
                        weights_[backward] = weight;
                    }
                }
            }
            matrix_[forward] = 1;
            if (!directed) {
                matrix_[backward] = 1;
            }
        }
        memory_bytes = sizeof(Graph) + count * count * (1 + (weights_ ? sizeof(Weight) : 0));
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

    Weight weight_before(Vertex vertex, Vertex position) const
    {
        // A posição fica uma célula depois do vizinho devolvido: O(1).
        return weights_[std::size_t{vertex} * vertex_count + position - 1];
    }

    static Vertex first_predecessor(Vertex) { return 0; }

    Vertex next_predecessor(Vertex vertex, Vertex & position) const
    {
        // Sem direção, a linha e a coluna coincidem e a linha usa memchr.
        if (!directed) {
            return next_neighbor(vertex, position);
        }
        // Coluna com passo V: O(V) por coluna completa, sem a localidade da linha.
        const auto count = std::size_t{vertex_count};
        for (; position < vertex_count; ++position) {
            if (matrix_[std::size_t{position} * count + vertex] != 0) {
                return position++;
            }
        }
        return no_vertex;
    }

    Weight weight_before_predecessor(Vertex vertex, Vertex position) const
    {
        // A célula (predecessor, vertex) guarda o peso da aresta que chega: O(1).
        return weights_[std::size_t{position - 1} * vertex_count + vertex];
    }

    std::unique_ptr<std::uint8_t[]> matrix_;
    std::unique_ptr<Weight[]> weights_;

#else

    // Vetor de adjacências: deslocamentos, vizinhos e, com pesos, um vetor paralelo.
    struct Csr {
        std::unique_ptr<Vertex[]> offsets;
        std::unique_ptr<Vertex[]> neighbors;
        std::unique_ptr<Weight[]> weights;
        std::size_t size = 0;
    };

    template <class Item> void build(std::span<const Item> edges)
    {
        // O(V + E); os graus totais só alimentam as estatísticas.
        compute_statistics(count_degrees(edges));

        // Sem direção, cada aresta entra nas duas listas. Com direção, `forward_` guarda as
        // arestas que saem de cada vértice e `backward_`, as que chegam, usadas por
        // Bellman-Ford para propagar distâncias até o destino.
        forward_ = make_csr(edges, true, !directed);
        if (directed) {
            backward_ = make_csr(edges, false, true);
        }
        weights_ = forward_.weights.get();

        const auto csr_bytes = [&](const Csr & csr) {
            return csr.offsets ? (std::size_t{vertex_count} + 1 + csr.size) * sizeof(Vertex) +
                                     (csr.weights ? csr.size * sizeof(Weight) : 0)
                               : 0;
        };
        memory_bytes = sizeof(Graph) + csr_bytes(forward_) + csr_bytes(backward_);
    }

    // O(V + E): conta, soma prefixada e preenchimento na ordem da entrada.
    template <class Item>
    Csr make_csr(std::span<const Item> edges, bool forward, bool backward) const
    {
        auto cursor = std::vector<Vertex>(vertex_count, 0);
        for (const auto & edge : edges) {
            cursor[std::get<0>(edge)] += forward;
            cursor[std::get<1>(edge)] += backward;
        }

        auto csr = Csr{};
        csr.size = edges.size() * (std::size_t{forward} + backward);
        // Os arrays fixos serão completamente escritos durante a construção.
        csr.offsets = std::make_unique_for_overwrite<Vertex[]>(std::size_t{vertex_count} + 1);
        csr.neighbors = std::make_unique_for_overwrite<Vertex[]>(csr.size);
        if constexpr (weighted<Item>) {
            csr.weights = std::make_unique_for_overwrite<Weight[]>(csr.size);
        }
        csr.offsets[0] = 0;

        // Soma prefixada e inicialização dos cursores: O(V).
        for (auto vertex = Vertex{0}; vertex < vertex_count; ++vertex) {
            csr.offsets[vertex + 1] = csr.offsets[vertex] + cursor[vertex];
            cursor[vertex] = csr.offsets[vertex];
        }

        // Preenchimento O(E); cada peso usa o mesmo índice do vizinho correspondente.
        const auto place = [&](Vertex from, Vertex to, [[maybe_unused]] const Item & edge) {
            const auto index = cursor[from]++;
            csr.neighbors[index] = to;
            if constexpr (weighted<Item>) {
                csr.weights[index] = std::get<2>(edge);
            }
        };
        for (const auto & edge : edges) {
            if (forward) {
                place(std::get<0>(edge), std::get<1>(edge), edge);
            }
            if (backward) {
                place(std::get<1>(edge), std::get<0>(edge), edge);
            }
        }
        return csr;
    }

    Vertex first_neighbor(Vertex vertex) const { return forward_.offsets[vertex]; }

    Vertex next_neighbor(Vertex vertex, Vertex & position) const
    {
        // Consulta e avanço O(1) por incidência armazenada.
        if (position == forward_.offsets[vertex + 1]) {
            return no_vertex;
        }
        return forward_.neighbors[position++];
    }

    Weight weight_before(Vertex, Vertex position) const
    {
        // A posição fica uma incidência depois do vizinho devolvido: O(1).
        return weights_[position - 1];
    }

    // Sem direção, quem chega é vizinho: as duas listas coincidem.
    const Csr & incoming() const { return directed ? backward_ : forward_; }

    Vertex first_predecessor(Vertex vertex) const { return incoming().offsets[vertex]; }

    Vertex next_predecessor(Vertex vertex, Vertex & position) const
    {
        const auto & csr = incoming();
        if (position == csr.offsets[vertex + 1]) {
            return no_vertex;
        }
        return csr.neighbors[position++];
    }

    Weight weight_before_predecessor(Vertex, Vertex position) const
    {
        return incoming().weights[position - 1];
    }

    Csr forward_;
    Csr backward_;
    // Atalho para os pesos de `forward_`; nulo em grafos sem pesos.
    const Weight * weights_ = nullptr;

#endif
};

} // namespace cos_graph
