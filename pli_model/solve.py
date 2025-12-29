from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import time

import pyomo.environ as pyo
import networkx as nx

from .model import build_model_mr3dp


@dataclass(frozen=True)
class SolveConfig:
    time_limit_s: int = 900
    prefer_cplex_under_n: int = 333
    tee: bool = False


@dataclass(frozen=True)
class SolveResult:
    status: str  # "Optimal", "Best Found", "Infeasible"
    objective: Optional[float]
    runtime_s: float
    solver_name: str
    termination_condition: str


def _pick_solver(n_nodes: int, cfg: SolveConfig) -> Tuple[str, pyo.SolverFactory]:
    """
    Escolhe solver e aplica time limit.
    - Tenta CPLEX para instâncias menores (se disponível)
    - Caso contrário usa CBC (se disponível)
    """
    if n_nodes <= cfg.prefer_cplex_under_n:
        cplex = pyo.SolverFactory("cplex")
        if cplex is not None and cplex.available(exception_flag=False):
            cplex.options["timelimit"] = cfg.time_limit_s
            return "cplex", cplex

    cbc = pyo.SolverFactory("cbc")
    if cbc is None or not cbc.available(exception_flag=False):
        raise RuntimeError(
            "Solver CBC não está disponível. Instale o CBC ou configure outro solver."
        )
    cbc.options["seconds"] = cfg.time_limit_s
    return "cbc", cbc


def solve_graph(G: nx.Graph, cfg: SolveConfig = SolveConfig()) -> SolveResult:
    """
    Monta e resolve o PLI MR3DP para um grafo.
    """
    model, _ = build_model_mr3dp(G)
    solver_name, solver = _pick_solver(G.number_of_nodes(), cfg)

    t0 = time.time()
    results = solver.solve(model, tee=cfg.tee)
    runtime = time.time() - t0

    term = results.solver.termination_condition

    if term == pyo.TerminationCondition.optimal:
        return SolveResult(
            "Optimal", float(pyo.value(model.obj)), runtime, solver_name, str(term)
        )

    if term in {
        pyo.TerminationCondition.feasible,
        pyo.TerminationCondition.maxTimeLimit,
    }:
        return SolveResult(
            "Best Found", float(pyo.value(model.obj)), runtime, solver_name, str(term)
        )

    return SolveResult("Infeasible", None, runtime, solver_name, str(term))
