#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Atualiza (substitui) as colunas LB e UB em um ou mais CSVs, recalculando bounds
para Dominação {3}-Romana em QUALQUER grafo (inclusive desconexo e com isolados).

Definição assumida (Roman {3}-domination):
  f: V -> {0,1,2,3}
  se f(v)=0 então sum_{u in N(v)} f(u) >= 3
  se f(v)=1 então sum_{u in N(v)} f(u) >= 2

LB usado (válido, por componente):
  - componente com 1 vértice isolado: LB = 2
  - caso geral: ceil( 3*n / (Delta + 3) )

UB usado (sempre factível, construtivo):
  - vértices isolados: atribui 2
  - resto: acha conjunto dominante D por greedy e atribui 3 em D, 0 no resto
    => UB = 2*#isolados + 3*|D|

Uso:
  python update_bounds.py --graphs ./grafos --csv resultados1.csv resultados2.csv --outdir ./atualizados
  python update_bounds.py --graphs ./grafos --csv resultados.csv --inplace
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

import networkx as nx


# ----------------------------
# Leitura do grafo (.txt)
# ----------------------------


def read_graph_edgelist_with_header_n(path: Path, nodetype=int) -> nx.Graph:
    """
    Formato:
        n m
        u v
        ...
    Respeita n do header adicionando nós isolados ausentes na lista de arestas.
    Re-rotula para 0..n-1 (contíguo) para consistência interna.
    """
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")

        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")

        n_header = int(parts[0])

        edges: List[Tuple[int, int]] = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            pl = line.split()
            if len(pl) < 2:
                continue
            u = nodetype(pl[0])
            v = nodetype(pl[1])
            if u == v:
                continue
            edges.append((u, v))

    g_raw = nx.Graph()
    g_raw.add_edges_from(edges)

    # Re-rotula os nós que apareceram nas arestas para 0..k-1
    nodes_sorted = sorted(g_raw.nodes())
    mapping = {old: new for new, old in enumerate(nodes_sorted)}
    g = nx.relabel_nodes(g_raw, mapping, copy=True)

    # Adiciona nós isolados faltantes até n_header
    k = g.number_of_nodes()
    if n_header > k:
        g.add_nodes_from(range(n_header))
    # Se n_header < k, mantemos o que foi lido (arquivo inconsistente)
    return g


# ----------------------------
# Greedy para conjunto dominante
# ----------------------------


def greedy_dominating_set(G: nx.Graph) -> Set[int]:
    """
    Conjunto dominante sobre vizinhança fechada N[v]. Heurística greedy.
    """
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


# ----------------------------
# Bounds Roman {3} para qualquer grafo
# ----------------------------


def roman3_bounds_any_graph(G: nx.Graph) -> Tuple[int, int]:
    """
    LB e UB válidos para qualquer grafo (desconexo e com isolados).
    """
    if G.number_of_nodes() == 0:
        return 0, 0

    # LB por componente
    lb = 0
    for comp_nodes in nx.connected_components(G):
        H = G.subgraph(comp_nodes)
        n = H.number_of_nodes()
        if n == 1:
            lb += 2  # isolado precisa ser 2 ou 3
        else:
            Delta = max((d for _, d in H.degree()), default=0)
            lb += math.ceil((3 * n) / (Delta + 3))

    # UB construtivo
    iso_nodes = [v for v, d in G.degree() if d == 0]
    iso_count = len(iso_nodes)

    H = G.copy()
    H.remove_nodes_from(iso_nodes)

    D = greedy_dominating_set(H) if H.number_of_nodes() > 0 else set()
    ub = 2 * iso_count + 3 * len(D)

    if ub < lb:
        ub = lb

    return lb, ub


# ----------------------------
# Utilidades CSV
# ----------------------------


def iter_csv_paths(csv_args: List[str]) -> Iterator[Path]:
    for s in csv_args:
        p = Path(s)
        # permite glob simples tipo *.csv
        if any(ch in s for ch in ["*", "?", "["]):
            for m in Path(".").glob(s):
                if m.is_file():
                    yield m
        else:
            yield p


def ensure_out_path(in_csv: Path, outdir: Optional[Path], inplace: bool) -> Path:
    if inplace:
        return in_csv
    if outdir is None:
        return in_csv.with_name(in_csv.stem + "_bounds.csv")
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir / in_csv.name


def update_one_csv(graphs_dir: Path, in_csv: Path, out_csv: Path, strict: bool) -> None:
    """
    Lê CSV, recalcula LB/UB para cada linha com grafo GRAFO.txt, e sobrescreve colunas LB/UB.
    """
    if not in_csv.exists():
        raise FileNotFoundError(f"CSV não encontrado: {in_csv}")

    # cache para não reler o mesmo grafo várias vezes
    bounds_cache: Dict[str, Tuple[int, int]] = {}

    with open(in_csv, "r", encoding="utf-8", newline="") as f_in:
        reader = csv.DictReader(f_in)
        if reader.fieldnames is None:
            raise ValueError("CSV sem cabeçalho")

        fieldnames = list(reader.fieldnames)
        if "Grafo" not in fieldnames:
            raise ValueError("CSV precisa ter coluna 'Grafo'")
        if "LB" not in fieldnames or "UB" not in fieldnames:
            raise ValueError("CSV precisa ter colunas 'LB' e 'UB'")

        rows = list(reader)

    # Atualiza linhas
    for row in rows:
        name = row["Grafo"].strip()
        if not name:
            continue

        if name in bounds_cache:
            lb, ub = bounds_cache[name]
        else:
            gpath = graphs_dir / f"{name}.txt"
            if not gpath.exists():
                msg = f"[AVISO] Grafo não encontrado: {gpath}"
                if strict:
                    raise FileNotFoundError(msg)
                print(msg, file=sys.stderr)
                continue

            G = read_graph_edgelist_with_header_n(gpath, nodetype=int)
            lb, ub = roman3_bounds_any_graph(G)
            bounds_cache[name] = (lb, ub)

        row["LB"] = str(lb)
        row["UB"] = str(ub)

    # Escreve saída
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Recalcula e substitui LB/UB em CSVs usando grafos .txt"
    )
    ap.add_argument(
        "--graphs",
        required=True,
        help="Pasta onde estão os grafos .txt (nome = Grafo + .txt)",
    )
    ap.add_argument(
        "--csv",
        required=True,
        nargs="+",
        help="Um ou mais CSVs (aceita glob, ex: *.csv)",
    )
    ap.add_argument(
        "--outdir", default=None, help="Pasta de saída (ignorado se --inplace)"
    )
    ap.add_argument(
        "--inplace", action="store_true", help="Sobrescreve os CSVs de entrada"
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Falha se algum .txt não for encontrado (ao invés de avisar)",
    )
    args = ap.parse_args()

    graphs_dir = Path(args.graphs)
    if not graphs_dir.exists():
        print(f"[ERRO] Pasta de grafos não existe: {graphs_dir}", file=sys.stderr)
        return 2

    outdir = Path(args.outdir) if args.outdir else None

    for in_csv in iter_csv_paths(args.csv):
        out_csv = ensure_out_path(in_csv, outdir, args.inplace)
        try:
            update_one_csv(graphs_dir, in_csv, out_csv, strict=args.strict)
            print(f"[OK] {in_csv} -> {out_csv}")
        except Exception as e:
            print(f"[ERRO] {in_csv}: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
