"""Gera report/parte3/exemplo.json, o exemplo didático da Parte 3 (slides e relatório).

Uso (da raiz do repositório): python3 -I report/parte3/exemplo.py
Também grava os dois grafos em tests/fixtures/ para conferir com build/csr/cos_part3.
Simula o Bellman-Ford até o destino com a semântica de Graph::relax_rounds: rodadas sobre a
lista de ativos, arestas de entrada na ordem da CSR, parada em rodada sem mudança e parada
antecipada quando os sucessores `next` formam um ciclo.
"""
import heapq
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
N, DESTINO, ORIGEM = 6, 6, 1
# (u, v, peso), em ordem de u e depois v; a CSR guarda as arestas na ordem do arquivo.
ARESTAS = [(1, 2, 5), (1, 5, 1), (2, 3, 1), (3, 1, 1), (3, 4, 4),
           (3, 5, 5), (3, 6, -4), (4, 6, 3), (5, 6, 3)]
COORDENADAS = {1: (0, 1), 2: (1, 0), 3: (2, 1), 4: (4, 0), 5: (3, 2), 6: (5, 1)}
# Variante: um peso muda e o ciclo 1 -> 2 -> 3 -> 1 (soma 7) passa a somar -1.
VARIANTE = (1, 2, -3)


def csr(arestas, direcao):
    """Offsets, vizinhos e pesos 0-based; 'forward' agrupa por origem, 'backward' por destino."""
    chave, outro = (0, 1) if direcao == "forward" else (1, 0)
    offsets, vizinhos, pesos = [0], [], []
    for v in range(1, N + 1):
        for a in arestas:
            if a[chave] == v:
                vizinhos.append(a[outro] - 1)
                pesos.append(a[2])
        offsets.append(len(vizinhos))
    return {"offsets": offsets, "vizinhos": vizinhos, "pesos": pesos}


def bellman_ford(arestas, destino):
    entrada = {v: [(u, w) for u, x, w in arestas if x == v] for v in range(1, N + 1)}
    dist = {v: None for v in range(1, N + 1)}
    prox = {v: None for v in range(1, N + 1)}
    dist[destino] = 0
    ativos, rodadas, ciclo = [destino], [], None
    while ativos:
        if len(rodadas) == N:
            ciclo = True
            break
        proximos, ativos_da_rodada = [], list(ativos)
        for v in ativos:
            for u, w in entrada[v]:
                cand = dist[v] + w
                if dist[u] is None or cand < dist[u]:
                    if u == destino:
                        return rodadas, dist, prox, "destino_melhorou"
                    dist[u], prox[u] = cand, v
                    if u not in proximos:
                        proximos.append(u)
        rodadas.append({"rodada": len(rodadas) + 1, "ativos": ativos_da_rodada,
                        "mudaram": list(proximos), "distancia": dict(dist), "next": dict(prox)})
        for inicio in proximos:  # laço em `next` prova ciclo negativo
            visto, x = set(), inicio
            while x is not None:
                if x in visto:
                    return rodadas, dist, prox, "laco_em_next"
                visto.add(x)
                x = prox[x]
        ativos = proximos
    return rodadas, dist, prox, ciclo and "rodada_V"


def dijkstra(arestas, origem):
    """Dijkstra de livro: um vértice fechado nunca mais é alterado."""
    saida = {v: [(x, w) for u, x, w in arestas if u == v] for v in range(1, N + 1)}
    dist = {v: None for v in range(1, N + 1)}
    dist[origem] = 0
    fila, fechados = [(0, origem)], []
    while fila:
        d, u = heapq.heappop(fila)
        if u in fechados:
            continue
        fechados.append(u)
        for v, w in saida[u]:
            if v not in fechados and (dist[v] is None or d + w < dist[v]):
                dist[v] = d + w
                heapq.heappush(fila, (d + w, v))
    return dist, fechados


def distancias_corretas(arestas, origem):
    dist = {v: None for v in range(1, N + 1)}
    dist[origem] = 0
    for _ in range(N):
        for u, v, w in arestas:
            if dist[u] is not None and (dist[v] is None or dist[u] + w < dist[v]):
                dist[v] = dist[u] + w
    return dist


