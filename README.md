# tcc-experiments

Projeto de experimentos para TCC com duas frentes principais:
- modelagem e execução em Python para PLI
- infraestrutura C/C++ para metaheurísticas usando a biblioteca `hscopt`

## Estrutura

- [data](/home/hscheric/Work/tcc-experiments/data): instâncias e resultados
- [pli_model](/home/hscheric/Work/tcc-experiments/pli_model): pipeline Python para PLI
- [metaheuristic](/home/hscheric/Work/tcc-experiments/metaheuristic): grafo CSR e stubs das metaheurísticas em C++
- [external/hscopt](/home/hscheric/Work/tcc-experiments/external/hscopt): snapshot vendorizada da biblioteca `hscopt`
- [cmake](/home/hscheric/Work/tcc-experiments/cmake): módulos auxiliares do build CMake
- [docs](/home/hscheric/Work/tcc-experiments/docs): documentação do projeto

## Integração da biblioteca

`hscopt` foi adicionada como subdiretório versionado em `external/hscopt`, não como submodule.

Snapshot importada:
- repositório: `git@github.com:hscHeric/hscopt.git`
- revisão: `ffce4ed`

O build principal usa:

```cmake
set(HSCOPT_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
add_subdirectory(external/hscopt)
```

## Fluxo recomendado

1. Rode `mise install`
2. Rode `mise run cmake-configure` ou `mise run cmake-configure-debug`
3. Compile os alvos desejados
4. Execute os stubs de metaheurística com uma instância `.col`

Exemplo:

```bash
mise install
mise run cmake-compile-commands-release
mise run cmake-build-all
build/release/aco_ts data/instances/DIMACS/myciel3.col
```

Builds úteis via `mise`:
- `mise run cmake-compile-commands-release`
- `mise run cmake-compile-commands-debug`
- `mise run cmake-build-all`
- `mise run cmake-build-aco-ts`
- `mise run cmake-build-hho-rvns`
- `mise run cmake-build-brkga`

## Dependências

Antes de usar o build C/C++, tenha no sistema:
- `gcc`
- `g++`
- `make`
- `mise`

As ferramentas abaixo já estão declaradas em [mise.toml](/home/hscheric/Work/tcc-experiments/mise.toml):
- `cmake`
- `ninja`
- `python`

## Documentação

- [Build e Tooling](/home/hscheric/Work/tcc-experiments/docs/BUILD.md)
- [Arquitetura do Projeto](/home/hscheric/Work/tcc-experiments/docs/ARCHITECTURE.md)
- [Grafo CSR em C++](/home/hscheric/Work/tcc-experiments/docs/GRAPH.md)
- [Executáveis de Metaheurística](/home/hscheric/Work/tcc-experiments/docs/METAHEURISTICS.md)
