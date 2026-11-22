# Roteiro

Tempo total: 7min30 (limite de 8). O slide mostra a evidência (código, tabela ou figura); o que antes estava escrito
nele agora está aqui, para a fala. Para cada slide: a mensagem (o título diz só o assunto), o que dizer, os números de apoio e a frase que liga ao
próximo. O porquê de cada slide está em `EXPLICACAO.md`.

| # | Slide | Tempo | Acumulado |
|---|---|---|---|
| 1 | Capa | 0:20 | 0:20 |
| | **Implementação** | | |
| 2 | Representação do grafo | 0:30 | 0:50 |
| 3 | Um Dijkstra para duas filas | 0:50 | 1:40 |
| 4 | Vetor e heap | 0:45 | 2:25 |
| | **Benchmark** | | |
| 5 | Tempo de execução | 0:50 | 3:15 |
| 6 | Operações do heap | 0:40 | 3:55 |
| 7 | Ocupação do heap | 0:30 | 4:25 |
| 8 | Hierarquia de memória | 0:45 | 5:10 |
| 9 | Localidade dos vértices | 0:50 | 6:00 |
| | **Resultados** | | |
| 10 | Caminhos nos grafos W | 0:30 | 6:30 |
| 11 | Rede de colaboração | 0:35 | 7:05 |
| 12 | Conclusões | 0:25 | 7:30 |

A apresentação segue a ordem do trabalho: o algoritmo e o código (implementação), a medição das duas
versões (benchmark) e os caminhos encontrados (resultados). O rodapé de cada slide diz a parte.

## 1. Capa

- **Dizer**: título e autores; o trabalho pede o Dijkstra com vetor e com heap, os caminhos nos grafos W₃ a W₇ e na rede de
  colaboração, e o tempo das duas versões.
- **Ponte**: "primeiro a implementação, depois o benchmark das duas versões e, por fim, os caminhos
  encontrados. Começamos por como guardamos o grafo."

# Implementação

## 2. Representação do grafo

- **Mensagem**: o CSR do W₇ ocupa 1,64 GB; uma matriz ocuparia 22 PB.
- **Dizer**:
  - à esquerda, um grafo de 6 vértices; à direita, o mesmo grafo em CSR;
  - os vizinhos de todos os vértices ficam num array só; `offsets_[v]` diz onde começam os de *v*: os do
    vértice 2 estão nas posições 5 a 8 (0, 3, 5, 4), com os pesos no mesmo índice;
  - cada aresta aparece duas vezes, uma em cada ponta; percorrer os vizinhos de *v* custa O(grau(*v*)).
- **Ganchos**: o CSR ocupa 4(*n* + 1) + 24*m* bytes: 1,64 GB no W₇, contra 22 PB de uma matriz.
- **Ponte**: "este é o Dijkstra que usa isso."

## 3. Um Dijkstra para duas filas

- **Mensagem**: vetor e heap usam o mesmo Dijkstra; a fila é parâmetro do template.
- **Dizer**:
  - é o código real de `graph.hpp`;
  - o tipo da fila é um parâmetro do template: `dijkstra<VectorFrontier>` e `dijkstra<HeapFrontier>` são as
    duas versões;
  - as linhas destacadas são as únicas que dependem da fila: `push` da origem, `pop`, `push` do vizinho.
- **Ganchos**:
  - `push` insere um vértice ou diminui a chave de quem já está na fila;
  - não há vetor de visitados: com pesos ≥ 0, quem já saiu tem distância final, e o `<` do `if` o recusa;
  - `visit` recebe cada vértice ao sair da fila, com pai e distância;
  - com peso negativo, o programa para antes do laço.
- **Ponte**: "o que muda entre as versões é o que está atrás de `push` e `pop`."

## 4. Vetor e heap

- **Mensagem**: o heap sabe onde está cada vértice, por isso diminui a chave em O(log n).
- **Dizer**:
  - **vetor**: `push` é uma escrita; `pop` procura o mínimo nas *n* posições, inclusive as de quem já
    saiu, marcadas com ∞;
  - **heap**: `push` consulta `position_` para achar o vértice; se ele não está no heap, entra no fim;
  - `sift_up` sobe o vértice: enquanto o pai tem chave maior, o pai desce uma posição (`place`) e o índice
    sobe; no fim, o vértice entra no lugar que sobrou. São no máximo log *n* níveis;
  - `place` escreve no heap e atualiza `position_`; é por isso que o heap sempre sabe onde cada vértice está;
  - a tabela: O(*n*² + *m*) contra O((*n* + *m*) log *n*).
- **Ganchos**: sem `position_`, diminuir uma chave exigiria procurar o vértice em O(*n*).
- **Ponte**: "rodamos as duas versões nos cinco grafos W. Primeiro, o tempo."

# Benchmark

## 5. Tempo de execução

