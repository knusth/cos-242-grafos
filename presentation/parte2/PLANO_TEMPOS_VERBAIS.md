# Plano: tempos verbais da apresentação

Este plano define a história contada pelos slides e escolhe o tempo de cada verbo a partir dela. Depois,
propõe o texto novo de cada slide.

**Situação:** aplicado em `build.py`, com títulos em frase em todos os slides (não só do 7 ao 12),
para que a sequência de títulos conte a história. O slide 9 ganhou a virada da história (a conta cresceu
27×, o tempo do heap 582×).

## 1. O que a pesquisa diz

**Redação científica (inglês e português)**

- Guias de redação concordam:
  - o pretérito vai para o que os autores **fizeram** e **observaram** (método e resultados);
  - o presente vai para fatos gerais, interpretação, conclusões e para frases cujo sujeito é a própria
    figura ou tabela ("a Tabela 1 mostra").

  Fontes: Editage, AJE, International Science Editing.
- A Editage separa um caso para engenharia e computação:
  - **presente** para a descrição do sistema e do algoritmo;
  - **pretérito** para experimentos, benchmarks e testes.
- O tempo muda a força da afirmação:
  - "a temperatura aumentou" fala de um experimento;
  - "a temperatura aumenta" generaliza a observação.

  Pôr no presente um número medido numa máquina afirma mais do que os dados permitem.
- Guias em português (AJE Brasil, wiki do IFSC, FastFormat) dizem o mesmo:
  - pretérito na metodologia e nos resultados;
  - presente na introdução, na discussão e quando a figura é o sujeito.

  Também apontam que misturar tempos sem critério dentro de uma seção é um erro comum.

**Linguística do texto (Weinrich, via Koch)**

- Weinrich, em *Estructura y función de los tiempos en el lenguaje*, separa os tempos em dois
  "mundos". Koch adota a mesma divisão em *A coesão textual* e em *Argumentação e linguagem*:
  - **mundo comentado**: presente, pretérito perfeito e futuro do presente. O falante se dirige ao
    ouvinte e pede atenção e reação. É o registro de quem argumenta.
  - **mundo narrado**: pretérito perfeito, imperfeito, mais-que-perfeito e futuro do pretérito. É o
    registro de quem conta uma história.
- No mundo narrado, o tempo verbal também marca **relevo**:
  - o perfeito põe o fato em primeiro plano ("medimos", "o heap foi mais rápido");
  - o imperfeito descreve o pano de fundo ("outros processos rodavam na máquina").
- Uma apresentação é **comentário**: fala-se agora, para um público presente, sobre algo que está na
  tela. Dentro dela há trechos **narrados** (o que fizemos). Por isso a mistura de presente e pretérito
  é natural, desde que cada verbo responda a uma pergunta: *quando isso é verdade, em relação ao
  momento da fala?*

**Desenho de slides (Alley e Neeley, 2005)**

- O artigo defende que cada slide tenha um título em forma de frase, com a afirmação principal, e
  evidência visual no corpo, no lugar de listas de tópicos.
- Motivo dado pelos autores: listas "deixam premissas sem dizer" e "relações sem especificar".
- Os experimentos de Alley mostraram mais retenção com títulos em frase. Outros pesquisadores não
  replicaram o efeito (Blokzijl e Andeweg).

**O caso citado**

> "100 origens sorteadas, as mesmas para as duas filas; só o Dijkstra é cronometrado"

- O primeiro trecho é um particípio solto ("sorteadas"): não tem sujeito nem tempo. Parece anotação,
  não frase.
- O segundo está no presente passivo ("é cronometrado"), o tempo de uma regra ou de um processo que
  ainda acontece. Mas o fato é uma ação concluída, feita por nós.
- As duas partes estão em registros diferentes, unidas por ponto e vírgula. O relatório diz o mesmo de
  forma natural: "sorteamos *k* = 100 vértices de origem e usamos os mesmos nas duas versões. Medimos
  apenas a execução de Dijkstra, sem a leitura do arquivo."

## 2. A história

Antes de escolher tempos, a história em poucas frases, na ordem dos slides:

1. **O pedido** (agora, enunciado): o trabalho pede caminhos mínimos com Dijkstra em duas versões, sem
   escrever o algoritmo duas vezes.
