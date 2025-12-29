from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

import networkx as nx
import pyomo.environ as pyo


@dataclass(frozen=True)
class ModelData:
    nodes: List[int]
    closed_neighborhood: Dict[int, Set[int]]  # N_G[v] (v + vizinhos)


def build_model_mr3dp(G: nx.Graph) -> tuple[pyo.ConcreteModel, ModelData]:
    """
    Monta o PLI (Pyomo) do MR3DP a partir de um grafo NetworkX.
    """
    model = pyo.ConcreteModel()

    # Conjunto de vértices do grafo
    nodes = list(G.nodes())

    # Vértices do modelo
    model.V = pyo.Set(initialize=nodes, ordered=True)

    # NG[v] = vizinhança fechada de v (v + seus vizinhos)
    NG: Dict[int, Set[int]] = {v: set(G.neighbors(v)) | {v} for v in nodes}

    # Variáveis binárias do PLI
    model.a = pyo.Var(model.V, within=pyo.Binary)  # a[v] = 1 -> rótulo 0
    model.b = pyo.Var(model.V, within=pyo.Binary)  # b[v] = 1 -> rótulo 1
    model.c = pyo.Var(model.V, within=pyo.Binary)  # c[v] = 1 -> rótulo 2
    model.d = pyo.Var(model.V, within=pyo.Binary)  # d[v] = 1 -> rótulo 3

    # Restrição (8.3): cada vértice recebe exatamente um rótulo
    def one_label_rule(m, v):
        return m.a[v] + m.b[v] + m.c[v] + m.d[v] == 1

    # condição de rotulação da dominação {3}-romana (com vizinhança fechada)
    # Implementa: 1 - (a_v + b_v) + sum_{u in NG[v]} (b_u + 2c_u + 3d_u) >= 3
    def mr3dp_rule(m, v):
        lhs = 1 - (m.a[v] + m.b[v])
        lhs += sum(m.b[u] + 2 * m.c[u] + 3 * m.d[u] for u in NG[v])
        return lhs >= 3

    model.one_label = pyo.Constraint(model.V, rule=one_label_rule)
    model.mr3dp = pyo.Constraint(model.V, rule=mr3dp_rule)

    # minimizar soma dos pesos dos rótulos (0,1,2,3)
    model.obj = pyo.Objective(
        expr=sum(model.b[v] + 2 * model.c[v] + 3 * model.d[v] for v in model.V),
        sense=pyo.minimize,
    )

    return model, ModelData(nodes=nodes, closed_neighborhood=NG)
