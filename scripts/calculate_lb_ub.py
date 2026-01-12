from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Tuple
import csv
import math
import sys

import networkx as nx


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
    Itera recursivamente em arquivos de instância.
    Por padrão, pega todos os arquivos. Se quiser filtrar:
      extensions={".col"} (por exemplo)
    """
    root = Path(root)
    for p in root.rglob("*"):
        if p.is_file():
            if extensions is None or p.suffix.lower() in extensions:
                yield p


def load_instance(path: str | Path) -> GraphInstance:
    """
    Carrega 1 instância (1 arquivo) como GraphInstance.

    Agora suporta:
      - DIMACS .col (linhas 'c', 'p edge n m', 'e u v')
      - Formato antigo:
            n m
            u v
            u v
    """
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


def _peek_nonempty_noncomment_line(path: Path) -> str:
    """
    Retorna a primeira linha relevante para detecção de formato:
    - ignora vazias
    - ignora comentários DIMACS (c ...)
    """
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("c"):
                continue
            return line
    return ""


def _is_dimacs_col(path: Path) -> bool:
    """
    Heurística de detecção:
      - extensão .col, ou
      - primeira linha relevante começa com 'p ' (DIMACS), ou
      - contém tokens típicos 'p edge'/'p col'
    """
    if path.suffix.lower() == ".col":
        return True
    first = _peek_nonempty_noncomment_line(path)
    if not first:
        return False
    if first.startswith("p "):
        return True
    parts = first.split()
    return len(parts) >= 2 and parts[0] == "p" and parts[1] in {"edge", "col"}


def _read_dimacs_col(path: Path) -> nx.Graph:
    """
    Lê grafo em DIMACS (.col), típico de instâncias de coloração:
      c comment...
      p edge n m
      e u v
      e u v
    Nós geralmente são 1..n. Aqui convertemos para 0..n-1.

    Saneamento:
      - remove laços
      - ignora linhas inválidas
      - garante nós isolados (0..n-1) conforme header
      - não duplica arestas (nx.Graph já garante)
    """
    n_header = None
    g = nx.Graph()

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("c"):
                continue

            parts = line.split()
            if not parts:
                continue

            tag = parts[0]

            # Header: p edge n m  (ou p col n m)
            if tag == "p":
                # aceita "p edge n m" e "p col n m"
                if len(parts) < 4:
                    raise ValueError("Header DIMACS inválido. Esperado: 'p edge n m'")
                if parts[1] not in {"edge", "col"}:
                    raise ValueError(
                        f"Header DIMACS inválido. Esperado 'p edge' ou 'p col', veio: {parts[1]!r}"
                    )
                n_header = int(parts[2])
                # m_header = int(parts[3])  # pode divergir; não é necessário
                continue

            # Aresta: e u v
            if tag == "e":
                if len(parts) < 3:
                    continue
                u = int(parts[1])
                v = int(parts[2])

                # DIMACS costuma ser 1-based
                u0 = u - 1
                v0 = v - 1
                if u0 == v0:
                    continue
                g.add_edge(u0, v0)
                continue

            # Algumas variações usam "a u v" ou outras linhas; ignoramos.
            continue

    if n_header is None:
        raise ValueError("Arquivo DIMACS sem linha de header 'p edge n m'.")

    # Garante nós isolados (0..n-1)
    g.add_nodes_from(range(n_header))
    return g


def _read_legacy_nm_edgelist(path: Path, nodetype=int) -> nx.Graph:
    """
    Formato antigo:
        n m
        u v
        u v

    Saneamento:
      - remove laços
      - relabela nós para 0..k-1 (ordem determinística)
      - ADICIONA vértices isolados implícitos do header, completando até n_header
    """
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")

        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")

        n_header = int(parts[0])
        # m_header = int(parts[1])  # pode divergir se houver duplicatas/loops; não é necessário

        g_raw = nx.Graph()
        for line in f:
            line = line.strip()
            if not line:
                continue

            pl = line.split()
            if len(pl) < 2:
                continue

            u = nodetype(pl[0])
            v = nodetype(pl[1])
            if u == v:
                continue
            g_raw.add_edge(u, v)

    # Relabel para 0..k-1 (ordem determinística)
    nodes_sorted = sorted(g_raw.nodes())
    mapping = {old: new for new, old in enumerate(nodes_sorted)}
    g = nx.relabel_nodes(g_raw, mapping, copy=True)

    # inclui isolados do header (se existirem)
    k = g.number_of_nodes()
    if n_header > k:
        g.add_nodes_from(range(n_header))

    return g


def read_graph_edgelist(path: str | Path, nodetype=int) -> nx.Graph:
    """
    Mantém a interface original, mas agora suporta DIMACS .col.

    - Se detectar DIMACS (.col), lê via _read_dimacs_col()
    - Caso contrário, lê no formato antigo "n m" + arestas
    """
    path = Path(path)
    if _is_dimacs_col(path):
        return _read_dimacs_col(path)
    return _read_legacy_nm_edgelist(path, nodetype=nodetype)


def read_nm_header(path: str | Path) -> tuple[int, int]:
    """
    Lê (n, m) do arquivo sem carregar o grafo inteiro.

    Suporta:
      - DIMACS .col: lê a linha "p edge n m" (ou "p col n m")
      - Formato antigo: lê a primeira linha "n m"
    """
    path = Path(path)

    if _is_dimacs_col(path):
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("c"):
                    continue
                parts = line.split()
                if parts and parts[0] == "p":
                    if len(parts) < 4:
                        raise ValueError(
                            "Header DIMACS inválido. Esperado: 'p edge n m'"
                        )
                    if parts[1] not in {"edge", "col"}:
                        raise ValueError(
                            f"Header DIMACS inválido. Esperado 'p edge' ou 'p col', veio: {parts[1]!r}"
                        )
                    return int(parts[2]), int(parts[3])
        raise ValueError("Arquivo DIMACS sem linha de header 'p edge n m'.")

    # legado
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()
        if not header:
            raise ValueError("Arquivo vazio")
        parts = header.strip().split()
        if len(parts) < 2:
            raise ValueError("Primeira linha deve conter: n m")
        return int(parts[0]), int(parts[1])


def component_lb(n: int, delta: int) -> int:
    if n == 1:
        return 2
    if n in {2, 3}:
        return 3
    return math.ceil(
        min(
            3 * n / (delta + 2),
            (2 * n + delta) / (delta + 1),
        )
    )


def component_ub(n: int, delta: int) -> int:
    if n == 1:
        return 2
    if n in {2, 3}:
        return 3
    return n - delta + 2


def graph_bounds(G: nx.Graph) -> tuple[int, int]:
    lb_total = 0
    ub_total = 0

    for nodes in nx.connected_components(G):
        Gi = G.subgraph(nodes)
        ni = Gi.number_of_nodes()
        deltai = max(dict(Gi.degree()).values())

        lb_total += component_lb(ni, deltai)
        ub_total += component_ub(ni, deltai)

    return lb_total, ub_total


def process_csv(instances_dir: Path, csv_in: Path, csv_out: Path) -> None:
    # indexa arquivos de instância por stem (nome sem extensão)
    instance_map = {}
    for p in iter_instance_files(instances_dir):
        instance_map[p.stem] = p

    with (
        open(csv_in, newline="", encoding="utf-8") as fin,
        open(csv_out, "w", newline="", encoding="utf-8") as fout,
    ):
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames + ["LB", "UB"]

        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            raw_name = row["Grafo"]
            stem = Path(raw_name).stem
            row["Grafo"] = stem  # remove .col do CSV

            if stem not in instance_map:
                raise FileNotFoundError(
                    f"Instância '{stem}' não encontrada em {instances_dir}"
                )

            G = read_graph_edgelist(instance_map[stem])

            lb, ub = graph_bounds(G)

            row["LB"] = lb
            row["UB"] = ub

            writer.writerow(row)


def main():
    if len(sys.argv) != 4:
        print(
            "Uso:\n  python add_bounds.py <pasta_instancias> <entrada.csv> <saida.csv>",
            file=sys.stderr,
        )
        sys.exit(1)

    instances_dir = Path(sys.argv[1])
    csv_in = Path(sys.argv[2])
    csv_out = Path(sys.argv[3])

    process_csv(instances_dir, csv_in, csv_out)


if __name__ == "__main__":
    main()
