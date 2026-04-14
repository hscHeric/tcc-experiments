# hscopt

Biblioteca C de metaheuristicas para otimizacao combinatoria baseada em random keys.

## Visao geral

- Representacao por random keys no hipercubo [0,1)
- Algoritmos: Ant Colony Optimization (ACO), Harris Hawks Optimization (HHO), RVNS e Tabu Search (TS)
- RNG xoshiro256** com funcoes de salto
- API simples e focada em desempenho

## Estrutura

- `include/hscopt/` headers publicos
- `src/` implementacoes
- `examples/` exemplos de uso
- `docs/` guias de build e contribuicao

## Build

Veja `docs/BUILD.md`.
Contrato do decoder: `docs/DECODER.md`.

## Tutorial: usar como `external/` em outro projeto

Exemplo com CMake e a biblioteca dentro do seu repositorio em `external/hscopt`.

### 1) Adicione o repositorio

```bash
mkdir -p external
# opcao 1: git submodule
# git submodule add <url-do-hscopt> external/hscopt

# opcao 2: git clone
# git clone <url-do-hscopt> external/hscopt
```

### 2) No CMake do seu projeto

```cmake
# CMakeLists.txt do seu projeto
add_subdirectory(external/hscopt)

add_executable(meu_app src/main.c)

target_link_libraries(meu_app PRIVATE hscopt::hscopt)
```

### 3) No codigo

```c
#include "hscopt/hscopt.h"
```

### 4) Build do seu projeto

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Para debug:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

## Uso rapido

Fluxo tipico:

- gerar random keys em [0,1)
- avaliar via `hscopt_decoder_fn`
- iterar com `hscopt_hho_iterate` ou `hscopt_rvns_iterate`
- usar `hscopt_ts_iterate` como busca local sobre uma solucao inicial

Exemplos disponiveis:

- `examples/rng_example.c`
- `examples/decoder_example.c`
- `examples/hho_example.c`
- `examples/knapsack_hho_example.c`
- `examples/knapsack_rvns_example.c`
- `examples/knapsack_aco_example.c`
- `examples/knapsack_ts_example.c`

## Notas

- As chaves sao tratadas como random keys em [0,1).
- O clamp do dominio e aplicado internamente nas iteracoes do HHO e RVNS.
- A avaliacao e feita via `hscopt_decoder_fn`.
- O decoder deve ser thread-safe para execucao concorrente.

## Contribuindo

Veja `docs/CONTRIBUTING.md`.