- **Mensagem**: o heap é mais rápido em todos os grafos; com vetor, uma origem leva 10,9 min já no W₄.
- **Dizer**:
  - medimos só o Dijkstra, sem a leitura do arquivo, num M3 Pro com 36 GiB;
  - do W₅ em diante, o vetor levaria de 16 h a 16 dias por origem; por isso, estimamos esses valores pelo
    tempo de uma extração (asterisco). Onde deu para comparar, a estimativa errou 1% e 11%;
  - a última coluna varia muito: 122× no W₃, 44 mil× no W₇.
- **Ganchos**: do W₃ ao W₇, (*n* + *m*) log *n* cresce 27×, e o tempo do heap, 582×.
- **Ponte**: "a análise conta um `push` por aresta. Contamos quantos o heap faz de fato."

## 6. Operações do heap

- **Mensagem**: quanto mais denso o grafo, menos arestas geram `push`: 7% no W₃, 90% no W₇.
- **Dizer**:
  - ao tirar `u` da fila, o Dijkstra olha cada aresta (u, v); se `distance[u] + peso` é menor que
    `distance[v]`, a aresta melhorou a distância de `v`, e o código chama `push(v)`; se não, nada acontece;
  - a linha tracejada é o que a análise supõe: toda aresta melhora, ou seja, *m* `push`;
  - no W₃, denso, só 7% das arestas fizeram `push`; no W₇, esparso, 90%;
  - por isso o heap ganha mais do vetor nos grafos esparsos, e o W₅ e o W₆, com o mesmo *n*, têm razões
    diferentes (11 mil× e 8 mil×).
- **Ganchos**:
  - grafo denso: quando um vértice é visto de novo, ele já tem uma estimativa boa, e o `<` recusa;
  - grafo esparso: quase toda aresta é a primeira a alcançar o vizinho;
  - o relatório conclui que, nesses grafos, o custo do heap fica mais perto de O(*m* + *n* log *n*).
- **Ponte**: "e quantos vértices ficam no heap ao mesmo tempo?"

## 7. Ocupação do heap

- **Mensagem**: no grafo denso, quase todos os vértices entram no heap logo no início; no esparso, o heap
  fica pequeno.
- **Dizer**:
  - cada curva é uma execução: no eixo x, quantos vértices já saíram; no y, quantos estão no heap;
  - a diagonal que desce é o limite: todos os vértices que ainda não saíram estão no heap, ou seja, já
    têm alguma estimativa;
  - W₃ (grau 122): depois de 4% das extrações, 95% dos vértices já estão no heap. Com tantos vizinhos,
    poucas extrações alcançam o grafo inteiro;
  - W₇ (grau 2,4): o heap nunca passa de 14% de *n*; a fronteira avança como uma onda estreita.
- **Ganchos**:
  - é o outro lado do slide anterior: no denso, todo vértice entra cedo e depois só recebe propostas
    piores, por isso poucos `push`;
  - o tamanho do heap define a altura da árvore: no W₃, com 95 mil vértices, ~17 níveis; o log *n* da
    análise é real nos grafos densos.
- **Ponte**: "isso é a contagem. O outro lado é quanto custa cada operação."

## 8. Hierarquia de memória

- **Mensagem**: só os dados do W₃ cabem no cache.
- **Dizer**:
  - a curva é o tempo de uma leitura em posição aleatória nesta máquina; as faixas são L1, L2 e RAM;
  - em vermelho, o que o Dijkstra lê fora de ordem: `distance`, `parent`, `heap_` e `position_`, 32 bytes
    por vértice;
  - o W₃ fica na L2, ~7 ns por leitura; do W₅ em diante, RAM, ~116 ns;
  - na tabela, o tempo por operação cresceu 21× do W₃ ao W₇, e os ciclos parados à espera da memória
    passaram de 46% para 77%.
- **Ganchos**: os vizinhos de um vértice são contíguos no CSR; o que fica espalhado são os dados desses
  vizinhos.
- **Ponte**: "para testar se é mesmo a memória, mudamos só a numeração."

## 9. Localidade dos vértices

- **Mensagem**: só mudar a numeração deixa o Dijkstra até 3,3× mais lento.
- **Dizer**:
  - a pergunta: o tempo depende só do número de operações, ou também de onde os dados ficam? Para
    separar as duas coisas, mudamos só a numeração dos vértices;
  - o grafo do teste é um anel: cada vértice liga-se a 4 dos 64 seguintes. Os anéis em cima mostram as
    duas numerações do mesmo grafo: na local, vizinhos têm índices próximos; na aleatória, embaralhados;
  - embaixo, cada ponto é um vértice: no eixo x, quando o Dijkstra o extrai; no y, seu índice no array;
  - **local**: partindo do meio, o Dijkstra anda pelo anel nas duas direções, e o desenho vira um "V".
    Vértices extraídos em seguida têm índices próximos, então `distance`, `parent`, `heap_` e `position_`
    são lidos numa região pequena, que fica no cache;
  - **aleatória**: mesma ordem de extração, mas os índices viram uma nuvem; cada leitura cai num ponto
    qualquer do array e, se ele não cabe no cache, vai à RAM (~116 ns contra ~7 ns);
  - **direita**: com 100 mil vértices, tudo cabe no cache: 1,2×. Com 10 mi e 50 mi: 3,1× e 3,3×.