def johnson(arestas):
    """Potenciais h(u) = min(0, menor peso de um passeio que começa em u) (Bellman-Ford com destino virtual
    ligado a todos com peso 0) e os pesos reponderados w' = w + h(v) - h(u)."""
    h = {v: 0 for v in range(1, N + 1)}
    for _ in range(N):
        for u, v, w in arestas:
            h[u] = min(h[u], w + h[v])
    novos = [[u, v, w + h[v] - h[u]] for u, v, w in arestas]
    assert all(w >= 0 for _, _, w in novos)
    return h, novos


def texto_grafo(arestas):
    return f"{N}\n" + "".join(f"{u} {v} {w}\n" for u, v, w in arestas)


def chaves(d):
    return {str(k): v for k, v in d.items()}


def main():
    rodadas, dist, prox, parada = bellman_ford(ARESTAS, DESTINO)
    assert parada is None and len(rodadas) == 4, (parada, len(rodadas))
    assert sum(1 for a in ARESTAS if a[2] < 0) == 1
    d_dij, fechados = dijkstra(ARESTAS, ORIGEM)
    d_ok = distancias_corretas(ARESTAS, ORIGEM)
    errado = [v for v in d_ok if d_dij[v] != d_ok[v]]
    assert errado == [DESTINO], errado

    variante = [(u, v, VARIANTE[2]) if (u, v) == VARIANTE[:2] else (u, v, w)
                for u, v, w in ARESTAS]
    rodadas_v, _, prox_v, parada_v = bellman_ford(variante, DESTINO)
    assert parada_v is not None
    ciclo = [1, 2, 3, 1]
    pesos = {(u, v): w for u, v, w in variante}
    soma = sum(pesos[(a, b)] for a, b in zip(ciclo, ciclo[1:]))
    assert soma < 0
    # ponteiros next da execução real da variante, rodada a rodada (o laço aparece na última)
    nx_final = rodadas_v[-1]["next"]
    x, visto = rodadas_v[-1]["mudaram"][0], []
    while x not in visto:
        visto.append(x)
        x = nx_final[x]
    laco = visto[visto.index(x):] + [x]
    assert sorted(laco[:-1]) == sorted(ciclo[:-1]), (laco, ciclo)

    h, novos = johnson(ARESTAS)
    dados = {
        "vertices": N, "destino": DESTINO, "origem_dijkstra": ORIGEM,
        "coordenadas": {str(v): list(c) for v, c in COORDENADAS.items()},
        "arestas": [list(a) for a in ARESTAS],
        "csr": {"forward": csr(ARESTAS, "forward"), "backward": csr(ARESTAS, "backward"),
                "nota": "Índices 0-based, como a biblioteca guarda (vértice k do desenho = k - 1); "
                        "forward agrupa as arestas por origem, backward por destino."},
        "bellman_ford": {
            "rodadas": [{"rodada": r["rodada"], "ativos": r["ativos"], "mudaram": r["mudaram"],
                         "distancia": chaves(r["distancia"]), "next": chaves(r["next"])}
                        for r in rodadas],
            "distancia": chaves(dist), "next": chaves(prox),
        },
        "johnson": {"h": chaves(h), "arestas_novas": novos},
        "dijkstra_errado": {"origem": ORIGEM, "vertice": errado[0], "dijkstra": d_dij[errado[0]],
                            "correto": d_ok[errado[0]], "ordem_de_fechamento": fechados},
        "variante_ciclo": {"aresta_alterada": list(VARIANTE), "ciclo": ciclo, "soma": soma,
                           "rodadas": len(rodadas_v), "parada": parada_v,
                           "rodadas_detalhe": [{"rodada": r["rodada"], "ativos": r["ativos"], "mudaram": r["mudaram"],
                                                "distancia": chaves(r["distancia"]), "next": chaves(r["next"])}
                                               for r in rodadas_v],
                           "laco_em_next": laco},
    }
    (RAIZ / "report/parte3/exemplo.json").write_text(
        json.dumps(dados, indent=1, ensure_ascii=False) + "\n")
    (RAIZ / "tests/fixtures/exemplo_p3.txt").write_text(texto_grafo(ARESTAS))
    (RAIZ / "tests/fixtures/exemplo_p3_ciclo.txt").write_text(texto_grafo(variante))
    for r in rodadas:
        print(r["rodada"], r["ativos"], "->", r["mudaram"])
    print("dist", dist, "next", prox)
    print("dijkstra", d_dij, "correto", d_ok, "fechamento", fechados)
    print("johnson h", h, novos)
    print("variante", parada_v, len(rodadas_v), soma)


main()
