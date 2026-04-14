#ifndef HSCOPT_ACO_H
#define HSCOPT_ACO_H

#include <stddef.h>

#include "hscopt/decoder.h"
#include "hscopt/rng.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file aco.h
 * @brief API publica do Ant Colony Optimization (ACO) para random keys.
 */

/**
 * @brief Contexto opaco do algoritmo ACO.
 */
typedef struct hscopt_aco_ctx hscopt_aco_ctx;

/**
 * @brief Cria e inicializa um contexto ACO.
 *
 * @param n_keys Dimensao (numero de random keys).
 * @param archive_size Tamanho do arquivo de solucoes (k).
 * @param n_ants Numero de novas solucoes geradas por iteracao (m).
 * @param max_iters Numero maximo de iteracoes.
 * @param max_threads Numero maximo de threads para avaliacao.
 * @param q Parametro q da distribuicao de pesos por rank.
 * @param xi Parametro xi usado no calculo de desvio padrao.
 * @param decoder Funcao de avaliacao.
 * @param dctx Contexto do decoder (pode ser NULL).
 * @param rng RNG base (obrigatorio).
 *
 * @return Ponteiro para contexto valido, ou NULL em erro.
 */
hscopt_aco_ctx *hscopt_aco_create(size_t n_keys, size_t archive_size,
                                  size_t n_ants, unsigned max_iters,
                                  unsigned max_threads, double q, double xi,
                                  hscopt_decoder_fn decoder,
                                  hscopt_decode_ctx *dctx, hscopt_rng *rng);

/**
 * @brief Libera recursos do contexto ACO.
 */
void hscopt_aco_destroy(hscopt_aco_ctx *ctx);

/**
 * @brief Reinicializa o arquivo com solucoes aleatorias.
 *
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_aco_reset(hscopt_aco_ctx *ctx);

/**
 * @brief Executa um numero de iteracoes do ACO.
 *
 * @param ctx Contexto ACO.
 * @param iters Quantidade de iteracoes (>= 1).
 *
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_aco_iterate(hscopt_aco_ctx *ctx, unsigned iters);

/**
 * @brief Retorna melhor fitness global encontrado.
 */
double hscopt_aco_best_fitness(const hscopt_aco_ctx *ctx);

/**
 * @brief Retorna as random keys da melhor solucao global.
 *
 * @note Ponteiro valido enquanto o contexto existir e nao sofrer reset/iterate.
 */
const double *hscopt_aco_best_keys(const hscopt_aco_ctx *ctx);

/**
 * @brief Retorna iteracao atual.
 */
unsigned hscopt_aco_iteration(const hscopt_aco_ctx *ctx);

/**
 * @brief Retorna numero maximo de iteracoes.
 */
unsigned hscopt_aco_max_iters(const hscopt_aco_ctx *ctx);

/**
 * @brief Retorna dimensao do problema.
 */
size_t hscopt_aco_n_keys(const hscopt_aco_ctx *ctx);

/**
 * @brief Retorna tamanho do arquivo (k).
 */
size_t hscopt_aco_archive_size(const hscopt_aco_ctx *ctx);

/**
 * @brief Retorna numero de formigas (m).
 */
size_t hscopt_aco_n_ants(const hscopt_aco_ctx *ctx);

/**
 * @brief Retorna numero maximo de threads efetivo.
 */
unsigned hscopt_aco_max_threads(const hscopt_aco_ctx *ctx);

#ifdef __cplusplus
}
#endif

#endif /* HSCOPT_ACO_H */
