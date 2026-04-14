# Build

Este projeto usa um unico `CMakeLists.txt` na raiz.

## Requisitos

- GCC
- CMake >= 3.16

## Build rapido

Diretorio padrao de build: `build/`

Release:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Debug:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

Se trocar entre `Release` e `Debug` no mesmo diretorio, reconfigure antes:

```bash
rm -rf build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

## Target gerado

- Biblioteca estatica: `hscopt` (arquivo `libhscopt.a`)

## Opcoes

- `HSCOPT_BUILD_EXAMPLES`:
  compila os exemplos; por padrao fica `ON` apenas quando `hscopt` e o projeto raiz.
- `HSCOPT_ENABLE_OPENMP`:
  tenta usar OpenMP quando disponivel; por padrao `ON`.

Exemplo sem OpenMP:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DHSCOPT_ENABLE_OPENMP=OFF
cmake --build build
```

## Uso como subdiretorio

No projeto consumidor:

```cmake
add_subdirectory(hscopt)
target_link_libraries(meu_app PRIVATE hscopt::hscopt)
```
