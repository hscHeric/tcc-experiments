# Executáveis de Metaheurística

## Estado atual

Os executáveis atuais são stubs.

Arquivos:
- [aco_ts_main.cpp](/home/hscheric/Work/tcc-experiments/metaheuristic/aco_ts_main.cpp)
- [hho_rvns_main.cpp](/home/hscheric/Work/tcc-experiments/metaheuristic/hho_rvns_main.cpp)
- [brkga_main.cpp](/home/hscheric/Work/tcc-experiments/metaheuristic/brkga_main.cpp)
- [app_stub_common.hpp](/home/hscheric/Work/tcc-experiments/metaheuristic/app_stub_common.hpp)

## O que cada um faz hoje

Cada stub:
- imprime o nome do algoritmo
- imprime o status atual
- imprime a versão da `hscopt`
- aceita um caminho de arquivo de grafo
- carrega o arquivo usando `Graph`
- imprime ordem, tamanho e densidade

## Objetivo futuro

### `aco_ts`

Reservado para uma pipeline:
- construção com `ACO` da `hscopt`
- refinamento local com busca tabu implementada no projeto

### `hho_rvns`

Reservado para uma pipeline:
- construção ou melhoria com `HHO`
- refinamento com `RVNS`

### `brkga`

Reservado para BRKGA.

Observação:
- a API pública atual da `hscopt` ainda não expõe BRKGA
- por isso, o stub existe apenas como ponto de entrada e alvo de build

## Como executar

Depois de compilar:

```bash
build/release/aco_ts data/instances/DIMACS/myciel3.col
build/release/hho_rvns data/instances/DIMACS/myciel3.col
build/release/brkga data/instances/DIMACS/myciel3.col
```

Em debug:

```bash
build/debug/aco_ts data/instances/DIMACS/myciel3.col
```

## Convenção adotada

Mesmo sendo stubs, os três executáveis já foram separados para evitar:
- um `main` monolítico
- ifs por algoritmo
- acoplamento desnecessário entre pipelines futuras
