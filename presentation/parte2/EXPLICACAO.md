# Explicação dos slides

Este documento fica fora dos slides. Para cada slide, ele diz:

- o que o slide mostra;
- por que mostra;
- como o conteúdo se liga ao projeto (código, enunciado, dados);
- por que o slide está nessa posição.

## Escopo e critério de corte

O enunciado pede no máximo 8 minutos "mostrando detalhes da sua implementação e os resultados obtidos".
A apresentação segue a ordem de um seminário:

1. problema;
2. implementação;
3. metodologia;
4. resultados;
5. discussão;
6. conclusões.

Cada slide tem uma ideia principal. O critério de corte foi de Pareto: fica no corpo principal o que
responde ao enunciado ou explica um resultado. Detalhes que só sustentam um número vão para o apêndice;
o resto sai.

**Saiu do corpo principal** (fica no apêndice ou no relatório):

- declaração dos arrays do CSR;
- figura do caminho 10 → 20;
- pseudocódigo do Dijkstra: era genérico e não mostrava como o trabalho evita escrever o algoritmo duas
  vezes. O código real mostra;
- figura do "mesmo passo nas duas filas": o código das duas filas diz o mesmo com menos explicação;
- leitura do arquivo;
- tabela completa de contadores (apêndice A4).

**Entrou no corpo principal**, porque explica os tempos:

- tamanho do heap ao longo da execução (slide 10);
- curva de latência da memória medida na máquina (slide 11);
- o teste de numeração local × aleatória, antes no apêndice (slide 12).

**Identidade visual**

- Fundo branco, barra de título escura e rodapé com autores, seção e número do slide, no padrão do tema
  Metropolis do Beamer.
- Figuras e tabelas numeradas e com legenda; tabelas com três filetes, como no relatório.
- Mesmas fontes (Fira Sans, Inconsolata) e cores do relatório:
  - azul: destaque e operações da fila;
  - verde-azulado: heap;
  - vermelho: vetor.
- Código C++ real, com número de linha. O build procura cada linha mostrada em
  `include/cos/graph.hpp` e para se alguma não existir; `…` marca linhas omitidas.

## História e tempos verbais

Cada slide é um passo de uma história, e o título é a frase desse passo:

1. o trabalho pede caminhos mínimos com Dijkstra, em duas versões (2);
2. guardamos o grafo em CSR, escrevemos um único Dijkstra e duas filas (3–5);
3. rodamos 100 origens por grafo e cronometramos só o Dijkstra (6);
4. as versões deram as mesmas distâncias, e o heap foi de 122× a 44 mil× mais rápido (7–9);
5. mas o tempo do heap cresceu mais que (*n* + *m*) log *n*: 582× contra 27× (9);
6. contamos as operações, medimos o custo de uma leitura e testamos a hipótese renumerando os vértices
   (10–12);
7. a análise conta operações; em grafos grandes, o tempo também depende da memória (13).

O tempo de cada verbo diz quando a frase é verdade em relação ao momento da fala:

| Plano | Tempo | Exemplo |
|---|---|---|
| código, definição, propriedade fixa do grafo | presente | "`push` insere um vértice ou diminui a chave" |
| o que fizemos | pretérito perfeito, "nós" | "sorteamos 100 origens"; "cronometramos só o Dijkstra" |
| o que medimos | pretérito perfeito | "o heap foi 122× mais rápido"; "levou 0,11 s" |
| estado durante uma execução | imperfeito | "o heap já guardava 89% dos vértices" |
| interpretação | presente | "em grafo denso, o heap enche cedo" |
| o que não foi feito | futuro do pretérito | "uma matriz ocuparia 9*n*²"; "levaria 16 dias" |

Frases do corpo têm sujeito e verbo conjugado; particípio solto só em rótulo de tabela ou figura. Os
critérios e as fontes estão em `PLANO_TEMPOS_VERBAIS.md`.

## Fontes dos números

O build lê os arquivos abaixo; nenhum número é digitado à mão.

| Fonte | O que traz |
|---|---|
| `report/parte2/data.json` | grafos, tempos, validação da estimativa, rede de colaboração, contadores, máquina |
| `report/parte2/contagens.json` | inserções no heap por aresta (100 origens); tamanho do heap ao longo de uma execução |
| `data.json` → `lowlevel.chase` | tempo de uma leitura aleatória por tamanho dos dados (`bench/lowlevel_bench.cpp`) |
| `data.json` → `lowlevel.layout` | grafos sintéticos com numeração local e aleatória |
| `data.json` → `lowlevel.order` | W₅ com numeração original, aleatória e de BFS |
| `bench/results/parte2/caminhos_W_*.txt` | graus e caminhos |
| `include/cos/graph.hpp` | código dos slides 4 e 5; o build para se uma linha mudar |

