from __future__ import annotations

import csv
import math
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import networkx as nx

# ==========================================
# CÓDIGO DE CARREGAMENTO
# ==========================================


@dataclass(frozen=True)
class GraphInstance:
    name: str
    path: Path
    G: nx.Graph
    n: int
    m: int
    density: float


def iter_instance_files(
    root: str | Path, extensions: Optional[set[str]] = None
) -> Iterator[Path]:
    """
    Itera recursivamente em arquivos de instância na pasta fornecida.
    """
    root = Path(root)
    for p in root.rglob("*"):
        if p.is_file():
            # Se extensions for None, aceita tudo. Senão, filtra pela extensão.
            if extensions is None or p.suffix.lower() in extensions:
                yield p


def read_graph_edgelist(path: str | Path, nodetype=int) -> nx.Graph:
    """
    Lê um grafo no formato de lista de arestas:
        n m
        u v
        ...
    """
    path = Path(path)

    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")

        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")

        # n_header = int(parts[0])
        # m_header = int(parts[1])

        g_raw = nx.Graph()
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts_line = line.split()
            if len(parts_line) < 2:
                continue

            u_str, v_str = parts_line[:2]
            u = nodetype(u_str)
            v = nodetype(v_str)
            g_raw.add_edge(u, v)

    # Remove loops (u == v)
    loops = [(u, v) for (u, v) in g_raw.edges() if u == v]
    if loops:
        g_raw.remove_edges_from(loops)

    # Relabel para 0..n-1 para garantir consistência
    nodes_sorted = sorted(g_raw.nodes())
    mapping = {old: new for new, old in enumerate(nodes_sorted)}
    g = nx.relabel_nodes(g_raw, mapping, copy=True)

    return g


def load_instance(path: str | Path) -> GraphInstance:
    path = Path(path)
    g = read_graph_edgelist(path, nodetype=int)

    n = g.number_of_nodes()
    m = g.number_of_edges()
    dens = nx.density(g)

    return GraphInstance(
        name=path.stem,
        path=path,
        G=g,
        n=n,
        m=m,
        density=dens,
    )


# ==========================================
# CÓDIGO DE CÁLCULO DOS LIMITANTES
# ==========================================


def calculate_roman3_bounds(G: nx.Graph, n: int) -> tuple[int, int]:
    """
    Calcula os limitantes para Roman {3}-Domination baseados em Ebrahimi et al. (2023).
    LB >= (2n + Delta + 1) / (Delta + 3)
    UB <= n - Delta + 2
    """
    if n == 0:
        return 0, 0

    # Calcular Grau Máximo (Delta)
    degrees = [d for _, d in G.degree()]

    if not degrees:
        delta = 0
    else:
        delta = max(degrees)

    # --- Limitante Inferior (Lower Bound) ---
    lb_val = (2 * n + delta + 1) / (delta + 3)
    lower_bound = math.ceil(lb_val)

    # --- Limitante Superior (Upper Bound) ---
    upper_bound = n - delta + 2
    # Ajuste: UB nunca pode ser maior que n
    upper_bound = min(upper_bound, n)

    return lower_bound, upper_bound


def process_dataset(input_folder: str, output_csv: str):
    input_path = Path(input_folder)

    if not input_path.exists():
        print(f"[ERRO] A pasta de entrada não existe: {input_folder}")
        sys.exit(1)

    print(f"--- Iniciando processamento ---")
    print(f"Entrada: {input_folder}")
    print(f"Saída:   {output_csv}")

    # Prepara o CSV
    with open(output_csv, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Grafo", "Lower Bound", "Upper Bound"])

        count = 0
        success_count = 0

        # Filtra apenas .txt (se tiver outras extensões, adicione no conjunto abaixo ou passe None)
        extensions_to_read = {".txt"}

        for file_path in iter_instance_files(input_path, extensions=extensions_to_read):
            count += 1
            try:
                # 1. Carregar
                instance = load_instance(file_path)

                # 2. Calcular
                lb, ub = calculate_roman3_bounds(instance.G, instance.n)

                # 3. Salvar
                writer.writerow([instance.name, lb, ub])
                success_count += 1

                if success_count % 50 == 0:
                    print(f"Processados {success_count} grafos com sucesso...")

            except Exception as e:
                print(f"[AVISO] Falha ao processar '{file_path.name}': {e}")

    print(f"--- Concluído! ---")
    print(f"Total encontrado: {count}")
    print(f"Total processado: {success_count}")
    print(f"Arquivo salvo em: {output_csv}")


if __name__ == "__main__":
    # Configuração dos argumentos da linha de comando
    parser = argparse.ArgumentParser(
        description="Calcula limitantes (bounds) Roman {3}-Domination para um conjunto de grafos."
    )

    parser.add_argument(
        "input_folder",
        type=str,
        help="Caminho da pasta contendo os arquivos dos grafos (.txt)",
    )

    parser.add_argument(
        "output_file",
        type=str,
        help="Caminho/Nome do arquivo CSV de saída (ex: resultados.csv)",
    )

    args = parser.parse_args()

    # Chama a função principal passando os argumentos
    process_dataset(args.input_folder, args.output_file)

