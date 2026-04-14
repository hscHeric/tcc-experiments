# tcc-experiments

Experimentos para o TCC com foco em heuristicas e metaheuristicas para problemas em grafos.

Hoje o repositorio contem:

- uma biblioteca `core` em C++ com estruturas e decoders do projeto;
- um executavel `brkga_runner` para integrar o decoder ao `hsc-brkga-api`;
- scripts Python para PLI, analise de resultados e manipulacao de instancias;
- conjuntos de instancias em `data/instances`;
- submodulos em `external/` para algoritmos reutilizaveis.

## Dependencias

O build C++ usa:

- CMake 3.20+
- Conan 2
- compilador com suporte a C++23 no projeto principal
- suporte a OpenMP para o submodulo `hsc-brkga-api`

Pacotes resolvidos via Conan:

- `CLI11`
- `spdlog`
- `nlohmann_json`

## Submodulos

Os submodulos versionados no projeto sao:

- `external/hsc-brkga-api` na tag `v1.0.0`
- `external/hscopt` na tag `v1.0.0`

No estado atual, apenas `hsc-brkga-api` esta ligado ao `brkga_runner`. O `hscopt` ja entra no grafo do CMake, mas nao e usado por nenhum alvo da raiz por enquanto.

## Build

Inicialize os submodulos:

```bash
git submodule update --init --recursive
```

Instale as dependencias C++ com Conan:

```bash
conan install . --output-folder=build --build=missing -s build_type=Debug
```

Configure o projeto com o toolchain gerado:

```bash
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Debug
```

Compile:

```bash
cmake --build build
```

## Estrutura

```text
src/core/           Biblioteca principal em C++
src/runners/        Executaveis de experimento
python/             Scripts e modelos auxiliares em Python
data/instances/     Instancias de benchmark
results/            Resultados gerados por execucoes
external/           Dependencias versionadas como submodulos
```

## Estado atual

- `brkga_runner` executa um exemplo minimo da integracao com BRKGA sobre um grafo pequeno em memoria.
- `core` concentra a estrutura de grafo e os decoders experimentais.
- os scripts Python continuam separados do fluxo de build C++.