---

## 1. Capa

- **Mostra**:
  - título do relatório;
  - autores, disciplina, professor;
  - universidade e escola;
  - logo da UFRJ.
- **Por quê**: identifica o trabalho com o mesmo título do relatório, para que os dois documentos sejam
  reconhecidos como partes da mesma entrega.
- **Projeto**: `report/parte2/relatorio.tex` (folha de rosto) e `report/comum/minerva.png`.
- **Posição**: abertura.

## 2. Problema

- **Mostra**:
  - definição de caminhos mínimos de origem única com pesos não negativos;
  - o que o trabalho pede;
  - Figura 1: um grafo de 6 vértices com a árvore de caminhos mínimos a partir de 0.
- **Por quê**:
  - fixa a notação usada no resto da apresentação (*G*, *w*, *s*, *dist*, árvore);
  - lembra os três entregáveis do enunciado: duas versões do Dijkstra, estudo nos grafos W, rede de
    colaboração.
  - A figura dá um exemplo concreto pequeno, que os slides 3 e 5 reaproveitam. Assim, o público aprende
    o grafo uma vez só.
- **Projeto**:
  - requisitos em `docs/REQUISITOS.md` (Parte 2);
  - o grafo de exemplo e suas distâncias são calculados em `build.py` (`ex_arvore`).
- **Posição**:
  - não depende de nada;
  - prepara todos os outros, porque define o problema e o exemplo.

## 3. Representação do grafo (CSR)

- **Mostra**:
  - Figura 2: o grafo da Figura 1 nos três arrays (`offsets_`, `neighbors_`, `weights_`), com os
    vizinhos do vértice 2 destacados;
  - a fórmula de memória;
  - Tabela 1: CSR contra matriz no W₃ e no W₇.
- **Por quê**:
  - antes do algoritmo, o público precisa saber como "percorrer os vizinhos de *u*" é feito e quanto
    custa, porque é o laço interno do Dijkstra (`first_neighbor`, `next_neighbor`);
  - a Tabela 1 justifica a escolha: a matriz precisaria de 90 GB no W₃ e 22 PB no W₇.
- **Projeto**:
  - `Graph` em `include/cos/graph.hpp` (membros `offsets_`, `neighbors_`, `weights_`, métodos
    `first_neighbor`, `next_neighbor`, `weight_before`);
  - memória vinda de `data.json` (`memory_bytes`, `matrix_bytes_estimate`).
- **Posição**:
  - depende do slide 2 (mesmo grafo);
  - vem antes do algoritmo porque o custo O(grau) da vizinhança entra na análise de complexidade do
    slide 5.

## 4. Algoritmo de Dijkstra em `graph.hpp`

- **Mostra**:
  - o código do Dijkstra, da assinatura do template ao fim do laço (linhas 265 e 276–310), com as
    linhas que usam a fila destacadas;
  - ao lado: a fila como parâmetro, `push` que também diminui a chave, ausência de vetor de visitados,
    o callback `visit` e o teste de peso negativo.
- **Por quê**:
  - o enunciado pede as duas versões "sem escrever o algoritmo duas vezes";
  - um pseudocódigo mostraria o Dijkstra de qualquer livro. O código mostra a decisão do trabalho: o
    tipo da fila é um parâmetro do template, e o laço não sabe qual fila usa;
  - o algoritmo é curto o bastante para caber inteiro, então não há o que esconder;
  - a nota sobre pesos negativos cobre outro item do enunciado.
- **Projeto**:
  - `Graph::dijkstra<Frontier>` em `include/cos/graph.hpp`;
  - `part2/main.cpp` usa `HeapFrontier`; `bench/dijkstra_bench.cpp` usa as duas;
  - o `std::domain_error` também está em `graph.hpp`.
- **Posição**:
  - depende do slide 3 (`first_neighbor`, `next_neighbor`);
  - isola as operações da fila, que o slide 5 abre.

## 5. Filas de prioridade

- **Mostra**:
  - o código de `VectorFrontier` (`push` e `pop`) e de `HeapFrontier` (`place`, que atualiza
    `position_`);
  - tabela com o custo de `push`, `pop` e do Dijkstra nas duas filas.
