# Decisões de projeto

O fluxo completo de informações é direto:

```text
arquivo de texto -> pares ou triplas numéricas -> grafo imutável -> algoritmos -> relatório
```

`file_reader.hpp` lê um cabeçalho e pares ou triplas numéricas sem interpretar
seu significado. Os programas das Partes 1, 2 e 3 convertem os identificadores que
começam em `1` para os índices internos que começam em `0` e formatam os
resultados.
`graph.hpp` possui a topologia escolhida, as estatísticas e os algoritmos.

## Representação

`COS_MATRIX` escolhe a representação durante a compilação. Cada executável
contém CSR ou matriz de bytes, nunca as duas. Não existem marca em tempo de
execução, variante, hierarquia de classes, chamada virtual ou política de
armazenamento.

Vértices densos em `uint32_t` atendem ao formato da entrada e reduzem a memória
usada em máquinas de 64 bits. A CSR guarda vetores imutáveis de deslocamentos e
vizinhos na ordem das arestas da entrada. A matriz usa um byte por célula e
`memchr` para pular sequências vazias. Palavras de 64 bits guardam as marcas de
visita, com um bit por vértice.

As estatísticas são calculadas pelas incidências da entrada antes da construção
da topologia. Assim, arestas repetidas e laços mantêm o grau esperado mesmo
quando a matriz booleana reúne células duplicadas.

## Pesos

`Weight` é `double` e `WeightedEdge` é a tripla `(u, v, peso)`. O grafo tem um
construtor para `Edge` e outro para `WeightedEdge`; os dois usam a mesma
construção, que só grava pesos quando o tipo da aresta os possui. Grafos sem
pesos não alocam o vetor de pesos; o objeto só ganha um ponteiro nulo e um bool.
A presença de pesos é verificada em tempo de execução apenas pelo ponteiro
`weights_`, sem variante nem chamada virtual.

Na CSR, `weights_` é um vetor paralelo a `neighbors_`: cada peso é gravado no
mesmo índice do vizinho correspondente, e arestas repetidas continuam
separadas. Na matriz, a matriz de bytes e o `memchr` continuam iguais, e uma
segunda matriz `V × V` de `double` guarda os pesos. Entre arestas repetidas, a
célula fica com o menor peso, que é o único relevante para caminhos mínimos.

A matriz com pesos ocupa `9V²` bytes. Com `V = 10⁵`, isso dá cerca de 90 GB (84 GiB);
por isso, nos grafos da Parte 2, a matriz serve apenas aos testes e a grafos
pequenos.

Durante a contagem dos graus, que já percorre todas as arestas, o grafo marca
`negative_weight`. A condição `!(peso >= 0)` também trata `NaN` como peso
inválido para Dijkstra.

## Algoritmos

BFS e DFS recebem uma função visitante com `(vertice, pai, nivel)`. O visitante
produz somente o resultado necessário ao chamador e é incorporado pelo
compilador ao laço da busca, sem chamada virtual ou indireta.

A BFS usa uma fila fixa e não inicializada de `Vertex[V]`, além das marcas
compactadas. A DFS usa uma pilha iterativa de `(vertice, proximo_vizinho)`,
preserva a ordem da versão recursiva e não consome a pilha de chamadas do
processo. Componentes e diâmetro exato reutilizam seus vetores de trabalho nas
buscas repetidas.

Uma busca com CSR custa `O(V + E)`; com matriz, `O(V²)`. O diâmetro exato custa
`O(V(V + E))` com CSR e `O(V³)` com matriz. A memória temporária das buscas é
`O(V)` nas duas representações.

## Direção

A direção é um parâmetro do construtor (`Direction`), escolhido em tempo de
execução e guardado no campo `directed`. Sem ela, o grafo é não direcionado e
cada aresta vale nos dois sentidos. Com ela, a aresta `(u, v)` vai de `u` para
`v`.

