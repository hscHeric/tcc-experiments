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

## Dependência vendorizada

A biblioteca `hscopt` é mantida dentro do próprio repositório em [external/hscopt](/home/hscheric/Work/tcc-experiments/external/hscopt).

Origem da snapshot atual:
- repositório: `git@github.com:hscHeric/hscopt.git`
- commit importado: `ffce4ed`

O projeto principal força:
- `HSCOPT_BUILD_EXAMPLES=OFF`

Isso evita compilar os exemplos do `hscopt` quando o foco é o build do TCC.

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

Tasks dedicadas no `mise`:

```bash
mise run cmake-compile-commands-release
mise run cmake-compile-commands-debug
```

Se quiser apenas atualizar o link:

```bash
mise run cmake-link-compile-commands-release
mise run cmake-link-compile-commands-debug
```

## Tasks disponíveis

### Release

- `mise run cmake-configure`
- `mise run cmake-compile-commands-release`
- `mise run cmake-link-compile-commands-release`
- `mise run cmake-build-all`
- `mise run cmake-build-metaheuristics`
- `mise run cmake-build-aco-ts`
- `mise run cmake-build-hho-rvns`
- `mise run cmake-build-brkga`

### Debug

- `mise run cmake-configure-debug`
- `mise run cmake-compile-commands-debug`
- `mise run cmake-link-compile-commands-debug`
- `mise run cmake-build-all-debug`
- `mise run cmake-build-metaheuristics-debug`
- `mise run cmake-build-aco-ts-debug`
- `mise run cmake-build-hho-rvns-debug`
- `mise run cmake-build-brkga-debug`

## Build dos binários

Para compilar tudo em release:

```bash
mise run cmake-build-all
```

Para compilar individualmente em release:

```bash
mise run cmake-build-aco-ts
mise run cmake-build-hho-rvns
mise run cmake-build-brkga
```

Para compilar tudo em debug:

```bash
mise run cmake-build-all-debug
```

Para compilar individualmente em debug:

```bash
mise run cmake-build-aco-ts-debug
mise run cmake-build-hho-rvns-debug
mise run cmake-build-brkga-debug
```

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
