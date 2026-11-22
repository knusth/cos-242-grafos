#!/usr/bin/env python3
"""Apresentação da Parte 2: index.html (navegável) e apresentacao.pdf (uma página por slide).

    python3 -I presentation/parte2/build.py            # HTML e PDF
    python3 -I presentation/parte2/build.py --sem-pdf  # só HTML

Os números vêm de report/parte2/data.json, report/parte2/contagens.json e bench/results/parte2/. Os trechos de código
são conferidos contra include/cos/graph.hpp e levam o número real das linhas; se o código mudar,
o build para com erro. Todo gráfico é SVG estático: tela e PDF mostram a mesma coisa.
"""

import base64
import html
import json
import math
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
RES = RAIZ / 'bench/results/parte2'
DADOS = json.loads((RAIZ / 'report/parte2/data.json').read_text())
CONTAGENS = json.loads((RAIZ / 'report/parte2/contagens.json').read_text())
CONT = CONTAGENS['graphs']
G = {g['name']: g for g in DADOS['graphs']}
WS = ['W_3', 'W_4', 'W_5', 'W_6', 'W_7']
COLAB = DADOS['colab']
MAQ = DADOS['machine']
K = MAQ['k']
CTR = DADOS['counters']
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

# Cores do relatório: heap verde-azulado, vetor vermelho, azul das palavras-chave para destaque.
INK, INK2, INK3, LINHA, FUNDO = '#23373b', '#5b6b70', '#9aa5a8', '#dde3e4', '#f3f5f6'
AZUL, AZUL_BG = '#1f4e9c', '#e3eaf6'
HEAP, HEAP_BG = '#1b7f79', '#d9ecea'
VET, VET_BG = '#c0392b', '#f6dcd8'
SANS, MONO = "'Fira Sans'", 'Inconsolata'


# ---------------------------------------------------------------- números em pt-BR

def br(x, casas=0):
    s = f'{x:,.{casas}f}'
    return s.replace(',', '\0').replace('.', ',').replace('\0', '.')


def qtd(x):
    if x < 1e4:
        return br(x, 0)
    if x >= 1e6:
        v = x / 1e6
        return (br(v, 1) if v < 10 else br(v, 0)) + ' mi'
    return br(x / 1e3, 0) + ' mil'


def bytes_(b):
    for lim, u in ((1e15, 'PB'), (1e12, 'TB'), (1e9, 'GB'), (1e6, 'MB'), (1e3, 'kB')):
        if b >= lim * 0.9995:
            v = b / lim
            return (br(v, 2) if v < 10 else br(v, 0)) + ' ' + u
    return f'{b:.0f} B'


def dur(s):
    for lim, div, u, c in ((0.1, 1e-3, 'ms', 0), (60, 1, 's', 2), (3600, 60, 'min', 1),
                           (86400, 3600, 'h', 1), (1e12, 86400, 'dias', 1)):
        if s < lim:
            v = s / div
            return br(v, c if v < 10 else (1 if v < 100 and c else 0)) + ' ' + u


def wsub(nome):
    return f'W<sub>{nome[-1]}</sub>'


def wsvg(nome):
    return f'W<tspan dy="0.25em" font-size="70%">{nome[-1]}</tspan>'


def vetor_s(w):
    v = G[w]['vector']
    if v and v.get('mean_s'):
        return v['mean_s'], False
    return G[w]['vector_estimate_s'], True


def heap_s(w):
    return G[w]['heap']['mean_s']


def grau(w):
    return 2 * G[w]['edges'] / G[w]['vertices']


def espera(c):
    return c['ciclos_espera_l1d'] / c['ciclos']


def secao_grafo(arq):
    """Lê a seção [grafo] de uma saída do programa."""
    out, dentro = {}, False
    for l in (RES / arq).read_text().splitlines():
        if l.startswith('['):
            dentro = l == '[grafo]'
        elif dentro and '=' in l:
            k, v = l.split('=', 1)
            out[k] = v
    return out


# ---------------------------------------------------------------- legendas numeradas

NUM = {'Figura': 0, 'Tabela': 0}


def leg(tipo, texto, cima=False):
    NUM[tipo] += 1
    return f'<div class="leg{" cima" if cima else ""}"><b>{tipo} {NUM[tipo]}.</b> {texto}</div>'


# ---------------------------------------------------------------- SVG

def svg(w, h, corpo, k=1):
    return (f'<svg class="fig" width="{w * k:.0f}" height="{h * k:.0f}" viewBox="0 0 {w} {h}" '
            f'xmlns="http://www.w3.org/2000/svg">{corpo}</svg>')


def T(x, y, s, tam=15, cor=INK, anc='start', peso=400, fonte=SANS, extra=''):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" fill="{cor}" text-anchor="{anc}" '
            f'font-weight="{peso}" font-family="{fonte}" {extra}>{s}</text>')


def L(x1, y1, x2, y2, cor=INK, larg=1.5, extra=''):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{cor}" '
            f'stroke-width="{larg}" {extra}/>')


def R(x, y, w, h, fill='none', stroke='none', larg=1.5, extra=''):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{larg}" {extra}/>')


def C(x, y, r, fill, stroke='none', larg=2):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{larg}"/>'


HALO = 'stroke="#fff" stroke-width="4" paint-order="stroke"'
DEFS = ''.join(
    f'<marker id="p{nome}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{cor}"/></marker>'
    for nome, cor in (('i', INK), ('a', AZUL), ('h', HEAP), ('c', INK3)))
DEFS = f'<defs>{DEFS}</defs>'


def celulas(x, y, vals, w=38, h=32, fill=None, cor=None, tam=16, indices=True):
    """Um array desenhado como fileira de casas, com índices embaixo."""
    out = []
    for i, v in enumerate(vals):
        out.append(R(x + i * w, y, w, h, (fill or {}).get(i, '#fff'), INK2, 1))
        out.append(T(x + i * w + w / 2, y + h / 2 + tam * 0.36, v, tam, (cor or {}).get(i, INK), 'middle',
                     500, MONO))
        if indices:
            out.append(T(x + i * w + w / 2, y + h + 14, i, 11, INK3, 'middle', 400, MONO))
    return ''.join(out)


def eixo_log(v, lo, hi, a, b):
    return a + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (b - a)


# ---------------------------------------------------------------- código com linhas reais

FONTE = (RAIZ / 'include/cos/graph.hpp').read_text().splitlines()
KW = {'template', 'class', 'void', 'auto', 'const', 'while', 'true', 'if', 'break', 'return', 'throw',
      'struct'}