- **Por quê**:
  - é aqui que as complexidades O(*n*² + *m*) e O((*n* + *m*) log *n*) aparecem, e os resultados vão
    ser comparados com elas;
  - o código explica a parte menos óbvia da implementação. Um heap binário comum não sabe onde está
    um vértice; sem `position_`, reduzir a chave exigiria procurá-lo.
- **Projeto**: `VectorFrontier` e `HeapFrontier` em `graph.hpp` (`estimate_`, `heap_`, `position_`,
  `place`).
- **Posição**:
  - fecha a parte de implementação;
  - a tabela é a previsão que os slides 9 a 12 testam.

## 6. Metodologia

- **Mostra**:
  - Tabela 3: os cinco grafos (*n*, *m*, grau médio, memória);
  - nota de que o W₆ não é conexo;
  - tamanho da rede de colaboração;
  - três itens de protocolo:
    - máquina, memória e `-O3`;
    - 100 origens, as mesmas nas duas filas, e só o Dijkstra cronometrado;
    - vetor medido no W₃ e no W₄ e estimado do W₅ ao W₇, com o erro da estimativa (1% e 11%).
- **Por quê**:
  - os resultados só podem ser avaliados se o público souber como foram medidos;
  - a estimativa do vetor precisa ser declarada antes da tabela de tempos, para que os asteriscos não
    surpreendam;
  - o grau médio da tabela é a variável que explica os slides 7 e 10, e o *n* explica os slides 11 e 12.
- **Projeto**:
  - `data.json` (`machine`, `graphs`, `fit.validation`);
  - metodologia descrita em `report/parte2/relatorio.tex`;
  - medições em `bench/`.
- **Posição**: separa implementação de resultados, como numa seção de métodos.

## 7. Estudo de caso: distâncias

- **Mostra**:
  - Tabela 4: distância de 10 a 20, 30, 40, 50 e 60 nos cinco grafos, com o número de arestas de cada
    caminho;
  - nota de que vetor e heap concordam;
  - uma observação: no W₃, o caminho de 10 a 20 usa 18 arestas.
- **Por quê**:
  - é a tabela que o enunciado pede;
  - o número de arestas mostra uma propriedade do problema com pesos: mesmo num grafo de grau médio
    122, o caminho mínimo é longo em arestas.
- **Projeto**:
  - `bench/results/parte2/caminhos_W_*.txt` (saída de `part2`), via `data.json`;
  - `mismatches = 0` em todos os grafos (o build verifica).
- **Posição**:
  - primeiro resultado: correção antes de desempenho;
  - prepara o slide 8, que mostra a mesma propriedade com nomes.

## 8. Estudo de caso: rede de colaboração

- **Mostra**: Figura 4, com os caminhos a partir de Edsger W. Dijkstra até:
  - Kleinberg;
  - Tardos;
  - Kruskal;
  - Figueiredo.

  Cada aresta tem seu peso; as de peso 1,00 aparecem em vermelho. Turing aparece como não alcançável.
- **Por quê**:
  - é o outro item do enunciado;
  - mostra no grafo real a observação do slide 7. Kleinberg está a 9 arestas e Kruskal a 8, mas
    Kleinberg está mais perto (2,71 contra 3,48), porque o caminho de Kruskal tem duas arestas de peso
    1,00.
- **Projeto**:
  - `data.json` → `colab` (caminhos, nomes, pesos por aresta, status de Turing);
  - saída do programa da Parte 2.
- **Posição**:
  - fecha os resultados de correção;
  - vem antes dos tempos para não interromper a sequência tempo → discussão.

## 9. Estudo de caso: tempo médio

- **Mostra**:
  - Tabela 5: tempo médio do heap (com desvio), tempo do vetor (medido ou estimado) e razão;
  - barra da razão em escala logarítmica;
  - um bloco com a conclusão: 122× a 44 mil×, e só o heap é viável a partir do W₄.
- **Por quê**:
  - é o estudo de desempenho pedido;
  - a escala logarítmica cabe numa barra uma diferença que vai de 10² a 10⁴.
- **Projeto**:
  - `data.json` (`heap.mean_s`, `heap.std_s`, `vector.mean_s`, `vector_estimate_s`);
  - o asterisco remete à estimativa explicada no slide 6.
- **Posição**:
  - depende do slide 6 (protocolo) e do slide 5 (previsão);
  - abre a discussão: o que a contagem assintótica não captura (número real de operações, custo de cada uma).