- **Ganchos**:
  - contadores com 10 mi: as mesmas instruções (3,46 bi contra 3,44 bi), faltas no L1 de 6,8 mi para
    82 mi, ciclos à espera da memória de 4% para 67%;
  - o heap nesse grafo é pequeno: no máximo 424 vértices;
  - os grafos W já têm numeração aleatória; renumerar o W₅ em ordem de BFS só baixou o tempo de 5,19 s
    para 5,03 s.
- **Ponte**: "isso é o custo. Agora, o que o programa calcula: em 100 origens por grafo, vetor e heap deram
  as mesmas distâncias. Como são esses caminhos?"

# Resultados

## 10. Caminhos nos grafos W

- **Mensagem**: no grafo denso, os caminhos mínimos usam só as arestas mais leves; no esparso, não há
  como escolher.
- **Dizer**:
  - em cima, os caminhos do vértice 10 a 20, 30, 40, 50 e 60 no W₃, desenhados em escala: o trecho
    horizontal de cada aresta mede o seu peso (lido do arquivo do grafo), e o eixo dá a distância;
  - muitas bolinhas juntas = muitas arestas quase sem peso: o caminho até 20 tem 18 arestas e não passa
    de 0,80;
  - embaixo, a tabela compara o peso médio das arestas do grafo com o das arestas dos 5 caminhos;
  - W₃ (grau 122): o grafo tem peso médio 4,96, mas os caminhos usam arestas de 0,07 em média, todas
    ≤ 0,26;
  - W₇ (grau 2): peso médio 2,92 no grafo e 2,58 nos caminhos; com dois vizinhos por vértice, o caminho
    usa as arestas que existem.
- **Ganchos**:
  - no W₃, só 2,7% das arestas têm peso ≤ 0,26, mas com grau 122 cada vértice tem umas 3 delas, o que
    basta para encadear um caminho;
  - as distâncias de todos os grafos estão em `bench/results/parte2/caminhos_W_*.txt` e no relatório.
- **Ponte**: "o mesmo acontece na rede de colaboração."

## 11. Rede de colaboração

- **Mensagem**: Kleinberg, a 9 arestas, está mais perto que Kruskal, a 8.
- **Dizer**:
  - 722 mil pesquisadores e 2,3 mi arestas; peso menor significa mais colaboração;
  - o desenho está em escala, como o anterior: quanto mais à direita, mais longe de Dijkstra;
  - Kleinberg tem 9 arestas e fica em 2,71; Kruskal tem 8 e fica em 3,48. As duas arestas vermelhas, de
    peso 1,00, explicam a diferença.
- **Ganchos**:
  - Kleinberg está a 9 arestas e Kruskal a 8, mas Kleinberg está mais perto (2,71 contra 3,48), porque o
    caminho de Kruskal passa por duas arestas de peso 1,00;
  - Turing está em outra componente;
  - com heap, cada origem levou 0,11 s.
- **Ponte**: "para fechar."

## 12. Conclusões

- **Mensagem**: o tempo depende das operações e da memória.
- **Dizer**: uma frase por parte.
  - implementação: um só Dijkstra dá as duas versões, com as mesmas distâncias;
  - benchmark: o heap ganha em todos os grafos; quanto ganha depende de quantas arestas geram `push` e de
    onde os dados ficam na memória;
  - resultados: no W₃ os caminhos usam só as arestas mais leves.
- **Fechar**: "obrigado; perguntas."

## Perguntas prováveis

| Pergunta | Resposta | Apoio |
|---|---|---|
| Por que não medir o vetor no W₅ a W₇? | levaria de 16 h a 16 dias por origem; a estimativa foi conferida no W₃ e no W₄ | 5 |
| Por que não usar `std::priority_queue`? | não diminui chave; inserir de novo deixa entradas velhas no heap | 4 |
| Por que não há vetor de visitados? | com pesos não negativos, quem saiu tem distância final; o `<` do `if` recusa | 3 |
| O W₆ é conexo? | não: em média, 9.999.997 dos 10 mi de vértices são alcançados | — |
| Por que Turing não tem caminho? | está em outra componente; o programa imprime `inalcancavel` | 11 |
| Como sabem que o custo é memória? | curva de latência, teste de numeração e contadores de hardware | 8, 9 |
| Renumerar os vértices ajudaria nos grafos W? | no W₅, ordem de BFS deu só 3% a menos | 9 |
| E com pesos negativos? | o programa para com a mensagem do enunciado | 3 |
