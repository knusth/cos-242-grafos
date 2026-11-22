# cos-grafos

Este repositório reúne a biblioteca de grafos `cos` e os programas
desenvolvidos para as Partes 1, 2 e 3 do trabalho de COS242. A Parte 1 usa
grafos não direcionados e sem pesos, a Parte 2 acrescenta pesos reais nas
arestas e a Parte 3 acrescenta grafos direcionados e pesos negativos.

A biblioteca é escrita em C++20, é `header-only` e usa somente a biblioteca
padrão. Depois de construído, o grafo é imutável. Essa escolha deixa a
representação compacta e permite que as buscas percorram dados contíguos na
memória.

Cada parte acrescenta operações à mesma biblioteca, sem misturar os algoritmos
do grafo com a leitura e a escrita específicas de cada programa.

## Funcionalidades

A implementação atual oferece:

- matriz e vetor de adjacências;
- número de vértices e arestas;
- graus mínimo e máximo, média e mediana dos graus;
- busca em largura (BFS) e busca em profundidade (DFS), com pai e nível de cada
  vértice;
- distância entre vértices e diâmetro exato (só em grafos não direcionados);
- componentes conexas em ordem decrescente de tamanho (só em grafos não
  direcionados);
- grafos com pesos e detecção de pesos negativos;
- grafos direcionados, escolhidos por um parâmetro em tempo de execução;
- distâncias e árvore de caminhos mínimos a partir de uma origem, pelo
  algoritmo de Dijkstra com vetor de estimativas, com heap binário ou com heap
  radix (`RadixFrontier`);
- Bellman-Ford de todos os vértices até um destino, com detecção de ciclo
  negativo que alcança o destino (`bellman_ford`) e em qualquer ponto do grafo
  (`has_negative_cycle`);
- Bellman-Ford de todos os pares (`all_pairs_bellman_ford`), uma execução por
  destino, com distâncias, sucessores e detecção de ciclo negativo;
- Floyd-Warshall em blocos, com distâncias e árvores de caminhos mínimos entre
  todos os pares, detecção de ciclo negativo e `threads` threads (com 1, nenhuma
  thread é criada);
- Johnson (`johnson`), um extra além do enunciado: potenciais por Bellman-Ford e
  `V` buscas de Dijkstra com pesos reponderados, com a fronteira à escolha
  (`HeapFrontier` por padrão, ou `RadixFrontier`) e `threads` threads.

Dijkstra exige pesos não negativos; com pesos negativos, use Bellman-Ford,
Floyd-Warshall ou Johnson. `components()` e `diameter()` lançam
`std::logic_error` em grafos direcionados.

Os vértices do arquivo são identificados pelos inteiros de `1` a `V`.
Internamente, a biblioteca usa índices consecutivos de 32 bits, de `0` a
`V - 1`.

## Organização

```text
include/cos/       biblioteca e leitor de pares e triplas numéricas
part1/             programa da Parte 1
part2/             programa da Parte 2
part3/             programa da Parte 3
bench/             medições, estudos de caso e gerador de grafos de teste
bench/results/     resultados medidos: parte2/ e parte3/
report/            relatórios em LaTeX: comum/, parte2/ e parte3/
presentation/      apresentações: comum/ (estilo e fontes), parte2/ e parte3/
data/              grafos de entrada (veja "Dados da Parte 3")
tests/             testes e grafos pequenos de exemplo
docs/              requisitos e decisões de projeto
```

`graph.hpp` contém a representação e os algoritmos. `file_reader.hpp` limita-se
a ler um cabeçalho seguido de pares ou triplas de números. A conversão da
numeração dos vértices e a produção dos relatórios ficam em `part1/main.cpp` e
`part2/main.cpp` e `part3/main.cpp`.

## Compilação

É necessário ter CMake 3.20 ou mais recente e um compilador compatível com
C++20. O projeto não possui dependências externas.

A CSR é a representação padrão:

