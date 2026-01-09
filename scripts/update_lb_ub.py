#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

import networkx as nx


# ============================================================
# Localização de arquivos de grafo por stem (recursivo)
# ============================================================


def build_stem_index(graphs_root: Path) -> Dict[str, Path]:
    idx: Dict[str, Path] = {}
    for p in graphs_root.rglob("*"):
        if p.is_file():
            key = p.stem.lower()
            if key not in idx:
                idx[key] = p
    return idx


# ============================================================
# Leitura de grafos (edgelist com "n m" e DIMACS)
#   - Se o formato informa n: adiciona nós 0..n-1 (isolados inclusos)
# ============================================================


def read_graph_any_format(path: Path) -> nx.Graph:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    if not lines:
        raise ValueError("Arquivo vazio")

    # DIMACS se tiver linha "p ..."
    if any(ln.startswith("p ") for ln in lines):
        return read_dimacs(lines)

    # caso contrário, tenta "n m" + arestas
    return read_n_m_edgelist(lines)


def read_dimacs(lines: List[str]) -> nx.Graph:
    n_header: Optional[int] = None
    edges: List[Tuple[int, int]] = []

    for ln in lines:
        if ln.startswith("c"):
            continue
        if ln.startswith("p"):
            parts = ln.split()
            # p edge n m
            if len(parts) >= 4:
                n_header = int(parts[2])
            continue
        if ln.startswith("e"):
            parts = ln.split()
            if len(parts) >= 3:
                u = int(parts[1])
                v = int(parts[2])
                if u != v:
                    # DIMACS normalmente é 1-indexed
                    edges.append((u - 1, v - 1))

    g = nx.Graph()
    if n_header is not None:
        g.add_nodes_from(range(n_header))
    g.add_edges_from(edges)
    return g


def read_n_m_edgelist(lines: List[str]) -> nx.Graph:
    header = lines[0].split()
    if len(header) < 2:
        raise ValueError("Primeira linha deve conter: n m (ou use DIMACS)")

    n_header = int(header[0])

    g_raw = nx.Graph()
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) < 2:
            continue
        u = int(parts[0])
        v = int(parts[1])
        if u == v:
            continue
        g_raw.add_edge(u, v)

    # re-rotula nós que aparecem para 0..k-1
    nodes_sorted = sorted(g_raw.nodes())
    mapping = {old: new for new, old in enumerate(nodes_sorted)}
    g = nx.relabel_nodes(g_raw, mapping, copy=True)

    # adiciona isolados implícitos do header
    k = g.number_of_nodes()
    if n_header > k:
        g.add_nodes_from(range(n_header))

    return g


# ============================================================
# Greedy para conjunto dominante (sobre N[v])
# ============================================================


def greedy_dominating_set(G: nx.Graph) -> Set[int]:
    if G.number_of_nodes() == 0:
        return set()

    undominated = set(G.nodes())
    D: Set[int] = set()

    closed_nb = {v: set(G.neighbors(v)) | {v} for v in G.nodes()}

    while undominated:
        best_v = None
        best_gain = -1

        for v in G.nodes():
            gain = len(closed_nb[v] & undominated)
            if gain > best_gain:
                best_gain = gain
                best_v = v
            if best_gain == len(undominated):
                break

        if best_v is None:
            best_v = next(iter(undominated))

        D.add(best_v)
        undominated -= closed_nb[best_v]

    return D


# ============================================================
# Bounds Roman {3} válidos para QUALQUER grafo (inclui isolados)
# Definição (Mojdeh–Volkmann / Chakradhar–Reddy):
#   f:V->{0,1,2,3}
#   f(v)=0 => sum_{u in N(v)} f(u) >= 3
#   f(v)=1 => sum_{u in N(v)} f(u) >= 2
# ============================================================


def roman3_bounds_any_graph(G: nx.Graph) -> Tuple[int, int, int]:
    """
    Retorna (LB, UB, iso_count).
    """
    if G.number_of_nodes() == 0:
        return 0, 0, 0

    iso_nodes = [v for v, d in G.degree() if d == 0]
    iso = len(iso_nodes)

    # Subgrafo sem isolados (componentes não-triviais)
    H = G.copy()
    H.remove_nodes_from(iso_nodes)

    # LB:
    #  - cada isolado contribui >= 2
    #  - por componente conectada não-trivial C: ceil(3|C| / (Δ(C)+3))
    lb = 2 * iso
    for comp_nodes in nx.connected_components(H):
        C = H.subgraph(comp_nodes)
        nC = C.number_of_nodes()
        if nC == 0:
            continue
        Delta = max((d for _, d in C.degree()), default=0)
        lb += math.ceil((3 * nC) / (Delta + 3))

    # UB construtivo:
    #  - isolados: 2
    #  - resto: 3 em um conjunto dominante D, 0 no resto
    D = greedy_dominating_set(H) if H.number_of_nodes() > 0 else set()
    ub = 2 * iso + 3 * len(D)

    if ub < lb:
        ub = lb

    return lb, ub, iso


