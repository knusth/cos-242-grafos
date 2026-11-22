#!/usr/bin/env python3
"""Apresentação da Parte 3: index.html (navegável) e apresentacao.pdf (uma página por slide).

    python3 -I presentation/parte3/build.py            # HTML e PDF
    python3 -I presentation/parte3/build.py --sem-pdf  # só HTML

Todo número de resultado vem de report/parte3/data.json (gerado por bench/summarize_p3.py). Valor
ausente aparece como "—" e a linha leva a marca "em execução"; rode o build de novo quando o
benchmark terminar. O trecho de código é conferido contra include/cos/graph.hpp. Gráficos são SVG
estáticos: tela e PDF mostram a mesma coisa.
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
ARQ = Path(sys.argv[sys.argv.index('--dados') + 1]) if '--dados' in sys.argv else RAIZ / 'report/parte3/data.json'
DADOS = json.loads(ARQ.read_text())
G = {g['name']: g for g in DADOS['graphs']}
NOMES = ['W_1', 'W_2', 'W_3', 'W_4', 'W_5']
MAQ = DADOS['machine']
THREADS = MAQ['threads']
RAM = MAQ['memory_bytes']
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
REPO = 'https://github.com/knusth/cos-242-grafos'

INK, INK2, INK3, LINHA, FUNDO = '#23373b', '#5b6b70', '#9aa5a8', '#dde3e4', '#f3f5f6'
AZUL, AZUL_BG = '#1f4e9c', '#e3eaf6'
HEAP, HEAP_BG = '#1b7f79', '#d9ecea'
VET, VET_BG = '#c0392b', '#f6dcd8'
SANS, MONO = "'Fira Sans'", 'Inconsolata'


# ---------------------------------------------------------------- formatação pt-BR

def br(x, casas=0):
    s = f'{x:,.{casas}f}'
    return s.replace(',', '\0').replace('.', ',').replace('\0', '.')


def sig(x, n=3):
    """x com n algarismos significativos, sem zeros à direita desnecessários."""
    if x == 0:
        return '0'
    casas = max(0, n - 1 - int(math.floor(math.log10(abs(x)))))
    s = br(x, casas)
    if ',' in s:
        s = s.rstrip('0').rstrip(',')
    return s


def dur(s):
    for lim, div, u in ((1e-3, 1e-6, 'µs'), (1, 1e-3, 'ms'), (60, 1, 's'), (3600, 60, 'min'),
                        (86400, 3600, 'h'), (365 * 86400, 86400, 'dias'), (1e30, 365 * 86400, 'anos')):
        if s < lim:
            return sig(s / div) + ' ' + u


def bytes_(b):
    for lim, u in ((1e15, 'PB'), (1e12, 'TB'), (1e9, 'GB'), (1e6, 'MB'), (1e3, 'kB')):
        if b >= lim * 0.9995:
            return sig(b / lim) + ' ' + u
    return f'{b:.0f} B'


def qtd(x):
    if x >= 1e6:
        return sig(x / 1e6, 3) + ' mi'
    if x >= 1e4:
        return br(x / 1e3, 0) + ' mil'
    return br(x)


def sci(x):
    e = int(math.floor(math.log10(x)))
    return f'{br(x / 10 ** e, 2)}·10<sup>{e}</sup>'


def sci_txt(x):
    """Mesmo valor de sci(), em texto puro (expoente em sobrescrito Unicode)."""
    e = int(math.floor(math.log10(x)))
    sup = str(e).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))
    return f'{br(x / 10 ** e, 2)}·10{sup}'


def wsub(n):
    return f'W<sub>{n[-1]}</sub>'


def wsvg(n):
    return f'W<tspan dy="0.25em" font-size="70%">{n[-1]}</tspan>'


PD = '<span class="pd">—</span>'


def em_exec(g):
    return '' if g['complete'] else '<span class="ex">em execução</span>'


def cel(v, f):
    return PD if v is None else f(v)


# ---------------------------------------------------------------- dados derivados

def fw_media_w2():
    return G['W_2']['floyd_warshall']['mean_s']


def fw_est(n):
    """Estimativa do FW por V^3 a partir da média medida no W_2; None se faltar dado."""
    g, m = G[n], fw_media_w2()
    if m is None or g['vertices'] is None or G['W_2']['vertices'] is None:
        return None
    return m * (g['vertices'] / G['W_2']['vertices']) ** 3


def fw_tempo(n):
    """(segundos, estimado?) do Floyd-Warshall; None se não houver."""
    f = G[n]['floyd_warshall']
    if f['mean_s'] is not None:
        return f['mean_s'], False
    if f['status'] == 'memoria_insuficiente':
        e = fw_est(n)
        return (e, True) if e is not None else None
    return None


def bf_todos(n):
    """(segundos em 1 thread equivalente ao relógio medido, threads, estimado?)."""
    a = G[n]['all_pairs_bf']
    if a['mean_s'] is None:
        return None
    return a['mean_s'], a['threads'], bool(a['estimated'])


def bf_todos_equiv(n):
    """Tempo do BF todos-pares como se rodasse com THREADS threads (escala linear)."""
    r = bf_todos(n)
    return None if r is None else r[0] * r[1] / THREADS


# ---------------------------------------------------------------- SVG

def svg(w, h, corpo):
    return (f'<svg class="fig" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'xmlns="http://www.w3.org/2000/svg">{corpo}</svg>')


def T(x, y, s, tam=16, cor=INK, anc='start', peso=400, fonte=SANS, extra=''):
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


DEFS = ''.join(
    f'<marker id="p{nome}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{cor}"/></marker>'
    for nome, cor in (('i', INK), ('a', AZUL), ('c', INK3)))
DEFS += (f'<pattern id="hach" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         f'<rect width="8" height="8" fill="#fff"/><rect width="4" height="8" fill="{VET}"/></pattern>'
         f'<pattern id="hachb" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         f'<rect width="8" height="8" fill="#fff"/><rect width="4" height="8" fill="{HEAP}"/></pattern>')
DEFS = f'<defs>{DEFS}</defs>'


def celulas(x, y, vals, w=44, h=34, fill=None, tam=18):
    out = []
    for i, v in enumerate(vals):
        out.append(R(x + i * w, y, w, h, (fill or {}).get(i, '#fff'), INK2, 1))
        out.append(T(x + i * w + w / 2, y + h / 2 + tam * 0.36, v, tam, INK, 'middle', 500, MONO))
    return ''.join(out)


# ---------------------------------------------------------------- código real de graph.hpp

FONTE = (RAIZ / 'include/cos/graph.hpp').read_text().splitlines()
KW = {'template', 'class', 'void', 'auto', 'const', 'while', 'true', 'if', 'break', 'return', 'for'}
TOK = re.compile(r'(//.*$)|("[^"]*")|(\b\d+\b)|([A-Za-z_]\w*)|(.)')


def localiza(trecho):
    nums, k = [], 0
    for l in trecho.splitlines():
        if l.strip() == '…':
            nums.append(None)
            continue
        while k < len(FONTE) and FONTE[k].strip() != l.strip():
            k += 1
        if k == len(FONTE):
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
        else:
            out.append(html.escape(pal or outro))
    return ''.join(out)


def codigo(trecho, foco=()):
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
    return f'<div class="cod"><div class="arq">include/cos/graph.hpp</div><pre>{"".join(linhas)}</pre></div>'


def constante(nome):
    m = re.search(rf'{nome}\s*=\s*(\d+);', '\n'.join(FONTE))
    if not m:
        sys.exit(f'constante {nome} não encontrada em graph.hpp')
    return int(m.group(1))


FW_BLOCO = constante('fw_block')

# ---------------------------------------------------------------- slides

slides = []


def slide(titulo, corpo, secao='', cls=''):
    slides.append(dict(titulo=titulo, corpo=corpo, secao=secao, cls=cls))


NEG = '−∞'

# 1. Capa ---------------------------------------------------------------------------------------
logo = base64.b64encode((RAIZ / 'report/comum/minerva.png').read_bytes()).decode()
slide(None, f'''<div class="capa">
<img src="data:image/png;base64,{logo}" alt="Minerva, UFRJ">
<h1>Caminhos mínimos com pesos negativos</h1>
<h2>Bellman-Ford e Floyd-Warshall em grafos direcionados</h2>
<hr>
<div class="aut">Felipe Marroni · Hygor Knust</div>
<div class="inst">COS242 Teoria dos Grafos, 2026/2 · Trabalho de Disciplina, Parte 3 · Professor: Daniel Ratton Figueiredo<br>
Universidade Federal do Rio de Janeiro · Escola Politécnica<br>
Código: {REPO}</div>
</div>''', cls='titulo')

# 2. O pedido e os grafos -----------------------------------------------------------------------
linhas = []
for n in NOMES:
    g = G[n]
    sim = lambda b: PD if b is None else ('sim' if b else 'não')
    ciclo = {'ciclo_negativo': 'sim', 'ok': 'não'}.get(g['bellman_ford']['status'], PD)
    linhas.append(f'<tr><td class="e">{wsub(n)}{em_exec(g)}</td><td>{cel(g["vertices"], qtd)}</td>'
                  f'<td>{cel(g["edges"], qtd)}</td><td>{sim(g["negative_weights"])}</td><td>{ciclo}</td></tr>')
slide('A Parte 3: pesos negativos e os cinco grafos W', f'''<div class="g2" style="grid-template-columns: 1fr 1.05fr; gap:44px">
<div>
<ul class="l">
<li>Grafos <b>direcionados</b>, pesos reais, possivelmente negativos.</li>
<li><b>Bellman-Ford</b> de todos até um destino: distâncias, árvore, ciclo negativo.</li>
<li><b>Floyd-Warshall</b> entre todos os pares.</li>
<li>Estudo de caso, em cada grafo:
<ul class="l"><li>distâncias dos vértices 10, 20 e 30 até o 100;</li>
<li>distâncias entre os vértices 10, 20, 30, 40 e 50;</li>
<li>tempo médio de 10 execuções;</li>
<li>todos-pares por Bellman-Ford contra Floyd-Warshall.</li></ul></li>
</ul></div>
<div><table class="bt" style="font-size:25px"><tr><th class="e">grafo</th><th>V</th><th>E</th><th>pesos negativos</th><th>ciclo negativo</th></tr>
{"".join(linhas)}</table>
<p class="nota">{wsub("W_1")} é o único com pesos negativos, e tem ciclo negativo. {wsub("W_2")} a {wsub("W_5")}: pesos não negativos.</p></div>
</div>''', 'Problema')

# 3. Grafo direcionado --------------------------------------------------------------------------
EX3 = [(0, 1), (0, 2), (1, 2), (2, 0), (2, 3), (3, 1)]
N3 = 4


def csr(arestas, saida):
    adj = [[] for _ in range(N3)]
    for u, v in arestas:
        if saida:
            adj[u].append(v)
        else:
            adj[v].append(u)
    off, viz = [0], []
    for a in adj:
        viz += a
        off.append(len(viz))
    return off, viz, adj


def fig_csr():
    pos = {0: (60, 70), 1: (210, 70), 2: (60, 210), 3: (210, 210)}
    o = [DEFS.replace('<defs>', '').replace('</defs>', '')]
    o = []
    for u, v in EX3:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        off = 7 if (v, u) in EX3 else 0
        nx, ny = -dy / d * off, dx / d * off
        o.append(L(x1 + dx / d * 24 + nx, y1 + dy / d * 24 + ny, x2 - dx / d * 27 + nx, y2 - dy / d * 27 + ny,
                   INK, 2, 'marker-end="url(#pi)"'))
    for v, (x, y) in pos.items():
        o.append(C(x, y, 22, '#fff', INK, 2))
        o.append(T(x, y + 6, v, 20, INK, 'middle', 600))
    g = svg(270, 280, ''.join(o))
    fo, fv, fa = csr(EX3, True)
    bo, bv, ba = csr(EX3, False)

    def par(titulo, cor, off, viz, y0):
        s = T(0, y0, titulo, 20, cor, 'start', 600)
        s += T(0, y0 + 38, 'offsets', 17, INK2, 'start', 400, MONO) + celulas(100, y0 + 16, off, 44, 34)
        s += T(0, y0 + 88, 'vizinhos', 17, INK2, 'start', 400, MONO) + celulas(100, y0 + 66, viz, 44, 34)
        return s
    t = par('forward_  (saem)', AZUL, fo, fv, 24) + par('backward_  (chegam)', HEAP, bo, bv, 160)
    return g, svg(100 + 44 * 7 + 4, 290, t)


g3, t3 = fig_csr()
slide('Grafo direcionado: duas listas de adjacência', f'''<div class="g2" style="grid-template-columns: 280px 1fr; gap:36px">
<div>{g3}</div>
<div>{t3}</div></div>
<ul class="l grande" style="margin-top:6px">
<li>Direção é um parâmetro de execução (<code>direcionado</code> | <code>nao_direcionado</code>); a aresta <code>u v peso</code> vai de <code>u</code> para <code>v</code>.</li>
<li>CSR com duas listas: <code>forward_</code> (saem) e <code>backward_</code> (chegam). Sem direção, as duas coincidem e a segunda não é alocada.</li>
<li><b>BFS, DFS e Dijkstra</b> percorrem <code>forward_</code>. <b>Bellman-Ford até o destino</b> percorre <code>backward_</code>.</li>
</ul>''', 'Implementação')

# 4. Bellman-Ford até o destino -----------------------------------------------------------------
BF_ARESTAS = [(1, 0, 5), (2, 0, 2), (3, 1, 1), (3, 2, 6), (4, 2, 1), (4, 3, 1), (5, 3, 2), (5, 4, 7)]
BF_N, BF_ALVO = 6, 0
BF_POS = {0: (470, 150), 1: (350, 60), 2: (350, 240), 3: (220, 60), 4: (220, 240), 5: (80, 150)}


def simula_bf():
    """Bellman-Ford até BF_ALVO com as mesmas regras da biblioteca (atualização na própria rodada)."""
    d = [math.inf] * BF_N
    nxt = [None] * BF_N
    d[BF_ALVO] = 0
    ativos, rodadas, quando = [BF_ALVO], [], {}
    while ativos:
        prox = []
        for v in ativos:
            for u, w, p in BF_ARESTAS:
                if w == v and d[v] + p < d[u]:
                    d[u], nxt[u] = d[v] + p, v
                    if u not in prox:
                        prox.append(u)
        rodadas.append((ativos, prox))
        for u in prox:
            quando[u] = len(rodadas)
        ativos = prox
    return d, nxt, rodadas, quando


def fig_bf():
    d, nxt, rodadas, quando = simula_bf()
    cores = {1: '#cfdcf1', 2: '#9db8e3', 3: '#6b92cf'}
    o = []
    for u, v, p in BF_ARESTAS:
        arv = nxt[u] == v
        x1, y1 = BF_POS[u]
        x2, y2 = BF_POS[v]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy)
        cor = AZUL if arv else INK3
        o.append(L(x1 + dx / n * 24, y1 + dy / n * 24, x2 - dx / n * 28, y2 - dy / n * 28, cor,
                   3.2 if arv else 1.6, f'marker-end="url(#p{"a" if arv else "c"})"'))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        o.append(T(mx + (-14 if dy * dx > 0 else 14) * 0.6, my - 7 if abs(dy) < 5 else my + 5, p, 17,
                   INK if arv else INK2, 'middle', 500, extra='stroke="#fff" stroke-width="4" paint-order="stroke"'))
    for v, (x, y) in BF_POS.items():
        alvo = v == BF_ALVO
        o.append(C(x, y, 23, INK if alvo else cores[quando[v]], INK, 2))
        o.append(T(x, y + 6, v if not alvo else 't', 19, '#fff' if alvo else INK, 'middle', 600))
        o.append(T(x, y - 31, br(d[v]), 17, AZUL, 'middle', 600))
    return svg(540, 290, ''.join(o)), rodadas, d, nxt


f4, rod4, d4, nx4 = fig_bf()
passos = ''.join(
    f'<tr><td class="e">rodada {i}</td><td class="e">{{{", ".join("t" if v == BF_ALVO else str(v) for v in a)}}}</td>'
    f'<td class="e">{"{" + ", ".join(map(str, p)) + "}" if p else "∅"}</td></tr>' for i, (a, p) in enumerate(rod4, 1))
cod4 = codigo('''for (const auto vertex : active) {
    auto position = first_predecessor(vertex);
…
    const auto candidate =
        distance[vertex] + weight_before_predecessor(vertex, position);
    if (candidate < distance[previous] - tolerance) {
…
        distance[previous] = candidate;
        next[previous] = vertex;
        if (mark(queued, previous)) {
            upcoming.push_back(previous);
''', foco=('candidate <', 'upcoming.push_back'))
slide('Bellman-Ford até o destino: arestas que chegam e lista de ativos', f'''<div class="g2" style="grid-template-columns: 560px 1fr; gap:28px">
<div>{f4}
<table class="bt" style="margin-top:2px"><tr><th class="e"></th><th class="e">ativos (examinados)</th><th class="e">mudaram (próximos)</th></tr>{passos}</table>
<p class="nota">Exemplo de 6 vértices. Azul: árvore de sucessores <code>next</code>, com raiz no destino t; número em azul: distância até t.</p></div>
<div>
<ul class="l">
<li>Rodada <i>i</i>: para cada ativo <i>v</i>, relaxa as arestas <b>que chegam</b> em <i>v</i>; <i>next</i> aponta para o sucessor rumo a t.</li>
<li><b>Otimização 1:</b> rodada sem mudança encerra o laço.</li>
<li><b>Otimização 2:</b> só quem mudou na rodada anterior fica ativo.</li>
</ul>
{cod4}
</div></div>''', 'Implementação', cls='cod15')

# 5. Ciclo negativo -----------------------------------------------------------------------------
w1 = G['W_1']
bf1, fw1, ap1 = w1['bellman_ford'], w1['floyd_warshall'], w1['all_pairs_bf']


def tile(valor, rot):
    return f'<div class="tile"><b>{valor}</b><span>{rot}</span></div>'




def fig_inalcancavel():
    o = [C(70, 60, 24, '#fff', INK, 2), T(70, 66, 'v', 20, INK, 'middle', 600),
         T(70, 100, 'qualquer vértice', 17, INK2, 'middle')]
    o.append(L(96, 60, 250, 60, INK, 2.4, 'marker-end="url(#pi)"'))
    o.append(R(250, 8, 190, 84, VET_BG, VET, 2))
    for k, (x, y) in enumerate(((290, 38), (400, 38), (345, 78))):
        o.append(C(x, y, 11, '#fff', VET, 2))
    o.append(L(301, 38, 389, 38, VET, 2, 'marker-end="url(#pi)"'))
    o.append(L(393, 47, 355, 70, VET, 2, 'marker-end="url(#pi)"'))
    o.append(L(335, 70, 296, 47, VET, 2, 'marker-end="url(#pi)"'))
    o.append(T(345, 112, 'ciclo de soma negativa', 17, VET, 'middle', 600))
    o.append(L(440, 60, 600, 60, INK, 2.4, 'marker-end="url(#pi)"'))
    o.append(C(630, 60, 28, INK, INK, 2))
    o.append(T(630, 67, '100', 20, '#fff', 'middle', 600))
    o.append(T(630, 100, 'destino', 17, INK2, 'middle'))
    o.append(T(672, 52, 'cada volta no ciclo reduz o custo:', 19, INK) + T(672, 78, 'd = ' + NEG, 24, VET, 'start', 600))
    return svg(1000, 122, ''.join(o))

slide(f'Ciclo negativo: detecção antecipada no {wsub("W_1")}', f'''<div class="tiles">
{tile(cel(bf1['rounds'], lambda r: f'{r} rodadas'), 'Bellman-Ford até o vértice 100')}
{tile(cel(bf1['mean_s'], dur), 'tempo médio de detecção')}
{tile(cel(fw1['mean_s'], dur), f'Floyd-Warshall ({fw1["threads"] or THREADS} threads)')}
</div>
<div class="g2" style="grid-template-columns: 1.1fr 1fr; gap:40px; margin-top:12px">
<div><h3>Bellman-Ford para antes de V rodadas se:</h3>
<ul class="l">
<li>há um <b>ciclo entre os sucessores</b> <code>next</code> (busca O(V) por rodada);</li>
<li>o <b>próprio destino melhora</b>: só ocorre com um passeio negativo que volta a ele;</li>
<li>a rodada <i>V</i> ainda muda alguma distância.</li>
</ul></div>
<div><h3>Resultado no {wsub("W_1")}</h3>
<ul class="l">
<li>{wsub("W_1")} é fortemente conexo: o ciclo alcança todos, e <b>toda distância é {NEG}</b>.</li>
<li>Floyd-Warshall para ao achar <code>d[i][i] &lt; 0</code> e encerra as threads na barreira seguinte.</li>
</ul></div></div>
<h3 style="margin-top:8px">Por que {NEG} para todos</h3>
{fig_inalcancavel()}''', 'Implementação')

# 6. Floyd-Warshall -----------------------------------------------------------------------------


def fig_memoria():
    w, h = 640, 330
    x0, x1 = 150, 610
    vals = [G[n]['floyd_warshall']['memory_needed_bytes'] for n in NOMES]
    alvo = [v for v in vals if v] + [RAM]
    lo, hi = 10 ** math.floor(math.log10(min(alvo)) - 0.3), 10 ** math.ceil(math.log10(max(alvo)))

    def X(v):
        return x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)
    o = []
    e = math.ceil(math.log10(lo))
    while 10 ** e <= hi:
        if 10 ** e % 1 == 0 or True:
            o.append(L(X(10 ** e), 30, X(10 ** e), 290, LINHA, 1))
            o.append(T(X(10 ** e), 312, bytes_(10 ** e), 15, INK2, 'middle'))
        e += 3 if hi / lo > 1e8 else 1
    for i, n in enumerate(NOMES):
        y = 44 + i * 50
        o.append(T(x0 - 14, y + 22, wsvg(n), 20, INK, 'end', 600))
        v = vals[i]
        if v is None:
            o.append(T(x0 + 6, y + 22, '—  em execução', 16, INK3))
            continue
        cabe = v <= RAM
        o.append(R(x0, y, X(v) - x0, 32, HEAP if cabe else VET))
        o.append(T(X(v) + 8 if X(v) < x1 - 150 else X(v) - 8, y + 22, f'{bytes_(v)}', 18,
                   INK if X(v) < x1 - 150 else '#fff', 'start' if X(v) < x1 - 150 else 'end', 600))
    o.append(L(X(RAM), 22, X(RAM), 292, INK, 2.2, 'stroke-dasharray="7 5"'))
    o.append(T(X(RAM), 18, f'RAM: {br(RAM / 2 ** 30)} GiB', 16, INK, 'middle', 600))
    return svg(w, h, ''.join(o))


slide('Floyd-Warshall: uma matriz, blocos e threads', f'''<div class="g2" style="grid-template-columns: 1fr 660px; gap:28px">
<div>
<ul class="l">
<li><b>Matriz única</b>, atualizada no lugar: <code>12·V²</code> bytes (8 de distância + 4 de pai), em vez de uma matriz por <i>k</i>.</li>
<li><b>Blocos de {FW_BLOCO}×{FW_BLOCO}</b>: os blocos lidos cabem no cache L1.</li>
<li><b>{THREADS} threads</b> nos blocos de cada fase.</li>
<li><b>Saída antecipada</b> se a diagonal fica negativa.</li>
<li>A memória é o limite: do {wsub("W_3")} em diante a matriz não cabe. Aí, a tabela 5×5 sai do Bellman-Ford (um por destino).</li>
</ul></div>
<div>{fig_memoria()}
<p class="nota">Memória da matriz do Floyd-Warshall por grafo (escala logarítmica). Vermelho: não cabe na RAM.</p></div>
</div>''', 'Implementação')

# 7. Q1 -----------------------------------------------------------------------------------------
linhas = []
for n in NOMES:
    g = G[n]
    b = g['bellman_ford']
    if b['status'] == 'ciclo_negativo':
        ds = [f'<td>{NEG}</td>'] * 3
    elif b['status'] == 'ok':
        ds = [f'<td>{br(b["distances"][k], 2) if b["distances"][k] is not None else "∞"}</td>' for k in ('10', '20', '30')]
    else:
        ds = [f'<td>{PD}</td>'] * 3
    linhas.append(f'<tr><td class="e">{wsub(n)}{em_exec(g)}</td>{"".join(ds)}<td>{cel(b["rounds"], br)}</td>'
                  f'<td>{cel(b["mean_s"], dur)}</td></tr>')
slide('Q1: distâncias de 10, 20 e 30 até o vértice 100 (Bellman-Ford)', f'''<table class="bt" style="font-size:28px">
<tr><th class="e">grafo</th><th>10 → 100</th><th>20 → 100</th><th>30 → 100</th><th>rodadas</th><th>tempo médio</th></tr>
{"".join(linhas)}</table>
<ul class="l grande" style="margin-top:24px">
<li>{wsub("W_1")}: o ciclo negativo alcança o 100, então toda distância é {NEG}; as rodadas contam até a detecção.</li>
<li>Nos demais, as rodadas até parar são poucas perto de V: só os ativos examinam arestas.</li>
</ul>''', 'Resultados')

# 8. Q2 -----------------------------------------------------------------------------------------
ROT = {'floyd_warshall': 'Floyd-Warshall', 'bellman_ford': 'Bellman-Ford, um por destino'}


def matriz(n, tam, larg, alt):
    g = G[n]
    m = g['matrix']
    vs = m['vertices']
    cab = '<tr><th class="e"></th>' + ''.join(f'<th>{v}</th>' for v in vs) + '</tr>'
    if m['rows'] is None:
        corpo = ''.join(f'<tr><td class="e">{v}</td>' + f'<td>{PD}</td>' * 5 + '</tr>' for v in vs)
        fonte = ''
    else:
        corpo = ''.join(f'<tr><td class="e">{v}</td>' + ''.join(
            f'<td>{"∞" if x is None else br(x, 2)}</td>' for x in row) + '</tr>' for v, row in zip(vs, m['rows']))
        fonte = f'<span class="meth">{ROT[m["source"]]}</span>'
    return (f'<div class="mat" style="font-size:{tam}px"><div class="mt">{wsub(n)}{em_exec(g) if not g["complete"] else ""} {fonte}</div>'
            f'<table class="bt mx" style="--lg:{larg}px;--al:{alt}px">{cab}{corpo}</table></div>')


slide('Q2: distâncias entre os vértices 10, 20, 30, 40 e 50', f'''<div class="g2" style="grid-template-columns: 600px 1fr; gap:36px">
<div>{matriz("W_2", 26, 78, 42)}
<p class="nota" style="margin-top:14px">Linha = origem, coluna = destino. {wsub("W_1")}: ciclo negativo, as 25 células valem {NEG}.<br>
{wsub("W_3")} a {wsub("W_5")}: a matriz de Floyd-Warshall não cabe; as distâncias vêm de 5 execuções do Bellman-Ford (uma por destino), conferidas contra o Floyd-Warshall em um grafo de 10 mil vértices.</p></div>
<div>{matriz("W_3", 20, 66, 24)}{matriz("W_4", 20, 66, 24)}{matriz("W_5", 20, 66, 24)}</div>
</div>''', 'Resultados')

# 9. Q3 -----------------------------------------------------------------------------------------
linhas = []
for n in NOMES:
    g = G[n]
    b, f = g['bellman_ford'], g['floyd_warshall']
    c1 = cel(b['mean_s'], dur) + ('<small>detecção</small>' if b['status'] == 'ciclo_negativo' else '')
    ft = fw_tempo(n)
    if f['mean_s'] is not None:
        c2 = dur(f['mean_s']) + ('<small>detecção</small>' if f['status'] == 'ciclo_negativo' else f'<small>{f["threads"]} thr</small>')
    elif ft:
        c2 = f'<span class="est">{dur(ft[0])}</span><small>est. V³</small>'
    elif f['status'] == 'memoria_insuficiente':
        c2 = 'não cabe'
    else:
        c2 = PD
    a = g['all_pairs_bf']
    if a['mean_s'] is None:
        c3 = PD
    else:
        c3 = (f'<span class="{"est" if a["estimated"] else ""}">{dur(a["mean_s"])}</span>'
              + ('<small>detecção</small>' if a['status'] == 'ciclo_negativo' else
                 f'<small>{"est., " if a["estimated"] else ""}{a["threads"]} thr</small>'))
    linhas.append(f'<tr><td class="e">{wsub(n)}{em_exec(g)}</td><td>{c1}</td><td>{c2}</td><td>{c3}</td></tr>')
slide('Q3: tempo médio de 10 execuções', f'''<table class="bt" style="font-size:23px">
<tr><th class="e">grafo</th><th>Bellman-Ford até o 100 (1 thread)</th><th>Floyd-Warshall</th><th>Bellman-Ford, todos os pares</th></tr>
{"".join(linhas)}</table>
<ul class="l" style="margin-top:12px;font-size:20px">
<li>{wsub("W_1")}: os três tempos são de <b>detecção</b> do ciclo negativo; cada algoritmo para num ponto diferente, então não se comparam.</li>
<li><span class="est">Itálico</span> = estimativa. Floyd-Warshall: média do {wsub("W_2")} × (V/V<sub>2</sub>)³. Todos-pares: destinos amostrados em 1 thread, extrapolados para V.</li>
<li>Tempos sem leitura nem escrita de arquivo.</li>
</ul>''', 'Resultados')

# 10. Q4 ----------------------------------------------------------------------------------------


def fig_q4():
    gs = ['W_2', 'W_3', 'W_4', 'W_5']
    w, h = 680, 400
    x0, x1, yt, yb = 70, 615, 36, 340
    vals = []
    for n in gs:
        ft, bf = fw_tempo(n), bf_todos_equiv(n)
        vals.append((ft, bf))
    todos = [v[0][0] for v in vals if v[0]] + [v[1] for v in vals if v[1]]
    lo = 1.0
    hi = 10 ** math.ceil(math.log10(max(todos))) if todos else 1e6
    if todos and min(todos) < 1:
        lo = 10 ** math.floor(math.log10(min(todos)))

    def Y(v):
        return yb - (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (yb - yt)
    o = []
    passo = 2 if math.log10(hi / lo) > 8 else 1
    e = int(math.log10(lo))
    while 10 ** e <= hi * 1.001:
        o.append(L(x0, Y(10 ** e), x1, Y(10 ** e), LINHA, 1))
        o.append(T(x0 - 8, Y(10 ** e) + 5, f'10<tspan dy="-6" font-size="70%">{e}</tspan>', 16, INK2, 'end'))
        e += passo
    for rot, s in (('1 h', 3600), ('1 dia', 86400), ('1 ano', 365 * 86400)):
        if lo < s < hi:
            o.append(L(x0, Y(s), x1, Y(s), INK3, 1.2, 'stroke-dasharray="3 5"'))
            o.append(T(x1 + 6, Y(s) + 5, rot, 16, INK2))
    o.append(T(4, 14, 'segundos (escala logarítmica)', 16, INK2))
    gw = (x1 - x0) / len(gs)
    bw = 56
    for i, n in enumerate(gs):
        cx = x0 + gw * (i + 0.5)
        o.append(T(cx, yb + 28, wsvg(n), 20, INK, 'middle', 600))
        ft, bf = vals[i]
        for k, (val, cor, hach) in enumerate(((ft, VET, 'hach'), (bf and (bf, bool(G[n]['all_pairs_bf']['estimated'])), HEAP, 'hachb'))):
            pass
        for k, (item, cor, hach) in enumerate(((ft, VET, 'hach'),
                                                ((bf, bool(G[n]['all_pairs_bf']['estimated'])) if bf else None, HEAP, 'hachb'))):
            bx = cx - bw - 4 + k * (bw + 8)
            if item is None:
                o.append(T(bx + bw / 2, yb - 8, '—', 20, INK3, 'middle'))
                continue
            v, est = item
            o.append(R(bx, Y(v), bw, yb - Y(v), f'url(#{hach})' if est else cor, cor, 2))
            o.append(T(bx + bw / 2, Y(v) - 6, dur(v), 15, INK, 'middle', 600,
                       extra='stroke="#fff" stroke-width="4" paint-order="stroke"'))
    return svg(w, h, ''.join(o))


def linhas_ops():
    out = []
    for n in ['W_2', 'W_3', 'W_4', 'W_5']:
        g = G[n]
        o = g['ops']
        fw, bf = o['fw_relaxations'], o['bf_ops_upper_bound']
        out.append(f'<tr><td class="e">{wsub(n)}{em_exec(g)}</td><td>{cel(fw, sci)}</td><td>{cel(bf, sci)}</td>'
                   f'<td>{PD if fw is None or bf is None else "×" + sig(fw / bf, 2)}</td></tr>')
    return ''.join(out)


w2 = G['W_2']
ft2, bf2 = fw_tempo('W_2'), bf_todos_equiv('W_2')
if ft2 and bf2:
    venc = ('Bellman-Ford' if bf2 < ft2[0] else 'Floyd-Warshall')
    razao = max(bf2, ft2[0]) / min(bf2, ft2[0])
    placar = f'<b>{wsub("W_2")}: {venc} foi {sig(razao, 2)}× mais rápido</b> ({dur(min(bf2, ft2[0]))} contra {dur(max(bf2, ft2[0]))}, com {THREADS} threads).'
else:
    razao = None
    placar = f'<b>{wsub("W_2")}</b>: resultado pendente <span class="ex">em execução</span>.'
slide('Q4: todos os pares, Bellman-Ford contra Floyd-Warshall', f'''<div class="g2" style="grid-template-columns: 690px 1fr; gap:22px">
<div>{fig_q4()}
<p class="nota"><span class="sw" style="background:{VET}"></span>Floyd-Warshall <span class="sw" style="background:{HEAP};margin-left:14px"></span>Bellman-Ford, V execuções (equivalente a {THREADS} threads). Listrado = estimado.</p></div>
<div><p style="font-size:22px">{placar}</p>
<table class="bt p" style="font-size:20px"><tr><th class="e"></th><th>FW: V³</th><th>BF: V·R·E</th><th>razão</th></tr>{linhas_ops()}</table>
<ul class="l" style="margin-top:12px;font-size:21px">
<li>FW faz <b>V³ relaxações</b> sempre, mesmo em grafo esparso.</li>
<li>BF examina só as arestas dos <b>ativos</b>; V·R·E é o teto.</li>
<li>FW ainda exige <b>V² de memória</b>: não roda do {wsub("W_3")} em diante.</li>
</ul></div></div>''', 'Resultados')

# 11. Conclusão ---------------------------------------------------------------------------------
fw2 = G['W_2']['floyd_warshall']
conc_w2 = (f'No {wsub("W_2")}, o Floyd-Warshall levou {dur(fw2["mean_s"])} com {THREADS} threads' +
           (f'; todos os pares por Bellman-Ford, {dur(bf2)}, também com {THREADS} threads.' if bf2 else '.')
           ) if fw2['mean_s'] is not None else f'No {wsub("W_2")}, a comparação ainda está em execução <span class="ex">em execução</span>.'
slide('Conclusões', f'''<ul class="l" style="font-size:30px;line-height:1.45">
<li><b>Ciclo negativo:</b> a detecção antecipada acha o ciclo do {wsub("W_1")} em {cel(bf1["rounds"], br)} rodadas e {cel(bf1["mean_s"], dur)}; todas as distâncias valem {NEG}.</li>
<li><b>Grafo esparso:</b> Bellman-Ford com lista de ativos paga só pelas arestas que mudam; Floyd-Warshall paga V³. {conc_w2}</li>
<li><b>Memória decide:</b> a matriz de 12·V² bytes não cabe do {wsub("W_3")} em diante ({bytes_(G["W_3"]["floyd_warshall"]["memory_needed_bytes"]) if G["W_3"]["floyd_warshall"]["memory_needed_bytes"] else PD} no {wsub("W_3")}, contra {br(RAM / 2 ** 30)} GiB de RAM).</li>
</ul>
<p class="nota" style="margin-top:30px;font-size:20px">Validação: 55,8 milhões de verificações nos testes; distâncias do {wsub("W_2")} conferem com um Dijkstra independente em Python. Código: {REPO}</p>''',
      'Conclusão')

# ---------------------------------------------------------------- página

CSS = (AQUI.parent / 'comum' / 'estilo.css').read_text() + f'''
.pd {{ color: {INK3}; }}
.ex {{ font-size: 14px; background: #f6e3b4; color: #7a5a00; padding: 1px 8px; border-radius: 10px; margin-left: 8px;
      font-weight: 500; white-space: nowrap; font-style: normal; }}
.est {{ font-style: italic; }}
table.bt td small {{ display: block; margin-left: 0; line-height: 1.1; }}
table.bt.mx td, table.bt.mx th {{ line-height: 1.1; padding: 1px 8px; min-width: var(--lg); }}
table.bt.mx tr > * {{ height: var(--al); }}
.mat {{ margin-bottom: 8px; }}
.mt {{ font-weight: 600; margin-bottom: 2px; }}
.meth {{ font-weight: 400; color: var(--tinta2); font-size: 0.8em; margin-left: 8px; }}
.tiles {{ display: flex; gap: 28px; margin-top: 6px; }}
.tile {{ flex: 1; background: var(--fundo); border-left: 4px solid var(--azul); padding: 8px 20px; }}
.tile b {{ display: block; font-size: 40px; font-weight: 600; color: var(--azul); line-height: 1.15; }}
.tile span {{ font-size: 19px; color: var(--tinta2); }}
.sw {{ display: inline-block; width: 14px; height: 14px; vertical-align: -1px; margin-right: 6px; }}
.cod15 .cod pre {{ font-size: 15px; }}
.grande {{ font-size: 27px; }}
'''
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
    partes = []
    total = len(slides)
    for n, s in enumerate(slides, 1):
        if s['titulo'] is None:
            partes.append(f'<section class="slide {s["cls"]}" id="s{n}">{s["corpo"]}</section>')
            continue
        partes.append(
            f'<section class="slide {s["cls"]}" id="s{n}"><header><span>{s["titulo"]}</span></header>'
            f'<div class="corpo">{s["corpo"]}</div>'
            f'<footer><span>Marroni e Knust · Caminhos mínimos com pesos negativos</span><span>{s["secao"]}</span>'
            f'<b>{n} / {total}</b></footer></section>')
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Caminhos mínimos com pesos negativos · COS242</title>
<style>{CSS}</style></head>
<body>
<svg width="0" height="0" style="position:absolute">{DEFS}</svg>
{"".join(partes)}
<script>{JS}</script>
</body></html>
'''


def valores_roteiro():
    """Valores dos marcadores {{...}} do roteiro, com as mesmas funções de formatação dos slides."""
    def ok(v, f):
        return '—' if v is None else f(v)
    v = {'THREADS': str(THREADS), 'RAM_GIB': br(RAM / 2 ** 30), 'Q4_RAZAO': ok(razao, lambda r: sig(r, 2))}
    for n in NOMES:
        g = G[n]
        b, f, a, o = g['bellman_ford'], g['floyd_warshall'], g['all_pairs_bf'], g['ops']
        ft = fw_tempo(n)
        for k in ('10', '20', '30'):
            v[f'{n}.d{k}'] = ok(b['distances'].get(k), lambda x: br(x, 2))
        v[f'{n}.bf_r'] = ok(b['rounds'], br)
        v[f'{n}.bf_t'] = ok(b['mean_s'], dur)
        v[f'{n}.fw'] = ok(ft, lambda x: dur(x[0]))
        v[f'{n}.fw_s'] = ok(f['mean_s'], lambda x: br(round(x)))
        v[f'{n}.fw_mem'] = ok(f['memory_needed_bytes'], bytes_)
        v[f'{n}.ap'] = ok(bf_todos(n), lambda x: dur(x[0]))
        v[f'{n}.amostra'] = ok(a['sample'], br)
        v[f'{n}.e_v'] = ok(g['edges'] and g['vertices'] and g['edges'] / g['vertices'], lambda x: sig(x, 2))
        v[f'{n}.fw_ops'] = ok(o['fw_relaxations'], sci_txt)
        v[f'{n}.bf_ops'] = ok(o['bf_ops_upper_bound'], sci_txt)
        fo, bo = o['fw_relaxations'], o['bf_ops_upper_bound']
        v[f'{n}.ops_razao'] = '—' if fo is None or bo is None else sig(fo / bo, 2)
    return v


def roteiro():
    """Gera ROTEIRO.md a partir de ROTEIRO.modelo.md; falha se algum marcador for desconhecido."""
    modelo = AQUI / 'ROTEIRO.modelo.md'
    valores = valores_roteiro()
    desconhecidos = sorted({m for m in re.findall(r'\{\{\s*([^}]*?)\s*\}\}', modelo.read_text()) if m not in valores})
    if desconhecidos:
        sys.exit(f'erro: {modelo.name}: marcador(es) desconhecido(s): ' + ', '.join(desconhecidos))
    texto = re.sub(r'\{\{\s*([^}]*?)\s*\}\}', lambda m: valores[m.group(1)], modelo.read_text())
    if '{{' in texto:
        sys.exit(f'erro: {modelo.name}: sobrou "{{{{" após a substituição (marcador malformado)')
    saida = AQUI / 'ROTEIRO.md'
    saida.write_text('<!-- gerado por build.py a partir de ROTEIRO.modelo.md; não edite -->\n' + texto)
    print(saida.relative_to(RAIZ))


def pendentes():
    out = []
    for n in NOMES:
        g = G[n]
        for campo, v in (('V', g['vertices']), ('BF', g['bellman_ford']['mean_s']),
                         ('matriz', g['matrix']['rows'] if n != 'W_1' else 0), ('todos-pares', g['all_pairs_bf']['mean_s'])):
            if v is None:
                out.append(f'{n}:{campo}')
        if g['floyd_warshall']['status'] == 'pendente':
            out.append(f'{n}:FW')
    return out


def main():
    saida = AQUI / 'index.html'
    saida.write_text(pagina())
    roteiro()
    print(f'{saida.relative_to(RAIZ)}: {len(slides)} slides')
    print('pendentes:', ', '.join(pendentes()) or 'nenhum')
    if '--sem-pdf' in sys.argv:
        return
    pdf = AQUI / 'apresentacao.pdf'
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                    '--virtual-time-budget=5000', f'--print-to-pdf={pdf}', saida.as_uri()],
                   check=True, capture_output=True)
    print(pdf.relative_to(RAIZ))


if __name__ == '__main__':
    main()
