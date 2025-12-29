from __future__ import annotations

import argparse
from pathlib import Path

from pli_model.io import iter_instance_files, load_instance
from pli_model.io import append_result, RunResultRow
from pli_model.solve import SolveConfig, solve_graph


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Executa o PLI (MR3DP) nas instâncias e salva um resultados.csv por subpasta."
    )
    ap.add_argument(
        "--input", default="data/instances", help="Pasta raiz das instâncias"
    )
    ap.add_argument("--output", default="data/results/pli", help="Pasta raiz de saída")
    ap.add_argument(
        "--time-limit", type=int, default=900, help="Limite de tempo (segundos)"
    )
    ap.add_argument(
        "--prefer-cplex-under-n",
        type=int,
        default=333,
        help="Preferir CPLEX se n <= este valor (se disponível)",
    )
    ap.add_argument("--tee", action="store_true", help="Mostrar log do solver")
    ap.add_argument(
        "--ext",
        nargs="*",
        default=None,
        help="Extensões permitidas (ex.: .txt .edgelist). Se vazio, pega tudo.",
    )
    args = ap.parse_args()

    input_root = Path(args.input)
    output_root = Path(args.output)
    exts = set(args.ext) if args.ext else None

    cfg = SolveConfig(
        time_limit_s=args.time_limit,
        prefer_cplex_under_n=args.prefer_cplex_under_n,
        tee=args.tee,
    )

    for file_path in iter_instance_files(input_root, extensions=exts):
        # 1 CSV por subpasta dentro de data/instances (ex.: small/medium/large)
        rel = file_path.relative_to(input_root)
        group = rel.parts[0] if len(rel.parts) > 1 else "root"
        csv_path = output_root / group / "resultados.csv"

        try:
            inst = load_instance(file_path)
            res = solve_graph(inst.G, cfg)

            append_result(
                csv_path,
                RunResultRow(
                    filename=file_path.name,
                    vertex=inst.n,
                    edge=inst.m,
                    density=inst.density,
                    objective=res.objective,
                    runtime_s=res.runtime_s,
                    status=res.status,
                    message=f"solver={res.solver_name}; term={res.termination_condition}",
                ),
            )

        except Exception as e:
            append_result(
                csv_path,
                RunResultRow(
                    filename=file_path.name,
                    vertex=0,
                    edge=0,
                    density=0.0,
                    objective=None,
                    runtime_s=0.0,
                    status="Error",
                    message=str(e),
                ),
            )


if __name__ == "__main__":
    main()
