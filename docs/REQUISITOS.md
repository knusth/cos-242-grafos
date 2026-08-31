# Requisitos da Parte 1

A Parte 1 trabalha com grafos não direcionados, sem pesos e imutáveis. Os
vértices do arquivo de entrada são numerados de `1` até `V`.

Fonte: [enunciado oficial da Parte
1](https://www.cos.ufrj.br/~daniel/grafos-2025/trabalhos/trabalho-P1.pdf).

A biblioteca e o programa oferecem:

- representações por vetor de adjacências (CSR) e matriz de adjacências;
- quantidades de vértices e arestas;
- graus mínimo e máximo, média e mediana dos graus;
- BFS e DFS a partir de uma origem escolhida, com pai e nível de cada vértice;
- menores distâncias sem pesos e diâmetro exato;
- quantidade, membros e tamanhos das componentes conexas;
- componentes em ordem decrescente de tamanho;
- leitura da entrada e escrita do relatório nos limites do programa.

O estudo de caso também compara as duas representações com os grafos oficiais.
Ele mede a memória do grafo, executa 100 BFS e 100 DFS, consulta pais
específicos, calcula as distâncias pedidas, informa os tamanhos das componentes
e calcula o diâmetro. A medição dos algoritmos não deve incluir a leitura nem a
escrita de arquivos.

Esta revisão implementa somente a Parte 1. As duas partes seguintes deverão
ampliar a mesma biblioteca. Por isso, o armazenamento e os algoritmos do grafo
ficam separados da leitura e do relatório específicos desta parte.

