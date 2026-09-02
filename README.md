# cos-grafos

Este repositório reúne a biblioteca de grafos `cos` e o programa desenvolvido
para a Parte 1 do trabalho de COS242. Nesta etapa, o projeto trabalha com
grafos não direcionados e sem pesos.

A biblioteca é escrita em C++20, é `header-only` e usa somente a biblioteca
padrão. Depois de construído, o grafo é imutável. Essa escolha deixa a
representação compacta e permite que as buscas percorram dados contíguos na
memória.

O trabalho terá outras duas partes. Elas poderão acrescentar operações à mesma
biblioteca, sem misturar os algoritmos do grafo com a leitura e a escrita
específicas de cada programa.

## Funcionalidades

A implementação atual oferece:

- matriz e vetor de adjacências;
- número de vértices e arestas;
- graus mínimo e máximo, média e mediana dos graus;
- busca em largura (BFS) e busca em profundidade (DFS), com pai e nível de cada
  vértice;
- distância entre vértices e diâmetro exato;
- componentes conexas em ordem decrescente de tamanho.

Os vértices do arquivo são identificados pelos inteiros de `1` a `V`.
Internamente, a biblioteca usa índices consecutivos de 32 bits, de `0` a
`V - 1`.

## Organização

```text
include/cos/       biblioteca e leitor de pares numéricos
part1/             programa da Parte 1
tests/             testes e grafo pequeno de exemplo
docs/              requisitos e decisões de projeto
```

`graph.hpp` contém a representação e os algoritmos. `file_reader.hpp` limita-se
a ler um cabeçalho seguido de pares de números. A conversão da numeração dos
vértices e a produção do relatório ficam em `part1/main.cpp`.

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

## Verificação

Os mesmos testes são executados nas duas representações. A compilação habilita
`-Wall -Wextra -Wpedantic`, ou `/W4` no MSVC. O arquivo `.clang-format` define a
formatação do código.

Os requisitos da atividade estão em [docs/REQUISITOS.md](docs/REQUISITOS.md).
As principais decisões de implementação estão em
[docs/PROJETO.md](docs/PROJETO.md).