TIPOS = {'Vertex', 'Weight', 'Frontier', 'Entry', 'VectorFrontier', 'HeapFrontier'}
TOK = re.compile(r'(//.*$)|("[^"]*")|(\b\d+\b)|([A-Za-z_]\w*)|(.)')


def localiza(trecho, fonte=FONTE):
    """Número da linha de cada linha do trecho, em ordem; '…' marca um salto."""
    nums, k = [], 0
    for l in trecho.splitlines():
        if l.strip() == '…':
            nums.append(None)
            continue
        while k < len(fonte) and fonte[k].strip() != l.strip():
            k += 1
        if k == len(fonte):
            sys.exit(f'trecho não encontrado em graph.hpp: {l.strip()!r}')
        nums.append(k + 1)
        k += 1
    return nums


def realce(l):
    out = []
    for com, txt, num, pal, outro in TOK.findall(l):
        if com:
            out.append(f'<span class="c">{html.escape(com)}</span>')
        elif txt:
            out.append(f'<span class="s">{html.escape(txt)}</span>')
        elif num:
            out.append(f'<span class="n">{num}</span>')
        elif pal in KW:
            out.append(f'<span class="k">{pal}</span>')
        elif pal in TIPOS:
            out.append(f'<span class="t">{pal}</span>')
        else:
            out.append(html.escape(pal or outro))
    return ''.join(out)


def codigo(trecho, foco=(), titulo='include/cos/graph.hpp'):
    """Bloco de código com o texto e o número reais de cada linha de graph.hpp, sem a indentação
    comum. foco: trechos de texto; a linha que contém algum deles é destacada."""
    nums = localiza(trecho)
    reais = [FONTE[n - 1] for n in nums if n]
    ind = min(len(l) - len(l.lstrip()) for l in reais if l.strip())
    linhas = []
    for n in nums:
        if n is None:
            linhas.append('<span class="l gap"><i>…</i></span>')
            continue
        l = FONTE[n - 1][ind:]
        c = ' hi' if any(f in l for f in foco) else ''
        linhas.append(f'<span class="l{c}"><i>{n}</i>{realce(l)}</span>')
    return f'<div class="cod"><div class="arq">{titulo}</div><pre>{"".join(linhas)}</pre></div>'


def linha_de(texto, apos=None):
    """Número da linha de graph.hpp que contém o texto (deve ser única).
    Com `apos`, só conta as 10 linhas a partir da primeira que contém esse trecho."""
    inicio = 0
    if apos is not None:
        marcas = [i for i, l in enumerate(FONTE) if apos in l]
        if not marcas:
            sys.exit(f'{apos!r} não aparece em graph.hpp')
        inicio = marcas[0]
    achou = [i + 1 for i, l in enumerate(FONTE) if inicio <= i < inicio + (10 if apos else len(FONTE)) and texto in l]
    if len(achou) != 1:
        sys.exit(f'{texto!r} aparece {len(achou)} vezes em graph.hpp')
    return achou[0]


# ---------------------------------------------------------------- grafo de exemplo

EX_ARESTAS = [(0, 1, 7), (0, 2, 9), (0, 3, 2), (3, 2, 1), (3, 4, 8), (2, 5, 2), (2, 4, 4), (1, 5, 6),
              (4, 5, 3)]
EX_N = 6
EX_POS = {0: (40, 140), 1: (160, 40), 2: (190, 150), 3: (120, 250), 4: (300, 250), 5: (320, 80)}
# Onde vai o rótulo de distância de cada vértice, longe das arestas.
EX_ROT = {0: (-8, -22, 'end'), 1: (0, -26, 'middle'), 2: (0, -26, 'middle'), 3: (-24, 6, 'end'),
          4: (24, 6, 'start'), 5: (24, -8, 'start')}


def ex_csr():
    viz = {v: [] for v in range(EX_N)}
    for u, v, w in EX_ARESTAS:          # mesma ordem de preenchimento do build()
        viz[u].append((v, w))
        viz[v].append((u, w))
    offs, nb, ws = [0], [], []
    for v in range(EX_N):
        nb += [x for x, _ in viz[v]]
        ws += [w for _, w in viz[v]]
        offs.append(len(nb))
    return offs, nb, ws


def ex_arvore():
    """Distâncias e pais a partir do vértice 0 (Dijkstra simples, só para a figura)."""
    INF = float('inf')
    dist, pai, fora = [INF] * EX_N, [None] * EX_N, set()
    dist[0] = 0
    while len(fora) < EX_N:
        u = min((v for v in range(EX_N) if v not in fora), key=lambda v: dist[v])
        fora.add(u)
        for a, b, w in EX_ARESTAS:
            for x, y in ((a, b), (b, a)):
                if x == u and dist[u] + w < dist[y]:
                    dist[y], pai[y] = dist[u] + w, u
    return dist, pai


EX_OFFS, EX_NB, EX_WS = ex_csr()
EX_DIST, EX_PAI = ex_arvore()


def inf(x):
    return '∞' if x == float('inf') else f'{x:g}'


def grafo_ex(foco=None, arvore=False, dx=0, dy=0):
    """O grafo de exemplo. foco: vértice com as arestas destacadas. arvore: árvore de caminhos
    mínimos a partir de 0, com a distância de cada vértice."""
    P = {v: (x + dx, y + dy) for v, (x, y) in EX_POS.items()}
    out = []
    for u, v, w in EX_ARESTAS:
        (x1, y1), (x2, y2) = P[u], P[v]
        cor, larg = INK3, 1.6
        if foco is not None and foco in (u, v):
            cor, larg = AZUL, 3
        if arvore and (EX_PAI[v] == u or EX_PAI[u] == v):
            cor, larg = AZUL, 3.5
        out.append(L(x1, y1, x2, y2, cor, larg))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append(C(mx, my, 10, '#fff'))
        out.append(T(mx, my + 5, w, 14, cor if cor != INK3 else INK2, 'middle', 600, MONO))
    for v, (x, y) in P.items():
        f, c, t = '#fff', INK, INK
        if foco == v or (arvore and v == 0):
            f, c, t = AZUL, AZUL, '#fff'
        out.append(C(x, y, 17, f, c, 2))
        out.append(T(x, y + 6, v, 17, t, 'middle', 700, MONO))
        if arvore:
            ox, oy, anc = EX_ROT[v]
            out.append(T(x + ox, y + oy, f'<tspan font-style="italic">d</tspan> = {EX_DIST[v]:g}', 15, AZUL,
                         anc, 600, SANS, HALO))
    return ''.join(out)


# ---------------------------------------------------------------- slides

slides = []


def slide(titulo, corpo, secao='', cls=''):
    slides.append(dict(titulo=titulo, corpo=corpo, secao=secao, cls=cls))


