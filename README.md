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

Exemplo de build `Debug`:

```bash
conan install . --output-folder=build/Debug --build=missing -s build_type=Debug
cmake -S . -B build/Debug \
  -DCMAKE_TOOLCHAIN_FILE=build/Debug/generators/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Debug
cmake --build build/Debug
```

Exemplo de build `Release`:

```bash
conan install . --output-folder=build/Release --build=missing -s build_type=Release
cmake -S . -B build/Release \
  -DCMAKE_TOOLCHAIN_FILE=build/Release/generators/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build/Release
```

O executavel gerado e o `brkga_runner`.