## 10. Discussão: quantas operações o heap faz

- **Mostra**:
  - Figura: tamanho do heap (fração de *n*) contra o número de extrações, uma origem por grafo. No W₃,
    depois de 2% das extrações o heap já tem 89% dos vértices; no W₇, o pico é 14%;
  - Figura: proporção de arestas que geram `push` no heap, de 7% (W₃) a 90% (W₇).
- **Por quê**:
  - a análise do pior caso conta uma operação no heap por aresta. As figuras mostram quanto disso
    acontece de fato e por que depende do grau;
  - grafo denso: todo vértice entra cedo, e depois quase nenhuma aresta melhora uma estimativa;
  - grafo esparso: o heap fica pequeno, mas quase toda aresta é a primeira a alcançar o vizinho.
- **Projeto**: `contagens.json`, contado fora da cronometragem (`trace` com extrações, tamanho do heap
  e distância; inserções em média de 100 origens).
- **Posição**:
  - depende dos slides 5 (complexidades) e 9 (tempos);
  - primeira das duas partes da análise: o número de operações. O slide 11 trata o custo de cada uma.

## 11. Discussão: quanto custa cada operação

- **Mostra**:
  - Figura: tempo de uma leitura em posição aleatória, medido na máquina, de 1,1 ns (cabe no cache L1)
    a ~120 ns (fora do cache). As linhas vermelhas marcam o tamanho do que o Dijkstra lê fora de ordem
    em cada grafo: 32 bytes por vértice (`distance`, `parent`, entrada de `heap_`, `position_`);
  - Tabela: tempo do heap dividido por (*n* + *m*) log₂ *n*, que cresce 21× do W₃ ao W₇, e fração dos
    ciclos parados à espera da memória (46% → 77%).
- **Por quê**:
  - a análise supõe custo constante por operação. A curva mostra que isso vale enquanto os dados cabem
    no cache, e o W₃ cabe (~7 ns); do W₅ em diante, cada leitura custa ~116 ns;
  - liga o tempo medido a uma medida independente, feita na mesma máquina.
- **Projeto**:
  - `data.json` → `lowlevel.chase` (`bench/lowlevel_bench.cpp`);
  - os 32 bytes vêm dos tipos em `graph.hpp`: `Weight = double`, `Vertex = uint32_t`, `Entry` com 16 B;
  - `data.json` → `counters` (contadores de hardware até o W₅).
- **Posição**: completa a explicação dos tempos; o slide 12 testa a hipótese.

## 12. Teste: a mesma conta com outra numeração dos vértices

- **Mostra**:
  - Figura: Dijkstra com heap em grafos sintéticos (cada vértice liga-se a 4 dos 64 seguintes), com
    numeração local e aleatória. O grafo é o mesmo; a razão dos tempos vai de 1,2× (100 mil vértices)
    a 3,3× (50 milhões);
  - bloco: os grafos W já têm numeração aleatória (distância média entre as pontas de 0,33*n*), e
    renumerar o W₅ em ordem de BFS quase não mudou o tempo (5,03 s contra 5,19 s).
- **Por quê**:
  - o slide 11 é uma correlação; este é um teste. As operações do heap não mudam, só a posição dos
    dados na memória;
  - o bloco responde à pergunta seguinte, "dá para melhorar os grafos W assim?": não, porque eles não
    têm vizinhança local a recuperar.
- **Projeto**: `data.json` → `lowlevel.layout` e `lowlevel.order`.
- **Posição**: fecha a discussão antes das conclusões.

## 13. Conclusões

- **Mostra**: cinco conclusões:
  - implementação única;
  - desempenho;
  - número de operações;
  - custo da memória;
  - rede de colaboração.

  E o trabalho futuro: pesos negativos.
- **Por quê**: resume o que o público deve levar, na ordem em que foi apresentado.
- **Projeto**: mesma conclusão de `report/parte2/relatorio.tex`.
- **Posição**: fim; abre perguntas.

## Apêndice

Usado só em perguntas.

| Slide | Conteúdo | Responde a |
|---|---|---|
| A1–A2 | caminhos completos da Tabela 4 | "qual é o caminho?" |
| A3 | validação da estimativa do vetor no W₃ (+1%) e no W₄ (−11%) | "a estimativa é confiável?" |
| A4 | contadores de hardware por grafo e fila | "de onde vem a espera de 46–77%?" |