# 1. Capa ---------------------------------------------------------------------------------------
logo = base64.b64encode((RAIZ / 'report/comum/minerva.png').read_bytes()).decode()
slide(None, f'''<div class="capa">
<img src="data:image/png;base64,{logo}" alt="Minerva, UFRJ">
<h1>Caminhos mínimos em grafos com pesos</h1>
<h2>Dijkstra com vetor e com heap</h2>
<hr>
<div class="aut">Felipe Marroni · Hygor Knust</div>
<div class="inst">COS242 Teoria dos Grafos, 2026/2 · Trabalho de Disciplina, Parte 2 · Professor: Daniel Ratton Figueiredo<br>
Universidade Federal do Rio de Janeiro · Escola Politécnica</div>
</div>''', cls='titulo')


# 2. Problema -----------------------------------------------------------------------------------
# 3. Representação: CSR -------------------------------------------------------------------------
def fig_csr(k=1):
    v = 2
    a, b = EX_OFFS[v], EX_OFFS[v + 1]
    W, H, x0, cw = 720, 250, 120, 46
    out = []
    for y, nome, sub in ((10, 'offsets_', 'n + 1 posições'), (110, 'neighbors_', '2m posições'),
                         (180, 'weights_', '2m posições')):
        out.append(T(x0 - 14, y + 21, nome, 17, INK, 'end', 700, MONO))
        out.append(T(x0 - 14, y + 39, sub, 12, INK2, 'end', 400))
    out.append(celulas(x0, 10, EX_OFFS, cw, 32, {v: AZUL_BG, v + 1: AZUL_BG}))
    viz = {i: AZUL_BG for i in range(a, b)}
    out.append(celulas(x0, 110, EX_NB, 33, 32, viz, tam=15))
    out.append(celulas(x0, 180, EX_WS, 33, 32, viz, tam=15))
    for i, alvo in ((v, a), (v + 1, b)):
        xs = x0 + i * cw + cw / 2
        xt = x0 + alvo * 33
        out.append(f'<path d="M{xs:.1f},58 C{xs:.1f},84 {xt:.1f},80 {xt:.1f},106" fill="none" '
                   f'stroke="{AZUL}" stroke-width="2" marker-end="url(#pa)"/>')
    out.append(T(x0 + a * 33, 244, f'vizinhos e pesos do vértice {v}: posições {a} a {b - 1}', 14, AZUL,
                 'start', 600))
    return svg(W, H, ''.join(out), k)


mem = ''.join(f'<tr><td class="e">{wsub(w)}</td><td>{qtd(G[w]["vertices"])}</td><td>{qtd(G[w]["edges"])}</td>'
              f'<td>{bytes_(G[w]["memory_bytes"])}</td><td>{bytes_(G[w]["matrix_bytes_estimate"])}</td></tr>'
              for w in ('W_3', 'W_7'))
slide('Representação do grafo', f'''<div class="g2" style="grid-template-columns: 340px 1fr; gap: 30px; align-items: center">
<figure>{svg(360, 290, grafo_ex(foco=2), 0.94)}</figure>
<figure>{fig_csr(1.08)}</figure>
</div>
{leg('Figura', 'Um grafo de 6 vértices e sua representação em CSR; em azul, o vértice 2 e seus vizinhos.')}
<div style="width: 560px; margin: 14px auto 0">{leg('Tabela', 'Memória do grafo.', True)}
<table class="bt"><tr><th class="e">grafo</th><th><span class="m">n</span></th><th><span class="m">m</span></th><th>CSR</th><th>matriz</th></tr>{mem}</table>
</div>''', 'Implementação')


# 4. Algoritmo: o código de graph.hpp -----------------------------------------------------------
DIJKSTRA = '''template <class Frontier> void dijkstra(Vertex source, auto visit) const
…
auto distance = std::vector<Weight>(vertex_count, no_distance);
auto parent = std::vector<Vertex>(vertex_count, no_vertex);
auto frontier = Frontier{vertex_count};
…
distance[source] = 0;
frontier.push(source, 0);
while (true) {
const auto current = frontier.pop();
if (current == no_vertex) {
break;
}
visit(current, parent[current], distance[current]);
auto position = first_neighbor(current);
while (true) {
const auto next = next_neighbor(current, position);
if (next == no_vertex) {
break;
}
…
const auto candidate =
distance[current] + reweigh(current, next, weight_before(current, position));
if (candidate < distance[next]) {
distance[next] = candidate;
parent[next] = current;
frontier.push(next, candidate);
}
}
}
}'''
L_CAND = linha_de('if (candidate < distance[next]) {')
L_NEG = linha_de('if (negative_weight) {', apos='template <class Frontier> void dijkstra(')
slide('Um Dijkstra para duas filas', f'''<div class="cod-dij" style="width: 820px; margin: 0 auto">{codigo(DIJKSTRA, ('frontier', 'Frontier'))}</div>''', 'Implementação')


# 5. Filas de prioridade: o código das duas -----------------------------------------------------
VET_COD = '''void push(Vertex vertex, Weight distance) { estimate_[vertex] = distance; }
…
Vertex pop()
{
const auto found = std::ranges::min_element(estimate_);
if (found == estimate_.end() || *found == no_distance) {
return no_vertex;
}
…
*found = no_distance;
return Vertex(found - estimate_.begin());
}'''
HEAP_COD = '''void push(Vertex vertex, Weight distance)
{
auto index = position_[vertex];
if (index == no_vertex) {
index = size_++;
}
…
sift_up(index, Entry{distance, vertex});
}
…
void sift_up(Vertex index, Entry entry)
{
// No máximo log V trocas até a raiz.
while (index > 0) {
const auto parent = (index - 1) / 2;
if (heap_[parent].key <= entry.key) {
break;
}
place(index, heap_[parent]);
index = parent;
}
place(index, entry);
}'''
custo = [('<code>push</code>', 'O(1)', 'O(log <span class="m">n</span>)'),
         ('<code>pop</code>', 'O(<span class="m">n</span>)', 'O(log <span class="m">n</span>)'),
         ('Dijkstra', 'O(<span class="m">n</span>² + <span class="m">m</span>)',
          'O((<span class="m">n</span> + <span class="m">m</span>) log <span class="m">n</span>)')]
