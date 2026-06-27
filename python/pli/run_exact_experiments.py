from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_ROOT))

from pli import heuristics
from pli.io import (
    RunResultRow,
    append_result,
    iter_instance_files,
    load_instance,
    read_nm_header,
)
from pli.solve import SolveConfig, solve_graph

RESULT_FILENAMES = {
    "CUBIC": "cubic_results.csv",
    "DIMACS": "dimacs_resultados.csv",
    "HB": "harwell_boieng_results.csv",
}


def instance_id(value: str | Path) -> str:
    name = Path(value).name
    return name[:-4] if name.casefold().endswith(".col") else name


def completed_instances(csv_path: Path) -> set[str]:
    if not csv_path.is_file():
        return set()
    with csv_path.open(newline="", encoding="utf-8") as result_file:
        return {
            instance_id(row["Grafo"])
            for row in csv.DictReader(result_file)
            if row.get("Grafo") and row.get("Status", "").casefold() != "error"
        }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Executa o PLI (MR3DP) nas instâncias e salva CSV por subpasta."
    )
    ap.add_argument(
        "--input", default="data/instances", help="Pasta raiz das instâncias"
    )
    ap.add_argument("--output", default="results/pli", help="Pasta raiz de saída")
    ap.add_argument(
        "--time-limit", type=int, default=900, help="Limite de tempo (segundos)"
    )
    ap.add_argument("--tee", action="store_true", help="Mostrar log do solver")
    ap.add_argument("--solver", default="gurobi", choices=["gurobi"])
    ap.add_argument(
        "--ext",
        nargs="*",
        default=None,
        help="Extensões permitidas (ex.: .col .txt .edgelist). Se vazio, pega tudo.",
    )
    args = ap.parse_args()

    input_root = Path(args.input)
    output_root = Path(args.output)
    exts = set(args.ext) if args.ext else None

    cfg = SolveConfig(
        time_limit_s=args.time_limit,
        solver=args.solver,
        tee=args.tee,
        heuristics=(heuristics.trivial, heuristics.h1, heuristics.h2, heuristics.h3),
        use_warmstart=True,
    )

    print("=== PLI Model - MR3DP ===")
    print(f"Buscando instâncias em: {input_root}")
    print(f"Salvando resultados em: {output_root}")
    print(f"Configuração: solver={cfg.solver}, time_limit={cfg.time_limit_s}s")
    print("-" * 60)

    # Coleta e ordena instâncias (primeiro menos vértices; desempata por m e nome)
    files = list(iter_instance_files(input_root, extensions=exts))
    files.sort(key=lambda p: (*read_nm_header(p), p.name))

    total = 0
    success = 0
    skipped = 0
    completed_by_csv: dict[Path, set[str]] = {}

    for file_path in files:
        total += 1

        # Mantém a lógica "1 CSV por subpasta"
        rel = file_path.relative_to(input_root)
        group = rel.parts[0] if len(rel.parts) > 1 else "root"
        csv_path = output_root / group / RESULT_FILENAMES.get(group, "resultados.csv")
        completed = completed_by_csv.setdefault(
            csv_path, completed_instances(csv_path)
        )
        if instance_id(file_path) in completed:
            skipped += 1
            print(f"[{total}] Ignorando resultado existente: {file_path.name}")
            continue

        print(f"[{total}] Processando: {file_path.name}...", end=" ", flush=True)

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

            success += 1
            completed.add(instance_id(file_path))
            print(f"✓ [{res.status}] obj={res.objective}, tempo={res.runtime_s:.2f}s")

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
            print(f"✗ ERRO: {str(e)}")

    print("-" * 60)
    print(
        f"Concluído: {success} processadas, {skipped} existentes, "
        f"{total - success - skipped} falhas."
    )


if __name__ == "__main__":
    main()