```sh
cmake --preset csr
cmake --build --preset csr
ctest --preset csr
```

Para compilar com a matriz de adjacências:

```sh
cmake --preset matrix
cmake --build --preset matrix
ctest --preset matrix
```

Cada perfil gera `cos_part1`, `cos_part2`, `cos_part3`, `cos_bench2`,
`cos_bench3`, `cos_lowlevel`, `cos_busy` e `cos_tests` em `build/csr/` ou
`build/matrix/`. No macOS, também gera `cos_counters`.

`COS_MATRIX` é resolvida durante o build. Cada executável contém apenas a
representação escolhida; não há seleção em runtime.

Os perfis não usam opções específicas do processador. O mesmo código compila
de forma nativa em x86-64 e AArch64.

## Execução

```sh
./build/csr/cos_part1 GRAFO.txt RELATORIO.txt
./build/csr/cos_part1 GRAFO.txt RELATORIO.txt 3
```

O terceiro argumento é o vértice de origem das buscas. Se ele for omitido, o
programa usa o vértice `1`.

O arquivo do grafo deve ter o número de vértices na primeira linha e uma aresta
por linha nas demais:

```text
quantidade_de_vertices
primeiro_vertice segundo_vertice
primeiro_vertice segundo_vertice
...
```

O relatório contém as estatísticas do grafo, as árvores produzidas por BFS e
DFS, as consultas de distância pedidas no trabalho, as componentes conexas e o
diâmetro. O campo `memoria_bytes` informa o espaço ocupado pela estrutura do
grafo; ele não representa toda a memória residente do processo.

### Parte 2

```sh
./build/csr/cos_part2 GRAFO.txt RELATORIO.txt
./build/csr/cos_part2 rede_colaboracao.txt RELATORIO.txt rede_colaboracao_vertices.txt
```

O arquivo do grafo tem o mesmo cabeçalho e um peso real em cada aresta:

```text
quantidade_de_vertices
primeiro_vertice segundo_vertice peso
...
```

Sem o arquivo de nomes, a origem é o vértice `10` e os destinos são `20`, `30`,
`40`, `50` e `60`. Com o arquivo de nomes, cujas linhas têm a forma
`indice,nome`, a origem é Edsger W. Dijkstra e os destinos são Alan M. Turing,
J. B. Kruskal, Jon M. Kleinberg, Éva Tardos e Daniel R. Figueiredo.

O relatório repete o resumo do grafo, indica se há pesos negativos e lista a
distância e o caminho mínimo até cada destino. Destinos sem caminho aparecem
como `inalcancavel`; destinos maiores que `V` aparecem como `fora_do_grafo`.
As distâncias usam 15 algarismos significativos, a precisão dos pesos da rede
de colaboração e o máximo que um `double` preserva em decimal. Se algum peso for negativo, a seção de
caminhos mínimos registra `situacao=nao_implementado` e o programa termina com
sucesso; para pesos negativos, use `cos_part3`.

### Parte 3

```sh
./build/csr/cos_part3 GRAFO.txt RELATORIO.txt direcionado
./build/csr/cos_part3 GRAFO.txt RELATORIO.txt nao_direcionado
COS_FW_LIMITE_GIB=64 ./build/csr/cos_part3 GRAFO.txt RELATORIO.txt direcionado
```

O arquivo do grafo tem o mesmo formato da Parte 2. O terceiro argumento é
`direcionado` (cada aresta vai do primeiro para o segundo vértice) ou
`nao_direcionado`. A variável opcional `COS_FW_LIMITE_GIB` limita a memória do
Floyd-Warshall em GiB (padrão 16); sem o limite, um grafo grande esgotaria a
memória da máquina.

O Floyd-Warshall do relatório usa todas as threads da máquina
(`std::thread::hardware_concurrency`); isso só encurta a espera, pois o resultado
não depende do número de threads.

O relatório tem as seções abaixo, em `chave=valor`:

