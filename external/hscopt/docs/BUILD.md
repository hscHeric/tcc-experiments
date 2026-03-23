# Build

Este projeto usa CMake modular e presets. O alvo principal e Linux com GCC.

## Requisitos

- GCC
- CMake >= 3.16
- Ninja (recomendado)

No Arch:

```bash
sudo pacman -S ninja cmake
```

## Build rapido (release)

Com presets (requer Ninja):

```bash
cmake --preset release
cmake --build --preset release
```

Sem Ninja (Unix Makefiles):

```bash
cmake -S . -B build/release -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build build/release
```

## Build debug

Com presets:

```bash
cmake --preset debug
cmake --build --preset debug
```

Sem Ninja:

```bash
cmake -S . -B build/debug -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug
cmake --build build/debug
```

## Target gerado

- Biblioteca estatica: `hscopt` (arquivo `libhscopt.a`)

## Feature flags

As opcoes abaixo podem ser ligadas/desligadas via `-D`:

- `HSCOPT_ENABLE_OPENMP` (default: ON)
- `HSCOPT_ENABLE_LTO` (default: ON)
- `HSCOPT_ENABLE_NATIVE` (default: ON)
- `HSCOPT_ENABLE_FAST_MATH` (default: OFF)
- `HSCOPT_ENABLE_WARNINGS` (default: ON)
- `HSCOPT_ENABLE_STRICT_ALIASING` (default: ON)
- `HSCOPT_ENABLE_VISIBILITY_HIDDEN` (default: ON)

Exemplo:

```bash
cmake -S . -B build -DHSCOPT_ENABLE_LTO=OFF -DHSCOPT_ENABLE_NATIVE=OFF
cmake --build build
```

Notas:

- `HSCOPT_ENABLE_FAST_MATH` pode alterar resultados numericos.
- `HSCOPT_ENABLE_NATIVE` gera binarios otimizados para a maquina atual.

## Usando mise

O repositorio inclui tarefas em `mise.toml`:

```bash
mise run build
mise run build_debug
mise run build_release
mise run build_no_openmp
mise run build_debug_no_openmp
mise run check
mise run example_hho
```

As flags podem ser alteradas via variaveis de ambiente, por exemplo:

```bash
HSCOPT_ENABLE_LTO=OFF HSCOPT_ENABLE_NATIVE=OFF mise run build
```

`mise run check` executa uma validacao rapida de matriz de build:
- Debug com OpenMP ON
- Debug com OpenMP OFF
- Release com OpenMP ON

## Alocador customizado

Para usar um alocador customizado (ex.: alinhado), defina um `hscopt_allocator`
e passe para as funcoes `hscopt_hho_create_with_allocator` ou
`hscopt_rvns_create_with_allocator`, ou configure o alocador global via
`hscopt_set_allocator`. Para voltar ao padrao (malloc/calloc/free), chame
`hscopt_set_allocator(NULL)`.
