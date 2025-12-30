from __future__ import annotations
from typing import Dict, Set
import networkx as nx

Labeling = Dict[int, int]  # v -> {0,1,2,3}


def trivial(G: nx.Graph) -> Labeling:
    """
    Heurística trivial:
    todos os vértices recebem rótulo 2.
    """
    return {v: 2 for v in G.nodes()}
