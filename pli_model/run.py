from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pli_model.io import iter_instance_files, load_instance
from pli_model.io import append_result, RunResultRow
from pli_model.solve import SolveConfig, solve_graph


def read_nm_header(path: str | Path) -> tuple[int, int]:
    """
    Lê apenas a primeira linha (n m) do arquivo.
    Usado para ordenar instâncias sem carregar o grafo inteiro.
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


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Executa o PLI (MR3DP) nas instâncias e salva CSV por subpasta."
    )
    ap.add_argument(
        "--input", default="data/instances", help="Pasta raiz das instâncias"
    )
    ap.add_argument("--output", default="data/results/pli", help="Pasta raiz de saída")
    ap.add_argument(
        "--time-limit", type=int, default=900, help="Limite de tempo (segundos)"
    )
    ap.add_argument("--tee", action="store_true", help="Mostrar log do solver")
    ap.add_argument(
        "--solver", default="cbc", choices=["cbc", "gurobi"], help="Solver a ser usado"
    )
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
        solver=args.solver,
        tee=args.tee,
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

    for file_path in files:
        total += 1

        # Mantém a lógica "1 CSV por subpasta"
        rel = file_path.relative_to(input_root)
        group = rel.parts[0] if len(rel.parts) > 1 else "root"
        csv_path = output_root / group / "resultados.csv"

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
    print(f"Concluído! {success}/{total} instâncias processadas com sucesso.")


if __name__ == "__main__":
    main()
