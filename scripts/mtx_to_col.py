import os
import argparse
from scipy.io import mmread


def mtx_para_dimacs_col(mtx_path, col_path):
    """Converte um arquivo .mtx para .col (DIMACS) com loops para vértices isolados"""
    matriz = mmread(mtx_path).tocoo()
    nrows, ncols = matriz.shape
    arestas = set()

    # Adiciona arestas não-diagonais
    for i, j in zip(matriz.row, matriz.col):
        if i != j:
            u, v = i + 1, j + 1
            if u > v:
                u, v = v, u
            arestas.add((u, v))

    # Vértices isolados
    todos_vertices = set(range(1, nrows + 1))
    vertices_com_arestas = set(u for u, v in arestas) | set(v for u, v in arestas)
    isolados = todos_vertices - vertices_com_arestas

    # Adiciona loops para isolados
    for v in isolados:
        arestas.add((v, v))

    # Escreve arquivo .col
    with open(col_path, "w") as f:
        f.write(f"c Arquivo convertido de {os.path.basename(mtx_path)}\n")
        f.write(f"p edge {nrows} {len(arestas)}\n")
        for u, v in sorted(arestas):
            f.write(f"e {u} {v}\n")


def converter_e_substituir_mtx_por_col(pasta):
    """Converte todos os arquivos .mtx na pasta para .col e remove os .mtx"""
    if not os.path.isdir(pasta):
        print(f"[ERRO] Pasta não encontrada: {pasta}")
        return

    arquivos = [f for f in os.listdir(pasta) if f.endswith(".mtx")]
    if not arquivos:
        print(f"Nenhum arquivo .mtx encontrado em {pasta}")
        return

    for arquivo in arquivos:
        mtx_path = os.path.join(pasta, arquivo)
        col_path = os.path.join(pasta, arquivo.replace(".mtx", ".col"))
        try:
            mtx_para_dimacs_col(mtx_path, col_path)
            os.remove(mtx_path)
            print(f"{arquivo} -> {os.path.basename(col_path)} (MTX excluído)")
        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converte arquivos .mtx em uma pasta para .col DIMACS."
    )
    parser.add_argument("pasta", help="Caminho da pasta com arquivos .mtx")
    args = parser.parse_args()

    converter_e_substituir_mtx_por_col(args.pasta)
