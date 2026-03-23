#ifndef HSCOPT_RVNS_H
#define HSCOPT_RVNS_H

#include <stddef.h>

#include "hscopt/alloc.h"
#include "hscopt/decoder.h"
#include "hscopt/rng.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file rvns.h
 * @brief API pública do algoritmo RVNS.
 */

/**
 * @struct hscopt_rvns_ctx
 * @brief Contexto opaco do algoritmo RVNS.
 *
 * O contexto encapsula:
 * - parâmetros (dimensão, k_max, limites de iteração),
 * - solução incumbente e melhor solução encontrada,
 * - contador de iterações,
 * - referências ao RNG e ao decoder.
 *
 * O usuário não deve acessar nem modificar diretamente os campos internos.
 */
typedef struct hscopt_rvns_ctx hscopt_rvns_ctx;

/**
 * @brief Cria e inicializa um contexto do RVNS.
 *
 * Esta função:
 * - aloca o contexto e buffers internos,
 * - define a solução inicial:
 *   - se @p initial_keys != NULL, copia @p initial_keys,
 *   - se @p initial_keys == NULL, gera uma solução aleatória em [0,1),
 * - avalia a solução inicial e inicializa o melhor conhecido.
 *
 * @param n_keys Dimensão do vetor de chaves.
 * @param k_max Maior vizinhança a ser reconhecida (>= 1).
 * @param max_iters Número máximo de iterações configurado para o contexto.
 * @param max_threads Número máximo de threads para avaliação (se OpenMP estiver
 * ativo).
 * @param decoder Função decoder responsável por avaliar uma solução.
 * @param dctx Contexto do decoder (pode ser NULL).
 * @param rng Gerador de números aleatórios (obrigatório).
 * @param initial_keys Solução inicial (vetor de tamanho @p n_keys) ou NULL.
 *
 * @return Ponteiro para o contexto RVNS em caso de sucesso, ou NULL em erro.
 */
hscopt_rvns_ctx *hscopt_rvns_create(
    size_t n_keys, size_t k_max, unsigned max_iters, unsigned max_threads,
    hscopt_decoder_fn decoder, hscopt_decode_ctx *dctx, hscopt_rng *rng,
    const double *initial_keys);

/**
 * @brief Cria e inicializa um contexto do RVNS com alocador customizado.
 *
 * Se @p alloc for NULL, usa o alocador global.
 *
 * @param alloc Alocador customizado (opcional).
 * @return Ponteiro para o contexto RVNS em caso de sucesso, ou NULL em erro.
 */
hscopt_rvns_ctx *hscopt_rvns_create_with_allocator(
    size_t n_keys, size_t k_max, unsigned max_iters, unsigned max_threads,
    hscopt_decoder_fn decoder, hscopt_decode_ctx *dctx, hscopt_rng *rng,
    const double *initial_keys, const hscopt_allocator *alloc);

/**
 * @brief Libera todos os recursos associados ao contexto RVNS.
 *
 * Após esta chamada, o ponteiro @p ctx torna-se inválido.
 *
 * @param ctx Contexto RVNS.
 */
void hscopt_rvns_destroy(hscopt_rvns_ctx *ctx);

/**
 * @brief Reinicializa o RVNS com uma nova solução inicial.
 *
 * Esta função:
 * - define a solução incumbente:
 *   - se @p initial_keys != NULL, copia @p initial_keys,
 *   - se @p initial_keys == NULL, gera uma solução aleatória em [0,1),
 * - reinicia o contador de iterações,
 * - reinicia o melhor fitness encontrado.
 *
 * @param ctx Contexto RVNS.
 * @param initial_keys Solução inicial (vetor de tamanho @p n_keys) ou NULL.
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_rvns_reset(hscopt_rvns_ctx *ctx, const double *initial_keys);

/**
 * @brief Executa um número de iterações do RVNS.
 *
 * Cada iteração executa, conceitualmente:
 * - escolha/uso do k atual,
 * - *shaking* para gerar x' em N_k(x),
 * - avaliação via decoder,
 * - regra de aceitação:
 *   - se melhora, aceita e reinicia k,
 *   - senão incrementa k (até k_max).
 *
 * @param ctx Contexto RVNS.
 * @param iters Número de iterações a executar (>= 1).
 *
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_rvns_iterate(hscopt_rvns_ctx *ctx, unsigned iters);

/**
 * @brief Retorna o melhor valor da função objetivo encontrado.
 *
 * @param ctx Contexto RVNS.
 * @return Melhor fitness encontrado até o momento.
 */
double hscopt_rvns_best_fitness(const hscopt_rvns_ctx *ctx);

/**
 * @brief Retorna o vetor de chaves da melhor solução encontrada.
 *
 * @param ctx Contexto RVNS.
 * @return Ponteiro para o vetor de keys da melhor solução.
 *
 * @note
 * - O ponteiro retornado é válido enquanto o contexto existir
 *   e não for chamada hscopt_rvns_reset() ou hscopt_rvns_iterate().
 */
const double *hscopt_rvns_best_keys(const hscopt_rvns_ctx *ctx);

/**
 * @brief Retorna o número da iteração atual.
 *
 * @param ctx Contexto RVNS.
 * @return Índice da iteração atual (inicia em 0).
 */
unsigned hscopt_rvns_iteration(const hscopt_rvns_ctx *ctx);

/**
 * @brief Retorna a dimensão do problema (número de chaves).
 *
 * @param ctx Contexto RVNS.
 * @return Dimensão (dim).
 */
size_t hscopt_rvns_n_keys(const hscopt_rvns_ctx *ctx);

/**
 * @brief Retorna o máximo de perturbação.
 *
 * @param ctx Contexto RVNS.
 * @return k_max.
 */
size_t hscopt_rvns_k_max(const hscopt_rvns_ctx *ctx);

/**
 * @brief Retorna o número máximo de threads configurado para avaliação.
 *
 * @param ctx Contexto RVNS.
 * @return Número máximo de threads.
 */
unsigned hscopt_rvns_max_threads(const hscopt_rvns_ctx *ctx);

#ifdef __cplusplus
}
#endif

#endif  // !HSCOPT_RVNS_H
