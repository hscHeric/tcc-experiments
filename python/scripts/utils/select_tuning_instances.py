#!/usr/bin/env python3
import pandas as pd
from pathlib import Path


def main():
    base_dir = (
        Path(__file__).resolve().parents[3] if "__file__" in locals() else Path(".")
    )
    pli_results_dir = base_dir / "results" / "pli"
    output_file = base_dir / "experiments" / "tuning" / "instances-list.txt"

    csv_files = [
        pli_results_dir / "CUBIC" / "cubic_results.csv",
        pli_results_dir / "DIMACS" / "dimacs_resultados.csv",
        pli_results_dir / "HB" / "harwell_boieng_results.csv",
    ]

    all_instances = []

    for csv_path in csv_files:
        if not csv_path.exists():
            print(f"Aviso: Arquivo não encontrado: {csv_path}")
            continue

        # Lendo o CSV
        df = pd.read_csv(csv_path)

        instance_col = "Grafo"
        time_col = "Tempo (s)"

        for _, row in df.iterrows():
            inst_name = str(row[instance_col])
            runtime = float(row[time_col])

            if "CUBIC" in str(csv_path):
                rel_path = f"CUBIC/{inst_name}"
            elif "DIMACS" in str(csv_path):
                rel_path = f"DIMACS/{inst_name}"
            elif "HB" in str(csv_path):
                rel_path = f"HB/{inst_name}"
            else:
                rel_path = inst_name

            if not rel_path.endswith(".col"):
                rel_path += ".col"

            all_instances.append({"path": rel_path, "runtime": runtime})

    if not all_instances:
        print(
            "Nenhuma instância foi carregada. Verifique os caminhos dos arquivos CSV."
        )
        return

    df_all = pd.DataFrame(all_instances)

    df_all = df_all.sort_values(by="runtime", ascending=False).reset_index(drop=True)

    total_instancias = len(df_all)
    qtd_tuning = max(1, int(total_instancias * 0.30))

    df_tuning = df_all.head(qtd_tuning)

    print(f"Total de instâncias encontradas no PLI: {total_instancias}")
    print(f"Selecionando as {qtd_tuning} instâncias mais difíceis (Top 30%).")
    print(
        f"Tempo da mais difícil: {df_tuning.iloc[0]['runtime']:.2f}s | Tempo da menos difícil do grupo: {df_tuning.iloc[-1]['runtime']:.2f}s"
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        for path in df_tuning["path"]:
            f.write(f"{path}\n")

    print(f"Arquivo gerado com sucesso em: {output_file}")


if __name__ == "__main__":
    main()
