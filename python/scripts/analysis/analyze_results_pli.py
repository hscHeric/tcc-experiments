import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse
import time


# Função para criar gráficos e salvar os resultados
def analyze_and_save(csv_file):
    # Lê o arquivo CSV
    df = pd.read_csv(csv_file)

    # Ignora a primeira coluna (nome do grafo), se necessário
    df = df.drop(columns=["Grafo"])

    # Obtém o nome da pasta pai
    parent_folder = os.path.basename(os.path.dirname(csv_file))

    # Cria uma pasta com o nome da pasta pai e o timestamp
    folder_name = ensure_unique_folder(parent_folder)

    # Cria a pasta, caso não exista
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Estatísticas descritivas
    stats = df.describe()
    stats.to_csv(os.path.join(folder_name, "estatisticas_descritivas.csv"))

    # Seleciona apenas as colunas numéricas para calcular a correlação
    numeric_df = df.select_dtypes(include="number")

    # Análise de correlação
    if not numeric_df.empty:
        correlation = numeric_df.corr()
        correlation.to_csv(os.path.join(folder_name, "correlacao.csv"))
    else:
        print(
            f"Aviso: Nenhuma coluna numérica encontrada no arquivo {csv_file} para cálculo de correlação."
        )

    # Gerar gráficos
    # 1. Gráfico de dispersão: Densidade vs Tempo de Execução
    plt.figure(figsize=(8, 6))
    sns.scatterplot(x="Densidade", y="Tempo (s)", data=df)
    plt.title("Densidade vs Tempo de Execução")
    plt.xlabel("Densidade")
    plt.ylabel("Tempo (s)")
    plt.savefig(os.path.join(folder_name, "densidade_vs_tempo.png"))
    plt.close()

    # 2. Histograma da Densidade
    plt.figure(figsize=(8, 6))
    sns.histplot(df["Densidade"], kde=True, bins=20)
    plt.title("Distribuição de Densidade")
    plt.xlabel("Densidade")
    plt.ylabel("Frequência")
    plt.savefig(os.path.join(folder_name, "distribuicao_densidade.png"))
    plt.close()

    # 3. Histograma do Tempo de Execução
    plt.figure(figsize=(8, 6))
    sns.histplot(df["Tempo (s)"], kde=True, bins=20)
    plt.title("Distribuição do Tempo de Execução")
    plt.xlabel("Tempo (s)")
    plt.ylabel("Frequência")
    plt.savefig(os.path.join(folder_name, "distribuicao_tempo.png"))
    plt.close()

    # 4. Gráfico de barras para Status (Ótimo vs Melhor)
    plt.figure(figsize=(8, 6))
    status_counts = df["Status"].value_counts()
    status_counts.plot(kind="bar")
    plt.title("Distribuição de Status das Soluções")
    plt.xlabel("Status")
    plt.ylabel("Contagem")
    plt.xticks(rotation=0)
    plt.savefig(os.path.join(folder_name, "status_solucao.png"))
    plt.close()

    # 5. Gráfico de dispersão: Densidade vs Objetivo
    plt.figure(figsize=(8, 6))
    sns.scatterplot(x="Densidade", y="Objetivo", data=df)
    plt.title("Densidade vs Objetivo")
    plt.xlabel("Densidade")
    plt.ylabel("Objetivo")
    plt.savefig(os.path.join(folder_name, "densidade_vs_objetivo.png"))
    plt.close()

    # 6. Gráfico de dispersão: Tempo de Execução vs Objetivo
    plt.figure(figsize=(8, 6))
    sns.scatterplot(x="Tempo (s)", y="Objetivo", data=df)
    plt.title("Tempo de Execução vs Objetivo")
    plt.xlabel("Tempo (s)")
    plt.ylabel("Objetivo")
    plt.savefig(os.path.join(folder_name, "tempo_vs_objetivo.png"))
    plt.close()


# Função para garantir que a pasta seja única (evitar sobrescrição)
def ensure_unique_folder(base_name):
    timestamp = time.strftime("%Y%m%d_%H%M%S")  # Gera um timestamp único
    folder_name = f"{base_name}_{timestamp}"
    if os.path.exists(folder_name):
        count = 1
        while os.path.exists(f"{folder_name}_{count}"):
            count += 1
        folder_name = f"{folder_name}_{count}"
    return folder_name


# Função principal para parsear os argumentos
def main():
    # Configuração do argparse para pegar os arquivos CSV da linha de comando
    parser = argparse.ArgumentParser(
        description="Analisar arquivos CSV e gerar resultados."
    )
    parser.add_argument(
        "csv_files", nargs="+", help="Lista de arquivos CSV para análise"
    )
    args = parser.parse_args()

    # Para cada arquivo CSV passado na linha de comando, faz a análise
    for csv_file in args.csv_files:
        print(f"Iniciando análise do arquivo: {csv_file}")
        analyze_and_save(
            csv_file
        )  # Passa o nome do arquivo como referência para a pasta
        print(
            f"Análise do arquivo {csv_file} concluída e salva na pasta {os.path.basename(os.path.dirname(csv_file))}."
        )


if __name__ == "__main__":
    main()

