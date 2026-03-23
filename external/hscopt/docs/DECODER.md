# Decoder

Esta biblioteca assume que `hscopt_decoder_fn` e thread-safe por contrato.

## Requisitos obrigatorios

- Nao escrever em memoria compartilhada sem sincronizacao.
- Nao manter estado global mutavel sem protecao.
- Nao modificar `keys`.
- Nao modificar `ctx->inst`.
- Retornar resultado deterministico para a mesma entrada.

## Padroes recomendados

- Tratar `ctx->inst` como somente leitura.
- Guardar estado temporario por thread (TLS) ou usar buffers locais.
- Se houver estado mutavel compartilhado, usar sincronizacao explicita.
- Evitar alocacao e I/O no hot loop.

## Exemplo de risco

- Incrementar contador global dentro do decoder sem lock.
- Reusar buffer global unico para montar solucao.

Esses casos podem causar corrida de dados quando OpenMP estiver ativo.
