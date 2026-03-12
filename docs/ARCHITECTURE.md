# Arquitetura do Projeto

## Visão geral

O repositório está dividido em duas partes:

### Python

A pasta [pli_model](/home/hscheric/Work/tcc-experiments/pli_model) concentra a modelagem e execução do problema por PLI.

### C/C++

O código C/C++ organiza:
- a dependência [external/hscopt](/home/hscheric/Work/tcc-experiments/external/hscopt)
- a biblioteca de grafo em [metaheuristic](/home/hscheric/Work/tcc-experiments/metaheuristic)
- os executáveis stub em [metaheuristics](/home/hscheric/Work/tcc-experiments/metaheuristics)

## Biblioteca `tcc_graph`

O alvo `tcc_graph` é definido na raiz do CMake e compila:
- [graph.cpp](/home/hscheric/Work/tcc-experiments/metaheuristic/graph.cpp)

Headers expostos:
- [graph.hpp](/home/hscheric/Work/tcc-experiments/metaheuristic/graph.hpp)

Dependências:
- inclui headers de `hscopt`
- linka contra a biblioteca estática `hscopt`

## Integração com `hscopt`

O projeto adiciona a dependência como subdiretório:

```cmake
add_subdirectory(external/hscopt)
```

O build força:
- `HSCOPT_BUILD_EXAMPLES=OFF`

Isso evita compilar exemplos da dependência quando o foco é o projeto principal.

## Executáveis stub

Os alvos atuais são:
- `aco_ts`
- `hho_rvns`
- `brkga`

Eles ainda não implementam as metaheurísticas reais. O objetivo atual é:
- reservar pontos de entrada independentes
- validar integração com `hscopt`
- validar parsing de instância por meio da classe `Graph`

## Módulos CMake

A pasta [cmake](/home/hscheric/Work/tcc-experiments/cmake) contém:
- [Options.cmake](/home/hscheric/Work/tcc-experiments/cmake/Options.cmake)
- [CompilerWarnings.cmake](/home/hscheric/Work/tcc-experiments/cmake/CompilerWarnings.cmake)
- [Optimize.cmake](/home/hscheric/Work/tcc-experiments/cmake/Optimize.cmake)
- [OpenMP.cmake](/home/hscheric/Work/tcc-experiments/cmake/OpenMP.cmake)
- [TccProjectSetup.cmake](/home/hscheric/Work/tcc-experiments/cmake/TccProjectSetup.cmake)
- [TccLinkCompileCommands.cmake](/home/hscheric/Work/tcc-experiments/cmake/TccLinkCompileCommands.cmake)

Esses módulos seguem a mesma ideia do build da `hscopt`, mas com namespace próprio `tcc_*`.
