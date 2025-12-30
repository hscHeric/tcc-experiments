from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Adiciona a raiz do projeto ao Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pli_model.io import iter_instance_files, load_instance
from pli_model.io import append_result, RunResultRow
from pli_model.solve import SolveConfig, solve_graph


def process_instance(
    file_path: Path,
    input_root: Path,
    output_root: Path,
    cfg: SolveConfig,
):
    """
    Processa UMA instância: carrega, resolve e grava no CSV do grupo.
    Precisa ficar no topo do módulo (não dentro da main) para funcionar com ProcessPool.
    """
    rel = file_path.relative_to(input_root)
    group = rel.parts[0] if len(rel.parts) > 1 else "root"
    csv_path = output_root / group / "resultados.csv"

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

    return file_path.name, res


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Executa o PLI (MR3DP) nas instâncias e salva CSV por subpasta (paralelo)."
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
    ap.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="Quantidade de workers (processos). Padrão: nº de CPUs.",
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
    print(
        f"Configuração: solver={cfg.solver}, time_limit={cfg.time_limit_s}s, jobs={args.jobs}"
    )
    print("-" * 60)

    files = list(iter_instance_files(input_root, extensions=exts))
    total = len(files)
    success = 0

    if total == 0:
        print("Nenhuma instância encontrada.")
        return

    # ProcessPoolExecutor: 1 instância por processo (melhor para CPU/solver externo)
    with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        futures = [
            executor.submit(process_instance, file_path, input_root, output_root, cfg)
            for file_path in files
        ]

        for i, fut in enumerate(as_completed(futures), start=1):
            try:
                name, res = fut.result()
                success += 1
                print(
                    f"[{i}/{total}] {name} [{res.status}] obj={res.objective}, tempo={res.runtime_s:.2f}s"
                )
            except Exception as e:
                # Se der erro aqui, pode ser erro de carga/solve ou erro de pickle/worker.
                # Tenta ao menos imprimir.
                print(f"[{i}/{total}]  ERRO: {e}")

    print("-" * 60)
    print(f"Concluído! {success}/{total} instâncias processadas com sucesso.")


if __name__ == "__main__":
    main()