- `[grafo]`: representação, direção, vértices, arestas, graus, `memoria_bytes`
  e `pesos_negativos`. Em grafo direcionado, os graus contam entradas e saídas.
- `[bellman_ford]`: destino `100`, `rodadas` executadas e dois indicadores.
  `ciclo_negativo_alcanca_destino` informa se existe ciclo negativo de onde o
  destino é alcançável; nesse caso as distâncias até ele não são
  mínimas e o relatório registra `situacao=ciclo_negativo`.
  `ciclo_negativo_no_grafo` informa se existe ciclo negativo em qualquer ponto
  do grafo. Um ciclo que não alcança o destino não invalida as distâncias até
  ele; por isso os dois campos podem divergir. Sem ciclo alcançando o destino,
  a tabela `origem,distancia,caminho` lista as origens `10`, `20` e `30`.
  Origens sem caminho aparecem como `inalcancavel` e vértices maiores que `V`
  como `fora_do_grafo`; um destino maior que `V` gera
  `situacao=fora_do_grafo`.
- `[floyd_warshall]`: `ciclo_negativo` e, sem ciclo, a matriz de distâncias
  entre `10`, `20`, `30`, `40` e `50` (`inf` para pares sem caminho, `-` para
  vértices fora do grafo). Se a memória necessária (`12·V²` bytes) passar do
  limite, o relatório traz `situacao=memoria_insuficiente` e
  `memoria_necessaria_bytes`.
- `[floyd_warshall_caminhos]`: o caminho mínimo de cada par dessa matriz, a
  partir da árvore da origem.
- `[distancias_por_bellman_ford]` e `[distancias_por_bellman_ford_caminhos]`:
  só aparecem quando falta memória para o Floyd-Warshall. Trazem a mesma matriz
  e os mesmos caminhos, obtidos com um Bellman-Ford por destino (`motivo=floyd_warshall_sem_memoria`);
  com ciclo negativo, a seção registra `situacao=ciclo_negativo`.

As distâncias usam 15 algarismos significativos. O programa termina com
sucesso nos casos de ciclo negativo, memória insuficiente e vértices fora do
grafo.

### Medição de Dijkstra

```sh
./build/csr/cos_bench2 GRAFO.txt K SEMENTE EXECUCOES_VETOR
```

O programa mede a leitura, informa `memoria_bytes` e o pico de memória
residente do processo, sorteia `K` origens com a semente dada e mede cada
execução de Dijkstra com heap. As primeiras `EXECUCOES_VETOR` origens também
executam a versão com vetor, que confere a soma das distâncias calculadas pelo
heap. Todas as origens executam ainda a versão com fronteira radix, também
conferida contra o heap. Cada linha da tabela informa a origem, os vértices
alcançados e os tempos (`heap_s`, `vetor_s` e `radix_s`), para que médias, desvios
e extrapolações sejam calculados depois. Divergência de soma faz o programa
terminar com erro.

`cos_lowlevel` reúne os experimentos sobre o custo de cada operação: a
frequência do núcleo (`clock`), a latência de leituras dependentes (`chase`),
três versões da varredura do vetor (`scan`), o custo por extração do vetor
dentro de Dijkstra (`pops`), o efeito da numeração dos vértices nos grafos W
(`order`) e em dois grafos isomorfos gerados (`layout`).
`bench/run_lowlevel.sh` roda todos e grava `bench/results/parte2/baixo_nivel.txt`.
`bench/run_contention.sh` repete o `pops` do W_4 sozinho e com quatro vizinhos
(`cos_busy registradores` e `cos_busy memoria`) e grava `bench/results/parte2/disputa.txt`.
No macOS, `cos_counters` (o mesmo programa com `COS_COUNTERS=1`) lê os contadores
de hardware do processador (ciclos, instruções, faltas no L1 e no TLB) pelos
frameworks internos `kperf`/`kperfdata`, o que exige root:
`sudo bench/run_counters.sh` grava `bench/results/parte2/contadores.txt`.

