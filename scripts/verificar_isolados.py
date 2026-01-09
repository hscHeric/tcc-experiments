#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterator, Optional, Tuple

import networkx as nx


def iter_instance_files(
    root: str | Path, extensions: Optional[set[str]] = None
) -> Iterator[Path]:
    root = Path(root)
    for p in root.rglob("*"):
        if p.is_file():
            if extensions is None or p.suffix.lower() in extensions:
                yield p


def read_graph_edgelist_header_n(path: Path) -> Tuple[nx.Graph, int]:
    """
    Formato:
        n m
        u v
        ...
    Retorna (grafo, n_header). Inclui nós 0..n_header-1 para capturar isolados implícitos.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")

        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")

        n_header = int(parts[0])

        edges = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            pl = line.split()
            if len(pl) < 2:
                continue
            u = int(pl[0])
            v = int(pl[1])
            if u != v:
                edges.append((u, v))

    g_raw = nx.Graph()
    g_raw.add_edges_from(edges)

    # relabel para 0..k-1 dos nós que aparecem
    nodes_sorted = sorted(g_raw.nodes())
    mapping = {old: new for new, old in enumerate(nodes_sorted)}
    g = nx.relabel_nodes(g_raw, mapping, copy=True)

    # adiciona isolados implícitos do header
    k = g.number_of_nodes()
    if n_header > k:
        g.add_nodes_from(range(n_header))

    return g, n_header


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Detecta instâncias .txt com vértices isolados (grafo n m + arestas)."
    )
    ap.add_argument(
        "folder", type=str, help="Pasta raiz contendo os .txt (busca recursiva)."
    )
    ap.add_argument(
        "--ext",
        nargs="*",
        default=[".txt"],
        help="Extensões a considerar (default: .txt).",
    )
    ap.add_argument(
        "--min",
        type=int,
        default=1,
        help="Reportar apenas se #isolados >= min (default: 1).",
    )
    ap.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Opcional: salvar relatório em CSV (path).",
    )
    args = ap.parse_args()

    root = Path(args.folder)
    if not root.exists():
        print(f"[ERRO] Pasta não existe: {root}")
        return 2

    extensions = {e if e.startswith(".") else f".{e}" for e in args.ext}

    results = []
    total = 0
    with_iso = 0

    for fp in iter_instance_files(root, extensions=extensions):
        total += 1
        try:
            G, n_header = read_graph_edgelist_header_n(fp)
            iso = sum(1 for _, d in G.degree() if d == 0)
            if iso >= args.min:
                with_iso += 1
                results.append(
                    (fp, n_header, G.number_of_nodes(), G.number_of_edges(), iso)
                )
        except Exception as e:
            print(f"[AVISO] Falha em {fp}: {e}")

    # imprime
    for fp, n_header, n, m, iso in sorted(results, key=lambda x: (-x[4], str(x[0]))):
        print(f"{fp}  n_header={n_header}  n={n}  m={m}  isolados={iso}")

    print(f"\nTotal arquivos: {total}")
    print(f"Com isolados (>= {args.min}): {with_iso}")

    # csv opcional
    if args.csv:
        import csv

        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["arquivo", "n_header", "n", "m", "isolados"])
            for fp, n_header, n, m, iso in sorted(
                results, key=lambda x: (-x[4], str(x[0]))
            ):
                w.writerow([str(fp), n_header, n, m, iso])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