Na CSR, um grafo não direcionado tem uma lista de adjacências, com cada aresta
nas duas pontas. Um grafo direcionado tem duas: `forward_`, com as arestas que
saem de cada vértice, e `backward_`, com as que chegam. BFS, DFS e Dijkstra
percorrem `forward_`; Bellman-Ford propaga distâncias até o destino e por isso
percorre as arestas que chegam, em `backward_`. Sem direção, as duas listas
coincidem e `backward_` não é alocada. Cada lista guarda `V + 1` deslocamentos
e, por aresta armazenada, um vizinho de 4 bytes e um peso de 8 bytes.

Na matriz, a célula `(u, v)` representa a aresta de `u` para `v`. No grafo
direcionado, só essa célula é gravada; sem direção, também a `(v, u)`. As
arestas que saem de `u` estão na linha `u`, percorrida com `memchr`. As que
chegam em `v` estão na coluna `v`, percorrida com passo `V`, sem a localidade da
linha. Sem direção, a coluna coincide com a linha e a busca usa `memchr`.

`components()` e `diameter()` só têm definição em grafos não direcionados: com
`directed` verdadeiro, lançam `std::logic_error`. A BFS alcançável de um grafo
direcionado não define componentes conexas nem uma distância simétrica.

`memoria_bytes` soma `sizeof(Graph)` e as estruturas de cada representação: na
CSR, `forward_` mais `backward_`; na matriz, `V²` bytes da matriz mais `8V²` dos
pesos, igual com ou sem direção.

As estatísticas de grau continuam usando o grau total: cada aresta soma um às
duas pontas, entrando ou saindo. Em um grafo direcionado, o grau de um vértice é
a soma dos graus de entrada e de saída.

## Dijkstra

`dijkstra<Frontier>(origem, visitante)` aloca os vetores de distância e de pai
e chama `dijkstra_search`, o único corpo do algoritmo (Johnson usa o mesmo
corpo; veja abaixo). Ele examina os vizinhos pelas mesmas
funções usadas por BFS e DFS e delega à fronteira apenas três operações:
construção com `V`, `push(vertice, distancia)` para inserir ou reduzir uma
estimativa e `pop()` para extrair a menor. O visitante recebe
`(vertice, pai, distancia)` uma vez por vértice alcançado, quando ele é
fechado, em ordem não decrescente de distância.

- `VectorFrontier` guarda um vetor de estimativas. `push` custa `O(1)` e `pop`
  procura o mínimo em `O(V)`. Com CSR, Dijkstra custa `O(V² + E)`.
- `HeapFrontier` é um heap binário indexado. Cada entrada guarda a chave e o
  vértice; um vetor de posições permite reduzir a chave de um vértice que já
  está no heap. `push` e `pop` custam `O(log V)`. Com CSR, Dijkstra custa
  `O((V + E) log V)`.
- `RadixFrontier` é um heap radix, descrito na seção sobre Johnson. Também
  serve a `dijkstra<RadixFrontier>`.

Não há marca de vértices fechados. A relaxação usa comparação estrita: com
pesos não negativos, um vértice fechado tem distância menor ou igual à do
vértice atual e, portanto, nunca volta à fronteira. É nesse ponto que a
restrição de pesos não negativos é usada.

Antes de começar, Dijkstra lança `std::logic_error` se o grafo não tiver pesos
e `std::domain_error` se algum peso for negativo. A mensagem do segundo erro
indica Bellman-Ford ou Floyd-Warshall para pesos negativos. O programa da Parte
2 registra essa mensagem no relatório em vez de falhar.

## Bellman-Ford

`bellman_ford(destino)` calcula a distância de todos os vértices até o destino,
e não a partir de uma origem. Por isso a relaxação examina as arestas que
chegam em cada vértice: se `previous -> vertex` melhora o caminho de `previous`
até o destino, `distance[previous]` recebe `distance[vertex]` mais o peso da
aresta e `next[previous]` recebe `vertex`. Os ponteiros `next` formam uma árvore
com raiz no destino; o caminho de um vértice até ele é obtido seguindo `next`.
O resultado, `PathsToTarget`, traz `distance`, `next`, o número de `rodadas` e
`negative_cycle`.

