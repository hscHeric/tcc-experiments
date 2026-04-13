from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Callable, Dict, List
import time

import pyomo.environ as pyo
import networkx as nx

from .model import build_model_mr3dp

Labeling = Dict[int, int]  # v -> {0,1,2,3}
Heuristic = Callable[[nx.Graph], Optional[Labeling]]  # retorna rotulação ou None


@dataclass(frozen=True)
class SolveConfig:
    time_limit_s: int = 900
    solver: str = "cbc"  # "cbc" ou "gurobi"
    tee: bool = False

    # warm start acoplável
    heuristics: Tuple[Heuristic, ...] = ()  # várias heurísticas
    use_warmstart: bool = True  # liga/desliga


@dataclass(frozen=True)
class SolveResult:
    status: str
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

    raise ValueError(f"Solver inválido: {cfg.solver}. Use 'cbc' ou 'gurobi'.")


def _label_cost(labeling: Labeling) -> int:
    w = {0: 0, 1: 1, 2: 2, 3: 3}
    return sum(w[labeling[v]] for v in labeling)


def _apply_mip_start(model: pyo.ConcreteModel, labeling: Labeling) -> None:
    # model tem a,b,c,d (one-hot) :contentReference[oaicite:1]{index=1}
    for v in model.V:
        lab = labeling.get(int(v), None)
        if lab is None:
            continue
        model.a[v].value = 1 if lab == 0 else 0
        model.b[v].value = 1 if lab == 1 else 0
        model.c[v].value = 1 if lab == 2 else 0
        model.d[v].value = 1 if lab == 3 else 0


def _best_labeling_from_heuristics(
    G: nx.Graph, hs: Tuple[Heuristic, ...]
) -> Optional[Labeling]:
    best: Optional[Labeling] = None
    best_cost = None

    for h in hs:
        try:
            lab = h(G)
        except Exception:
            lab = None
        if not lab:
            continue
        c = _label_cost(lab)
        if best is None or c < best_cost:
            best, best_cost = lab, c

    return best


def solve_graph(G: nx.Graph, cfg: SolveConfig = SolveConfig()) -> SolveResult:
    model, _ = build_model_mr3dp(G)  # :contentReference[oaicite:2]{index=2}
    solver_name, solver = _pick_solver(cfg)

    # escolhe o melhor warm start a partir de várias heurísticas (se houver)
    warm = None
    if cfg.use_warmstart and cfg.heuristics:
        warm = _best_labeling_from_heuristics(G, cfg.heuristics)
        if warm is not None:
            _apply_mip_start(model, warm)

    start = time.time()
    results = solver.solve(
        model,
        tee=cfg.tee,
        warmstart=(
            warm is not None
        ),  # Pyomo -> passa MIP start ao Gurobi (quando possível)
    )
    runtime = time.time() - start

    term = results.solver.termination_condition

    if term == pyo.TerminationCondition.optimal:
        return SolveResult(
            "Ótimo", float(pyo.value(model.obj)), runtime, solver_name, str(term)
        )

    if term in {
        pyo.TerminationCondition.feasible,
        pyo.TerminationCondition.maxTimeLimit,
    }:
        return SolveResult(
            "Melhor", float(pyo.value(model.obj)), runtime, solver_name, str(term)
        )

    return SolveResult("Infeasible", None, runtime, solver_name, str(term))
