#!/usr/bin/env python3
"""
Gera as 10 figuras vetoriais (SVG) da Parte 3 a partir dos dados medidos em
report/parte3/*.json e bench/results/parte3/*.txt.

Regras estritas para compatibilidade com Typst (usvg):
- font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif (ou Menlo p/ código)
- Nunca usar ∈ (U+2208) nem ✕ (U+2715) em <text>; usar 'em' e '×' (U+00D7).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REPORT = ROOT / "report" / "parte3"
BENCH = ROOT / "bench" / "results" / "parte3"
ASSETS = HERE / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

# ── Paleta editorial (idêntica ao slides.typ) ────────────────────────────────
INK = "#0f172a"
NAVY = "#1b365d"
TEAL = "#0f6260"
TEAL_BG = "#e6f2f1"
NAVY_BG = "#eaf0f7"
OCHRE = "#b45309"
OCHRE_BG = "#fef3e2"
CRIMSON = "#9f1239"
CRIMSON_BG = "#fbeaf0"
SLATE = "#475569"
MUTED = "#64748b"
SOFT = "#f8fafc"
RULE = "#cbd5e1"
HAIR = "#e2e8f0"
WHITE = "#ffffff"

FONT_SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
FONT_MONO = "Menlo, monospace"


# ── Helpers de formatação e SVG ──────────────────────────────────────────────
def br(val: float, dec: int = 1) -> str:
    s = f"{val:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def br_int(val: int) -> str:
    return f"{val:,}".replace(",", ".")


def sig_br(val: float, n: int = 2) -> str:
    if val == 0:
        return "0"
    exp = math.floor(math.log10(abs(val)))
    dec = max(0, n - 1 - exp)
    if abs(val) >= 100 and dec == 0:
        r = round(val, -max(0, exp + 1 - n))
        return br_int(int(round(r)))
    return br(val, dec)


def fmt_dur(s: float, sig: int = 2) -> str:
    for lim, div, u in (
        (1e-3, 1e-6, "µs"),
        (1, 1e-3, "ms"),
        (120, 1, "s"),
        (7200, 60, "min"),
        (172800, 3600, "h"),
        (330 * 86400, 86400, "dias"),
        (1e30, 365 * 86400, "anos"),
    ):
        if s < lim:
            val = s / div
            if u == "anos" and round(val) == 1 and sig <= 2:
                return f"{sig_br(val, sig)} ano"
            return f"{sig_br(val, sig)} {u}"
    return f"{s:.1f} s"


def svg_wrap(w: float, h: float, body: str, defs: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">\n'
        f"<style>\n"
        f"  text {{ font-family: {FONT_SANS}; }}\n"
        f"  .mono {{ font-family: {FONT_MONO}; }}\n"
        f"</style>\n"
        f"<defs>\n"
        f'  <marker id="arr-ink" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="{SLATE}"/></marker>\n'
        f'  <marker id="arr-navy" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="{NAVY}"/></marker>\n'
        f'  <marker id="arr-teal" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="{TEAL}"/></marker>\n'
        f'  <marker id="arr-crim" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="{CRIMSON}"/></marker>\n'
        f'  <marker id="arr-ochre" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="{OCHRE}"/></marker>\n'
        f'  <marker id="arr-rule" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="{MUTED}"/></marker>\n'
        f'  <pattern id="hatch-teal" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><rect width="7" height="7" fill="{TEAL_BG}"/><line x1="0" y1="0" x2="0" y2="7" stroke="{TEAL}" stroke-width="1.4" stroke-opacity="0.35"/></pattern>\n'
        f'  <pattern id="hatch-navy" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><rect width="7" height="7" fill="{NAVY_BG}"/><line x1="0" y1="0" x2="0" y2="7" stroke="{NAVY}" stroke-width="1.4" stroke-opacity="0.35"/></pattern>\n'
        f'  <pattern id="hatch-gray" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="{SOFT}"/><line x1="0" y1="0" x2="0" y2="6" stroke="{RULE}" stroke-width="1.4"/></pattern>\n'
        f"{defs}"
        f"</defs>\n"
        f"{body}\n"
        f"</svg>\n"
    )


def T(
    x: float,
    y: float,
    txt: str,
    size: float = 12,
    fill: str = INK,
    anchor: str = "start",
    weight: str = "400",
    cls: str = "",
    extra: str = "",
) -> str:
    c = f' class="{cls}"' if cls else ""
    ex = f" {extra}" if extra else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}"{c}{ex}>{escape(txt)}</text>'
    )


def L(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str = RULE,
    sw: float = 1.2,
    extra: str = "",
) -> str:
    ex = f" {extra}" if extra else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{ex}/>'


def R(
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = WHITE,
    stroke: str = "none",
    sw: float = 1.0,
    rx: float = 0,
    extra: str = "",
) -> str:
    r_attr = f' rx="{rx}"' if rx else ""
    ex = f" {extra}" if extra else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(0.0, w):.1f}" height="{max(0.0, h):.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{r_attr}{ex}/>'
    )


def C(
    cx: float,
    cy: float,
    r: float,
    fill: str = WHITE,
    stroke: str = INK,
    sw: float = 1.5,
    extra: str = "",
) -> str:
    ex = f" {extra}" if extra else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{ex}/>'


# ── Carregar todos os dados brutos ───────────────────────────────────────────
DATA = json.loads((REPORT / "data.json").read_text())
CONT = json.loads((REPORT / "contagens.json").read_text())
GRAFOS = json.loads((REPORT / "grafos.json").read_text())
W1C = json.loads((REPORT / "w1_ciclos.json").read_text())
BUSCA = json.loads((REPORT / "tempo_busca_ciclo.json").read_text())
EXEMPLO = json.loads((REPORT / "exemplo.json").read_text())

G = {g["name"]: g for g in DATA["graphs"]}
CB = {g["nome"]: g for g in CONT["grafos"]}
GF = {g["nome"]: g for g in GRAFOS["grafos"]}
BS = {g["nome"]: g for g in BUSCA["grafos"]}


def parse_bench(path: Path) -> dict:
    res: dict = {}
    sec = "root"
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            sec = line[1:-1]
            res.setdefault(sec, {})
        elif "=" in line:
            k, v = line.split("=", 1)
            res.setdefault(sec, {})[k] = v
        elif "," in line and not line.startswith("execucao"):
            res.setdefault(sec, {}).setdefault("runs_list", []).append(line.split(","))
    return res


# =============================================================================
# FIG 01: Grafo de exemplo da capa (exemplo.json)
# =============================================================================
def gen_fig_01() -> None:
    W, H = 560, 440
    coords = {int(k): v for k, v in EXEMPLO["coordenadas"].items()}
    edges = EXEMPLO["arestas"]
    last_round = EXEMPLO["bellman_ford"]["rodadas"][-1]
    dist = {int(k): v for k, v in last_round["distancia"].items()}
    nxt = {int(k): v for k, v in last_round["next"].items()}
    target = EXEMPLO["destino"]

    # Map coordinates: x in [0..5], y in [0..2]
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    pad_l, pad_r, pad_t, pad_b = 58, 58, 72, 92
    sx = (W - pad_l - pad_r) / (max(xs) - min(xs))
    sy = (H - pad_t - pad_b) / (max(ys) - min(ys))
    pos = {
        v: (pad_l + (c[0] - min(xs)) * sx, pad_t + (max(ys) - c[1]) * sy)
        for v, c in coords.items()
    }

    tree_edges = {(u, v) for u, v in nxt.items() if v is not None}
    edge_pairs = {(u, v) for u, v, _ in edges}

    out = [R(0, 0, W, H, SOFT, "none")]
    # Subtle grid dots
    for gx in range(28, W, 32):
        for gy in range(28, H - 48, 32):
            out.append(C(gx, gy, 0.9, RULE, "none"))

    R_NODE = 23

    # Draw edges
    for u, v, w in edges:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        nx_, ny_ = -uy, ux

        is_neg = w < 0
        is_tree = (u, v) in tree_edges
        has_rev = (v, u) in edge_pairs

        if is_neg:
            col, sw, mk = CRIMSON, 3.0, "arr-crim"
        elif is_tree:
            col, sw, mk = TEAL, 2.8, "arr-teal"
        else:
            col, sw, mk = RULE, 1.7, "arr-rule"

        if has_rev:
            # Slight quadratic curve so 1->3 and 3->1 don't collide
            mx = (x1 + x2) / 2 + nx_ * 22
            my = (y1 + y2) / 2 + ny_ * 22
            # Compute start/end along chord offset
            p1x = x1 + ux * (R_NODE + 2) + nx_ * 7
            p1y = y1 + uy * (R_NODE + 2) + ny_ * 7
            p2x = x2 - ux * (R_NODE + 5) + nx_ * 7
            p2y = y2 - uy * (R_NODE + 5) + ny_ * 7
            out.append(
                f'<path d="M {p1x:.1f} {p1y:.1f} Q {mx:.1f} {my:.1f} {p2x:.1f} {p2y:.1f}" '
                f'fill="none" stroke="{col}" stroke-width="{sw}" marker-end="url(#{mk})"/>'
            )
            lx, ly = (x1 + x2) / 2 + nx_ * 14, (y1 + y2) / 2 + ny_ * 14
        else:
            p1x = x1 + ux * (R_NODE + 2)
            p1y = y1 + uy * (R_NODE + 2)
            p2x = x2 - ux * (R_NODE + 5)
            p2y = y2 - uy * (R_NODE + 5)
            out.append(L(p1x, p1y, p2x, p2y, col, sw, f'marker-end="url(#{mk})"'))
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
            # Small perpendicular nudge for readability
            if (u, v) == (3, 5):
                lx -= 12
                ly -= 6
            elif (u, v) == (3, 4):
                lx -= 8
                ly += 10
            elif (u, v) == (1, 5):
                lx -= 10
                ly -= 10
            elif (u, v) == (3, 6):
                ly -= 13

        w_txt = str(w).replace("-", "−")
        bw = 26 if not is_neg else 32
        bh = 19
        b_fill = CRIMSON_BG if is_neg else (TEAL_BG if is_tree else WHITE)
        b_str = CRIMSON if is_neg else (TEAL if is_tree else RULE)
        t_col = CRIMSON if is_neg else (TEAL if is_tree else SLATE)
        out.append(R(lx - bw / 2, ly - bh / 2, bw, bh, b_fill, b_str, 1.0, rx=4))
        out.append(T(lx, ly + 4.5, w_txt, 11.5, t_col, "middle", "700" if (is_neg or is_tree) else "500"))

    # Draw nodes
    for v, (cx, cy) in pos.items():
        is_tgt = v == target
        n_fill = NAVY if is_tgt else WHITE
        n_str = NAVY if is_tgt else TEAL
        t_fill = WHITE if is_tgt else INK
        out.append(C(cx, cy, R_NODE, n_fill, n_str, 2.4))
        out.append(T(cx, cy + 5.5, str(v), 15, t_fill, "middle", "700"))

        # Distance badge
        dv = dist[v]
        d_txt = f"d={str(dv).replace('-', '−')}"
        dy_off = -34 if coords[v][1] >= 1 else 36
        if v == 3:
            dy_off = -35
        elif v == 6:
            dy_off = -35
        bw = 44 if dv >= 0 else 48
        out.append(R(cx - bw / 2, cy + dy_off - 10, bw, 19, WHITE, NAVY if is_tgt else RULE, 1.0, rx=4))
        out.append(T(cx, cy + dy_off + 3.5, d_txt, 10.5, NAVY if is_tgt else SLATE, "middle", "700"))

    # Minimal bottom legend bar
    out.append(R(20, H - 46, W - 40, 32, WHITE, RULE, 1.0, rx=4))
    out.append(L(34, H - 30, 62, H - 30, TEAL, 2.8, 'marker-end="url(#arr-teal)"'))
    out.append(T(70, H - 26, "Árvore next → 6", 11, INK, "start", "600"))
    out.append(L(206, H - 30, 234, H - 30, CRIMSON, 3.0, 'marker-end="url(#arr-crim)"'))
    out.append(T(242, H - 26, "Aresta negativa 3 → 6 (−4)", 11, CRIMSON, "start", "600"))
    out.append(T(W - 32, H - 26, "exemplo.json · 4 rodadas", 10.5, MUTED, "end"))

    (ASSETS / "fig_01_cover_graph.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 02: Parede de memória (CSR vs FW 12*V^2 em escala log)
# =============================================================================
def gen_fig_02() -> None:
    W, H = 560, 420
    names = ["W_1", "W_2", "W_3", "W_4", "W_5"]
    labels = ["W₁ (25k)", "W₂ (25k)", "W₃ (100k)", "W₄ (1M)", "W₅ (10M)"]

    # Log axis in bytes: 10 MB (1e7) to 3 PB (3e15)
    lo, hi = 6.8, 15.6
    x0, x1 = 104, W - 26
    y0, y1 = 44, H - 56

    def X(val_bytes: float) -> float:
        lv = math.log10(max(val_bytes, 10**lo))
        return x0 + (lv - lo) / (hi - lo) * (x1 - x0)

    out = [R(0, 0, W, H, WHITE, "none")]

    # Grid & ticks
    ticks = [
        (1e7, "10 MB"),
        (1e9, "1 GB"),
        (1e11, "100 GB"),
        (1e13, "10 TB"),
        (1e15, "1 PB"),
    ]
    for val, lbl in ticks:
        xx = X(val)
        out.append(L(xx, y0, xx, y1, HAIR, 1.0))
        out.append(T(xx, y1 + 17, lbl, 10, MUTED, "middle"))
    out.append(T(x1, y1 + 35, "memória necessária (escala log₁₀)", 10, MUTED, "end"))

    # RAM limits: 16 GiB and 36 GiB
    lim_16 = 16 * 1024**3
    ram_36 = DATA["machine"]["memory_bytes"]  # 36 GiB
    # Shaded OOM zone > 36 GiB
    out.append(R(X(ram_36), y0, x1 - X(ram_36), y1 - y0, CRIMSON_BG, "none", extra='fill-opacity="0.45"'))
    out.append(L(X(lim_16), y0, X(lim_16), y1, OCHRE, 1.3, 'stroke-dasharray="4 3"'))
    out.append(L(X(ram_36), y0 - 8, X(ram_36), y1, CRIMSON, 1.8, 'stroke-dasharray="6 4"'))
    out.append(T(X(lim_16) - 4, y0 - 12, "limite 16 GiB", 9.5, OCHRE, "end", "600"))
    out.append(T(X(ram_36) + 5, y0 - 12, "36 GiB RAM (M3 Pro)", 9.5, CRIMSON, "start", "700"))

    row_h = (y1 - y0) / len(names)
    bh = 19
    gap = 4

    for idx, (n, lbl) in enumerate(zip(names, labels)):
        g = G[n]
        csr_b = g["graph_memory_bytes"]
        fw_b = g["floyd_warshall"]["memory_needed_bytes"]
        cy = y0 + idx * row_h + 10

        out.append(T(x0 - 10, cy + bh + 2, lbl, 11.5, INK, "end", "700"))

        # CSR bar
        w_csr = X(csr_b) - x0
        out.append(R(x0, cy, w_csr, bh, TEAL, TEAL, 1.0, rx=2))
        csr_txt = f"{br(csr_b / 1e6, 1)} MB" if csr_b < 1e9 else f"{br(csr_b / 1e9, 2)} GB"
        out.append(T(X(csr_b) + 6, cy + 13.5, csr_txt, 10.5, TEAL, "start", "700"))

        # FW bar
        fy = cy + bh + gap
        w_fw = X(fw_b) - x0
        oom = fw_b > lim_16
        fw_fill = CRIMSON if oom else NAVY
        fw_bg = CRIMSON_BG if oom else NAVY_BG
        out.append(R(x0, fy, w_fw, bh, fw_bg, fw_fill, 1.3, rx=2))
        if fw_b >= 1e15:
            fw_txt = f"{br(fw_b / 1e15, 1)} PB (OOM)"
        elif fw_b >= 1e12:
            fw_txt = f"{br(fw_b / 1e12, 0)} TB (OOM)"
        elif fw_b >= 1e9:
            fw_txt = f"{br(fw_b / 1e9, 1)} GB" + (" (OOM)" if oom else "")
        else:
            fw_txt = f"{br(fw_b / 1e6, 0)} MB"
        # Place label inside if bar crosses/extends near RAM lines, else outside
        if n in ("W_1", "W_2", "W_4", "W_5"):
            out.append(T(X(fw_b) - 8, fy + 13.5, fw_txt, 10.5, fw_fill, "end", "700"))
        else:
            out.append(T(X(fw_b) + 6, fy + 13.5, fw_txt, 10.5, fw_fill, "start", "700"))

        if idx < len(names) - 1:
            out.append(L(x0, y0 + (idx + 1) * row_h, x1, y0 + (idx + 1) * row_h, HAIR, 0.8))

    # Top legend
    out.append(R(x0, 6, 12, 12, TEAL, "none", rx=2))
    out.append(T(x0 + 17, 16, "CSR reverso (backward_)", 10.5, INK, "start", "600"))
    out.append(R(x0 + 175, 6, 12, 12, NAVY_BG, NAVY, 1.2, rx=2))
    out.append(T(x0 + 192, 16, "Matriz FW (12·V²)", 10.5, INK, "start", "600"))
    out.append(R(x0 + 315, 6, 12, 12, CRIMSON_BG, CRIMSON, 1.2, rx=2))
    out.append(T(x0 + 332, 16, "Excede RAM (OOM)", 10.5, CRIMSON, "start", "600"))

    (ASSETS / "fig_02_ram_cliff.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 03: Ciclos negativos em O(V) (W_1) e precisão IEEE-754
# =============================================================================
def gen_fig_03() -> None:
    W, H = 1040, 390
    out = [R(0, 0, W, H, WHITE, "none")]

    # Two panel frames
    p1x, p1w = 0, 560
    p2x, p2w = 584, W - 584
    out.append(R(p1x, 0, p1w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p1x, 0, p1w, 4, NAVY, "none"))
    out.append(R(p2x, 0, p2w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p2x, 0, p2w, 4, OCHRE, "none"))

    # ── Panel A: Detecção O(V) em next_ no W_1 ─────────────────────────────────
    bf1 = G["W_1"]["bellman_ford"]
    cb1 = CB["W_1"]
    cyc = cb1["ciclo_negativo"]
    vA, vB = cyc["vertices"][0], cyc["vertices"][1]
    wAB, wBA = cyc["pesos"][0], cyc["pesos"][1]
    w_sum = cyc["soma"]
    recip = GF["W_1"]["reciprocidade"] * 100

    out.append(T(p1x + 18, 28, "A. Detecção O(V) via selos (stamps) em next_ · W₁", 13.5, NAVY, "start", "700"))
    out.append(
        T(
            p1x + 18,
            47,
            f"Para na rodada {bf1['rounds']} em {fmt_dur(bf1['mean_s'], 2)} ({br_int(cb1['total_arestas_examinadas'])} arestas vs. {br_int(G['W_1']['vertices'] - 1)} rodadas)",
            11,
            SLATE,
            "start",
        )
    )

    # Schematic chain: u0 -> vA <-> vB, plus stamp tracking
    # Node positions inside Panel A
    nx0, nx1, nx2, ny = p1x + 88, p1x + 250, p1x + 455, 165
    # Incoming vertex chasing pointer
    out.append(L(nx0 + 28, ny, nx1 - 36, ny, NAVY, 2.0, 'marker-end="url(#arr-navy)"'))
    out.append(T((nx0 + nx1) / 2 - 4, ny - 10, "next_", 10.5, NAVY, "middle", "600", cls="mono"))

    # 2-cycle between vA (5438) and vB (1268)
    out.append(
        f'<path d="M {nx1 + 26:.1f} {ny - 18:.1f} C {nx1 + 85:.1f} {ny - 88:.1f}, {nx2 - 85:.1f} {ny - 88:.1f}, {nx2 - 28:.1f} {ny - 18:.1f}" '
        f'fill="none" stroke="{CRIMSON}" stroke-width="2.6" marker-end="url(#arr-crim)"/>'
    )
    out.append(
        f'<path d="M {nx2 - 26:.1f} {ny + 18:.1f} C {nx2 - 85:.1f} {ny + 88:.1f}, {nx1 + 85:.1f} {ny + 88:.1f}, {nx1 + 28:.1f} {ny + 18:.1f}" '
        f'fill="none" stroke="{CRIMSON}" stroke-width="2.6" marker-end="url(#arr-crim)"/>'
    )

    # Edge weight pills on cycle
    out.append(R((nx1 + nx2) / 2 - 32, ny - 76, 64, 22, WHITE, CRIMSON, 1.2, rx=4))
    out.append(T((nx1 + nx2) / 2, ny - 61, f"+{br(wAB, 2)}", 11.5, CRIMSON, "middle", "700"))

    out.append(R((nx1 + nx2) / 2 - 32, ny + 56, 64, 22, WHITE, CRIMSON, 1.2, rx=4))
    out.append(T((nx1 + nx2) / 2, ny + 71, f"{br(wBA, 2).replace('-', '−')}", 11.5, CRIMSON, "middle", "700"))

    # Nodes
    out.append(C(nx0, ny, 26, WHITE, NAVY, 2.0))
    out.append(T(nx0, ny + 4, "início", 11, NAVY, "middle", "700"))
    out.append(R(nx0 - 38, ny + 34, 76, 20, NAVY_BG, NAVY, 0.9, rx=3))
    out.append(T(nx0, ny + 48, "stamp = w", 10, NAVY, "middle", "600", cls="mono"))

    out.append(C(nx1, ny, 31, CRIMSON_BG, CRIMSON, 2.4))
    out.append(T(nx1, ny + 5, str(vA), 13, INK, "middle", "700"))
    out.append(R(nx1 - 48, ny + 39, 96, 20, WHITE, CRIMSON, 1.0, rx=3))
    out.append(T(nx1, ny + 53, "stamp == w!", 10, CRIMSON, "middle", "700", cls="mono"))

    out.append(C(nx2, ny, 31, CRIMSON_BG, CRIMSON, 2.4))
    out.append(T(nx2, ny + 5, str(vB), 13, INK, "middle", "700"))
    out.append(R(nx2 - 38, ny + 39, 76, 20, WHITE, RULE, 1.0, rx=3))
    out.append(T(nx2, ny + 53, "stamp = w", 10, SLATE, "middle", "600", cls="mono"))

    # Cycle sum badge in center
    out.append(R((nx1 + nx2) / 2 - 64, ny - 13, 128, 26, CRIMSON, "none", rx=4))
    out.append(T((nx1 + nx2) / 2, ny + 4, f"soma = {br(w_sum, 2).replace('-', '−')} < 0", 11.5, WHITE, "middle", "700"))

    # Stat callout box at bottom of Panel A
    out.append(R(p1x + 18, 266, p1w - 36, 106, WHITE, RULE, 1.0, rx=4))
    out.append(T(p1x + 32, 290, "Estrutura do grafo W₁ (25.000 vértices · 549.953 arestas)", 11.5, INK, "start", "700"))
    out.append(
        T(
            p1x + 32,
            312,
            f"• {br(recip, 1)}% das arestas têm inversa; {br_int(W1C['ciclos_negativos_2'])} ciclos negativos de 2 arestas.",
            11,
            SLATE,
            "start",
        )
    )
    out.append(
        T(
            p1x + 32,
            332,
            f"• has_cycle visita apenas {br_int(cb1['total_visitas_busca_ciclo'])} nós até fechar na rodada {bf1['rounds']}.",
            11,
            SLATE,
            "start",
        )
    )
    out.append(
        T(
            p1x + 32,
            354,
            "• W₁ é fortemente conexo: todo par possui distância −∞ até o destino 100.",
            11,
            CRIMSON,
            "start",
            "700",
        )
    )

    # ── Panel B: Armadilha IEEE-754 ────────────────────────────────────────────
    out.append(T(p2x + 18, 28, "B. Armadilha IEEE-754 em ponto flutuante", 13.5, OCHRE, "start", "700"))
    out.append(T(p2x + 18, 47, "Ciclo de soma exata 0 pode parecer negativo por 1 ulp em double", 11, SLATE, "start"))

    # Top sub-box: without tolerance
    bx, bw = p2x + 18, p2w - 36
    out.append(R(bx, 68, bw, 118, WHITE, CRIMSON, 1.2, rx=4))
    out.append(R(bx, 68, 125, 22, CRIMSON_BG, "none"))
    out.append(T(bx + 10, 83, "SEM TOLERÂNCIA", 10, CRIMSON, "start", "700"))
    out.append(T(bx + 135, 83, "d[u] > d[v] + w  (comparação exata)", 10.5, SLATE, "start", cls="mono"))

    out.append(T(bx + 14, 112, "Ciclo decimal de soma 0:  +0,1  +0,2  −0,3", 11.5, INK, "start", "600"))
    out.append(T(bx + 14, 134, "Em IEEE-754 binary64:  (0.1 + 0.2) − 0.3 = +5,55×10⁻¹⁷ ≠ 0", 10.5, CRIMSON, "start", "600", cls="mono"))
    out.append(T(bx + 14, 156, "→ melhora espúria de 1 ulp cria laço em next_ / parent", 11, SLATE, "start"))
    out.append(T(bx + 14, 174, "→ falso ciclo negativo ou loop infinito ao reconstruir caminho!", 11, CRIMSON, "start", "700"))

    # Bottom sub-box: with tolerance
    out.append(R(bx, 204, bw, 168, WHITE, TEAL, 1.3, rx=4))
    out.append(R(bx, 204, 135, 22, TEAL_BG, "none"))
    out.append(T(bx + 10, 219, "SOLUÇÃO NO CÓDIGO", 10, TEAL, "start", "700"))
    out.append(T(bx + 145, 219, "candidate < dist[u] − tolerance", 10.5, TEAL, "start", "700", cls="mono"))

    out.append(R(bx + 14, 238, bw - 28, 34, SOFT, RULE, 1.0, rx=3))
    out.append(T(bx + bw / 2, 260, "tolerance = 8 · ε · V · max|w|", 13, NAVY, "middle", "700", cls="mono"))

    out.append(T(bx + 14, 294, "• Garante por lema que todo ciclo em next_ tem soma < 0 real.", 11, INK, "start"))
    out.append(T(bx + 14, 315, "• Limite no W₅ (V = 10⁷, max|w| = 10): tol ≈ 1,8×10⁻⁷ << 10⁻².", 11, SLATE, "start"))
    out.append(T(bx + 14, 336, "• Elimina laços falsos na árvore next_ sem perder precisão", 11, TEAL, "start", "700"))
    out.append(T(bx + 24, 354, "nas distâncias finais dos caminhos mínimos.", 11, SLATE, "start"))

    (ASSETS / "fig_03_cycle_precision.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 04: Todos os pares — BF vs FW (W_2 medido + W_3..W_5 escala log)
# =============================================================================
def gen_fig_04() -> None:
    W, H = 1040, 390
    out = [R(0, 0, W, H, WHITE, "none")]

    # Zone A (left, 390px): W_2 measured
    zax, zaw = 0, 388
    zbx, zbw = 412, W - 412

    out.append(R(zax, 0, zaw, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(zax, 0, zaw, 4, TEAL, "none"))
    out.append(R(zbx, 0, zbw, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(zbx, 0, zbw, 4, NAVY, "none"))

    # ── Zone A: Medido no W_2 ─────────────────────────────────────────────────
    out.append(T(zax + 18, 28, "A. Medido no W₂ (25.000 vértices)", 13.5, TEAL, "start", "700"))
    out.append(T(zax + 18, 47, "Todos os 25.000 destinos · escala linear", 11, SLATE, "start"))

    bf2_11 = G["W_2"]["all_pairs_bf"]["mean_s"]
    fw2_11 = G["W_2"]["floyd_warshall"]["mean_s"]
    bf2_1t = float(parse_bench(BENCH / "p3_W_2.bf_1thread_amostra.txt")["bellman_ford_todos_pares"]["media_s"])
    ratio_w2 = fw2_11 / bf2_11

    bars_a = [
        ("BF · 11 threads", bf2_11, TEAL, TEAL_BG, f"{br(bf2_11, 1)} s", "13× mais rápido"),
        ("BF · 1 thread (amostra)", bf2_1t, TEAL, WHITE, f"{br(bf2_1t, 1)} s", "ainda bate FW 11T!"),
        ("FW · 11 threads (blocos)", fw2_11, NAVY, NAVY_BG, f"{br(fw2_11, 1)} s", "referência V³"),
    ]
    ax0, ax1 = zax + 20, zax + zaw - 24
    max_a = 560.0
    for idx, (lbl, val, col, bg, tstr, note) in enumerate(bars_a):
        yy = 82 + idx * 90
        out.append(T(ax0, yy, lbl, 11.5, INK, "start", "700"))
        out.append(T(ax1, yy, note, 10.5, col if idx < 2 else MUTED, "end", "600"))
        bw_max = ax1 - ax0
        bw_val = val / max_a * bw_max
        out.append(R(ax0, yy + 9, bw_max, 30, WHITE, HAIR, 1.0, rx=3))
        out.append(R(ax0, yy + 9, bw_val, 30, bg, col, 1.8, rx=3))
        if bw_val > 75:
            out.append(T(ax0 + bw_val - 8, yy + 29, tstr, 12, col, "end", "700"))
        else:
            out.append(T(ax0 + bw_val + 8, yy + 29, tstr, 12, col, "start", "700"))

    # Callout badge
    out.append(R(zax + 18, H - 52, zaw - 36, 36, WHITE, TEAL, 1.2, rx=4))
    out.append(T(zax + zaw / 2, H - 30, f"Mesmo com 11 threads, BF é {br(ratio_w2, 1)}× mais rápido que FW", 11.5, TEAL, "middle", "700"))

    # ── Zone B: Escala assintótica W_3..W_5 (log) ─────────────────────────────
    out.append(T(zbx + 18, 28, "B. Escala assintótica W₃–W₅ (escala log₁₀)", 13.5, NAVY, "start", "700"))
    out.append(T(zbx + 18, 47, "Barras hachuradas = estimativa (BF em 1T por amostra vs. FW em 11T por V³)", 11, SLATE, "start"))

    bx0, bx1 = zbx + 128, zbx + zbw - 24
    by0, by1 = 76, H - 58
    lo_s, hi_s = 3.0, 11.3  # 10^3 s (~16 min) to 2*10^11 s (~6300 anos)

    def XB(sec: float) -> float:
        return bx0 + (math.log10(sec) - lo_s) / (hi_s - lo_s) * (bx1 - bx0)

    ticks_b = [
        (3600, "1 h"),
        (86400, "1 dia"),
        (365 * 86400, "1 ano"),
        (1000 * 365 * 86400, "1.000 anos"),
    ]
    for sec, tlbl in ticks_b:
        xx = XB(sec)
        out.append(L(xx, by0, xx, by1, HAIR, 1.0))
        out.append(T(xx, by1 + 17, tlbl, 10, MUTED, "middle"))

    g_list = [("W_3", "W₃ (100k)"), ("W_4", "W₄ (1M)"), ("W_5", "W₅ (10M)")]
    row_hb = (by1 - by0) / len(g_list)
    bh_b = 26

    for idx, (gn, glbl) in enumerate(g_list):
        g = G[gn]
        bf_1t = g["all_pairs_bf"]["mean_s"]
        fw_11t = fw2_11 * (g["vertices"] / G["W_2"]["vertices"]) ** 3
        # Equal-thread ratio (11T vs 11T, matching report/parte3/tabelas.py):
        ratio_eq = fw_11t / (bf_1t / 11.0)
        ry = by0 + idx * row_hb + 10

        out.append(T(zbx + 18, ry + 26, glbl, 12, INK, "start", "700"))
        out.append(T(zbx + 18, ry + 43, f"razão eq. 11T: {sig_br(ratio_eq, 2)}×", 9.8, TEAL, "start", "700"))

        # BF bar (1T estim.)
        w_bf = XB(bf_1t) - bx0
        out.append(R(bx0, ry, w_bf, bh_b, "url(#hatch-teal)", TEAL, 1.4, rx=2))
        bf_lbl = f"~{fmt_dur(bf_1t, 2)} (BF 1T)"
        out.append(T(XB(bf_1t) + 7, ry + 17.5, bf_lbl, 10.5, TEAL, "start", "700"))

        # FW bar (11T estim.)
        fy = ry + bh_b + 5
        w_fw = XB(fw_11t) - bx0
        out.append(R(bx0, fy, w_fw, bh_b, "url(#hatch-navy)", NAVY, 1.4, rx=2))
        fw_lbl = f"~{fmt_dur(fw_11t, 2)} (FW 11T)"
        if XB(fw_11t) > bx1 - 125:
            out.append(T(XB(fw_11t) - 8, fy + 17.5, fw_lbl, 10.5, NAVY, "end", "700"))
        else:
            out.append(T(XB(fw_11t) + 7, fy + 17.5, fw_lbl, 10.5, NAVY, "start", "700"))

        if idx < len(g_list) - 1:
            out.append(L(zbx + 18, by0 + (idx + 1) * row_hb, bx1, by0 + (idx + 1) * row_hb, HAIR, 0.9))

    out.append(
        T(
            zbx + 18,
            H - 14,
            "BF 1T medido em amostras de 200 (W₃), 30 (W₄) e 10 (W₅) destinos; razão 11T assume escala linear conservadora p/ BF.",
            9.5,
            MUTED,
            "start",
        )
    )

    (ASSETS / "fig_04_apsp_times.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 03B: Como o Bellman-Ford evita trabalho inútil (lista de ativos + onda W_2)
# =============================================================================
def gen_fig_03_bf_ativos() -> None:
    W, H = 1040, 390
    out = [R(0, 0, W, H, WHITE, "none")]

    p1x, p1w = 0, 500
    p2x, p2w = 524, W - 524
    out.append(R(p1x, 0, p1w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p1x, 0, p1w, 4, NAVY, "none"))
    out.append(R(p2x, 0, p2w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p2x, 0, p2w, 4, TEAL, "none"))

    # ── Panel A: O que é Lista de Ativos + Parada Antecipada ─────────────────
    out.append(T(p1x + 18, 28, "A. As duas otimizações do Bellman-Ford", 13.5, NAVY, "start", "700"))
    out.append(T(p1x + 18, 47, "Por que não precisamos varrer todas as E arestas em V−1 rodadas", 11, SLATE, "start"))

    # Card 1: Clássico
    out.append(R(p1x + 18, 66, p1w - 36, 90, WHITE, RULE, 1.0, rx=5))
    out.append(R(p1x + 18, 66, 4.5, 90, CRIMSON, "none"))
    out.append(T(p1x + 34, 88, "BF Clássico (sem otimizações)", 12, CRIMSON, "start", "700"))
    out.append(T(p1x + 34, 108, "• Roda todas as V − 1 rodadas fixas (24.999 no W₂).", 10.8, SLATE, "start"))
    out.append(T(p1x + 34, 126, "• Testa TODAS as E arestas toda rodada, mesmo sem mudança.", 10.8, SLATE, "start"))
    out.append(T(p1x + 34, 144, "→ 20,6 bilhões de relaxações por destino no W₂!", 10.8, CRIMSON, "start", "700"))

    # Card 2: Lista de Ativos
    out.append(R(p1x + 18, 170, p1w - 36, 114, WHITE, RULE, 1.0, rx=5))
    out.append(R(p1x + 18, 170, 4.5, 114, TEAL, "none"))
    out.append(T(p1x + 34, 192, "1. Lista de ativos (fronteira que realmente mudou)", 12, TEAL, "start", "700"))
    out.append(T(p1x + 34, 212, "• Se a distância de v não melhorou na rodada r, relaxar", 10.8, SLATE, "start"))
    out.append(T(p1x + 42, 228, "suas arestas de entrada u → v na rodada r + 1 é inútil.", 10.8, SLATE, "start"))
    out.append(T(p1x + 34, 248, "• Guardamos em active[] só quem melhorou (bitmask evita", 10.8, INK, "start", "600"))
    out.append(T(p1x + 42, 264, "duplicatas) e varremos só backward_[v] na próxima rodada.", 10.8, INK, "start", "600"))

    # Card 3: Parada Antecipada
    out.append(R(p1x + 18, 298, p1w - 36, 74, WHITE, RULE, 1.0, rx=5))
    out.append(R(p1x + 18, 298, 4.5, 74, NAVY, "none"))
    out.append(T(p1x + 34, 320, "2. Parada antecipada", 12, NAVY, "start", "700"))
    out.append(T(p1x + 34, 340, "• Quando active[] fica vazia, nenhuma distância pode mais", 10.8, SLATE, "start"))
    out.append(T(p1x + 42, 356, "diminuir → encerra na rodada 24 (em vez de 24.999)!", 10.8, NAVY, "start", "700"))

    # ── Panel B: Onda de vértices ativos no W_2 ──────────────────────────────
    rodadas = CB["W_2"]["rodadas"]
    ativos = [r["ativos"] for r in rodadas]
    n_r = len(rodadas)
    v2 = G["W_2"]["vertices"]
    peak_i = max(range(n_r), key=ativos.__getitem__)
    peak_v = ativos[peak_i]
    peak_pct = round(100 * peak_v / v2)
    hops = GF["W_2"]["saltos_ate_100"]

    out.append(T(p2x + 18, 28, "B. A lista de ativos em ação no W₂ (destino 100)", 13.5, TEAL, "start", "700"))
    out.append(T(p2x + 18, 47, f"Começa em 1 vértice (100), sobe a {br_int(peak_v)} ({peak_pct}%) e zera na rodada {n_r}", 11, SLATE, "start"))

    ax0, ax1 = p2x + 62, p2x + p2w - 22
    ay0, ay1 = 74, H - 56
    ymax_a = 22000.0

    def XA(r_idx: int) -> float:
        return ax0 + r_idx / (n_r - 1) * (ax1 - ax0)

    def YA(val: float) -> float:
        return ay1 - val / ymax_a * (ay1 - ay0)

    for yv, ylbl in ((0, "0"), (5000, "5k"), (10000, "10k"), (15000, "15k"), (20000, "20k")):
        yy = YA(yv)
        out.append(L(ax0, yy, ax1, yy, HAIR if yv > 0 else RULE, 1.0))
        out.append(T(ax0 - 8, yy + 3.5, ylbl, 10, MUTED, "end"))

    for r_num in (1, 4, 7, 12, 18, 24):
        xx = XA(r_num - 1)
        out.append(T(xx, ay1 + 16, str(r_num), 10, MUTED, "middle"))
    out.append(T(ax1, ay1 + 34, "rodada do Bellman-Ford", 10, MUTED, "end"))

    xh = XA(hops - 1)
    out.append(L(xh, ay0 + 22, xh, ay1, NAVY, 1.2, 'stroke-dasharray="4 3"'))

    pts = " ".join(f"{XA(i):.1f},{YA(v):.1f}" for i, v in enumerate(ativos))
    out.append(f'<polygon points="{XA(0):.1f},{YA(0):.1f} {pts} {XA(n_r - 1):.1f},{YA(0):.1f}" fill="{TEAL_BG}" stroke="none"/>')
    out.append(f'<polyline points="{pts}" fill="none" stroke="{TEAL}" stroke-width="2.6"/>')
    out.append(T(xh + 6, ay1 - 12, f"{hops} saltos (sem peso)", 9.6, NAVY, "start", "700"))
    out.append(C(XA(peak_i), YA(peak_v), 5.0, TEAL, WHITE, 1.5))
    out.append(R(XA(peak_i) + 12, YA(peak_v) - 10, 194, 38, WHITE, TEAL, 1.0, rx=4))
    out.append(T(XA(peak_i) + 20, YA(peak_v) + 5, f"pico: {br_int(peak_v)} ativos ({peak_pct}%)", 10.5, TEAL, "start", "700"))
    out.append(T(XA(peak_i) + 20, YA(peak_v) + 20, f"média total: só 3,6 passagens em E", 9.6, SLATE, "start"))

    # End point badge at round 24
    out.append(C(XA(n_r - 1), YA(0), 4.5, NAVY, WHITE, 1.5))
    out.append(T(XA(n_r - 1) - 6, YA(0) - 12, "active = ∅ (para!)", 9.8, NAVY, "end", "700"))

    (ASSETS / "fig_03_bf_ativos.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 05: Por que 211x menos operações viram 13x no relógio (2 PAINÉIS LIMPOS!)
# =============================================================================
def gen_fig_05() -> None:
    W, H = 1040, 390
    V2 = G["W_2"]["vertices"]
    E2 = G["W_2"]["edges"]
    tp2 = CB["W_2"]["todos_os_pares"]
    rod_m = tp2["rodadas_media"]
    exam_m = tp2["arestas_examinadas_media"]
    pass_m = tp2["passagens_por_E_media"]

    bf_s = G["W_2"]["all_pairs_bf"]["mean_s"]
    fw_s = G["W_2"]["floyd_warshall"]["mean_s"]
    fw_ns = fw_s * 11 / (V2**3) * 1e9
    bf_ns = bf_s * 11 / tp2["arestas_examinadas_total_extrapolado"] * 1e9

    ops_bf_worst = (V2 - 1) * E2  # 20.62 bi
    ops_fw = V2**2  # 625 mi
    ops_bf_opt = exam_m  # 2.97 mi
    ratio_ops = ops_fw / ops_bf_opt  # 210.8
    ratio_ns = bf_ns / fw_ns  # 16.1
    ratio_time = fw_s / bf_s  # 13.1

    out = [R(0, 0, W, H, WHITE, "none")]

    p1x, p1w = 0, 560
    p2x, p2w = 584, W - 584
    panel_h = 312
    out.append(R(p1x, 0, p1w, panel_h, SOFT, RULE, 1.0, rx=4))
    out.append(R(p1x, 0, p1w, 4, TEAL, "none"))
    out.append(R(p2x, 0, p2w, panel_h, SOFT, RULE, 1.0, rx=4))
    out.append(R(p2x, 0, p2w, 4, OCHRE, "none"))

    # ── Panel A: Volume de operações (3 barras limpas em escala log) ─────────
    out.append(T(p1x + 18, 28, "A. Quantas relaxações cada algoritmo faz (por destino)", 13.2, TEAL, "start", "700"))
    out.append(T(p1x + 18, 46, f"Escala log₁₀ no W₂ — parada ({br(rod_m, 1)} rod.) + ativos ({br(pass_m, 2)}×E) cortam 6.950×", 10.8, SLATE, "start"))

    ax0, ax1 = p1x + 158, p1x + p1w - 115
    ay0, ay1 = 74, panel_h - 40
    lo_o, hi_o = math.log10(1e6), math.log10(4e10)

    def XO(v: float) -> float:
        return ax0 + (math.log10(v) - lo_o) / (hi_o - lo_o) * (ax1 - ax0)

    for tv, tlbl in ((1e6, "1M"), (1e7, "10M"), (1e8, "100M"), (1e9, "1 bi"), (1e10, "10 bi")):
        xx = XO(tv)
        out.append(L(xx, ay0, xx, ay1, HAIR if tv > 1e6 else RULE, 1.0))
        out.append(T(xx, ay1 + 16, tlbl, 9.8, MUTED, "middle"))

    bars_a = [
        ("BF pior caso", "(V−1)·E", ops_bf_worst, CRIMSON, CRIMSON_BG, f"{br(ops_bf_worst / 1e9, 1)} bi", "33× mais que FW"),
        ("Floyd-Warshall", "V² fixo", ops_fw, NAVY, NAVY_BG, f"{br(ops_fw / 1e6, 0)} mi", "base (1×)"),
        ("BF otimizado", "parada + ativos", ops_bf_opt, TEAL, TEAL_BG, f"{br(ops_bf_opt / 1e6, 2)} mi", f"{br(ratio_ops, 0)}× menos que FW!"),
    ]
    rh_a = (ay1 - ay0) / 3
    for i, (lbl, sub, val, col, bg, vtxt, note) in enumerate(bars_a):
        ry = ay0 + i * rh_a + 14
        bh = 34
        out.append(T(ax0 - 12, ry + 14, lbl, 11.8, INK, "end", "700"))
        out.append(T(ax0 - 12, ry + 29, sub, 9.8, SLATE, "end"))
        bw = max(XO(val) - ax0, 8)
        out.append(R(ax0, ry, bw, bh, bg, col, 1.8, rx=3))
        out.append(T(ax0 + bw + 8, ry + 14, vtxt, 12, col, "start", "700"))
        out.append(T(ax0 + bw + 8, ry + 29, note, 9.8, col if i == 2 else SLATE, "start", "700" if i == 2 else "400"))

    # ── Panel B: Custo por operação (2 barras lineares limpas) ───────────────
    out.append(T(p2x + 18, 28, "B. Quanto custa 1 relaxação na CPU", 13.2, OCHRE, "start", "700"))
    out.append(T(p2x + 18, 46, "Acesso sequencial L1/NEON vs. saltos aleatórios em CSR", 10.8, SLATE, "start"))

    bx0, bx1 = p2x + 132, p2x + p2w - 92
    by0, by1 = 84, panel_h - 46

    def XB(v: float) -> float:
        return bx0 + v / 6.5 * (bx1 - bx0)

    for tv in (0, 2, 4, 6):
        xx = XB(tv)
        out.append(L(xx, by0, xx, by1, HAIR if tv > 0 else RULE, 1.0))
        out.append(T(xx, by1 + 16, f"{tv} ns", 9.8, MUTED, "middle"))

    bars_b = [
        ("Floyd-Warshall", "blocos L1 + NEON", fw_ns, NAVY, NAVY_BG, f"{br(fw_ns, 2)} ns", "contíguo"),
        ("Bellman-Ford", "CSR aleatório", bf_ns, OCHRE, OCHRE_BG, f"{br(bf_ns, 2)} ns", f"{br(ratio_ns, 0)}× mais caro!"),
    ]
    rh_b = (by1 - by0) / 2
    for i, (lbl, sub, val, col, bg, vtxt, note) in enumerate(bars_b):
        ry = by0 + i * rh_b + 18
        bh = 40
        out.append(T(bx0 - 12, ry + 17, lbl, 11.8, INK, "end", "700"))
        out.append(T(bx0 - 12, ry + 32, sub, 9.8, SLATE, "end"))
        bw = max(XB(val) - bx0, 12)
        out.append(R(bx0, ry, bw, bh, bg, col, 1.8, rx=3))
        out.append(T(bx0 + bw + 8, ry + 17, vtxt, 12.2, col, "start", "700"))
        out.append(T(bx0 + bw + 8, ry + 33, note, 10, col if i == 1 else SLATE, "start", "700" if i == 1 else "400"))

    # ── Bottom Equation Strip connecting A and B ─────────────────────────────
    out.append(R(0, 328, W, 56, WHITE, NAVY, 1.4, rx=5))
    out.append(R(0, 328, 6, 56, NAVY, "none"))
    out.append(
        T(
            W / 2,
            352,
            f"Resultado no relógio (W₂ · 11 threads):   {br(ratio_ops, 0)}× menos operações  ÷  {br(ratio_ns, 1)}× mais caro por operação  ≈  {br(ratio_time, 1)}× mais rápido",
            12.8,
            INK,
            "middle",
            "700",
        )
    )
    out.append(
        T(
            W / 2,
            372,
            f"Bellman-Ford: {br(bf_s, 1)} s   vs.   Floyd-Warshall: {br(fw_s, 1)} s  —  a esparsidade algorítmica vence a eficiência bruta de hardware",
            10.8,
            TEAL,
            "middle",
            "600",
        )
    )

    (ASSETS / "fig_05_waterfall.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 06: Estouro de cache W_2 -> W_5 (2 painéis limpos e espaçosos!)
# =============================================================================
def gen_fig_06() -> None:
    W, H = 1040, 390
    out = [R(0, 0, W, H, WHITE, "none")]

    p1x, p1w = 0, 505
    p2x, p2w = 530, W - 530
    out.append(R(p1x, 0, p1w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p1x, 0, p1w, 4, NAVY, "none"))
    out.append(R(p2x, 0, p2w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p2x, 0, p2w, 4, CRIMSON, "none"))

    gnames = ["W_2", "W_3", "W_4", "W_5"]
    glabels = [("W₂", "0,3 MB"), ("W₃", "1,2 MB"), ("W₄", "12 MB"), ("W₅", "120 MB")]

    # ── Panel A: ns / aresta crescendo 14,6x ao estourar cache ───────────────
    out.append(T(p1x + 18, 28, "A. Custo por aresta relaxada (sem busca de ciclo)", 13.5, NAVY, "start", "700"))
    out.append(T(p1x + 18, 47, "Quando dist + next (12·V B) sai do cache L2 (16 MiB), custo sobe 14,6×", 11, SLATE, "start"))

    ax0, ax1 = p1x + 64, p1x + p1w - 24
    ay0, ay1 = 76, H - 58
    slot_a = (ax1 - ax0) / 4

    def YA(v: float) -> float:
        return ay1 - v / 42.0 * (ay1 - ay0)

    for tv in (0, 10, 20, 30, 40):
        yy = YA(tv)
        out.append(L(ax0, yy, ax1, yy, HAIR if tv > 0 else RULE, 1.0))
        out.append(T(ax0 - 8, yy + 3.5, f"{tv} ns", 10, MUTED, "end"))

    l2_xa = ax0 + 2.95 * slot_a
    out.append(L(l2_xa, ay0 - 4, l2_xa, ay1, OCHRE, 1.4, 'stroke-dasharray="4 3"'))
    out.append(T(l2_xa - 6, ay0 + 10, "L2 = 16 MiB", 9.8, OCHRE, "end", "700"))

    for i, (gn, (gl, gsz)) in enumerate(zip(gnames, glabels)):
        ns_e = BS[gn]["ns_por_aresta_sem_busca"]
        cx = ax0 + (i + 0.5) * slot_a
        bw = 54
        bh = ay1 - YA(ns_e)
        col = CRIMSON if i == 3 else NAVY
        bg = CRIMSON_BG if i == 3 else NAVY_BG
        out.append(R(cx - bw / 2, YA(ns_e), bw, bh, bg, col, 1.6, rx=3))
        out.append(T(cx, YA(ns_e) - 8, f"{br(ns_e, 2)} ns", 11, col, "middle", "700"))
        out.append(T(cx, ay1 + 17, gl, 11.5, INK, "middle", "700"))
        out.append(T(cx, ay1 + 32, gsz, 9.6, MUTED, "middle"))

    out.append(R(ax0 + 12, ay0 + 22, 224, 42, WHITE, NAVY, 1.0, rx=4))
    out.append(T(ax0 + 22, ay0 + 38, "Salto W₂ → W₅:  2,51 → 36,71 ns", 10.8, NAVY, "start", "700"))
    out.append(T(ax0 + 22, ay0 + 54, "14,6× mais lento por aresta (RAM)", 9.8, SLATE, "start"))

    # ── Panel B: Fração do tempo gasta em has_cycle ──────────────────────────
    out.append(T(p2x + 18, 28, "B. Peso da busca de ciclo (has_cycle em next_)", 13.5, CRIMSON, "start", "700"))
    out.append(T(p2x + 18, 47, "Perseguir ponteiros aleatórios em 120 MB consome 1/3 do tempo no W₅", 11, SLATE, "start"))

    bx0, bx1 = p2x + 64, p2x + p2w - 24
    by0, by1 = 76, H - 58
    slot_b = (bx1 - bx0) / 4

    def YB(v: float) -> float:
        return by1 - v / 42.0 * (by1 - by0)

    for tv in (0, 10, 20, 30, 40):
        yy = YB(tv)
        out.append(L(bx0, yy, bx1, yy, HAIR if tv > 0 else RULE, 1.0))
        out.append(T(bx0 - 8, yy + 3.5, f"{tv}%", 10, MUTED, "end"))

    l2_xb = bx0 + 2.95 * slot_b
    out.append(L(l2_xb, by0 - 4, l2_xb, by1, OCHRE, 1.4, 'stroke-dasharray="4 3"'))
    out.append(T(l2_xb - 6, by0 + 10, "L2 = 16 MiB", 9.8, OCHRE, "end", "700"))

    for i, (gn, (gl, gsz)) in enumerate(zip(gnames, glabels)):
        b = BS[gn]
        frac = b["fracao_busca"] * 100.0
        cx = bx0 + (i + 0.5) * slot_b
        bw = 54
        bh = by1 - YB(frac)
        col = CRIMSON if i == 3 else TEAL
        bg = CRIMSON_BG if i == 3 else TEAL_BG
        out.append(R(cx - bw / 2, YB(frac), bw, bh, bg, col, 1.6, rx=3))
        out.append(T(cx, YB(frac) - 8, f"{br(frac, 1)}%", 11, col, "middle", "700"))
        out.append(T(cx, by1 + 17, gl, 11.5, INK, "middle", "700"))
        out.append(T(cx, by1 + 32, gsz, 9.6, MUTED, "middle"))

    b5 = BS["W_5"]
    f5_str = br(b5["fracao_busca"] * 100.0, 1)
    out.append(R(bx0 + 12, by0 + 22, 234, 42, WHITE, CRIMSON, 1.0, rx=4))
    out.append(T(bx0 + 22, by0 + 38, f"W₅: {br(b5['busca_s']['min'], 2)} s de {br(b5['completo_s']['min'], 2)} s ({f5_str}%)", 10.6, CRIMSON, "start", "700"))
    out.append(T(bx0 + 22, by0 + 54, "91,7M saltos em next_ · 27,5 ns/visita", 9.8, SLATE, "start"))

    (ASSETS / "fig_06_wave_cache.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 07: JOHNSON — POR QUE SOMAR +C FALHA vs. POTENCIAL h (3 PAINÉIS CLAROS!)
# =============================================================================
def gen_fig_07() -> None:
    W, H = 1040, 392
    out = [R(0, 0, W, H, WHITE, "none")]

    cw = 332
    gap = 22
    xs = [0, cw + gap, 2 * (cw + gap)]
    top_h = 294

    def draw_panel_tri(px: float, title: str, sub: str, accent: str, edges_w: dict, h_vals: dict | None, win_edges: set, win_lbl: str, alt_lbl: str, verdict: str, verdict_col: str) -> None:
        out.append(R(px, 0, cw, top_h, SOFT, RULE, 1.0, rx=5))
        out.append(R(px, 0, cw, 4.5, accent, "none"))
        out.append(T(px + 16, 28, title, 12.6, accent, "start", "700"))
        out.append(T(px + 16, 46, sub, 10.4, SLATE, "start"))

        # Triangle coordinates centered in panel
        pts = {"A": (px + 72, 186), "B": (px + cw / 2, 92), "C": (px + cw - 72, 186)}
        for (u, v), wval in edges_w.items():
            x1, y1 = pts[u]
            x2, y2 = pts[v]
            dx, dy = x2 - x1, y2 - y1
            d = math.hypot(dx, dy)
            ux, uy = dx / d, dy / d
            is_neg = wval < 0
            is_win = (u, v) in win_edges
            col = CRIMSON if is_neg else (verdict_col if is_win else MUTED)
            mk = "arr-crim" if is_neg else ("arr-teal" if col == TEAL else ("arr-ink" if col == MUTED else "arr-crim"))
            sw = 2.6 if (is_neg or is_win) else 1.6
            out.append(L(x1 + ux * 20, y1 + uy * 20, x2 - ux * 22, y2 - uy * 22, col, sw, f'marker-end="url(#{mk})"'))
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            nx_, ny_ = (-24, -6) if (u, v) == ("A", "B") else ((24, -6) if (u, v) == ("B", "C") else (0, 20))
            w_s = str(wval).replace("-", "−")
            out.append(R(mx + nx_ - 16, my + ny_ - 11, 32, 20, WHITE, col, 1.1, rx=3))
            out.append(T(mx + nx_, my + ny_ + 3, w_s, 11.5, col, "middle", "700"))

        for node, (cx, cy) in pts.items():
            out.append(C(cx, cy, 18, WHITE, INK, 2.0))
            out.append(T(cx, cy + 4.5, node, 12.5, INK, "middle", "700"))
            if h_vals is not None:
                hv = str(h_vals[node]).replace("-", "−")
                hy = cy - 26 if node == "B" else cy + 31
                out.append(T(cx, hy, f"h={hv}", 10.2, OCHRE, "middle", "700"))

        # Bottom summary box inside card
        out.append(R(px + 14, 224, cw - 28, 58, WHITE, verdict_col, 1.1, rx=4))
        out.append(T(px + 24, 243, win_lbl, 10.6, INK, "start", "700"))
        out.append(T(px + 24, 259, alt_lbl, 10.2, SLATE, "start"))
        out.append(T(px + 24, 275, verdict, 10.5, verdict_col, "start", "700"))

    # Panel 1: Original
    draw_panel_tri(
        xs[0],
        "1. Grafo original (peso negativo)",
        "Dijkstra falha na aresta B → C = −2",
        NAVY,
        {("A", "B"): 2, ("B", "C"): -2, ("A", "C"): 1},
        None,
        {("A", "B"), ("B", "C")},
        "A → B → C:  2 + (−2) = 0   (2 arestas)",
        "A → C:      1               (1 aresta)",
        "✓ Mínimo real é A → B → C (custo 0)",
        TEAL,
    )

    # Panel 2: Naive +2 shift (FAILS!)
    draw_panel_tri(
        xs[1],
        "2. Somar +2 em toda aresta (FALHA!)",
        "Penaliza caminhos com mais arestas",
        CRIMSON,
        {("A", "B"): 4, ("B", "C"): 0, ("A", "C"): 3},
        None,
        {("A", "C")},
        "A → B → C:  4 + 0 = 4   (+4 por 2 arestas!)",
        "A → C:      3           (+2 por 1 aresta)",
        "× ERRO: inverteu o mínimo para A → C!",
        CRIMSON,
    )

    # Panel 3: Johnson potential reweighting (WORKS!)
    draw_panel_tri(
        xs[2],
        "3. Potencial h de Johnson (CORRETO)",
        "w'(u,v) = w(u,v) + h(v) − h(u) ≥ 0",
        TEAL,
        {("A", "B"): 0, ("B", "C"): 0, ("A", "C"): 1},
        {"A": 0, "B": -2, "C": 0},
        {("A", "B"), ("B", "C")},
        "A → B → C:  0 + 0 = 0   (+h(B)−h(B) cancela!)",
        "A → C:      1           (mesmo +h(C)−h(A))",
        "✓ Pesos ≥ 0 e ordem 100% preservada!",
        TEAL,
    )

    # Bottom telescopic proof strip
    out.append(R(0, 310, W, 76, WHITE, NAVY, 1.3, rx=5))
    out.append(R(0, 310, 6, 76, NAVY, "none"))
    out.append(
        T(
            22,
            334,
            "Por que a soma telescópica funciona para qualquer caminho P = (s → v₁ → … → t):",
            11.8,
            NAVY,
            "start",
            "700",
        )
    )
    out.append(
        T(
            22,
            355,
            "w'(P) = w(P) + (h(v₁) − h(s)) + (h(v₂) − h(v₁)) + … + (h(t) − h(vₖ)) = w(P) + h(t) − h(s)   →   independe do nº de arestas!",
            11.2,
            INK,
            "start",
            "600",
        )
    )
    out.append(
        T(
            22,
            374,
            "Como achar h? Rodando 1 único Bellman-Ford até um vértice virtual q (no W₁ detecta ciclo e aborta; em W₂–W₅ pesos ≥ 0 já dão h = 0).",
            10.6,
            SLATE,
            "start",
        )
    )

    (ASSETS / "fig_07_johnson_radix.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 08: Fila Radix (65 baldes) + Benchmark Johnson vs BF no W_2
# =============================================================================
def gen_fig_08() -> None:
    W, H = 1040, 386
    bf_d = parse_bench(BENCH / "p3_W_2.bf_todos.txt")["bellman_ford_todos_pares"]
    jh_d = parse_bench(BENCH / "p3_W_2.johnson_heap.txt")["johnson"]
    jr_d = parse_bench(BENCH / "p3_W_2.johnson_radix.txt")["johnson"]

    bf_m, bf_sd = float(bf_d["media_s"]), float(bf_d["desvio_s"])
    jh_m, jh_sd = float(jh_d["media_s"]), float(jh_d["desvio_s"])
    jr_m, jr_sd = float(jr_d["media_s"]), float(jr_d["desvio_s"])

    V2, E2 = G["W_2"]["vertices"], G["W_2"]["edges"]
    pass_m = CB["W_2"]["todos_os_pares"]["passagens_por_E_media"]
    bf_ops_total = CB["W_2"]["todos_os_pares"]["arestas_examinadas_total_extrapolado"]
    dj_ops_total = V2 * E2

    ns_bf = bf_m * 11 / bf_ops_total * 1e9
    ns_jh = jh_m * 11 / dj_ops_total * 1e9
    ns_jr = jr_m * 11 / dj_ops_total * 1e9
    teto_s = bf_m / pass_m

    out = [R(0, 0, W, H, WHITE, "none")]

    p1x, p1w = 0, 480
    p2x, p2w = 502, W - 502
    out.append(R(p1x, 0, p1w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p1x, 0, p1w, 4, NAVY, "none"))
    out.append(R(p2x, 0, p2w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p2x, 0, p2w, 4, OCHRE, "none"))

    # ── Panel A: Radix Heap (65 baldes) ──────────────────────────────────────
    out.append(T(p1x + 18, 28, "A. Fila Radix (65 baldes · O(1) push)", 13.2, NAVY, "start", "700"))
    out.append(T(p1x + 18, 47, "bit_cast<uint64_t>(dist) preserva ordem; balde = bit_width(key ^ last)", 10.6, SLATE, "start"))

    stages = [
        ("1. Push O(1)", "last=0101 (5)", {0: ["5"], 2: ["6", "7"], 4: ["12"]}, None),
        ("2. Pop B₀", "last=0101 (5)", {0: [], 2: ["6", "7"], 4: ["12"]}, "sai 5"),
        ("3. Redistrib.", "last=0110 (6)", {0: ["6"], 1: ["7"], 4: ["12"]}, "sai 6"),
    ]
    cw = (p1w - 36 - 20) / 3
    for s_idx, (stitle, slast, bmap, sai_txt) in enumerate(stages):
        sx = p1x + 18 + s_idx * (cw + 10)
        out.append(R(sx, 66, cw, 212, WHITE, RULE, 1.0, rx=4))
        out.append(R(sx, 66, cw, 24, NAVY_BG, "none"))
        out.append(T(sx + 8, 82, stitle, 10.4, NAVY, "start", "700"))
        out.append(T(sx + 8, 104, slast, 9.5, OCHRE, "start", "700", cls="mono"))

        for b_idx in range(5):
            by = 112 + b_idx * 32
            out.append(L(sx + 6, by + 28, sx + cw - 6, by + 28, HAIR, 0.8))
            out.append(T(sx + 8, by + 19, f"B{b_idx}", 9.6, MUTED, "start", "700"))
            items = bmap.get(b_idx, [])
            ix = sx + 30
            for it in items:
                pw = 30
                out.append(R(ix, by + 3, pw, 20, OCHRE_BG if b_idx > 0 else TEAL_BG, OCHRE if b_idx > 0 else TEAL, 1.0, rx=3))
                out.append(T(ix + pw / 2, by + 17, it, 9.6, INK, "middle", "700", cls="mono"))
                ix += pw + 4
            if b_idx == 0 and sai_txt:
                out.append(T(sx + cw - 7, by + 17, sai_txt, 9.4, CRIMSON, "end", "700"))

    out.append(R(p1x + 18, 290, p1w - 36, 80, WHITE, NAVY, 1.0, rx=4))
    out.append(T(p1x + 28, 311, "• Como Dijkstra extrai distâncias em ordem crescente (≥ last),", 10.5, INK, "start"))
    out.append(T(p1x + 36, 327, "um elemento só desce para baldes menores (≤ 64 movimentos).", 10.5, SLATE, "start"))
    out.append(T(p1x + 28, 346, "• Trocar heap binário pela fila radix derruba o custo por", 10.5, SLATE, "start"))
    out.append(T(p1x + 36, 362, f"relaxação de {br(ns_jh, 1)} ns para {br(ns_jr, 1)} ns (quase sem fila!).", 10.5, TEAL, "start", "700"))

    # ── Panel B: Benchmark W_2 (mesma sessão ociosa · 11T) ───────────────────
    out.append(T(p2x + 18, 28, "B. Tempo no W₂ (11 threads · sessão ociosa)", 13.2, OCHRE, "start", "700"))
    out.append(T(p2x + 18, 47, "Média ± dp (3 execuções) — por que o ganho é 2,4× e não 10×", 10.6, SLATE, "start"))

    x0, x1 = p2x + 130, p2x + p2w - 134
    y0, y1 = 84, 272
    max_s = 33.0

    def X(s: float) -> float:
        return x0 + s / max_s * (x1 - x0)

    for tv in (0, 10, 20, 30):
        xx = X(tv)
        out.append(L(xx, y0, xx, y1, HAIR if tv > 0 else RULE, 1.0))
        out.append(T(xx, y1 + 16, f"{tv} s", 10, MUTED, "middle"))

    xt = X(teto_s)
    out.append(L(xt, y0 - 8, xt, y1, SLATE, 1.5, 'stroke-dasharray="4 3"'))
    out.append(T(xt + 5, y0 - 11, f"teto sem fila ≈ {br(teto_s, 1)} s", 9.8, SLATE, "start", "700"))

    rows = [
        ("BF (ativos)", f"{br(pass_m, 1)}×E · {br(ns_bf, 1)} ns", bf_m, bf_sd, TEAL, TEAL_BG, "base"),
        ("Johnson Heap", f"1,0×E · {br(ns_jh, 1)} ns", jh_m, jh_sd, OCHRE, WHITE, f"{br(bf_m / jh_m, 1)}×"),
        ("Johnson Radix", f"1,0×E · {br(ns_jr, 1)} ns", jr_m, jr_sd, OCHRE, OCHRE_BG, f"{br(bf_m / jr_m, 1)}×"),
    ]
    rh = (y1 - y0) / 3
    bh = 34
    for idx, (lbl, sub, m, sd, col, bg, gain) in enumerate(rows):
        ry = y0 + idx * rh + 12
        out.append(T(x0 - 10, ry + 15, lbl, 11.4, INK, "end", "700"))
        out.append(T(x0 - 10, ry + 30, sub, 9.4, SLATE, "end"))
        bw = X(m) - x0
        out.append(R(x0, ry, bw, bh, bg, col, 1.7, rx=3))
        xm_lo, xm_hi = X(max(0.0, m - sd)), X(m + sd)
        out.append(L(xm_lo, ry + bh / 2, xm_hi, ry + bh / 2, INK, 1.5))
        out.append(T(xm_hi + 8, ry + 15, f"{br(m, 1 if idx < 2 else 2)} s", 11.8, col, "start", "700"))
        out.append(T(xm_hi + 8, ry + 30, f"({gain})" if idx == 0 else f"({gain} mais rápido)", 9.8, col if idx > 0 else SLATE, "start", "700" if idx > 0 else "400"))

    out.append(R(p2x + 18, 296, p2w - 36, 74, WHITE, OCHRE, 1.0, rx=4))
    out.append(T(p2x + 28, 317, "Por que 2,4× e não 10×?", 10.8, OCHRE, "start", "700"))
    out.append(T(p2x + 28, 335, "BF otimizado já relaxa só 3,6×E sem fila (4,5 ns/op); Dijkstra reduz p/", 10.2, SLATE, "start"))
    out.append(T(p2x + 28, 351, "1,0×E mas paga 6,6 ns/op. (Sessão ociosa: BF 30,0 s vs 38,1 s sob carga.)", 10.2, SLATE, "start"))

    (ASSETS / "fig_08_johnson_bench.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 09: Arquitetura paralela (BF/Johnson pool vs FW blocos 64x64)
# =============================================================================
def gen_fig_09() -> None:
    W, H = 1040, 390
    out = [R(0, 0, W, H, WHITE, "none")]

    p1x, p1w = 0, 488
    p2x, p2w = 512, W - 512
    out.append(R(p1x, 0, p1w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p1x, 0, p1w, 4, TEAL, "none"))
    out.append(R(p2x, 0, p2w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p2x, 0, p2w, 4, NAVY, "none"))

    corte = GF["W_2"]["corte_11_faixas"] * 100
    chunk = int(re.search(r"count / \(std::size_t\{threads\} \* (\d+)\)", (ROOT / "include/cos/graph.hpp").read_text()).group(1))
    V2 = G["W_2"]["vertices"]
    nb2 = -(-V2 // 64)
    bars_w2 = 3 * nb2

    # ── Panel A: BF & Johnson pool de destinos ────────────────────────────────
    out.append(T(p1x + 18, 28, "A. BF & Johnson: pool dinâmico sem travas", 13.5, TEAL, "start", "700"))
    out.append(T(p1x + 18, 47, f"Particionar o grafo corta {br(corte, 1)}% das arestas (|u−v| ≈ V/3); paraleliza-se nos destinos", 11, SLATE, "start"))

    # Read-only CSR box at top
    out.append(R(p1x + 64, 66, 360, 42, WHITE, NAVY, 1.5, rx=4))
    out.append(T(p1x + 244, 84, "Grafo CSR compartilhado (somente leitura)", 11.5, NAVY, "middle", "700"))
    out.append(T(p1x + 244, 100, "offsets + neighbors + weights", 10, SLATE, "middle", cls="mono"))

    # Atomic counter box on left
    out.append(R(p1x + 22, 162, 134, 62, WHITE, TEAL, 1.5, rx=4))
    out.append(T(p1x + 89, 184, "ticket atômico", 11, TEAL, "middle", "700"))
    out.append(T(p1x + 89, 201, f"fetch_add({chunk})", 10.5, INK, "middle", "700", cls="mono"))
    out.append(T(p1x + 89, 216, "0 barreiras/rodada", 9.5, SLATE, "middle"))

    # 3 thread rows
    t_rows = [("T0", "dest. 0..15", TEAL_BG), ("T1", "dest. 16..31", TEAL_BG), ("T10", "próximo livre", OCHRE_BG)]
    for i, (tn, dst, tbg) in enumerate(t_rows):
        ty = 132 + i * 48
        # Arrow from CSR
        out.append(L(p1x + 244, 108, p1x + 244, 126, RULE, 1.2))
        # Arrow from ticket
        out.append(L(p1x + 156, 193, p1x + 188, ty + 18, TEAL, 1.4, 'marker-end="url(#arr-teal)"'))
        # Thread box
        out.append(R(p1x + 192, ty, 192, 36, tbg, TEAL if i < 2 else OCHRE, 1.3, rx=4))
        out.append(T(p1x + 202, ty + 16, f"{tn}: {dst}", 10.8, INK, "start", "700"))
        out.append(T(p1x + 202, ty + 30, "workspace local 12·V B", 9.5, SLATE, "start"))
        # Arrow to matrix row
        out.append(L(p1x + 384, ty + 18, p1x + 412, ty + 18, TEAL, 1.4, 'marker-end="url(#arr-teal)"'))
        out.append(R(p1x + 416, ty + 4, 52, 28, WHITE, RULE, 1.0, rx=2))
        out.append(T(p1x + 442, ty + 22, "linha", 9.5, SLATE, "middle"))

    # Bottom insight box
    out.append(R(p1x + 18, 290, p1w - 36, 82, WHITE, TEAL, 1.0, rx=4))
    out.append(T(p1x + 30, 312, "• Nenhuma escrita compartilhada (sem locks nem falsos compartilhamentos).", 10.8, INK, "start"))
    out.append(T(p1x + 30, 332, "• Balanceamento automático entre P-cores rápidos e E-cores mais lentos.", 10.8, SLATE, "start"))
    out.append(T(p1x + 30, 352, "• Na saída de relax_rounds, grava apenas a linha própria na matriz V×V.", 10.8, SLATE, "start"))

    # ── Panel B: Floyd-Warshall blocos 64x64 em 3 fases ───────────────────────
    out.append(T(p2x + 18, 28, "B. Floyd-Warshall: blocos 64×64 em 3 fases", 13.5, NAVY, "start", "700"))
    out.append(T(p2x + 18, 47, f"Bloco de 48 KiB (L1); std::barrier entre fases ({br_int(bars_w2)} barreiras vs. {br_int(V2)} no W₂)", 11, SLATE, "start"))

    # 3 phase mini-matrices (4x4 grid, kb = 1)
    cell = 26
    phases = [
        ("Fase 1 (1 thread)", "bloco (kb, kb)"),
        ("Fase 2 (11 threads)", "linha e coluna kb"),
        ("Fase 3 (11 threads)", "demais blocos (grupos de 4)"),
    ]
    pw_box = (p2w - 36 - 24) / 3
    for ph, (ptitle, psub) in enumerate(phases):
        px = p2x + 18 + ph * (pw_box + 12)
        out.append(R(px, 66, pw_box, 198, WHITE, RULE, 1.0, rx=4))
        out.append(T(px + pw_box / 2, 85, ptitle, 10.8, NAVY, "middle", "700"))
        out.append(T(px + pw_box / 2, 101, psub, 9.5, SLATE, "middle"))

        gx = px + (pw_box - 4 * cell) / 2
        gy = 114
        kb = 1
        for i in range(4):
            for j in range(4):
                diag = i == kb and j == kb
                cross = (i == kb) != (j == kb)
                if ph == 0:
                    cfill = NAVY if diag else WHITE
                elif ph == 1:
                    cfill = NAVY_BG if diag else (TEAL if cross else WHITE)
                else:
                    cfill = WHITE if diag else (TEAL_BG if cross else NAVY)
                out.append(R(gx + j * cell, gy + i * cell, cell, cell, cfill, RULE, 0.9))
                if (ph == 0 and diag) or (ph == 1 and cross) or (ph == 2 and not diag and not cross):
                    out.append(T(gx + j * cell + cell / 2, gy + i * cell + 16, "W", 9.5, WHITE, "middle", "700"))
                elif (ph == 1 and diag) or (ph == 2 and cross):
                    out.append(T(gx + j * cell + cell / 2, gy + i * cell + 16, "R", 9.5, NAVY if ph == 1 else TEAL, "middle", "700"))

        if ph < 2:
            # Barrier line between boxes
            bx_bar = px + pw_box + 6
            out.append(L(bx_bar, 72, bx_bar, 258, CRIMSON, 1.4, 'stroke-dasharray="4 3"'))
            out.append(T(bx_bar, 276, "barrier", 9.0, CRIMSON, "middle", "700"))

    # Legend for R / W
    out.append(R(p2x + 18, 286, p2w - 36, 86, WHITE, NAVY, 1.0, rx=4))
    out.append(T(p2x + 30, 307, "W = bloco atualizado  ·  R = bloco lido (já pronto da fase anterior)", 10.5, INK, "start", "700"))
    out.append(T(p2x + 30, 327, "• Fase 3: laço externo em i mantém a linha no cache L1/L2 durante os 64 passos de k.", 10.5, SLATE, "start"))
    out.append(T(p2x + 30, 347, "• relax_segment sem desvios (?: após todas as leituras) → auto-vetorizado em NEON.", 10.5, TEAL, "start", "700"))

    (ASSETS / "fig_09_parallel_arch.svg").write_text(svg_wrap(W, H, "\n".join(out)))


# =============================================================================
# FIG 10: Escala P/E-cores e parede de L2/DRAM
# =============================================================================
def gen_fig_10() -> None:
    W, H = 1040, 390
    out = [R(0, 0, W, H, WHITE, "none")]

    nuc = dict(l.split("=", 1) for l in (BENCH / "nucleo_eficiencia.txt").read_text().splitlines() if "=" in l and not l.startswith("#"))
    r_e = float(nuc["tempo_p_s"]) / float(nuc["tempo_e_s"])  # ~0.286

    maq = dict(l.split("=", 1) for l in (BENCH / "maquina.txt").read_text().splitlines() if "=" in l)
    np_cores = int(maq["nucleos_desempenho"])
    ne_cores = int(maq["nucleos_eficiencia"])
    l2_mib = int(maq["l2_desempenho_bytes"]) / (1024**2)

    def cap(t: float) -> float:
        return min(t, np_cores) + max(0.0, t - np_cores) * r_e

    p1x, p1w = 0, 505
    p2x, p2w = 530, W - 530
    out.append(R(p1x, 0, p1w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p1x, 0, p1w, 4, NAVY, "none"))
    out.append(R(p2x, 0, p2w, H, SOFT, RULE, 1.0, rx=4))
    out.append(R(p2x, 0, p2w, 4, CRIMSON, "none"))

    def draw_axes(px: float, pw: float, ymax: float = 8.4, right_pad: float = 104.0, cap_below: bool = False) -> tuple:
        ax0, ax1 = px + 44, px + pw - right_pad
        ay0, ay1 = 72, H - 52

        def X(t: float) -> float:
            return ax0 + (t - 1) / 10.0 * (ax1 - ax0)

        def Y(g: float) -> float:
            return ay1 - g / ymax * (ay1 - ay0)

        # P-core / E-core background bands
        out.append(R(X(1), ay0, X(np_cores + 0.5) - X(1), ay1 - ay0, WHITE, "none"))
        out.append(R(X(np_cores + 0.5), ay0, X(11) - X(np_cores + 0.5), ay1 - ay0, HAIR, "none", extra='fill-opacity="0.45"'))
        out.append(T((X(1) + X(np_cores + 0.5)) / 2, ay0 - 6, f"{np_cores} P-cores", 10, NAVY, "middle", "700"))
        out.append(T((X(np_cores + 0.5) + X(11)) / 2, ay0 - 6, f"{ne_cores} E-cores", 10, SLATE, "middle", "700"))

        for g in range(0, 9, 2):
            yy = Y(g)
            out.append(L(ax0, yy, ax1, yy, RULE if g == 0 else HAIR, 1.0))
            out.append(T(ax0 - 7, yy + 3.5, f"{g}×", 10, MUTED, "end"))

        for t in (1, 2, 3, 4, 5, 6, 8, 11):
            out.append(T(X(t), ay1 + 16, str(t), 10, MUTED, "middle"))
        out.append(T(ax1, ay1 + 34, "threads", 10, MUTED, "end"))

        # Capacity curve 5 + 6*r
        cpts = " ".join(f"{X(t):.1f},{Y(cap(t)):.1f}" for t in (1, np_cores, 11))
        out.append(f'<polyline points="{cpts}" fill="none" stroke="{SLATE}" stroke-width="1.6" stroke-dasharray="5 4"/>')
        cap_dy = 16 if cap_below else -10
        out.append(T(X(7.4), Y(cap(7.4)) + cap_dy, f"5 + 6·r = {br(cap(11), 1)}×", 9.5, SLATE, "middle", "600"))
        return X, Y, ax0, ax1, ay0, ay1

    # ── Panel A: aleatorio5000 (cabe na cache) ────────────────────────────────
    out.append(T(p1x + 18, 28, "A. Grafo aleatório 5.000 vértices (cabe na cache)", 13.5, NAVY, "start", "700"))
    out.append(T(p1x + 18, 47, "Os 3 algoritmos escalam juntos até o teto dos P/E-cores (≈6×)", 11, SLATE, "start"))

    XA, YA, ax0, ax1, ay0, ay1 = draw_axes(p1x, p1w, right_pad=98.0, cap_below=False)
    ts_5k = (1, 2, 3, 4, 5, 6, 8, 11)
    raw_5k = {t: parse_bench(BENCH / f"escala_aleatorio5000_t{t}.txt") for t in ts_5k}
    series_5k = [
        ("johnson", "Johnson", OCHRE, -14),
        ("bellman_ford_todos_pares", "BF", TEAL, 3),
        ("floyd_warshall", "FW", NAVY, 20),
    ]
    for sec, name, col, dy_lbl in series_5k:
        t1 = float(raw_5k[1][sec]["media_s"])
        pts_s = [(t, t1 / float(raw_5k[t][sec]["media_s"])) for t in ts_5k]
        pstr = " ".join(f"{XA(t):.1f},{YA(g):.1f}" for t, g in pts_s)
        out.append(f'<polyline points="{pstr}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        for t, g in pts_s:
            out.append(C(XA(t), YA(g), 3.6, col, WHITE, 1.0))
        g11 = pts_s[-1][1]
        ly = YA(g11) + dy_lbl
        out.append(L(XA(11) + 5, YA(g11), XA(11) + 12, ly - 3, col, 1.1))
        out.append(T(XA(11) + 14, ly, f"{name}: {br(g11, 1)}×", 10.2, col, "start", "700"))

    # ── Panel B: Grafos grandes (parede de L2 / DRAM) ─────────────────────────
    out.append(T(p2x + 18, 28, "B. Grafos do trabalho: parede de L2 / DRAM (BF)", 13.5, CRIMSON, "start", "700"))
    out.append(T(p2x + 18, 47, f"Melhor de 2–3 execuções; 12·V B/thread excede L2 ({br(l2_mib, 0)} MiB) e satura DRAM", 11, SLATE, "start"))

    XB, YB, bx0, bx1, by0, by1 = draw_axes(p2x, p2w, right_pad=116.0, cap_below=True)
    ts_g = (1, 2, 5, 11)

    # Vertical marker at t = 2 where 2 * 12 MB = 24 MB > 16 MiB L2 for W_4
    out.append(L(XB(2), by0 + 22, XB(2), by1, OCHRE, 1.3, 'stroke-dasharray="4 3"'))
    out.append(R(XB(2) + 4, by0 + 24, 148, 30, WHITE, OCHRE, 0.9, rx=3))
    out.append(T(XB(2) + 9, by0 + 37, "W₄: 2T×12 MB = 24 MB", 9.2, OCHRE, "start", "700"))
    out.append(T(XB(2) + 9, by0 + 49, "> 16 MiB L2 → queda!", 9.2, OCHRE, "start", "600"))

    g_configs = [
        ("W_2", "W₂", "0,3 MB/thr", TEAL, False, 0),
        ("W_4", "W₄", "12 MB/thr", NAVY, False, 0),
        ("W_5", "W₅", "120 MB/thr", CRIMSON, True, 0),
    ]
    for gn, gshort, gsub, col, is_w5, _ in g_configs:
        mins = {}
        for t in ts_g:
            d = parse_bench(BENCH / f"escala_{gn}_amostra_t{t}.txt")["bellman_ford_todos_pares"]
            runs = [float(r[1]) for r in d["runs_list"]]
            mins[t] = min(runs)
        pts_g = [(t, mins[1] / mins[t]) for t in ts_g]
        pstr = " ".join(f"{XB(t):.1f},{YB(g):.1f}" for t, g in pts_g)
        dash = ' stroke-dasharray="6 4"' if is_w5 else ""
        out.append(f'<polyline points="{pstr}" fill="none" stroke="{col}" stroke-width="2.6"{dash}/>')
        for t, g in pts_g:
            if is_w5:
                out.append(C(XB(t), YB(g), 4.2, WHITE, col, 2.0))
            else:
                out.append(C(XB(t), YB(g), 4.2, col, WHITE, 1.2))
        g11 = pts_g[-1][1]
        out.append(T(XB(11) + 10, YB(g11) - 1, f"{gshort}: {br(g11, 1)}×", 10.5, col, "start", "700"))
        out.append(T(XB(11) + 10, YB(g11) + 12, gsub, 9.2, MUTED, "start"))
        if is_w5:
            out.append(T(XB(6.0), YB(pts_g[2][1]) - 11, "DRAM wall (2 runs sob carga)", 9.0, CRIMSON, "middle", "600"))

    (ASSETS / "fig_10_scaling.svg").write_text(svg_wrap(W, H, "\n".join(out)))


def main() -> None:
    gen_fig_01()
    gen_fig_02()
    gen_fig_03_bf_ativos()
    gen_fig_03()
    gen_fig_04()
    gen_fig_05()
    gen_fig_06()
    gen_fig_07()
    gen_fig_08()
    gen_fig_09()
    gen_fig_10()
    svgs = sorted(ASSETS.glob("fig_*.svg"))
    print(f"OK: {len(svgs)} SVGs gerados em {ASSETS}")
    for s in svgs:
        print(f"  - {s.name} ({s.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