Há um único corpo, `relax_rounds`, que recebe os vetores `distance` e `next` (V
posições cada) e um `BellmanFordWorkspace` do chamador. O espaço de trabalho
reúne as listas de ativos (`active` e `upcoming`), o bitmap de marcas e os selos
da busca de ciclos, `O(V)` no total. Cada chamada reinicializa `distance` e
`next` em `O(V)` e limpa as marcas que uma execução anterior, encerrada no meio
de uma rodada, tenha deixado; nada é alocado. `bellman_ford(destino)` cria um
espaço de trabalho e os vetores do resultado a cada chamada. As execuções
repetidas de `all_pairs_bellman_ford` reutilizam o espaço de trabalho dentro de
cada thread.

As duas otimizações vistas em aula são:

1. Se uma rodada não muda nenhuma distância, o algoritmo para.
2. Só os vértices cuja distância mudou na rodada anterior podem melhorar
   outros. A rodada seguinte examina apenas as arestas que chegam neles. A
   lista de vértices ativos não tem repetições porque cada vértice é marcado em
   um bitmap ao entrar nela; as marcas são limpas ao fim da rodada.

As atualizações ficam visíveis dentro da própria rodada: um vértice processado
depois já lê a distância reduzida. Assim, o número de `rodadas` depende da ordem
em que as arestas são percorridas, que difere entre a CSR e a matriz. As
distâncias finais são iguais nas duas representações, mas `rodadas` pode
diferir.

### Ciclo negativo

Sem ciclo negativo, um caminho mínimo simples tem no máximo `V - 1` arestas.
Portanto, se a rodada `V` ainda tem vértices ativos, existe ciclo negativo que
alcança o destino. Esse é o critério de reserva; três verificações antecipam a
resposta:

- **Ciclo entre os sucessores.** Depois de cada rodada, uma busca percorre os
  ponteiros `next` a partir dos vértices alterados. Vale sempre
  `distance[p] >= distance[next[p]] + peso(p, next[p])`, porque as distâncias só
  diminuem. Quando a última aresta `p -> v` de um ciclo foi gravada, a melhora
  foi estrita. Somando as desigualdades ao longo do ciclo, obtém-se
  `0 > soma dos pesos`: todo ciclo entre os sucessores tem peso negativo. Um
  ciclo novo contém algum vértice alterado na rodada, então basta partir deles.
- **Selos.** Um vetor de `uint32_t` marca cada vértice visitado pela busca com o
  número da caminhada. Um selo da caminhada atual indica ciclo; um selo de outra
  caminhada da mesma chamada indica trecho já percorrido sem ciclo e encerra a
  caminhada. O contador cresce entre rodadas sem limpeza e só zera o vetor antes
  de estourar. Cada chamada custa `O(V)`.
- **Melhora do próprio destino.** O destino começa com distância `0`. Se uma
  relaxação melhora estritamente essa distância, existe um passeio fechado de
  peso negativo que passa por ele, e esse passeio contém um ciclo negativo.

`has_negative_cycle()` usa o mesmo núcleo (`relax_rounds` com `no_vertex` no
lugar do destino), com um vértice virtual e uma aresta de peso `0` ligada a
cada vértice. Como as distâncias são sempre até o destino, a aresta vai de cada
vértice ao vértice virtual. A rodada dessa aresta já está feita: todas as
distâncias valem `0` e todos os vértices começam ativos. Não há destino real,
então a verificação da melhora do destino não se aplica.

A diferença entre as duas consultas é o alcance. `bellman_ford` só enxerga
ciclos negativos de onde o destino é alcançável, pois a propagação parte dele
pelas arestas que chegam. Um ciclo negativo que não alcança o destino não afeta
as distâncias até ele e não é detectado. `has_negative_cycle` encontra ciclos em
qualquer ponto do grafo, porque todos os vértices partem ativos.

### Complexidade

- Pior caso: CSR `O(V·E)`; matriz `O(V³)`, pois examinar as arestas que chegam
  em um vértice custa `O(V)`.
