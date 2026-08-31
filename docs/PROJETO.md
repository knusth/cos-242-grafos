# Decisões de projeto

O fluxo completo de informações é direto:

```text
arquivo de texto -> pares numéricos -> grafo imutável -> algoritmos -> relatório
```

`file_reader.hpp` lê um cabeçalho e pares numéricos sem interpretar seu
significado. O programa da Parte 1 converte os identificadores que começam em
`1` para os índices internos que começam em `0` e formata os resultados.
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

## Posse e duração dos dados

- `Graph` possui a topologia pronta e as estatísticas escalares.
- A construção recebe uma visão das arestas e não guarda o vetor de entrada.
- Cada algoritmo público possui seus dados temporários durante uma chamada.
- Os resultados de BFS e DFS pertencem à função visitante.
- A otimização de retorno do C++ transfere os vetores de resultado.

Não há dependências externas nem instruções específicas de uma arquitetura. O
mesmo código e os mesmos perfis compilam de forma nativa em x86-64 e AArch64.