# ============================================================
# CSV
# ============================================================


def iter_csv_paths(csv_args: List[str]) -> Iterator[Path]:
    for s in csv_args:
        if any(ch in s for ch in ["*", "?", "["]):
            for m in Path(".").glob(s):
                if m.is_file():
                    yield m
        else:
            yield Path(s)


def ensure_out_path(in_csv: Path, outdir: Optional[Path], inplace: bool) -> Path:
    if inplace:
        return in_csv
    if outdir is None:
        return in_csv.with_name(in_csv.stem + "_bounds.csv")
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir / in_csv.name


def update_one_csv(
    graph_index: Dict[str, Path], in_csv: Path, out_csv: Path, strict: bool
) -> None:
    cache: Dict[str, Tuple[int, int, int]] = {}

    with open(in_csv, "r", encoding="utf-8", newline="") as f_in:
        reader = csv.DictReader(f_in)
        if reader.fieldnames is None:
            raise ValueError("CSV sem cabeçalho")

        fieldnames = list(reader.fieldnames)
        for col in ("Grafo", "LB", "UB"):
            if col not in fieldnames:
                raise ValueError(f"CSV precisa ter coluna '{col}'")

        has_obj = "Objetivo" in fieldnames
        rows = list(reader)

    for row in rows:
        name = row["Grafo"].strip()
        if not name:
            continue
        key = name.lower()

        if key in cache:
            lb, ub, iso = cache[key]
        else:
            gpath = graph_index.get(key)
            if gpath is None:
                msg = f"[AVISO] Grafo não encontrado (stem): {name}"
                if strict:
                    raise FileNotFoundError(msg)
                print(msg, file=sys.stderr)
                continue

            G = read_graph_any_format(gpath)
            lb, ub, iso = roman3_bounds_any_graph(G)
            cache[key] = (lb, ub, iso)

        row["LB"] = str(lb)
        row["UB"] = str(ub)

        # Warning útil: objetivo não pode ser < 2*iso se o objetivo conta isolados
        if has_obj and row.get("Objetivo"):
            try:
                obj = int(float(row["Objetivo"]))
                if obj < 2 * iso:
                    print(
                        f"[AVISO] {name}: Objetivo={obj} < 2*isolados={2 * iso}. "
                        f"Isso sugere que o Objetivo/PLI pode estar ignorando isolados do arquivo.",
                        file=sys.stderr,
                    )
            except Exception:
                pass

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Recalcula e substitui LB/UB (Roman {3}) para qualquer grafo, incluindo isolados."
    )
    ap.add_argument(
        "--graphs", required=True, help="Pasta raiz com os grafos (recursivo)."
    )
    ap.add_argument(
        "--csv",
        required=True,
        nargs="+",
        help="Um ou mais CSVs (aceita glob, ex: *.csv).",
    )
    ap.add_argument(
        "--outdir", default=None, help="Pasta de saída (ignorado se --inplace)."
    )
    ap.add_argument(
        "--inplace", action="store_true", help="Sobrescreve os CSVs de entrada."
    )
    ap.add_argument(
        "--strict", action="store_true", help="Falha se algum grafo não for encontrado."
    )
    args = ap.parse_args()

    graphs_root = Path(args.graphs)
    if not graphs_root.exists():
        print(f"[ERRO] Pasta de grafos não existe: {graphs_root}", file=sys.stderr)
        return 2

    graph_index = build_stem_index(graphs_root)
    if not graph_index:
        print(f"[ERRO] Nenhum arquivo encontrado em: {graphs_root}", file=sys.stderr)
        return 2

    outdir = Path(args.outdir) if args.outdir else None

    for in_csv in iter_csv_paths(args.csv):
        out_csv = ensure_out_path(in_csv, outdir, args.inplace)
        update_one_csv(graph_index, in_csv, out_csv, strict=args.strict)
        print(f"[OK] {in_csv} -> {out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