- Com `R` rodadas e as otimizações, o custo é o das arestas que chegam nos
  vértices ativos em cada rodada.
- A busca de ciclos entre sucessores custa `O(V)` por rodada.
- Memória temporária `O(V)`: distâncias, sucessores, vértices ativos, bitmap e
  selos.
- Na matriz com direção, a leitura por coluna com passo `V` torna cada vértice
  ativo mais caro do que na CSR.

### Todos os pares por Bellman-Ford

`all_pairs_bellman_ford(threads)` executa `bellman_ford` uma vez por destino e
devolve um `AllPairsToTargets`: duas matrizes `V × V`, de distâncias e de
sucessores, com uma linha por destino. `distance(from, to)` e `next(from, to)`
leem a célula `to · V + from`. Cada execução escreve a linha do seu destino, que
é contígua, direto na matriz do resultado. A memória é `12·V²` bytes, como no
Floyd-Warshall, mais `O(V)` por thread. O pior caso é `O(V·E)` por destino com
CSR, ou `O(V²·E)` no total.

Cada thread cria um `BellmanFordWorkspace` e reivindica destinos por um contador
atômico, em blocos de `clamp(V / (16 · threads), 1, 16)` destinos. Blocos
pequenos equilibram destinos de custo desigual sem disputar o contador. O grafo
é só lido, e cada linha tem um único escritor. A thread chamadora é uma das
`threads`; com `1`, nenhuma thread é criada. O número de threads é limitado a `V`
e a `1024`, e o resultado não depende dele.

Se uma execução acha ciclo negativo, ela marca um sinalizador atômico; as demais
threads verificam o sinalizador antes de cada bloco e terminam. `negative_cycle`
fica verdadeiro e as matrizes ficam inválidas, como no Floyd-Warshall. Cada
execução só vê os ciclos que alcançam o seu destino, mas um ciclo alcança os
próprios vértices; a união dos `V` destinos cobre todos os ciclos negativos.

`AllPairsToTargets` é um tipo à parte, e não reaproveita `AllPairsPaths`, por
dois motivos. Os campos têm semânticas diferentes: Bellman-Ford guarda, para cada
destino `t`, o sucessor de cada origem rumo a `t` (árvore com raiz em `t`),
enquanto `AllPairsPaths` guarda pais em árvores com raiz na origem. Converter
exigiria transpor as duas matrizes, com acessos de passo `V` e `O(V²)` de tempo e
de memória extras, e daria o nome `parent` a duas coisas distintas.

## Floyd-Warshall

`floyd_warshall(threads = 1)` devolve, em `AllPairsPaths`, duas matrizes `V × V`:
distâncias (`double`) e pais (`uint32_t`). A memória é `12·V²` bytes (`8·V²` de
distâncias e `4·V²` de pais) e o tempo, `O(V³)`.

### Matriz única e pais

A matriz de distâncias é única e atualizada no lugar, em vez de uma matriz por
valor de `k`; essa é a otimização de memória do enunciado. Ler valores já
atualizados é seguro porque a linha `k` e a coluna `k` não mudam na iteração
`k`: `d[i][k] + d[k][k] = d[i][k]` quando `d[k][k] = 0`. Por isso `relax_rows`
também pula a linha `k`. A condição `d[k][k] = 0` vale enquanto não há ciclo
negativo; com ciclo negativo, a execução termina cedo (veja abaixo).

A linha `i` da matriz de pais descreve a árvore de caminhos mínimos com raiz em
`i`: `parent(i, j)` é o pai de `j` nessa árvore, e vale `no_vertex` na raiz e nos
vértices inalcançáveis. Na inicialização, `parent(i, j) = i` para cada aresta
direta (entre arestas repetidas, a de menor peso). Quando `k` melhora `d[i][j]`,
`parent(i, j)` passa a ser `parent(k, j)`: o último trecho do caminho de `i` a
`j` é o último trecho do caminho de `k` a `j`.

### Blocos

