# tcc-experiments

Projeto de experimentos para TCC com duas frentes principais:
- modelagem e execução em Python para PLI
- infraestrutura C/C++ para metaheurísticas usando a biblioteca `hscopt`

## Estrutura

- [data](/home/hscheric/Work/tcc-experiments/data): instâncias e resultados
- [pli_model](/home/hscheric/Work/tcc-experiments/pli_model): pipeline Python para PLI
- [metaheuristic](/home/hscheric/Work/tcc-experiments/metaheuristic): biblioteca de grafo CSR em C++
- [metaheuristics](/home/hscheric/Work/tcc-experiments/metaheuristics): mains stub das metaheurísticas
- [external/hscopt](/home/hscheric/Work/tcc-experiments/external/hscopt): dependência local de metaheurísticas
- [cmake](/home/hscheric/Work/tcc-experiments/cmake): módulos auxiliares do build CMake
- [docs](/home/hscheric/Work/tcc-experiments/docs): documentação do projeto

## Fluxo recomendado

## Dependências

Antes de usar o build C/C++, tenha no sistema:
- `gcc`
- `g++`
- `make`
- `mise`

As ferramentas abaixo já estão declaradas em [mise.toml](/home/hscheric/Work/tcc-experiments/mise.toml) e são instaladas com:

```bash
mise install
```

Ferramentas provisionadas pelo `mise`:
- `cmake`
- `ninja`
- `python`

## Build

1. Rode `mise install`
2. Rode `mise run cmake-configure` ou `mise run cmake-configure-debug`
3. Compile os alvos desejados via `mise`

Exemplos:

```bash
mise install
mise run cmake-configure
mise run cmake-build-metaheuristics
```

Para debug:

```bash
mise install
mise run cmake-configure-debug
mise run cmake-build-aco-ts-debug
```

## Documentação

- [Build e Tooling](/home/hscheric/Work/tcc-experiments/docs/BUILD.md)
- [Arquitetura do Projeto](/home/hscheric/Work/tcc-experiments/docs/ARCHITECTURE.md)
- [Grafo CSR em C++](/home/hscheric/Work/tcc-experiments/docs/GRAPH.md)
- [Executáveis de Metaheurística](/home/hscheric/Work/tcc-experiments/docs/METAHEURISTICS.md)
