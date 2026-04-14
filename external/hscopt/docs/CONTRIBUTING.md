# Contribuindo

Obrigado por contribuir. Este guia descreve o fluxo basico de trabalho.

## Padrao de commits

Use um formato inspirado em Conventional Commits:

tipo(escopo): mensagem curta

- `tipo`: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`
- `escopo` (opcional): area afetada (ex.: `hho`, `rvns`, `rng`, `docs`, `build`)
- mensagem no imperativo, minuscula, sem ponto final

Exemplos:
- `docs(hho): documentar API publica`
- `fix(rng): corrigir overflow no salto`
- `feat(rvns): adicionar estrategia de shaking`

## Codigo e estilo

- Preferir C simples e claro.
- Evitar alocacoes no hot loop.
- Manter funcoes pequenas e bem nomeadas.
- Documentar APIs publicas com Doxygen.
- Manter o dominio de random keys em [0,1) quando aplicavel.
- Decoder obrigatoriamente thread-safe em execucao concorrente.
- Consulte `docs/DECODER.md` ao alterar decoders/exemplos.

## Build e testes

- Use `docs/BUILD.md` como referencia.
- Antes de abrir PR, compile em `Release` e `Debug`.
- Valide tambem com OpenMP ligado/desligado (`mise run check`).
- Inclua comandos e resultados de build/testes no PR.

## Estrutura do repo

- `include/hscopt/` headers publicos
- `src/` implementacoes
- `examples/` exemplos
- `docs/` documentacao

## Issues e PRs

- Descreva o problema e a motivacao.
- Inclua passos para reproduzir quando aplicavel.
- Explique o impacto de performance quando relevante.