A versão simples lê e escreve `12·V²` bytes a cada `k`. Com `V` grande, a matriz
não cabe na cache, e esse tráfego passa a ser o gargalo. A implementação divide
as matrizes em blocos de `64 × 64` (`fw_block`); um bloco ocupa 48 KiB (`64 · 64`
células de 12 bytes) e é reutilizado por 64 valores de `k` seguidos antes de sair
da cache. Para cada bloco diagonal `kb`, com `k` entre `k0` e `k1`:

1. **Fase 1:** atualiza o bloco `(kb, kb)`, com `k` como laço externo (a ordem do
   algoritmo clássico).
2. **Fase 2:** atualiza os blocos da linha `kb` e da coluna `kb`, que usam o
   bloco diagonal já pronto. Também com `k` como laço externo, pois a linha `k` ou
   a coluna `k` pertence ao próprio bloco.
3. **Fase 3:** atualiza os demais blocos `(ib, jb)`, que só leem a linha `kb` e a
   coluna `kb` já prontas. Aqui `i` é o laço externo e `k` o interno, o que mantém
   o trecho da linha `i` na cache enquanto todos os `k` do bloco o percorrem.

Cada fase termina em uma barreira. As três fases juntas fazem as mesmas
relaxações do algoritmo clássico, só que em outra ordem.

### Vetorização

`relax_segment` relaxa um trecho de linha por `k`:
`row[to] = min(row[to], to_k + through[to])`, com o pai acompanhando a melhora.
Todas as leituras (`row`, `row_parent`, `through_parent`) são copiadas para
variáveis locais antes das duas seleções (`?:`). Com leituras dentro do `?:`, o
compilador as transforma em escritas condicionais e não vetoriza. Sem desvios, o
laço é vetorizado automaticamente, com uma checagem de alias em tempo de
execução; não há intrínsecas nem código específico de arquitetura. Antes do
trecho, `relax_rows` pula a linha `i` cujo `d[i][k]` é infinito, pois nenhum
caminho por `k` a melhora.

### Threads

`threads` é limitado a `max(1, min(threads, blocos − 1))`. A thread chamadora é
uma delas; com `threads = 1`, nenhuma thread é criada. Em cada fase, as tarefas
são reivindicadas por um contador atômico (um par de contadores por `kb`):

- fase 2: `2(nb − 1)` tarefas, cada uma um bloco da linha ou da coluna `kb`;
- fase 3: cada tarefa é um grupo de até `fw_group = 4` blocos consecutivos de uma
  linha de blocos `ib ≠ kb`. Tarefas pequenas equilibram núcleos de desempenho
  diferente, e os blocos do mesmo grupo reaproveitam a coluna `kb` da linha.

A fase 1 roda só na thread de índice 0, e as demais esperam na barreira. Há três
barreiras por `kb`, em um `std::barrier` com uma função de conclusão. A função
roda uma vez por barreira, em uma só thread, e copia o sinalizador atômico
`negative` para a variável comum `stop`. Todas as threads leem `stop` depois da
barreira, então decidem juntas se continuam. O resultado não depende do número de
threads, porque as tarefas de uma fase escrevem em blocos disjuntos.

### Saída antecipada

Um laço negativo na inicialização (`d[v][v] < 0`) encerra a função antes das
iterações. Depois, só as fases 1 e 3 escrevem na diagonal; a fase 1 confere o
bloco `(kb, kb)` e a fase 3 confere cada bloco `(ib, ib)` que atualiza. Uma
diagonal abaixo de `−tolerância` marca `negative`, e a função de conclusão
transforma isso em `stop` na barreira seguinte. As threads retornam depois da
barreira da fase 1 ou da fase 3. As matrizes ficam incompletas, e
`negative_cycle` fica verdadeiro.

### Pais em ciclos de peso zero

Com a ordem em blocos, os empates entre dois caminhos de mesmo peso que passam
por um ciclo de peso zero podem ser resolvidos em sentidos opostos, e os pais de
uma linha formam um ciclo em vez de uma árvore. Isso acontece também com pesos
inteiros, então não é erro de arredondamento. As distâncias continuam corretas.

