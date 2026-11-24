#!/usr/bin/env python3
"""Gera grafos sintéticos com pesos para testar a Parte 3 (Bellman-Ford e Floyd-Warshall).

Uso: python3 -I bench/gerar_grafo.py V E SEMENTE SAIDA [--nao-direcionado] [--negativos] [--ciclo-negativo]

Formato de saída (igual a data/grafo_W_*.txt): primeira linha com V; depois uma
aresta por linha, "u v peso", vértices de 1 a V, peso com 2 casas decimais. No
grafo direcionado a aresta vai do primeiro para o segundo vértice.

Os pesos são mantidos em centavos inteiros e só viram texto na escrita, para
não haver erro de arredondamento em ponto flutuante. Somente biblioteca padrão.
"""

import argparse
import random
import sys

PESO_MAX = 1000        # pesos base em [0, 10.00], em centavos
POTENCIAL_MAX = 500    # potenciais em [-5.00, 5.00], em centavos
BLOCO = 100000         # linhas por bloco de escrita


def centavos_para_texto(c):
    """Converte centavos inteiros em texto com 2 casas decimais."""
    sinal = "-" if c < 0 else ""
    c = abs(c)
    return f"{sinal}{c // 100}.{c % 100:02d}"


def arestas_base(V, E, direcionado, rng):
    """Esqueleto conexo (ciclo hamiltoniano ou caminho) mais arestas aleatórias."""
    perm = list(range(1, V + 1))
    rng.shuffle(perm)
    arestas = [(perm[i], perm[(i + 1) % V]) for i in range(V if direcionado else V - 1)]
    while len(arestas) < E:
        u = rng.randint(1, V)
        v = rng.randint(1, V)
        if u != v:
            arestas.append((u, v))
    return [(u, v, rng.randint(0, PESO_MAX)) for u, v in arestas]


def aplicar_potenciais(arestas, V, rng):
    """Soma p(u) - p(v) a cada peso; ciclos mantêm a soma. Devolve (arestas, p)."""
    p = [0] + [rng.randint(-POTENCIAL_MAX, POTENCIAL_MAX) for _ in range(V)]
    return [(u, v, w + p[u] - p[v]) for u, v, w in arestas], p


def acrescentar_ciclo_negativo(arestas, V, rng):
    """Acrescenta a->b->c->a com peso -1.00 em cada aresta; devolve (a, b, c)."""
    a, b, c = rng.sample(range(1, V + 1), 3)
    arestas += [(a, b, -100), (b, c, -100), (c, a, -100)]
    return a, b, c


def escrever(caminho, linhas):
    """Escreve linhas de texto em blocos."""
    with open(caminho, "w") as f:
        bloco = []
        for linha in linhas:
            bloco.append(linha)
            if len(bloco) >= BLOCO:
                f.write("\n".join(bloco) + "\n")
                bloco = []
        if bloco:
            f.write("\n".join(bloco) + "\n")


def ler_args():
    ap = argparse.ArgumentParser(description="Gera grafos sintéticos com pesos (Parte 3).")
    ap.add_argument("V", type=int, help="número de vértices")
    ap.add_argument("E", type=int, help="número de arestas (direcionado: E >= V; "
                    "não direcionado: E >= V-1)")
    ap.add_argument("SEMENTE", type=int, help="semente do gerador (resultado determinístico)")
    ap.add_argument("SAIDA", help="arquivo de saída")
    ap.add_argument("--nao-direcionado", action="store_true",
                    help="grafo não direcionado (caminho aleatório + arestas extras)")
    ap.add_argument("--negativos", action="store_true",
                    help="aplica potenciais aleatórios: pesos negativos sem ciclo negativo; "
                    "grava SAIDA.potenciais com 'v p(v)'")
    ap.add_argument("--ciclo-negativo", action="store_true",
                    help="acrescenta (além das E arestas) um ciclo a->b->c->a de soma -3.00; "
                    "exige V >= 3")
    args = ap.parse_args()
    if args.nao_direcionado and (args.negativos or args.ciclo_negativo):
        ap.error("--negativos e --ciclo-negativo exigem grafo direcionado: "
                 "no não direcionado, qualquer aresta negativa já é um ciclo negativo")
    minimo = args.V - 1 if args.nao_direcionado else args.V
    if args.V < 2:
        ap.error("V deve ser pelo menos 2")
    if args.E < minimo:
        ap.error(f"E deve ser pelo menos {minimo} para V={args.V} "
                 f"({'caminho gerador' if args.nao_direcionado else 'ciclo hamiltoniano, fortemente conexo'})")
    if args.ciclo_negativo and args.V < 3:
        ap.error("--ciclo-negativo exige V >= 3")
    return args


def main():
    args = ler_args()
    rng = random.Random(args.SEMENTE)
    arestas = arestas_base(args.V, args.E, not args.nao_direcionado, rng)
    if args.negativos:
        arestas, p = aplicar_potenciais(arestas, args.V, rng)
        escrever(args.SAIDA + ".potenciais",
                 (f"{v} {centavos_para_texto(p[v])}" for v in range(1, args.V + 1)))
    if args.ciclo_negativo:
        a, b, c = acrescentar_ciclo_negativo(arestas, args.V, rng)
        print(f"ciclo negativo: {a} -> {b} -> {c} -> {a}", file=sys.stderr)
    linhas = (f"{u} {v} {centavos_para_texto(w)}" for u, v, w in arestas)
    escrever(args.SAIDA, [str(args.V), *linhas])
    negativas = sum(1 for _, _, w in arestas if w < 0)
    print(f"V={args.V} E={len(arestas)} arestas negativas={negativas}", file=sys.stderr)


if __name__ == "__main__":
    main()