2. **O que construímos** (passado, mas o código existe hoje): guardamos o grafo em CSR, escrevemos um
   único Dijkstra com a fila como parâmetro e duas filas, um vetor e um heap com índice.
3. **Como medimos** (passado): rodamos 100 origens por grafo e cronometramos só o Dijkstra. O vetor
   seria lento demais nos grafos grandes, então estimamos esses tempos e conferimos a estimativa onde
   deu.
4. **O que encontramos** (passado):
   - as duas versões deram as mesmas distâncias;
   - na rede de colaboração, o caminho mais curto nem sempre teve menos arestas;
   - o heap foi de 122× a 44 mil× mais rápido.
5. **A pergunta**: o tempo do heap não cresceu como (*n* + *m*) log *n*. O custo por operação ficou
   21× maior do W₃ ao W₇. Por quê?
6. **A investigação** (passado, com interpretação no presente):
   - contamos as operações: foram menos do que a análise conta, e o número depende do grau;
   - medimos o custo de uma leitura na máquina: de ~7 ns, com os dados no cache, a ~116 ns fora dele;
   - testamos a hipótese renumerando os vértices: mesmas operações, até 3,3× mais lento.
7. **O que fica** (presente): a análise assintótica conta operações. Em grafos grandes, o tempo também
   depende de onde os dados estão na memória.

## 3. Regras

Cada verbo responde: *quando isso é verdade, em relação ao momento da fala?*

| Plano | Tempo | Quando usar | Exemplo |
|---|---|---|---|
| Fato permanente | presente | definição, código, estrutura de dados, propriedade fixa de um grafo | "`position_` diz onde cada vértice está"; "o W₆ não é conexo" |
| O que está na tela | presente | a figura ou a tabela é o sujeito | "a figura mostra o tamanho do heap" |
| O que fizemos | pretérito perfeito, 1ª pessoa do plural | ações do trabalho: escrever, rodar, medir, estimar, testar | "sorteamos 100 origens"; "cronometramos só o Dijkstra" |
| O que observamos | pretérito perfeito | todo número que saiu de uma execução | "o heap foi 122× mais rápido"; "levou 0,11 s" |
| Estado de fundo | pretérito imperfeito | situação durante uma execução, não o resultado | "o heap já guardava 89% dos vértices" |
| Interpretação | presente | o que concluímos e estamos dispostos a generalizar | "em grafo denso, o heap enche cedo" |
| Hipótese | futuro do pretérito | o que não foi feito ou não aconteceu | "com vetor, uma origem levaria 16 dias"; "a matriz ocuparia 22 PB" |

Regras de forma:

1. Toda frase no corpo do slide tem sujeito e verbo conjugado. Particípio solto ("vetor medido no W₃")
   só pode aparecer em rótulo: título de tabela, cabeçalho, legenda curta.