`repair_zero_cycles` corrige os pais. Para cada linha, uma caminhada pelos pais
procura ciclos, em `O(V)` por linha. As linhas com ciclo são refeitas por uma
busca em largura a partir da origem pelas arestas justas (`d[i][a] + w = d[i][j]`),
que sempre produz uma árvore: `O(V + E)` por linha afetada na CSR. As arestas
justas aceitam o maior entre `1e-9` relativo e `2 · tolerância`, por causa do
arredondamento. Cada thread usa dois vetores de `V` posições. As linhas são
independentes e divididas entre as threads por um contador atômico.

A passagem roda quando não há ciclo negativo e o menor peso de aresta não é
positivo (`!(smallest > 0)`): com todos os pesos positivos, não existe ciclo de
peso zero. Nos demais casos, ela custa ao menos `O(V²)`, pela detecção, mesmo que
nenhuma linha precise ser refeita.

## Tolerância numérica

Os pesos são `double`, e a soma de decimais como `0,1 + 0,2 − 0,3` não dá exatamente
`0`. Em ciclos cuja soma decimal é `0`, o arredondamento produzia uma "melhora"
de 1 ulp a cada volta, e então um ciclo negativo falso ou pais em ciclo. Esses
falsos ciclos negativos apareceram nos dados; ao converter os pesos para inteiros
(escala fixa), eles desapareceram, o que aponta o arredondamento como causa.

Por isso o grafo calcula, uma vez, na contagem dos graus, a margem

```text
tolerance = 8 · ε · V · max|w|
```

com `ε = std::numeric_limits<double>::epsilon()` (`2,2e-16`) e `max|w|` o maior
peso em módulo. Em grafos sem pesos, vale `0`. Uma relaxação só vale se melhora a
distância em mais que `tolerance`.

Justificativa, que é uma heurística, e não um limite de pior caso:

- Um caminho tem até `V − 1` arestas, e cada soma em `double` erra no máximo
  `ε/2` do valor da soma. Se as somas parciais são da ordem de `max|w|`, o erro de
  um caminho fica abaixo de `(ε/2) · V · max|w|`.
- O fator `8` cobre somas parciais até 16 vezes maiores que `max|w|` e a
  comparação de dois caminhos (dois erros).
- Com somas parciais muito maiores que `max|w|`, o limite pode ser excedido; a
  margem não cobre esse caso.
- Em troca, diferenças reais menores que `tolerance` não são distinguidas. Para
  pesos com duas casas decimais, a menor melhora real é `0,01`, muito acima da
  margem (por exemplo, cerca de `6,6e-10` com `V = 25000` e `max|w| = 15`).

Onde a margem é usada:

- `relax_rounds` (Bellman-Ford): `candidate < distance[previous] − tolerance`. O
  lema da busca de ciclos entre sucessores também depende dela: a última melhora
  de um ciclo é estrita por mais que `tolerance`, e as demais desigualdades valem
  a menos de erros muito menores.
- `relax_segment` (Floyd-Warshall): `candidate < current − tolerance`.
- Detecção de ciclo negativo no Floyd-Warshall: `d[i][i] < −tolerance`.
- Arestas justas de `repair_zero_cycles`: `2 · tolerance`, junto do `1e-9`
  relativo.
- Johnson: os potenciais vêm de `relax_rounds`, e o peso reponderado usa
  `max(0, w')` (veja a próxima seção).

Onde ela não é usada, de propósito:

- **Dijkstra** (`dijkstra_search`): a comparação é estrita e sem margem. Os
  pesos não são negativos, então não há ciclo negativo a detectar, e a comparação
  estrita basta para que um vértice já extraído nunca volte à fronteira.
- **Inicialização do Floyd-Warshall**: o peso de uma aresta é comparado com
  outro peso de entrada e com a distância `0` da diagonal, sem somas. Não há
  arredondamento a absorver, e o laço negativo (`d[v][v] < 0`) é detectado com a
  comparação exata.

## Johnson e RadixFrontier

