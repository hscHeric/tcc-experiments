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
    solver: str = "cbc"  # "cbc" ou "gurobi"
    tee: bool = False


@dataclass(frozen=True)
class SolveResult:
    status: str  # "Optimal", "Best Found", "Infeasible"
    objective: Optional[float]
    runtime_s: float
    solver_name: str
    termination_condition: str


def _pick_solver(cfg: SolveConfig) -> Tuple[str, pyo.SolverFactory]:
    solver_name = cfg.solver.lower().strip()

    if solver_name == "gurobi":
        solver = pyo.SolverFactory("gurobi")
        if solver is None or not solver.available(exception_flag=False):
            raise RuntimeError("Solver GUROBI não está disponível no Pyomo.")
        solver.options["TimeLimit"] = cfg.time_limit_s
        return "gurobi", solver

    # if solver_name == "cbc":
    #     solver = pyo.SolverFactory("cbc")
    #     if solver is None or not solver.available(exception_flag=False):
    #         raise RuntimeError("Solver CBC não está disponível no Pyomo.")
    #     solver.options["seconds"] = cfg.time_limit_s
    #     return "cbc", solver
    #
    raise ValueError(f"Solver inválido: {cfg.solver}. Use 'cbc' ou 'gurobi'.")


def solve_graph(G: nx.Graph, cfg: SolveConfig = SolveConfig()) -> SolveResult:
    """
    Monta e resolve o PLI MR3DP para um grafo.
    """
    model, _ = build_model_mr3dp(G)
    solver_name, solver = _pick_solver(cfg)

    start = time.time()
    results = solver.solve(model, tee=cfg.tee)
    runtime = time.time() - start

    term = results.solver.termination_condition

    if term == pyo.TerminationCondition.optimal:
        return SolveResult(
            status="Optimal",
            objective=float(pyo.value(model.obj)),
            runtime_s=runtime,
            solver_name=solver_name,
            termination_condition=str(term),
        )

    if term in {
        pyo.TerminationCondition.feasible,
        pyo.TerminationCondition.maxTimeLimit,
    }:
        return SolveResult(
            status="Best Found",
            objective=float(pyo.value(model.obj)),
            runtime_s=runtime,
            solver_name=solver_name,
            termination_condition=str(term),
        )

    return SolveResult(
        status="Infeasible",
        objective=None,
        runtime_s=runtime,
        solver_name=solver_name,
        termination_condition=str(term),
    )
