#ifndef HSCOPT_DECODER_H
#define HSCOPT_DECODER_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file decoder.h
 * @brief Tipos e assinaturas para a função decoder.
 */

/**
 * @brief Tipo opaco que representa a instância do problema.
 *
 * A instância é tratada como somente leitura durante as chamadas do decoder.
 */
typedef struct hscopt_instance hscopt_instance;

/**
 * @brief Tipo opaco para workspace reutilizável.
 *
 * Pode armazenar buffers temporários para evitar alocações repetidas.
 */
typedef struct hscopt_workspace hscopt_workspace;

/**
 * @struct hscopt_decode_ctx
 * @brief Contexto passado ao decoder.
 *
 * Permite ao decoder acessar:
 * - a instância do problema (somente leitura),
 * - um ponteiro de usuário (opcional),
 * - um workspace reutilizável (opcional).
 */
typedef struct hscopt_decode_ctx {
  const hscopt_instance *inst;  // Instância do problema (somente leitura)
  void *user;  // Ponteiro opcional para dados do usuário (pode ser NULL)
  hscopt_workspace *ws;  // Workspace reutilizável (pode ser NULL), use isso
                         // para evitar alocações durante as execuções
} hscopt_decode_ctx;

/**
 * @typedef hscopt_decoder_fn
 * @brief Assinatura de função decoder: keys -> objetivo.
 *
 * @param keys Vetor de chaves (tamanho @p n). Tipicamente em [0,1).
 * @param n Número de chaves.
 * @param ctx Contexto do decoder (instância + dados extras + workspace).
 *
 * @return Valor da função objetivo (double).
 *
 * @note Requisitos obrigatorios:
 * - Não modificar @p keys.
 * - Não modificar @p ctx->inst.
 * - Evitar alocações e I/O no hot loop.
 * - Ser determinístico para a mesma entrada (keys, ctx).
 * - Deve ser thread-safe quando chamado em paralelo (OpenMP ou equivalente).
 *
 * Comportamento indefinido:
 * - Compartilhar estado mutavel sem sincronizacao entre chamadas concorrentes.
 */
typedef double (*hscopt_decoder_fn)(const double *keys, size_t n,
                                    hscopt_decode_ctx *ctx);

#ifdef __cplusplus
}
#endif

#endif /* HSCOPT_DECODER_H */