### Medição da Parte 3

```sh
./build/csr/cos_bench3 GRAFO.txt direcionado RODADAS
./build/csr/cos_bench3 GRAFO.txt direcionado 10 --fw --bf-todos --bf-amostra 1000
```

O programa lê o grafo e mede, em segundos e sem contar a leitura, `RODADAS`
execuções de Bellman-Ford até o vértice `100`, em uma thread. Cada linha informa
o tempo, as rodadas do algoritmo e a presença de ciclo negativo; no fim saem
média, desvio padrão e mínimo. As opções são:

- `--fw`: mede Floyd-Warshall; `--fw-rodadas N` troca o número de execuções
  (padrão: `RODADAS`) e `--fw-limite-gib G` define o limite de memória (padrão
  16), acima do qual a seção traz `situacao=memoria_insuficiente`;
- `--bf-todos`: mede todos os pares por Bellman-Ford, uma execução por destino
  (`all_pairs_bellman_ford`, com `--threads` threads);
- `--bf-amostra K`: com `--bf-todos`, mede só `K` destinos igualmente
  espaçados, em uma thread, e estima o tempo total como o tempo médio por destino
  vezes `V` (`estimado=sim`);
- `--johnson`: mede Johnson, `RODADAS` execuções, com o limite de memória de
  `--fw-limite-gib`; a seção `[johnson]` informa a fronteira usada;
- `--fronteira heap|radix`: fronteira de Johnson (padrão `heap`);
- `--threads N`: threads do Floyd-Warshall, do todos-pares completo por
  Bellman-Ford e de Johnson (padrão 1). Bellman-Ford de um destino e a amostra
  sempre usam uma thread.

`bench/run_part3.sh [DADOS] [RESULTADOS]` roda o protocolo da Parte 3 nos grafos
`p3_W_1` a `p3_W_5` de `DADOS` (padrão `data/`) e grava em `RESULTADOS` (padrão
`bench/results/parte3/`): `maquina.txt`, `NOME.txt` (uma chamada de `cos_bench3`
por grafo, 10 rodadas, `--threads` igual ao número de núcleos via `hw.ncpu` ou
`nproc`) e `NOME.relatorio.txt` (`cos_part3`, com caminhos, sem medição de tempo).
Cada chamada mede Bellman-Ford até o vértice 100, o todos-pares por Bellman-Ford
(completo em W_1 e W_2; amostra de 200, 30 e 10 destinos em W_3, W_4 e W_5) e o
Floyd-Warshall (pulado com `situacao=memoria_insuficiente` quando a matriz passa
de `FW_LIMITE_GIB`). W_2 roda por último. As variáveis são `FW_RODADAS` (padrão
10), `FW_LIMITE_GIB` (padrão 16) e `GRAFOS` (lista separada por espaços, para
medir só alguns grafos; padrão todos). Leva cerca de 3 h, dominadas pelo
Floyd-Warshall de W_2, e os tempos só valem com a máquina ociosa.

### Dados da Parte 3

O estudo espera em `data/` os arquivos `p3_W_1.txt` a `p3_W_5.txt`. `p3_W_1` vem
do site da disciplina de 2025 (`grafos-2025/data/grafo_W_1.txt.gz`) e `p3_W_2` a
`p3_W_5` vêm de 2023 (`grafos-2023/data/grafo_W_n.txt.gz`), com base
`https://pesc.coppe.ufrj.br/~daniel/`:

```sh
base=https://pesc.coppe.ufrj.br/~daniel
curl -sS $base/grafos-2025/data/grafo_W_1.txt.gz | gunzip > data/p3_W_1.txt
for n in 2 3 4 5; do
  curl -sS $base/grafos-2023/data/grafo_W_$n.txt.gz | gunzip > data/p3_W_$n.txt
done
```

### Resultados da Parte 3

