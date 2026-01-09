from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import networkx as nx


@dataclass(frozen=True)
class GraphInstance:
    name: str
    path: Path
    G: nx.Graph
    n: int
    m: int
    density: float


def iter_instance_files(
    root: str | Path, extensions: Optional[set[str]] = None
) -> Iterator[Path]:
    """
    Itera recursivamente em arquivos de instância.
    Por padrão, pega todos os arquivos. Se quiser filtrar:
      extensions={".txt", ".edgelist", ".dat"} (por exemplo)
    """
    root = Path(root)
    for p in root.rglob("*"):
        if p.is_file():
            if extensions is None or p.suffix.lower() in extensions:
                yield p


def load_instance(path: str | Path) -> GraphInstance:
    """
    Carrega 1 instância (1 arquivo) como GraphInstance,
    assumindo cabeçalho 'n m' na primeira linha.
    """
    path = Path(path)
    g = read_graph_edgelist(path, nodetype=int)

    n = g.number_of_nodes()
    m = g.number_of_edges()
    dens = nx.density(g)

    return GraphInstance(
        name=path.stem,
        path=path,
        G=g,
        n=n,
        m=m,
        density=dens,
    )


def read_graph_edgelist(path: str | Path, nodetype=int) -> nx.Graph:
    """
    Lê um grafo no formato:
        n m
        u v
        u v

    Faz saneamento:
      - remove laços
      - relabela nós para 0..k-1 (ordem determinística)
      - ADICIONA vértices isolados implícitos do header, completando até n_header
    """
    path = Path(path)

    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")

        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")

        n_header = int(parts[0])
        # m_header = int(parts[1])  # pode divergir se houver duplicatas/loops; não é necessário

        g_raw = nx.Graph()
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
            g_raw.add_edge(u, v)

    # Relabel para 0..k-1 (ordem determinística)
    nodes_sorted = sorted(g_raw.nodes())
    mapping = {old: new for new, old in enumerate(nodes_sorted)}
    g = nx.relabel_nodes(g_raw, mapping, copy=True)

    # >>> CORREÇÃO: inclui isolados do header (se existirem)
    k = g.number_of_nodes()
    if n_header > k:
        g.add_nodes_from(range(n_header))

    return g


def read_nm_header(path: str | Path) -> tuple[int, int]:
    """
    Lê apenas a primeira linha (n m) do arquivo.
    Útil para ordenar instâncias sem carregar o grafo inteiro.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")
        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")
        return int(parts[0]), int(parts[1])