2. Agente explícito: "nós" quando a ação foi nossa ("medimos"), não a passiva sem agente ("é
   cronometrado"). É o que o relatório já faz.
3. Quando uma frase junta resultado e interpretação, cada parte fica no seu tempo. A frase começa pela
   lição, no presente, e traz a prova no pretérito: "o número de operações depende do grau: medimos 7%
   das arestas no W₃ e 90% no W₇".
4. Teste para o presente: *a frase continuaria verdadeira se rodássemos de novo em outra máquina?* Se
   não, o tempo é o pretérito.
5. Um número arredondado no texto tem que bater com o da figura (hoje o slide 12 diz "3×" e a figura,
   3,1×).

## 4. Diagnóstico do texto atual

| Slide | Trecho atual | Problema |
|---|---|---|
| 3 | "Memória: 4(*n* + 1) + 24*m* bytes, contra 9*n*² da matriz" | sem verbo; a matriz é hipotética e pede futuro do pretérito |
| 4 | "O algoritmo é escrito uma vez." | passiva no presente sem agente; soa como regra |
| 6 | "100 origens sorteadas, as mesmas para as duas filas; só o Dijkstra é cronometrado" | particípio solto + passiva presente |
| 6 | "vetor medido no W₃ e no W₄; do W₅ ao W₇, estimado por..." | só particípios; não diz quem fez nem quando |
| 8 | "Dijkstra com heap leva 0,11 s por origem" | número medido no presente |
| 9 | "com vetor, uma única origem levaria de minutos a dias" | o W₄ foi medido (10,9 min); "levaria" só vale do W₅ ao W₇ |
| 9 | "* Estimado: ... Vetor medido no W₃ com 100 origens e no W₄ com 5." | particípios soltos |
| 10 | "No W₃, depois de 2% das extrações o heap já guarda 89%" | uma execução descrita como regra |
| 11 | "Por isso o custo por operação cresce 21×" | número medido no presente; afirma causa sem dizer que o slide 12 a testa |
| 12 | "a partir de 10 mi, a aleatória é 3× mais lenta" | número medido no presente; 3× contra 3,1× da figura |
| 13 | itens alternam lição e prova sem padrão | mesma ideia em tempos diferentes (12: "é"; 13: "ficou") |

O que já está certo e fica: definições no presente (slides 2, 3, 5), "vetor e heap deram as mesmas
distâncias" (7), "o heap foi mais rápido" (9, 13), "sem ele, diminuir uma chave exigiria" (5).

## 5. Texto proposto por slide

Os números vêm dos mesmos campos de `data.json`, `contagens.json` e do relatório; nenhum é novo.

### 2. Problema

Sem mudança. A definição usa o infinitivo de tarefa ("calcular dist(*s*, *v*)"), como um enunciado, e
"O que o trabalho pede" governa os itens da lista.

### 3. CSR

- Antes: "Memória: 4(*n* + 1) + 24*m* bytes, contra 9*n*² da matriz de adjacências com pesos."
- Depois: "O CSR ocupa 4(*n* + 1) + 24*m* bytes; uma matriz de adjacências com pesos ocuparia 9*n*²."
- Legenda da tabela: "Memória do grafo em CSR e a que uma matriz ocuparia."

### 4. Código do Dijkstra

- Antes: "O algoritmo é escrito uma vez. `dijkstra<VectorFrontier>` e `dijkstra<HeapFrontier>` geram as
  duas versões; só as linhas destacadas dependem da fila."
- Depois: "O código tem um único Dijkstra. `dijkstra<VectorFrontier>` e `dijkstra<HeapFrontier>` geram
  as duas versões; só as linhas destacadas dependem da fila."
- Antes: "Peso negativo: o programa para antes do laço (linha 270)."
- Depois: "Se algum peso é negativo, o programa para antes do laço (linha 270)."

O restante já está no presente de descrição do código.

### 5. Filas de prioridade

Sem mudança. Tudo é descrição do código (presente) e uma hipótese ("exigiria").

### 6. Metodologia

É o slide que mais muda. Ele passa a narrar, como o relatório:

- "Rodamos tudo num Apple M3 Pro com 36 GiB, compilando com `-O3`."
- "Em cada grafo, sorteamos 100 origens e usamos as mesmas nas duas filas. Cronometramos só o Dijkstra,
  sem a leitura do arquivo."
- "Com o vetor, uma origem levaria horas no W₅ e dias no W₇. Por isso, medimos o vetor só no W₃ e no
  W₄; nos outros, estimamos o tempo pelo custo de uma extração. Onde deu para comparar, a estimativa
  errou 1% e 11%."
- Nota da tabela, antes: "O W₆ não é conexo: em média, 9.999.997 dos 10.000.000 vértices são
  alcançados."
- Nota da tabela, depois: "O W₆ não é conexo: em média, cada origem alcançou 9.999.997 dos 10.000.000
  vértices."

Conferir o tamanho: são três frases a mais que hoje. Se não couber, a primeira vira o rótulo "Apple M3
Pro, 36 GiB, `-O3`", que é um rótulo de dados, não uma frase.

### 7. Distâncias

- "Vetor e heap deram as mesmas distâncias em todas as origens comparadas." (já está certo)
- Antes: "com pesos, muitas arestas leves vencem poucas pesadas."
- Depois: "com pesos, muitas arestas leves podem vencer poucas pesadas."

O presente fica, porque é interpretação; o modal evita generalizar além do exemplo.

### 8. Rede de colaboração

- Antes: "Dijkstra com heap leva 0,11 s por origem."
- Depois: "Com heap, o Dijkstra levou 0,11 s por origem."
- A legenda ("Kleinberg está mais perto que Kruskal") fica no presente: é propriedade da rede.

### 9. Tempos

- Antes: "A partir do W₄, só a versão com heap é viável: com vetor, uma única origem levaria de minutos
  a dias."
- Depois: "A partir do W₄, só o heap foi viável: com vetor, uma origem levou 11 min no W₄ e levaria de
  16 h a 16 dias nos maiores."
- Antes: "* Estimado: tempo médio de uma extração × vértices alcançados. Vetor medido no W₃ com 100
  origens e no W₄ com 5."
- Depois: "* Estimado pelo custo de uma extração (slide 6). Medimos o vetor com 100 origens no W₃ e
  com 5 no W₄."

### 10. Quantas operações

- Legenda, antes: "No W₃, depois de 2% das extrações o heap já guarda 89% dos vértices."
- Legenda, depois: "Na execução mostrada, depois de 2% das extrações o heap do W₃ já guardava 89% dos
  vértices."
- Bloco: mantém a interpretação no presente e prende os números ao que foi medido. "Em grafo denso, o
  heap enche cedo, e depois quase nenhuma aresta melhora uma estimativa: no W₃, só 7% delas fizeram
  `push`. Em grafo esparso, o heap fica pequeno, mas quase toda aresta é a primeira a alcançar o
  vizinho: 90% no W₇."

### 11. Custo de cada operação

- Antes: "O W₃ cabe no cache: ~7 ns por leitura. Do W₅ em diante, ~116 ns. Por isso o custo por
  operação cresce 21× do W₃ ao W₇."
- Depois: "Os dados do W₃ cabem no cache, onde uma leitura levou ~7 ns; do W₅ em diante, cada leitura
  levou ~116 ns. Esta é a nossa explicação para o custo por operação ter crescido 21×; o próximo slide
  a testa."

A última frase deixa a história explícita: aqui há uma hipótese, e o slide 12 é o teste.

### 12. Numeração

- Antes: "As operações do heap são as mesmas; muda só onde os vizinhos ficam na memória."
- Depois: "Renumeramos os vértices do mesmo grafo: as operações do heap continuaram as mesmas, só mudou
  onde os vizinhos ficam na memória."
- Antes: "Com 100 mil vértices tudo cabe no cache e a numeração quase não importa; a partir de 10 mi, a
  aleatória é 3× mais lenta."
- Depois: "Com 100 mil vértices, tudo coube no cache e a numeração quase não mudou o tempo (1,2×); com
  10 mi, a aleatória foi 3,1× mais lenta."
- Bloco, antes: "Renumerar o W₅ em ordem de BFS deu 5,03 s, contra 5,19 s: não há vizinhança próxima a
  recuperar."
- Bloco, depois: "Renumeramos o W₅ em ordem de BFS, e o tempo caiu só de 5,19 s para 5,03 s: não há
  vizinhança próxima a recuperar."

### 13. Conclusões

Cada item: a lição no presente, a prova no pretérito.

- "Um único Dijkstra, com a fila como parâmetro do template, gera as duas versões pedidas; nos testes,
  as duas deram as mesmas distâncias."
- "O heap foi mais rápido em todos os grafos, de 122× a 44 mil×, e foi a única versão viável a partir
  do W₄."
- "O número de operações no heap depende do grau: medimos 7% das arestas no grafo mais denso e 90% no
  mais esparso."
- "Em grafos grandes, o custo de cada operação vem da memória: com os vértices numerados ao acaso, o
  mesmo grafo ficou até 3,3× mais lento."
- "Na rede de colaboração, o caminho mínimo nem sempre é o de menos arestas."
- Trabalho futuro: sem mudança (rótulo).

### Apêndice

Só legendas; ficam como estão. A legenda de A4 já está certa: "O vetor foi interrompido após poucas
extrações; compare as proporções, não os totais."

## 6. Títulos (decisão separada)

Alley sugere títulos em forma de frase, com a afirmação do slide. Isso combina com a história, porque
cada título vira uma frase dela. Os títulos seguiriam as mesmas regras de tempo:

| Slide | Título atual | Título em frase |
|---|---|---|
| 7 | Estudo de caso: distâncias e caminhos mínimos | Vetor e heap deram as mesmas distâncias |
| 8 | Estudo de caso: rede de colaboração | Na rede de colaboração, o caminho mais curto nem sempre tem menos arestas |
| 9 | Estudo de caso: tempo médio de execução | O heap foi de 122× a 44 mil× mais rápido |
| 10 | Discussão: quantas operações o heap faz | O heap fez menos operações do que a análise conta |
| 11 | Discussão: quanto custa cada operação | Cada operação ficou mais cara quando os dados saíram do cache |
| 12 | Teste: a mesma conta com outra numeração dos vértices | Com os vértices ao acaso, o mesmo grafo ficou até 3,3× mais lento |

Recomendação: adotar só nos slides 7 a 12, onde há uma afirmação a fazer. Nos slides 2 a 6, o título
de tópico ("Metodologia") funciona, porque o slide apresenta um objeto, não um resultado. Contra:
- a evidência de Alley não foi replicada;
- títulos longos ocupam duas linhas na barra de 76 px, que hoje tem uma.

## 7. Fala (ROTEIRO.md)

A fala segue as mesmas regras, com duas diferenças próprias da língua oral:

- o futuro perifrástico guia o público: "vamos ver quanto custa cada operação";
- as pontes entre slides narram: "medimos o tempo e vimos que...", "fomos atrás do porquê".

Reescrever os campos **Dizer** e **Ponte** do roteiro na primeira pessoa do plural. Os ganchos
numéricos ficam no pretérito.

## 8. Execução e verificação

1. Trocar as strings em `build.py` conforme a seção 5. No slide 12, usar 1 casa decimal na razão, para
   ficar igual à figura.
2. Gerar o PDF e conferir slides 6, 9, 11 e 12, que ganham texto.
3. Procurar particípios soltos no início de frase e números medidos no presente. A busca é manual,
   porque não há regra automática segura para isso:
   `pdftotext apresentacao.pdf - | grep -n "medido\|estimado\|sorteadas\| é [0-9]\| leva \| cresce "`
4. Atualizar `ROTEIRO.md` (seção 7) e acrescentar a `EXPLICACAO.md` uma seção curta "Tempos verbais"
   com a tabela da seção 3.
5. Decidir sobre os títulos (seção 6) depois de ver os slides com o texto novo.

## Fontes

- Editage, "The secret to using tenses in scientific writing":
  https://www.editage.com/insights/the-secret-to-using-tenses-in-scientific-writing
- AJE, "Escolhendo o tempo verbal correto para o seu artigo científico":
  https://www.aje.com/br/arc/escolhendo-o-tempo-verbal-correto-para-o-seu-artigo-cientifico-guia-gratuito-para-baixar
- International Science Editing, "Verb tenses in scientific manuscripts":
  https://www.internationalscienceediting.com/verb-tenses-scientific-manuscripts/
- IFSC, "Dicas para escrita de texto científico":
  https://wiki.sj.ifsc.edu.br/wiki/index.php/Dicas_para_escrita_de_texto_cient%C3%ADfico
- H. Weinrich, *Estructura y función de los tiempos en el lenguaje*, Gredos, 1968, cap. "Mundo
  comentado y mundo narrado".
- I. V. Koch, *A coesão textual*, e *Argumentação e linguagem*.
- Resumo da teoria aplicado ao imperfeito (UFPE):
  https://periodicos.ufpe.br/revistas/pedaletra/article/download/231760/25891/78521
- M. Alley e K. Neeley, "Rethinking the Design of Presentation Slides: A Case for Sentence Headlines
  and Visual Evidence", *Technical Communication* 52(4), 2005: http://writing.engr.psu.edu/2005_alley_neeley.pdf
- M. Alley, *The Craft of Scientific Presentations*, Springer.
- `report/parte2/relatorio.tex`, seção Metodologia: exemplo do mesmo conteúdo escrito com pretérito e primeira
  pessoa.

**Títulos:** estilo de capítulo, sem verbo ("Representação do grafo", "Tempo de execução"). A mensagem de cada slide fica no roteiro, no presente; o pretérito perfeito fica no corpo, nas legendas e na fala.