tcusto = ('<table class="bt"><tr><th class="e"></th><th class="v">vetor</th><th class="h">heap</th></tr>'
          + ''.join(f'<tr><td class="e" style="font-weight:400">{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in custo)
          + '</table>')
slide('Vetor e heap', f'''<div class="g2 cod15" style="grid-template-columns: 640px minmax(0, 1fr); gap: 28px">
<div><h3 style="color:{VET}"><code>VectorFrontier</code>: a estimativa de cada vértice</h3>
{codigo(VET_COD, ('estimate_[vertex] = distance', 'min_element'))}
<div style="margin-top:14px">{tcusto.replace('class="bt"', 'class="bt" style="width: 100%"', 1)}</div></div>
<div><h3 style="color:{HEAP}"><code>HeapFrontier</code>: heap com posições</h3>
{codigo(HEAP_COD, ('position_[vertex]', 'place('))}
</div>
</div>''', 'Implementação')


# 6. Metodologia --------------------------------------------------------------------------------
gr = {w: secao_grafo(f'caminhos_{w}.txt') for w in WS}
tg = ('<table class="bt"><tr><th class="e">grafo</th><th><span class="m">n</span></th><th><span class="m">m</span></th>'
      '<th>grau médio</th><th>CSR</th></tr>'
      + ''.join(f'<tr><td class="e">{wsub(w)}{"*" if w == "W_6" else ""}</td><td>{qtd(G[w]["vertices"])}</td>'
                f'<td>{qtd(G[w]["edges"])}</td><td>{br(grau(w), 1)}</td><td>{bytes_(G[w]["memory_bytes"])}</td></tr>'
                for w in WS) + '</table>')
val = {v['graph']: v for v in DADOS['fit']['validation']}


# 7. Estudo de caso: distâncias -----------------------------------------------------------------
alvos = [p['target'] for p in G['W_3']['paths']]
assert all(G[w]['mismatches'] == 0 for w in WS)
td = ('<table class="bt"><tr><th class="e">grafo</th>' + ''.join(f'<th>10 → {a}</th>' for a in alvos) + '</tr>'
      + ''.join(f'<tr><td class="e">{wsub(w)}</td>' + ''.join(
          f'<td>{br(p["distance"], 2)}<small>({len(p["path"]) - 1})</small></td>' for p in G[w]['paths']) + '</tr>'
          for w in WS) + '</table>')


PESOS = {w: json.loads((AQUI / f'pesos_{w}.json').read_text()) for w in ('W_3', 'W_7')}
assert all(abs(sum(c['pesos']) - c['distance']) < 1e-6 for d in PESOS.values() for c in d['caminhos'])
PW3 = PESOS['W_3']


def arvore_escala(cams, faixa, x0, esc, y_eixo, dmax, passo, rotulo_eixo, destaque=None):
    """Caminhos de uma origem desenhados em escala: o trecho horizontal de cada aresta mede o seu peso.

    cams: lista de (chave, vértices, pesos). Vértices de um prefixo comum ficam na média das faixas."""
    X = lambda d: x0 + d * esc
    out, passa, dist = [], {}, {}
    for ch, vs, ps in cams:
        acc = 0.0
        for i, v in enumerate(vs):
            passa.setdefault((i, v), []).append(faixa[ch])
            dist[v] = acc
            if i < len(ps):
                acc += ps[i]
    pos = {v: (X(dist[v]), sum(ys) / len(ys)) for (i, v), ys in passa.items()}
    # Grade e eixo de distância.
    k = 0
    while k * passo <= dmax + 1e-9:
        x = X(k * passo)
        out.append(L(x, faixa[cams[0][0]] - 18, x, y_eixo, LINHA, 1))
        out.append(L(x, y_eixo, x, y_eixo + 6, INK2, 1.2))
        out.append(T(x, y_eixo + 24, br(k * passo, 1 if passo < 1 else 0), 14, INK2, 'middle'))
        k += 1
    out.append(L(x0, y_eixo, X((k - 1) * passo), y_eixo, INK2, 1.2))
    out.append(T(x0, y_eixo + 48, rotulo_eixo, 14, INK2, 'start', 600))
    feitas = set()
    for ch, vs, ps in cams:
        for i, (u, v) in enumerate(zip(vs, vs[1:])):
            if (u, v) in feitas:
                continue
            feitas.add((u, v))
            (x1, y1), (x2, y2) = pos[u], pos[v]
            forte = destaque is not None and destaque(ps[i])
            out.append(f'<path d="M{x1:.1f},{y1:.1f} V{y2:.1f} H{x2:.1f}" fill="none" '
                       f'stroke="{VET if forte else AZUL}" stroke-width="{5 if forte else 2.5}" '
                       f'stroke-linejoin="round"/>')
            if forte:
                out.append(T((x1 + x2) / 2, y2 - 10, br(ps[i], 2), 14, VET, 'middle', 700, SANS, HALO))
    fins = {vs[-1] for _, vs, _ in cams}
    raiz = cams[0][1][0]
    for v, (x, y) in pos.items():
        if v not in fins and v != raiz:
            out.append(C(x, y, 3.5, '#fff', AZUL, 1.6))
    for v in fins | {raiz}:
        x, y = pos[v]
        out.append(C(x, y, 8, AZUL, AZUL, 2))
    return out, pos


def fig_caminhos_w3(k=1):
    """Caminhos mínimos do vértice 10 no W3 em escala de distância (pesos lidos do arquivo do grafo)."""
    cams = {c['target']: c for c in PW3['caminhos']}
    ordem = [20, 60, 40, 30, 50]
    W, H = 1180, 318
    faixa = {t: 30 + j * 50 for j, t in enumerate(ordem)}
    out, pos = arvore_escala([(t, cams[t]['path'], cams[t]['pesos']) for t in ordem], faixa, 70, 900, 262, 1.0, 0.2,
                             'distância a partir do vértice 10')
    x, y = pos[10]
    out.append(T(x - 14, y + 6, '10', 18, INK, 'end', 700, MONO))
    for t in ordem:
        x, y = pos[t]
        c = cams[t]
        out.append(T(x + 14, y + 6, str(t), 18, INK, 'start', 700, MONO))
        out.append(T(x + 46, y + 5, f'{br(c["distance"], 2)} · {len(c["pesos"])} arestas', 15, AZUL, 'start', 600))
    return svg(W, H, ''.join(out), k)


def tabela_pesos():
    """Peso médio das arestas no grafo e nos 5 caminhos, no W3 e no W7."""
    lin = []
    for w in ('W_3', 'W_7'):
        d = PESOS[w]
        ps = [v for c in d['caminhos'] for v in c['pesos']]
        lin.append(f'<tr><td class="e">{wsub(w)}</td><td>{br(grau(w), 0)}</td><td>{br(d["media"], 2)}</td>'
                   f'<td class="v">{br(sum(ps) / len(ps), 2)}</td></tr>')
    return ('<table class="bt" style="margin: 0 auto"><tr><th class="e">grafo</th><th>grau médio</th>'
            '<th>peso médio no grafo</th><th>nos 5 caminhos</th></tr>' + ''.join(lin) + '</table>')


# 8. Rede de colaboração ------------------------------------------------------------------------
def fig_colab():
    """Caminhos a partir de Dijkstra na rede de colaboração, em escala de distância."""
    caminhos = [p for p in COLAB['paths'] if p['status'] == 'ok']
    ordem = ['Jon M. Kleinberg', 'Éva Tardos', 'J. B. Kruskal', 'Daniel R. Figueiredo']
    caminhos.sort(key=lambda p: ordem.index(p['name']))
    W, H = 1168, 452
    x0 = 150
    faixa = {'Jon M. Kleinberg': 34, 'Éva Tardos': 112, 'J. B. Kruskal': 222, 'Daniel R. Figueiredo': 300}
    um = lambda w: abs(w - 1) < 1e-9
    out, pos = arvore_escala([(p['name'], p['path'], p['edge_weights']) for p in caminhos], faixa, x0, 233, 352,
                             3.5, 0.5, 'distância a partir de Edsger W. Dijkstra', um)
    nomes = {v: nm for p in caminhos for v, nm in zip(p['path'], p['path_names'])}
    for p in caminhos:
        x, y = pos[p['path'][-1]]
        out.append(T(x + 16, y + 6, p['name'], 18, INK, 'start', 600))
        out.append(T(x + 16, y + 26, f'{br(p["distance"], 2)} · {len(p["path"]) - 1} arestas', 14, AZUL, 'start', 600))
    x, y = pos[COLAB['source']]
    out.append(T(x - 14, y - 2, 'Edsger W.', 16, INK, 'end', 600))
    out.append(T(x - 14, y + 17, 'Dijkstra', 16, INK, 'end', 600))
    # Nomes dos vértices compartilhados; se ficam perto do anterior, vão para baixo da linha.
    ult = {}
    for v, (x, y) in sorted(pos.items(), key=lambda e: e[1][0]):
        if v == COLAB['source'] or sum(1 for p in caminhos if v in p['path']) < 2:
            continue
        baixo = x - ult.get(y, -999) < 90
        if not baixo:
            ult[y] = x
        out.append(T(x + 8 if baixo else x, y + (22 if baixo else -12), nomes[v].split()[-1], 13, INK2,
                     'start' if baixo else 'middle', 500, SANS, HALO))
    tur = next(p for p in COLAB['paths'] if p['status'] != 'ok')
    out.append(C(x0 + 8, 432, 8, '#fff', INK3, 2))
    out.append(T(x0 + 26, 438, f'{tur["name"]}: não alcançável a partir de Dijkstra (outra componente)', 16, INK2,
                 'start', 500))
    return svg(W, H, ''.join(out))


kl = next(p for p in COLAB['paths'] if p['name'] == 'Jon M. Kleinberg')
kr = next(p for p in COLAB['paths'] if p['name'] == 'J. B. Kruskal')


# 9. Estudo de caso: tempos ---------------------------------------------------------------------
tt = ('<table class="bt"><tr><th class="e">grafo</th><th><span class="m">n</span></th><th class="h">heap</th>'
      '<th class="v">vetor</th><th>vetor ÷ heap</th></tr>')
for w in WS:
    h = heap_s(w)
    v, est = vetor_s(w)
    r = v / h
    rot = br(r, 0) + '×' if r < 1000 else br(r / 1000, 0) + ' mil×'
    tt += (f'<tr><td class="e">{wsub(w)}</td><td>{qtd(G[w]["vertices"])}</td><td>{dur(h)}</td>'
           f'<td>{dur(v)}{"*" if est else "&nbsp;"}</td><td>{rot}{"*" if est else "&nbsp;"}</td></tr>')
tt += '</table>'
conta = lambda w: (G[w]['vertices'] + G[w]['edges']) * math.log2(G[w]['vertices'])


def fig_crescimento(k=1):
    """Tempo do heap e conta (n + m) log2 n, os dois relativos ao W3, em escala log."""
    W, H = 470, 380
    x0, x1, y0, y1 = 56, 330, 20, 330
    Y = lambda v: y1 - math.log10(v) / 3 * (y1 - y0)
    X = lambda i: x0 + 20 + i * (x1 - x0 - 40) / (len(WS) - 1)
    out = [L(x0, y1, x1, y1, INK, 1.2)]
    for v in (1, 10, 100, 1000):
        out.append(L(x0, Y(v), x1, Y(v), LINHA, 1))
        out.append(T(x0 - 8, Y(v) + 5, f'{v:,}×'.replace(',', '.'), 14, INK2, 'end'))
    for i, w in enumerate(WS):
        out.append(T(X(i), y1 + 22, wsvg(w), 17, INK, 'middle', 600))
    for f, cor, nome in ((lambda w: conta(w) / conta('W_3'), INK3, '(n + m) log₂ n'),
                         (lambda w: heap_s(w) / heap_s('W_3'), HEAP, 'tempo do heap')):
        pts = ' '.join(f'{X(i):.1f},{Y(f(w)):.1f}' for i, w in enumerate(WS))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{cor}" stroke-width="3.5"/>')
        for i, w in enumerate(WS):
            out.append(C(X(i), Y(f(w)), 4.5, cor))
        fim = f('W_7')
        out.append(T(x1 + 8, Y(fim) + 6, f'{br(fim, 0)}×', 19, cor, 'start', 700))
        out.append(T(x1 + 8, Y(fim) + 24, nome, 13, cor, 'start', 500))
    return svg(W, H, ''.join(out), k)


slide('Tempo de execução', f'''<div style="width: 760px; margin: 20px auto 0">{leg('Tabela', f'Tempo médio de um Dijkstra por origem.', True)}
<div style="font-size:32px">{tt.replace('class="bt"', 'class="bt" style="width: 100%"', 1)}</div>
<p class="nota">Sorteamos {K} origens por grafo e usamos as mesmas nas duas filas. * Estimado pelo tempo de uma extração.</p></div>''',
      'Benchmark')


# 10. Discussão: o heap trabalha menos que o pior caso ------------------------------------------
ORD = sorted(WS, key=grau, reverse=True)
TONS = {'W_3': '#0d3166', 'W_4': '#1f4e9c', 'W_6': '#5b82c4', 'W_5': '#9fb6de', 'W_7': '#c0392b'}


def fig_pushes():
    W, H = 1000, 400
    x0, larg = 150, 560
    out = [T(x0, 18, 'arestas que melhoram a distância do vizinho (e chamam <tspan font-family="Inconsolata">push</tspan>)', 16, INK2, 'start', 600),
           T(x0 + larg + 24, 18, 'melhoram / arestas', 16, INK2, 'start', 600)]
    y = 36
    for w in ORD:
        c = CONT[w]
        f = c['pushes'] / c['m']
        out.append(T(0, y + 26, wsvg(w), 24, INK, 'start', 600))
        out.append(T(44, y + 25, f'grau {br(grau(w), 0)}', 15, INK2, 'start', 400))
        out.append(R(x0, y + 6, larg, 30, FUNDO))
        out.append(R(x0, y + 6, larg * f, 30, TONS[w]))
        out.append(T(x0 + larg + 24, y + 28, f'{qtd(c["pushes"])} / {qtd(c["m"])}', 17, INK2, 'start', 500))
        out.append(T(W - 6, y + 28, f'{br(100 * f, 0)}%', 20, INK, 'end', 700))
        y += 64
    out.append(L(x0 + larg, 30, x0 + larg, y + 4, INK, 1.2, 'stroke-dasharray="4 3"'))
    out.append(T(x0 + larg, y + 24, 'a análise supõe que todas melhoram', 15, INK2, 'end', 500))
    return svg(W, H, ''.join(out))


def ns_op(w):
    n, m = G[w]['vertices'], G[w]['edges']
    return heap_s(w) / ((n + m) * math.log2(n)) * 1e9


lay = {(e['vertices'], e['labeling']): e for e in DADOS['lowlevel']['layout']}
tm = ('<table class="bt"><tr><th class="e">grafo</th><th>ns por (<span class="m">n</span> + <span class="m">m</span>) '
      'log₂ <span class="m">n</span></th><th>espera</th></tr>')
for w in WS:
    ch = CTR.get(f'{w}/original/heap')
    tm += (f'<tr><td class="e">{wsub(w)}</td><td>{br(ns_op(w), 2)}</td>'
           f'<td>{br(100 * espera(ch), 0) + "%" if ch else "—"}</td></tr>')
tm += '</table>'
def fig_ocupacao(escala=1):
    """Vértices no heap ao longo de uma execução, em fração de n (uma origem por grafo)."""
    W, H = 600, 380
    x0, x1, y0, y1 = 62, 585, 14, 320
    X = lambda f: x0 + f * (x1 - x0)
    Y = lambda f: y1 - f * (y1 - y0)
    out = [L(x0, y1, x1, y1, INK, 1.2), L(x0, y0, x0, y1, INK, 1.2)]
    for f in (0, 0.25, 0.5, 0.75, 1):
        out.append(T(x0 - 8, Y(f) + 5, f'{100 * f:.0f}%', 14, INK2, 'end'))
        out.append(T(X(f), y1 + 20, f'{100 * f:.0f}%', 14, INK2, 'middle'))
        if f:
            out.append(L(x0, Y(f), x1, Y(f), LINHA, 1))
    for w in ORD:
        n = CONT[w]['n']
        pts = ' '.join(f'{X(p / n):.1f},{Y(h / n):.1f}' for p, h, _ in CONT[w]['trace'])
        out.append(f'<polyline points="{pts}" fill="none" stroke="{TONS[w]}" stroke-width="3"/>')
    for k, w in enumerate(ORD):
        y = 40 + k * 26
        out.append(L(410, y - 5, 440, y - 5, TONS[w], 4))
        out.append(T(448, y, wsvg(w), 16, INK, 'start', 600))
        out.append(T(478, y, f'grau {br(grau(w), 0)}', 13, INK2))
    out.append(T((x0 + x1) / 2, H - 6, f'vértices já extraídos, em fração de <tspan font-style="italic">n</tspan>',
                 15, INK2, 'middle'))
    out.append(T(14, (y0 + y1) / 2, f'vértices no heap', 15, INK2, 'middle', 400, SANS,
                 f'transform="rotate(-90 14 {(y0 + y1) / 2})"'))
    return svg(W, H, ''.join(out), escala)


def ocupa(w, ate):
    """Fração de n no heap depois de 'ate' (fração de n) extrações."""
    n = CONT[w]['n']
    return next(h for p, h, _ in CONT[w]['trace'] if p >= ate * n) / n


pico7 = max(h for _, h, _ in CONT['W_7']['trace']) / CONT['W_7']['n']
f3, f7 = CONT['W_3']['pushes'] / CONT['W_3']['m'], CONT['W_7']['pushes'] / CONT['W_7']['m']
slide('Operações do heap', f'''<figure style="width: 1000px; margin: 16px auto 0">{fig_pushes()}
{leg('Figura', f'<code>push</code> feitos no heap contra o número de arestas <span class="m">m</span>, média de {CONTAGENS["origins"]} origens; grafos em ordem de grau médio.')}</figure>''', 'Benchmark')

slide('Ocupação do heap', f'''<figure style="width: 760px; margin: 12px auto 0">{fig_ocupacao(1.25)}
{leg('Figura', 'Vértices no heap ao longo de uma execução, em fração de <span class="m">n</span>; uma origem por grafo.')}</figure>''', 'Benchmark')


# 11. Discussão: o custo de cada operação -------------------------------------------------------
LAT = DADOS['lowlevel']['chase']
POR_VERTICE = 8 + 4 + 16 + 4      # distance (double), parent, heap_ (Entry: double + uint32), position_


def latencia(b):
    """Latência medida no tamanho mais próximo (escala log) de b bytes."""
    return min(LAT, key=lambda p: abs(math.log(p[0] / b)))[1]


def fig_latencia(k=1):
    W, H = 640, 400
    x0, x1, y0, y1 = 64, 620, 40, 330
    lo, hi, ylo, yhi = 16 * 2 ** 10, 2 * 2 ** 30, 0.8, 200
    X = lambda b: eixo_log(b, lo, hi, x0, x1)
    Y = lambda v: y1 - (eixo_log(v, ylo, yhi, 0, y1 - y0))
    # Zonas da hierarquia de memória do M3 Pro (relatorio.tex, tabela da hierarquia): L1 128 KiB, L2 16 MiB.
    out = []
    zonas = ((lo, 128 * 2 ** 10, 'L1', FUNDO), (128 * 2 ** 10, 16 * 2 ** 20, 'cache L2', AZUL_BG),
             (16 * 2 ** 20, hi, 'RAM', VET_BG))
    for a, b, rot, cor in zonas:
        out.append(R(X(a), y0, X(b) - X(a), y1 - y0, cor, extra='opacity="0.7"'))
        out.append(T((X(a) + X(b)) / 2, y0 + 20, rot, 15, INK2, 'middle', 600))
    out += [L(x0, y1, x1, y1, INK, 1.2), L(x0, y0, x0, y1, INK, 1.2)]
    for v in (1, 10, 100):
        out.append(L(x0, Y(v), x1, Y(v), LINHA, 1))
        out.append(T(x0 - 8, Y(v) + 5, f'{v} ns', 14, INK2, 'end'))
    for b, rot in ((2 ** 15, '32 kB'), (2 ** 20, '1 MB'), (2 ** 25, '32 MB'), (2 ** 30, '1 GB')):
        out.append(T(X(b), y1 + 20, rot, 14, INK2, 'middle'))
    pts = ' '.join(f'{X(b):.1f},{Y(v):.1f}' for b, v in LAT)
    out.append(f'<polyline points="{pts}" fill="none" stroke="{AZUL}" stroke-width="3"/>')
    marcas = [('W_3', 'W₃'), ('W_4', 'W₄'), ('W_5', 'W₅ W₆'), ('W_7', 'W₇')]
    for w, rot in marcas:
        b = G[w]['vertices'] * POR_VERTICE
        out.append(L(X(b), y0 - 6, X(b), y1, VET, 1.5, 'stroke-dasharray="4 3"'))
        out.append(C(X(b), Y(latencia(b)), 5, VET))
        out.append(T(X(b), y0 - 12, rot, 15, VET, 'middle', 600))
    out.append(T((x0 + x1) / 2, H - 6, 'tamanho dos dados lidos', 15, INK2, 'middle'))
    return svg(W, H, ''.join(out), k)


slide('Hierarquia de memória', f'''<div class="g2" style="grid-template-columns: 736px 1fr; gap: 30px">
<figure>{fig_latencia(1.15)}
{leg('Figura', f'Tempo de uma leitura em posição aleatória, nesta máquina. Em vermelho, o que o Dijkstra lê fora de ordem ({POR_VERTICE} bytes por vértice).')}</figure>
<div>{leg('Tabela', 'Tempo do heap por (<span class="m">n</span> + <span class="m">m</span>) log₂ <span class="m">n</span>, e ciclos parados à espera da memória.', True)}{tm}</div></div>''', 'Benchmark')


# 12. Teste: a mesma conta com outra numeração --------------------------------------------------
NS_LAY = (10 ** 5, 10 ** 6, 10 ** 7, 5 * 10 ** 7)


def fig_layout(k=1):
    W, H = 600, 360
    x0, y0, y1 = 60, 20, 300
    top = 2.5
    Y = lambda v: y1 - v / top * (y1 - y0)
    out = [L(x0, y1, W - 10, y1, INK, 1.2)]
    for v in (0.5, 1, 1.5, 2, 2.5):
        out.append(L(x0, Y(v), W - 10, Y(v), LINHA, 1))
        out.append(T(x0 - 8, Y(v) + 5, br(v, 1), 14, INK2, 'end'))
    gw = (W - 10 - x0) / len(NS_LAY)
    for g, n in enumerate(NS_LAY):
        a, b = lay[(n, 'local')], lay[(n, 'aleatoria')]
        gx = x0 + g * gw + gw / 2
        for j, (e, cor) in enumerate(((a, HEAP), (b, VET))):
            x = gx - 44 + j * 46
            out.append(R(x, Y(e['ns_per_op']), 42, y1 - Y(e['ns_per_op']), cor))
        out.append(T(gx, Y(b['ns_per_op']) - 10, f'{br(b["mean_s"] / a["mean_s"], 1)}×', 16, INK, 'middle', 700))
        out.append(T(gx, y1 + 20, f'<tspan font-style="italic">n</tspan> = {qtd(n)}', 15, INK, 'middle', 500))
        out.append(T(gx, y1 + 38, bytes_(n * POR_VERTICE), 13, INK2, 'middle'))
    out.append(R(x0 + 14, y0, 14, 14, HEAP))
    out.append(T(x0 + 34, y0 + 12, 'numeração local', 14, INK))
    out.append(R(x0 + 164, y0, 14, 14, VET))
    out.append(T(x0 + 184, y0 + 12, 'aleatória', 14, INK))
    return svg(W, H, ''.join(out), k)


ordem5 = DADOS['lowlevel']['order']['W_5']['labelings']


def ordem_extracao(n=3000, seed=1):
    """Simulação pequena do grafo sintético de bench/lowlevel_bench.cpp (local_graph: cada vértice
    liga-se a 4 vértices sorteados entre os 64 seguintes, em anel). Devolve, na ordem em que o
    Dijkstra extrai os vértices, o índice de cada um na numeração local e numa numeração aleatória."""
    import heapq
    import random
    r = random.Random(seed)
    viz = [[] for _ in range(n)]
    for v in range(n):
        for _ in range(4):
            u, w = (v + r.randint(1, 64)) % n, r.random()
            viz[v].append((u, w))
            viz[u].append((v, w))
    dist, fila, ordem = [math.inf] * n, [(0.0, n // 2)], []
    dist[n // 2] = 0.0
    while fila:
        d, v = heapq.heappop(fila)
        if d > dist[v]:
            continue
        ordem.append(v)
        for u, w in viz[v]:
            if d + w < dist[u]:
                dist[u] = d + w
                heapq.heappush(fila, (d + w, u))
    rotulo = list(range(n))
    r.shuffle(rotulo)
    return n, ordem, [rotulo[v] for v in ordem]


def anel(cx, cy, r, rotulos, cor):
    """Esquema do grafo do teste: vértices num anel, cada um ligado aos seguintes."""
    q = len(rotulos)
    P = [(cx + r * math.sin(2 * math.pi * i / q), cy - r * math.cos(2 * math.pi * i / q)) for i in range(q)]
    out = []
    for i in range(q):
        for d in (1, 2, 3):
            (x1, y1), (x2, y2) = P[i], P[(i + d) % q]
            out.append(L(x1, y1, x2, y2, INK3, 1))
    for i, (x, y) in enumerate(P):
        orig = i == q // 2
        out.append(C(x, y, 11, cor if orig else '#fff', cor, 1.6))
        out.append(T(x, y + 4.5, rotulos[i], 12, '#fff' if orig else INK, 'middle', 700, MONO))
    return ''.join(out)


def fig_acessos(k=1):
    n, local, aleat = ordem_extracao()
    W, H, top = 640, 500, 170
    q = 12
    embaralhado = [7, 2, 10, 5, 0, 9, 3, 11, 6, 1, 8, 4]
    out = []
    for j, (nome, idx, cor, rot) in enumerate((('numeração local', local, HEAP, list(range(q))),
                                               ('numeração aleatória', aleat, VET, embaralhado))):
        x0 = 40 + j * 310
        lado = 260
        out.append(T(x0 + lado / 2, 20, nome, 17, cor, 'middle', 700))
        out.append(anel(x0 + lado / 2, 92, 56, rot, cor))
        out.append(R(x0, top, lado, lado, '#fff', INK2, 1))
        for t, v in enumerate(idx):
            out.append(f'<rect x="{x0 + t / n * lado:.1f}" y="{top + lado - v / n * lado:.1f}" width="1.6" height="1.6" fill="{cor}"/>')
        out.append(T(x0 + lado / 2, top + lado + 20, 'ordem de extração →', 14, INK2, 'middle'))
    yc = top + lado / 2
    out.append(T(24, yc, 'índice do vértice →', 14, INK2, 'middle', 400, SANS, f'transform="rotate(-90 24 {yc})"'))
    return svg(W, H, ''.join(out), k)


slide('Localidade dos vértices', f'''<div class="g2" style="grid-template-columns: 600px 1fr; gap: 30px">
<figure>{fig_acessos(0.86)}
{leg('Figura', 'Em cima, o mesmo anel com as duas numerações (cada vértice liga-se aos seguintes; origem preenchida). Embaixo, índice de cada vértice na ordem em que o Dijkstra o extrai (simulação com <span class="m">n</span> = 3 mil).')}</figure>
<figure>{fig_layout(0.92)}
{leg('Figura', 'Tempo do heap por (<span class="m">n</span> + <span class="m">m</span>) log₂ <span class="m">n</span>, nas duas numerações. Rótulo: razão dos tempos.')}</figure>
</div>''', 'Benchmark')


# Resultados: os caminhos (as figuras são definidas acima) ----------------------------
slide('Caminhos nos grafos W', f'''<figure>{fig_caminhos_w3(0.95)}
{leg('Figura', 'Caminhos mínimos a partir do vértice 10 no W<sub>3</sub>; o trecho horizontal de cada aresta mede o seu peso.')}</figure>
<div style="width: 640px; margin: 14px auto 0">{leg('Tabela', 'Peso médio das arestas, no grafo e nos 5 caminhos.', True)}{tabela_pesos()}</div>''',
      'Resultados')
slide('Rede de colaboração', f'''<figure>{fig_colab()}
{leg('Figura', 'Rede de colaboração: caminhos mínimos a partir de Edsger W. Dijkstra; o trecho horizontal de cada aresta mede o seu peso. Em vermelho, arestas de peso 1,00.')}</figure>''', 'Resultados')


# 13. Conclusões --------------------------------------------------------------------------------
slide('Conclusões', f'''<h3>Implementação</h3>
<ul class="l" style="font-size: 27px; line-height: 1.45; margin-bottom: 14px">
<li>Um só Dijkstra gera as duas versões, com as mesmas distâncias.</li>
</ul>
<h3>Benchmark</h3>
<ul class="l" style="font-size: 27px; line-height: 1.45; margin-bottom: 14px">
<li>No W<sub>4</sub>, uma origem leva {dur(vetor_s("W_4")[0])} com vetor e {dur(heap_s("W_4"))} com heap.</li>
<li>O grau decide quantos <code>push</code> o heap faz: de {br(100 * f3, 0)}% a {br(100 * f7, 0)}% das arestas.</li>
<li>Em grafos grandes, a memória pesa: só a numeração muda o tempo em até {br(max(lay[(n, "aleatoria")]["mean_s"] / lay[(n, "local")]["mean_s"] for n in NS_LAY), 1)}×.</li>
</ul>
<h3>Resultados</h3>
<ul class="l" style="font-size: 27px; line-height: 1.45">
<li>No W<sub>3</sub>, denso, os caminhos usam só as arestas mais leves (peso médio {br(sum(v for c in PESOS["W_3"]["caminhos"] for v in c["pesos"]) / sum(len(c["pesos"]) for c in PESOS["W_3"]["caminhos"]), 2)}, contra {br(PESOS["W_3"]["media"], 2)} no grafo).</li>
</ul>''', 'Conclusões')


# ---------------------------------------------------------------- página

CSS = (AQUI.parent / 'comum' / 'estilo.css').read_text()
JS = '''
const S = [...document.querySelectorAll('.slide')];
let i = Math.min(S.length, Math.max(1, parseInt(location.hash.slice(1)) || 1)) - 1;
const fit = () => document.documentElement.style.setProperty('--k', Math.min(innerWidth / 1280, innerHeight / 720));
function go(n) {
  i = Math.max(0, Math.min(S.length - 1, n));
  S.forEach((s, k) => s.classList.toggle('on', k === i));
  history.replaceState(null, '', '#' + (i + 1));
}
addEventListener('keydown', (e) => {
  if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(e.key)) go(i + 1);
  else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'].includes(e.key)) go(i - 1);
  else if (e.key === 'Home') go(0);
  else if (e.key === 'End') go(S.length - 1);
  else return;
  e.preventDefault();
});
addEventListener('click', (e) => go(e.clientX > innerWidth / 3 ? i + 1 : i - 1));
addEventListener('resize', fit);
fit(); go(i);
'''


def pagina():
    principais = sum(1 for s in slides if 'apendice' not in s['cls'])
    partes = []
    for n, s in enumerate(slides, 1):
        if s['titulo'] is None:
            partes.append(f'<section class="slide {s["cls"]}" id="s{n}">{s["corpo"]}</section>')
            continue
        ap = 'apendice' in s['cls']
        num = f'A{n - principais}' if ap else f'{n} / {principais}'
        partes.append(
            f'<section class="slide {s["cls"]}" id="s{n}"><header><span>{s["titulo"]}</span></header>'
            f'<div class="corpo">{s["corpo"]}</div>'
            f'<footer><span>Marroni e Knust · Dijkstra com vetor e com heap</span><span>{s["secao"]}</span>'
            f'<b>{num}</b></footer></section>')
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Dijkstra com vetor e com heap · COS242</title>
<style>{CSS}</style></head>
<body>
<svg width="0" height="0" style="position:absolute">{DEFS}</svg>
{"".join(partes)}
<script>{JS}</script>
</body></html>
'''


def main():
    saida = AQUI / 'index.html'
    saida.write_text(pagina())
    print(f'{saida.relative_to(RAIZ)}: {len(slides)} slides')
    if '--sem-pdf' in sys.argv:
        return
    pdf = AQUI / 'apresentacao.pdf'
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                    '--virtual-time-budget=5000', f'--print-to-pdf={pdf}', saida.as_uri()],
                   check=True, capture_output=True)
    print(pdf.relative_to(RAIZ))


if __name__ == '__main__':
    main()
