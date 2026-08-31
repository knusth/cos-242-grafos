# cos-grafos

Biblioteca pequena em C++20 e programa da Parte 1 do trabalho. Este repositório
contém apenas a implementação atual. As outras duas partes poderão ampliar a
mesma biblioteca sem alterar o programa da Parte 1.

O código usa apenas a biblioteca padrão de C++. Os vértices são números
naturais densos de 32 bits, o grafo não muda depois de construído e cada
compilação contém somente uma representação:

- `csr`: vetores de deslocamentos e vizinhos, padrão para grafos esparsos;
- `matrix`: um byte por célula da matriz, ativado por `COS_MATRIX=ON`.

## Compilação e testes

Requisitos:

- CMake 3.20 ou mais recente;
- compilador compatível com C++20, como Clang, GCC ou MSVC.

CSR:

```sh
cmake --preset csr
cmake --build --preset csr
ctest --preset csr
```

Matriz:

```sh
cmake --preset matrix
cmake --build --preset matrix
ctest --preset matrix
```

Os perfis não usam opções específicas da máquina e compilam de forma nativa
em x86-64 e AArch64. Não é necessário baixar dependências, gerar código, usar
contêiner ou instalar pacotes do projeto.

## Execução da Parte 1

```sh
./build/csr/cos_part1 ENTRADA.txt RELATORIO.txt
./build/csr/cos_part1 ENTRADA.txt RELATORIO.txt 3
```

O vértice de origem é opcional, começa em `1` e tem valor padrão `1`. O arquivo
de entrada segue o formato do trabalho:

```text
quantidade_de_vertices
primeiro_vertice segundo_vertice
primeiro_vertice segundo_vertice
...
```

O programa escreve estatísticas do grafo, árvores de pais e níveis de BFS e
DFS, consultas de distância, componentes em ordem decrescente de tamanho e o
diâmetro exato. `memoria_bytes` mede o armazenamento pertencente ao grafo, não
toda a memória residente do processo.

## Organização do repositório

```text
include/cos/       biblioteca somente de cabeçalhos e leitor numérico
part1/             programa que produz o relatório da Parte 1
tests/             testes das duas representações e entrada pequena
docs/              requisitos e decisões de implementação
```

A biblioteca não conhece o formato específico do trabalho. `file_reader.hpp`
lê um cabeçalho e pares numéricos. `part1/main.cpp` converte a numeração que
começa em `1` e concentra toda a formatação do relatório.

## Qualidade do código

O arquivo `.clang-format` define a formatação. A compilação usa
`-Wall -Wextra -Wpedantic`, ou `/W4` no MSVC, e o código pode ser analisado pelo
Cppcheck sem configuração adicional.
