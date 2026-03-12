# Build e Tooling

## Objetivo

O projeto usa:
- `mise` para provisionar ferramentas e expor tasks
- `CMake` como sistema de build do código C/C++
- `Ninja` como generator do CMake
- `clangd` via `compile_commands.json` gerado no build e linkado na raiz

## Ferramentas

Dependências esperadas no sistema:
- `gcc`
- `g++`
- `make`
- `mise`

As ferramentas declaradas em [mise.toml](/home/hscheric/Work/tcc-experiments/mise.toml) e provisionadas via `mise install` são:
- `cmake`
- `ninja`
- `python`

Instalação:

```bash
mise install
```

Sem `mise install`, o `cmake` pode falhar ao tentar usar o `ninja` exposto pelos shims do `mise`.

## Configuração CMake

O projeto possui um único [CMakeLists.txt](/home/hscheric/Work/tcc-experiments/CMakeLists.txt) na raiz.

Configuração release:

```bash
mise run cmake-configure
```

Configuração debug:

```bash
mise run cmake-configure-debug
```

Essas tasks criam:
- `build/release`
- `build/debug`

## Compile Commands

O projeto define `CMAKE_EXPORT_COMPILE_COMMANDS=ON`.

Após a configuração, o módulo [TccLinkCompileCommands.cmake](/home/hscheric/Work/tcc-experiments/cmake/TccLinkCompileCommands.cmake) cria um link simbólico:

```text
compile_commands.json -> build/<perfil>/compile_commands.json
```

Isso permite que o `clangd` use a configuração de compilação diretamente na raiz do projeto.

## Tasks disponíveis

### Release

- `mise run cmake-configure`
- `mise run cmake-build-metaheuristics`
- `mise run cmake-build-aco-ts`
- `mise run cmake-build-hho-rvns`
- `mise run cmake-build-brkga`

### Debug

- `mise run cmake-configure-debug`
- `mise run cmake-build-metaheuristics-debug`
- `mise run cmake-build-aco-ts-debug`
- `mise run cmake-build-hho-rvns-debug`
- `mise run cmake-build-brkga-debug`

## Saída dos binários

Os executáveis ficam dentro do diretório de build do perfil escolhido.

Exemplos:
- `build/release/aco_ts`
- `build/release/hho_rvns`
- `build/release/brkga`
- `build/debug/aco_ts`

## Flags principais

O projeto define opções próprias `TCC_*` e também repassa opções `HSCOPT_*`:
- `TCC_ENABLE_LTO`
- `TCC_ENABLE_NATIVE`
- `TCC_ENABLE_OPENMP`
- `TCC_ENABLE_WARNINGS`
- `TCC_BUILD_METAHEURISTICS`
- `HSCOPT_ENABLE_LTO`
- `HSCOPT_ENABLE_NATIVE`
- `HSCOPT_ENABLE_OPENMP`

Essas opções são aplicadas pelas tasks do `mise`.