`johnson<Frontier>(threads)` é um extra, além do que o enunciado pede. Ele
devolve um `AllPairsPaths`, com as mesmas matrizes e a mesma semântica de pais do
Floyd-Warshall (árvores com raiz na origem), dentro da tolerância de
arredondamento; em empates, os pais podem diferir. Serve de comparação com o
Floyd-Warshall e com o todos-pares por Bellman-Ford.

### Potenciais

Se há peso negativo, `relax_rounds` roda no modo virtual (o mesmo de
`has_negative_cycle`): todas as distâncias começam em `0` e todos os vértices
começam ativos. Como as distâncias do Bellman-Ford são sempre até o destino,
esse modo equivale a um vértice virtual com uma aresta de peso `0` saindo de cada
vértice (e não chegando, como no Johnson clássico). O resultado é

```text
h(u) = min(0, menor peso de um passeio que começa em u)
```

Para toda aresta `u -> v`, `h(u) ≤ w(u, v) + h(v)`: um passeio de `v`, estendido
por `u -> v`, é um passeio de `u`, e `0` também vale para `h(u)`. Logo

```text
w'(u, v) = w(u, v) + h(v) − h(u) ≥ 0
```

Em um caminho `s -> t`, os `h` dos vértices intermediários se cancelam:
`d'(s, t) = d(s, t) + h(t) − h(s)`, e portanto
`d(s, t) = d'(s, t) − h(t) + h(s)`. O sinal é o oposto da convenção clássica
(`w + h(u) − h(v)`, com `h` a distância a partir da origem virtual) porque aqui
`h` é a distância até o vértice virtual. Os `h` são arredondados, então `w'`
pode sair `−tolerance`; o código usa `max(0, w')`, o que altera as distâncias
em no máximo `V · tolerance`. Sem pesos negativos, `h = 0` e o Bellman-Ford é
dispensado. Com ciclo negativo, `johnson` devolve logo após os potenciais, com
`negative_cycle` verdadeiro e sem alocar as matrizes.

### Buscas

As `V` buscas usam `dijkstra_search`, o mesmo corpo de `dijkstra`. A busca recebe
`distance` e `parent` (uma linha de cada matriz, escrita direto no resultado), a
fronteira e um functor `reweigh(from, to, w)` com o peso usado na aresta. Na
`dijkstra` pública, ele é a identidade; em Johnson, é `max(0, w + h(to) − h(from))`.
Como é parâmetro de template, o functor é incorporado ao laço. Depois de cada
busca, a linha é corrigida por `d = d' + h(s) − h(t)`; inalcançáveis continuam
infinitos. Os pais não mudam, porque a árvore das buscas já é a árvore de
caminhos mínimos do grafo original.

Cada thread cria a própria fronteira e a reutiliza nas origens que reivindica por
contador atômico, em blocos de `clamp(V / (16 · threads), 1, 16)`. A thread
chamadora é uma das `threads`; o número é limitado a `V` e a `1024`, e o resultado
não depende dele. A memória é `12·V²` bytes mais `O(V)` por thread, mais a
fronteira. A fronteira só pode ser reutilizada porque cada busca a esvazia
(`pop` até `no_vertex`).

### RadixFrontier

`RadixFrontier` é um heap radix monótono, com a mesma interface de
`VectorFrontier` e `HeapFrontier`.

- **Chave.** A chave é o padrão de bits IEEE-754 da distância lido como
  `uint64_t` (`std::bit_cast`). Para `double` não negativo, inclusive
  `+infinito`, a ordem dos bits coincide com a ordem numérica; todas as
  comparações são exatas e feitas com inteiros.
- **`-0.0`.** Tem o bit de sinal ligado e viraria uma chave enorme; `push` o
  normaliza para `+0.0`. `NaN` e valores negativos não são aceitos: o contrato
  vale, mas o código não os rejeita.
- **Baldes.** São 65 (`std::array`). O balde de uma chave é o índice do bit mais
  alto em que ela difere da última chave extraída (`bit_width(chave ^ ultima)`,
  `0` quando são iguais). Quando o balde `0` esvazia, o primeiro balde não vazio é
  redistribuído em torno de sua menor chave, que vira a nova referência; cada
  entrada só desce de balde. `push` custa `O(1)`; `pop`, amortizado `O(log C)`
  com `C = 64`.