Em `bench/results/parte3/`: `NOME.txt` (tempos de `cos_bench3`), `NOME.relatorio.txt`
(tabelas de `cos_part3`, com os caminhos), `maquina.txt` e `execucao.log`.
`primeira_execucao/` guarda a primeira passada de W_3 a W_5, mantida por
transparência: o tempo de uma thread saiu cerca de 2 vezes maior, provavelmente
por rodar em núcleos de eficiência. O relatório usa a segunda passada, com a
máquina ociosa. O relatório e a apresentação ficam em `report/parte3/` e
`presentation/parte3/`; o `README.md` de cada um explica como refazê-los.

`bench/fw_variants.cpp` compara o Floyd-Warshall em blocos da biblioteca com o
laço triplo simples (uma thread) e confere distâncias e pais. Não tem alvo no
CMake; compile à mão, a partir da raiz do repositório:

```sh
mkdir -p /tmp/fw
c++ -O3 -std=c++20 -I include bench/fw_variants.cpp -o /tmp/fw/fw_variants
/tmp/fw/fw_variants GRAFO.txt THREADS [direcionado|nao_direcionado] [--sem-ingenuo] [--repete N]
```

Sem `--sem-ingenuo`, o programa roda também a versão simples, compara as duas
matrizes e termina com erro se divergirem. A compilação usa a CSR; para a matriz,
acrescente `-DCOS_MATRIX=1`.

`bench/contagem_heap.cpp` conta as operações do heap em Dijkstra e gerou
`report/parte2/contagens.json`, usado por `report/parte2/tabelas.py`. Também não
tem alvo no CMake e exige C++23 (`std::print`):

```sh
mkdir -p /tmp/fw
c++ -O3 -std=c++23 -I include bench/contagem_heap.cpp -o /tmp/fw/contagem_heap
/tmp/fw/contagem_heap NOME ARQUIVO RODADAS
```

`bench/gerar_grafo.py V E SEMENTE SAIDA` gera grafos sintéticos no formato de
entrada. Com `--negativos`, cada peso `w(u, v)` ganha `p(u) - p(v)` para
potenciais aleatórios `p`. Todo ciclo mantém a soma dos pesos, então o grafo
tem arestas negativas e nenhum ciclo negativo; toda distância muda para
`d'(s, t) = d(s, t) + p(s) - p(t)`, o que permite conferir os resultados. Os
potenciais ficam em `SAIDA.potenciais`. Com `--ciclo-negativo`, o gerador
acrescenta um ciclo `a -> b -> c -> a` de soma `-3.00`. Ambas as opções exigem
grafo direcionado; `--nao-direcionado` gera o caso sem direção.

### Estudos de caso, relatório e apresentação

```sh
bench/run_case_studies.sh            # lê data/, grava bench/results/parte2/ (cerca de 2,6 h)
bench/run_lowlevel.sh                # experimentos de baixo nível (cerca de 10 min)
bench/run_contention.sh              # variação por disputa do processador (cerca de 40 min)
sudo bench/run_counters.sh           # contadores de hardware, só macOS (compile antes)
python3 -I bench/summarize.py        # gera presentation/parte2/data.js e report/parte2/data.json
python3 -I report/parte2/tabelas.py   # gera report/parte2/tabelas.tex a partir de data.json
(cd report/parte2 && tectonic relatorio.tex) # relatório em PDF (LaTeX)
```

A apresentação é `presentation/parte2/index.html` (reveal.js incluído, funciona sem
rede); veja [presentation/parte2/README.md](presentation/parte2/README.md).

## Verificação

Os mesmos testes são executados nas duas representações. A compilação habilita
`-Wall -Wextra -Wpedantic`, ou `/W4` no MSVC. O arquivo `.clang-format` define a
formatação do código.

Os requisitos da atividade estão em [docs/REQUISITOS.md](docs/REQUISITOS.md).
As principais decisões de implementação estão em
[docs/PROJETO.md](docs/PROJETO.md).
