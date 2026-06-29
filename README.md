# Experimentos do MR3DP

Implementações, instâncias, resultados brutos e pipeline reproduzível dos
experimentos para o Problema de Dominação {3}-Romana.

Os scripts produzem somente dados
estruturados (`.csv`), tabelas (`.tex`) e gráficos (`.png`).

## Estrutura

```text
data/instances/                   instâncias CUBIC, DIMACS e HB
experiments/configs/              configurações finais das meta-heurísticas
experiments/tuning/               cenários e parâmetros do irace
src/                              implementações e executores C++
python/pli/                       modelo exato e executor BIP
python/scripts/                   executor das meta-heurísticas
python/scripts/analysis/          análises e geradores de artefatos
python/scripts/utils/             conversores e utilitários de grafos
results/pli/                      resultados brutos do BIP
results/experiments/              resultados brutos das meta-heurísticas
results/tuning/                   resultados brutos da calibração
results/instance_characterization/ CSVs de caracterização (gerados)
results/csvs_definitivos/         CSVs e testes estatísticos (gerados)
results/tabelas_tex/              tabelas LaTeX (geradas)
results/graficos/                 gráficos (gerados)
```

## Requisitos

- Git com suporte a submódulos;
- compilador C++20 com OpenMP;
- CMake 3.20+, Conan 2 e Ninja;
- Python 3.13 e as dependências de `requirements.txt`;
- Gurobi com licença válida apenas para reexecutar o modelo exato;
- R e irace apenas para refazer a calibração.

O `mise.toml` fixa as versões das principais ferramentas.

## Configuração

```bash
git clone --recurse-submodules git@github.com:hscHeric/tcc-experiments.git
cd tcc-experiments
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Se o clone já foi feito sem os submódulos:

```bash
git submodule update --init --recursive
```

## Reproduzir os artefatos

Com `mise`:

```bash
mise run results-reproduce
```

Sem `mise`:

```bash
python python/scripts/analysis/characterize_instances.py
python python/scripts/analysis/generate_result_csvs.py
python python/scripts/analysis/generate_tex_tables.py results/tabelas_tex
python python/scripts/analysis/generate_plots.py
python python/scripts/analysis/validate_results.py --include-derived
```

O pipeline recria os CSVs derivados, executa Friedman e Wilcoxon, gera as
tabelas e os gráficos e, ao final, confere quantidades, extensões e
consistência entre os conjuntos.

Os artefatos derivados são ignorados pelo Git. Somente os resultados brutos
em `results/pli`, `results/experiments` e `results/tuning` são versionados.

## Reexecutar os experimentos

```bash
mise run build-release
mise run pli
mise run experiments
mise run results-reproduce
```

Os experimentos finais usam os arquivos em `experiments/configs/` e produzem
10 execuções por método e instância. O executor das meta-heurísticas retoma
resultados completos existentes; use `--no-skip-existing` para forçar uma nova
execução.

Para conferir os comandos sem executar:

```bash
python python/scripts/run_metaheuristic_experiments.py \
  experiments/configs/aco_ts.json --dry-run
```

## Tarefas úteis

```bash
mise run build-debug
mise run build-release
mise run experiments
mise run results-characterization
mise run results-csvs
mise run results-tables
mise run results-plots
mise run results-verify
```
