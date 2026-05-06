# tcc-experiments

Projeto de experimentos do TCC com implementacoes em C++ e scripts auxiliares em Python.

## Clone

```bash
git clone --recurse-submodules git@github.com:hscHeric/tcc-experiments.git
cd tcc-experiments
```

Se voce ja clonou sem os submodulos:

```bash
git submodule update --init --recursive
```

## Requirements

Para compilar a parte em C++ voce precisa de:

- `git`
- `cmake` 3.20+
- `conan` 2.x
- compilador com suporte a `C++23`
- suporte a OpenMP

Opcionalmente, o projeto tambem pode ser compilado pelas tarefas do
[`mise`](https://mise.jdx.dev/). O arquivo `mise.toml` ja declara as
ferramentas usadas no desenvolvimento, incluindo `cmake`, `conan`, `ninja` e
`python`.

Para os scripts Python:

- `python` 3.x
- dependencias do arquivo `requirements.txt`

Instalacao das dependencias Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Build

Ha duas formas equivalentes de compilar: usando as tarefas do `mise` ou
chamando `conan` e `cmake` manualmente.

### Usando mise

Build `Debug`:

```bash
mise run build-debug
```

Build `Release`:

```bash
mise run build-release
```

Tambem existem tarefas para compilar apenas um runner especifico:

```bash
mise run build-brkga-debug
mise run build-brkga-release

mise run build-brkga-mp-ipr-debug
mise run build-brkga-mp-ipr-release

mise run build-acots-debug
mise run build-acots-release

mise run build-hhorvns-debug
mise run build-hhorvns-release
```

### Manualmente com Conan e CMake

Build `Debug`:

```bash
conan install . --output-folder=. --build=missing -s build_type=Debug
cmake --fresh --preset conan-debug
cmake --build --preset conan-debug
```

Build `Release`:

```bash
conan install . --output-folder=. --build=missing -s build_type=Release
cmake -S . -B build/Release \
  -DCMAKE_TOOLCHAIN_FILE=build/Release/generators/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build/Release
```

Para compilar somente um alvo, informe o target no comando de build:

```bash
cmake --build --preset conan-debug --target brkga_runner
cmake --build build/Release --target brkga_runner
```

Os executaveis sao gerados dentro da pasta do tipo de build:

- `build/Debug/brkga_runner`
- `build/Debug/brkga_mp_ipr_runner`
- `build/Debug/aco_ts_runner`
- `build/Debug/hho_rvns_runner`
- `build/Release/brkga_runner`
- `build/Release/brkga_mp_ipr_runner`
- `build/Release/aco_ts_runner`
- `build/Release/hho_rvns_runner`

O build `Debug` usa `-O0 -g3` e, quando disponivel, ativa sanitizers de
address/undefined. O build `Release` usa `-O3 -march=native -DNDEBUG`.