- **Monotonicidade.** Toda chave inserida precisa ser maior ou igual à última
  extraída. Dijkstra cumpre isso: extrai em ordem não decrescente e só insere
  `distance[current] + w`, com `w ≥ 0`. Um `assert` confere a regra, e só nas
  compilações sem `NDEBUG`.
- **Redução de chave preguiçosa.** `push` insere uma entrada nova, e um vetor
  `best_` guarda a chave vigente de cada vértice; `pop` descarta as entradas com
  outra chave. A alternativa, posições indexadas como no `HeapFrontier`, exigiria
  guardar o índice de cada entrada dentro do balde e atualizá-lo a cada
  redistribuição. O custo da escolha é até uma entrada por relaxação: `O(E)` de
  memória no pior caso, em vez de `O(V)`.
- **Reutilização.** Ao esvaziar, `pop` zera a referência (`last_ = 0`), e a
  fronteira serve a outra busca.

Em `cos_bench2`, a fronteira radix roda em todas as origens, e a soma das
distâncias é conferida contra a do heap.


## Leitura com pesos

`read_triples` lê o arquivo em blocos de tamanho fixo, de 1 MiB por padrão, e
converte os campos com `std::from_chars`, sem criar strings nem usar
`iostream` por número. A linha incompleta no fim de um bloco é movida para o
início do próximo. O leitor aceita CRLF, linhas vazias e a falta de quebra de
linha no fim do arquivo. Campos inválidos, conteúdo extra numa linha, linhas
que não cabem no bloco e a falta do cabeçalho lançam `std::runtime_error`; cada
linha, sem a quebra, precisa ter menos bytes que o bloco.

Para reduzir o pico de memória, o leitor percorre o arquivo duas vezes. A
primeira conta as quebras de linha e reserva o vetor de arestas com o tamanho
exato; sem isso, o vetor cresceria dobrando, e cada realocação manteria as duas
cópias ao mesmo tempo, chegando a até três vezes o tamanho final. Além do vetor
de 16 bytes por aresta, a memória do leitor se limita a um bloco.

## Posse e duração dos dados

- `Graph` possui a topologia pronta e as estatísticas escalares.
- A construção recebe uma visão das arestas e não guarda o vetor de entrada.
- Cada algoritmo público possui seus dados temporários durante uma chamada.
- Os resultados de BFS, DFS e Dijkstra pertencem à função visitante; Dijkstra
  possui distâncias, pais e fronteira durante a chamada.
- `PathsToTarget` (Bellman-Ford) possui os vetores de distâncias e sucessores.
  `AllPairsPaths` (Floyd-Warshall e Johnson) e `AllPairsToTargets` (todos os pares
  por Bellman-Ford) possuem duas matrizes `V × V` cada um, em `unique_ptr`. Os
  três são devolvidos por valor, sem cópia, e independem do grafo depois da
  chamada. O chamador libera as matrizes ao destruir o resultado. Com ciclo
  negativo, as matrizes do Floyd-Warshall e do todos-pares por Bellman-Ford são
  inválidas, e as de Johnson nem são alocadas.
- Cada thread de `all_pairs_bellman_ford` possui um `BellmanFordWorkspace`, e cada
  thread de `johnson` possui uma fronteira; o de `repair_zero_cycles` usa dois
  vetores de `V` posições por thread. Todos são criados dentro da chamada e
  liberados antes do retorno. O Floyd-Warshall em blocos só usa memória extra
  `O(V / B)` para os contadores de tarefas. Os resultados são escritos em linhas
  disjuntas por threads que terminam (`std::jthread`) antes do retorno.
- A otimização de retorno do C++ transfere os vetores de resultado.

Não há dependências externas nem instruções específicas de uma arquitetura. O
mesmo código e os mesmos perfis compilam de forma nativa em x86-64 e AArch64.

