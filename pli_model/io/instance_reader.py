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


def read_graph_edgelist(path: str | Path, nodetype=int) -> nx.Graph:
    """
    Lê um grafo no formato:
        n m
        u v
        u v

    Faz saneamento:
      - remove laços
      - relabela nós para 0..n-1
    """
    path = Path(path)

    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")

        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")

        # n_header e m_header são lidos, mas não confiamos cegamente neles
        # (usamos o grafo construído para garantir consistência)
        n_header = int(parts[0])
        m_header = int(parts[1])

        g_raw = nx.Graph()
        for line in f:
            line = line.strip()
            if not line:
                continue

            u_str, v_str = line.split()[:2]
            u = nodetype(u_str)
            v = nodetype(v_str)
            g_raw.add_edge(u, v)

    # Remove loops (u == v)
    loops = [(u, v) for (u, v) in g_raw.edges() if u == v]
    if loops:
        g_raw.remove_edges_from(loops)

    # Relabel para 0..n-1 (ordem determinística)
    nodes_sorted = sorted(g_raw.nodes())
    mapping = {old: new for new, old in enumerate(nodes_sorted)}
    g = nx.relabel_nodes(g_raw, mapping, copy=True)

    return g


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
