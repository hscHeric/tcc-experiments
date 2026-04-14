#ifndef HSCOPT_TS_H
#define HSCOPT_TS_H

#include <stddef.h>

#include "hscopt/decoder.h"
#include "hscopt/rng.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Contexto opaco do algoritmo Tabu Search.
 */
typedef struct hscopt_ts_ctx hscopt_ts_ctx;

/**
 * @brief Cria e inicializa um contexto TS.
 *
 * O TS usa uma vizinhanca de movimentos 1-flip em random keys:
 * em cada candidato, uma posicao e sorteada e recebe uma nova key em [0,1).
 * A lista tabu atua sobre o indice modificado.
 *
 * @param n_keys Dimensao (numero de random keys).
 * @param neighborhood_size Numero de candidatos avaliados por iteracao.
 * @param tabu_tenure Tenure tabu aplicado ao indice modificado.
 * @param max_iters Numero maximo de iteracoes.
 * @param max_threads Numero maximo de threads para avaliacao.
 * @param decoder Funcao de avaliacao.
 * @param dctx Contexto do decoder (pode ser NULL).
 * @param rng RNG base (obrigatorio).
 * @param initial_keys Solucao inicial (vetor de tamanho @p n_keys) ou NULL.
 *
 * @return Ponteiro para contexto valido, ou NULL em erro.
 */
hscopt_ts_ctx *hscopt_ts_create(size_t n_keys, size_t neighborhood_size,
                                unsigned tabu_tenure, unsigned max_iters,
                                unsigned max_threads, hscopt_decoder_fn decoder,
                                hscopt_decode_ctx *dctx, hscopt_rng *rng,
                                const double *initial_keys);

/**
 * @brief Libera recursos do contexto TS.
 */
void hscopt_ts_destroy(hscopt_ts_ctx *ctx);

/**
 * @brief Reinicializa o TS com uma nova solucao inicial.
 *
 * Reinicia iteracao, lista tabu, solucao corrente e melhor global.
 *
 * @param ctx Contexto TS.
 * @param initial_keys Solucao inicial (vetor de tamanho @p n_keys) ou NULL.
 *
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_ts_reset(hscopt_ts_ctx *ctx, const double *initial_keys);

/**
 * @brief Executa um numero de iteracoes do TS.
 *
 * Cada iteracao:
 * - gera uma vizinhanca de candidatos,
 * - aplica restricao tabu por indice modificado,
 * - usa aspiracao quando um movimento melhora o melhor global,
 * - aceita o melhor candidato admissivel.
 *
 * @param ctx Contexto TS.
 * @param iters Quantidade de iteracoes (>= 1).
 *
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_ts_iterate(hscopt_ts_ctx *ctx, unsigned iters);

/**
 * @brief Retorna melhor fitness global encontrado.
 */
double hscopt_ts_best_fitness(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna as random keys da melhor solucao global.
 *
 * @note Ponteiro valido enquanto o contexto existir e nao sofrer reset/iterate.
 */
const double *hscopt_ts_best_keys(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna fitness da solucao corrente.
 */
double hscopt_ts_current_fitness(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna as random keys da solucao corrente.
 *
 * @note Ponteiro valido enquanto o contexto existir e nao sofrer reset/iterate.
 */
const double *hscopt_ts_current_keys(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna iteracao atual.
 */
unsigned hscopt_ts_iteration(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna numero maximo de iteracoes.
 */
unsigned hscopt_ts_max_iters(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna dimensao do problema.
 */
size_t hscopt_ts_n_keys(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna o tamanho da vizinhanca por iteracao.
 */
size_t hscopt_ts_neighborhood_size(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna tenure tabu configurado.
 */
unsigned hscopt_ts_tabu_tenure(const hscopt_ts_ctx *ctx);

/**
 * @brief Retorna numero maximo de threads efetivo.
 */
unsigned hscopt_ts_max_threads(const hscopt_ts_ctx *ctx);

/**
 * @brief Avalia uma solucao candidata e atualiza o melhor global se melhorar.
 *
 * @param ctx Contexto TS.
 * @param keys Vetor de chaves candidato (tamanho = hscopt_ts_n_keys(ctx)).
 *
 * @return
 * - 1 se o melhor global foi atualizado,
 * - 0 se a solucao nao melhorou,
 * - valor negativo em caso de erro.
 *
 * @note
 * - @p keys deve estar no intervalo [0,1).
 * - A funcao nao realiza clamp automaticamente.
 * - Esta funcao nao e thread-safe se chamada concorrentemente.
 */
int hscopt_ts_try_update_best(hscopt_ts_ctx *ctx, const double *keys);

#ifdef __cplusplus
}
#endif

#endif /* HSCOPT_TS_H */
