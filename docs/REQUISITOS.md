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

A Parte 1 usa somente grafos sem pesos. As partes seguintes ampliam a mesma
biblioteca. Por isso, o armazenamento e os algoritmos do grafo ficam separados
da leitura e do relatório específicos de cada parte.

# Requisitos da Parte 2

A Parte 2 trabalha com grafos não direcionados com pesos reais nas arestas. O
arquivo tem o número de vértices na primeira linha e uma aresta por linha, no
formato `u v peso`.

Fonte: [enunciado oficial da Parte
2](https://pesc.coppe.ufrj.br/~daniel/grafos/trabalhos/trabalho-P2.pdf).

A biblioteca e o programa oferecem:

- leitura e representação de grafos com pesos;
- distância e caminho mínimo de uma origem até todos os vértices;
- algoritmo de Dijkstra quando todos os pesos são não negativos;
- aviso de que caminhos mínimos com pesos negativos ainda não foram
  implementados quando algum peso é negativo;
- Dijkstra com vetor de estimativas e com heap, sem escrever o algoritmo duas
  vezes;
- relatório das distâncias e caminhos da origem `10` até `20`, `30`, `40`, `50`
  e `60`;
- na rede de colaboração, distâncias e caminhos de Edsger W. Dijkstra até Alan
  M. Turing, J. B. Kruskal, Jon M. Kleinberg, Éva Tardos e Daniel R. Figueiredo,
  com os nomes dos pesquisadores.

O estudo de caso compara o tempo médio de Dijkstra com vetor e com heap em
origens sorteadas. Execuções muito longas da versão com vetor podem ser
estimadas a partir de algumas medições.

# Requisitos da Parte 3

A Parte 3 trabalha com grafos direcionados com pesos reais, possivelmente
negativos. O arquivo tem o mesmo formato da Parte 2. Um parâmetro do usuário
indica se o grafo é direcionado; nesse caso, a aresta `u v peso` vai do
primeiro vértice para o segundo.

Fonte: [enunciado oficial da Parte
3](https://pesc.coppe.ufrj.br/~daniel/grafos/trabalhos/trabalho-P3.pdf).

A biblioteca e o programa oferecem:

- leitura e representação de grafos direcionados com pesos;
- BFS, DFS e Dijkstra em grafos direcionados;
- Bellman-Ford de todos os vértices até um vértice dado, que devolve as
  distâncias, a árvore de caminhos mínimos e se há ciclo negativo, com as duas
  otimizações vistas em aula;
- Floyd-Warshall entre todos os pares, que devolve as distâncias, as árvores de
  caminhos mínimos de cada vértice e a detecção de ciclo negativo, com a
  otimização de memória vista em aula.

O estudo de caso, para cada grafo, informa:

- as distâncias de Bellman-Ford dos vértices `10`, `20` e `30` até o `100`
  (tabela);
- as distâncias de Floyd-Warshall entre os vértices `10`, `20`, `30`, `40` e
  `50` (tabela);
- o tempo médio de 10 execuções de cada algoritmo, em segundos, sem contar a
  leitura nem a escrita de arquivos;
- o tempo de 10 execuções do todos-pares por Bellman-Ford, com uma execução
  para cada destino, contra Floyd-Warshall, com a indicação de qual foi mais
  eficiente e por quê.

O relatório tem no máximo 5 páginas e inclui o endereço da fonte. A apresentação
dura 8 minutos.

Grafos do estudo de caso: `W_1`, do site de 2025 (`grafos-2025`), e `W_2` a
`W_5`, do site de 2023 (`grafos-2023`), em
`https://pesc.coppe.ufrj.br/~daniel/`.

Prazo: entrega e apresentação em 23/11/2026.
