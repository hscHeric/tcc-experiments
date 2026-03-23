#ifndef HSCOPT_HHO_H
#define HSCOPT_HHO_H

#include <stddef.h>

#include "hscopt/alloc.h"
#include "hscopt/decoder.h"
#include "hscopt/rng.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file hho.h
 * @brief API pública do algoritmo Harris Hawks Optimization (HHO).
 */

/**
 * @brief Contexto opaco do algoritmo HHO.
 *
 * O contexto armazena todos os dados internos necessários para a execução
 * do algoritmo, incluindo parâmetros, população, melhor solução encontrada
 * (rabbit) e estado da iteração.
 *
 * O usuário não deve acessar diretamente os campos internos.
 */
typedef struct hscopt_hho_ctx hscopt_hho_ctx;

/**
 * @brief Cria e inicializa um contexto do HHO.
 *
 * Esta função:
 * - aloca o contexto e todos os buffers internos,
 * - inicializa a população de hawks com valores aleatórios em [0,1),
 * - avalia a população inicial,
 * - define a melhor solução inicial (rabbit).
 *
 * @param n_keys Número de chaves (dimensão do problema).
 * @param n_agents Número de agentes (hawks).
 * @param max_iters Número máximo de iterações do algoritmo (T no artigo).
 * @param max_threads Número máximo de threads para avaliação (se OpenMP estiver
 * ativo).
 * @param decoder Função decoder responsável por avaliar uma solução.
 * @param dctx Contexto do decoder (pode ser NULL).
 * @param rng Gerador de números aleatórios (obrigatório).
 *
 * @return Ponteiro para o contexto HHO em caso de sucesso, ou NULL em erro.
 */
hscopt_hho_ctx *hscopt_hho_create(size_t n_keys, size_t n_agents,
                                  unsigned max_iters, unsigned max_threads,
                                  hscopt_decoder_fn decoder,
                                  hscopt_decode_ctx *dctx, hscopt_rng *rng);

/**
 * @brief Cria e inicializa um contexto do HHO com alocador customizado.
 *
 * Se @p alloc for NULL, usa o alocador global.
 *
 * @param alloc Alocador customizado (opcional).
 * @return Ponteiro para o contexto HHO em caso de sucesso, ou NULL em erro.
 */
hscopt_hho_ctx *hscopt_hho_create_with_allocator(
    size_t n_keys, size_t n_agents, unsigned max_iters, unsigned max_threads,
    hscopt_decoder_fn decoder, hscopt_decode_ctx *dctx, hscopt_rng *rng,
    const hscopt_allocator *alloc);

/**
 * @brief Libera todos os recursos associados ao contexto HHO.
 *
 * Após esta chamada, o ponteiro @p ctx torna-se inválido.
 *
 * @param ctx Contexto HHO.
 */
void hscopt_hho_destroy(hscopt_hho_ctx *ctx);

/**
 * @brief Reinicializa o algoritmo HHO.
 *
 * Esta função:
 * - gera uma nova população aleatória de hawks,
 * - reinicia o contador de iterações,
 * - reinicia o melhor fitness encontrado.
 *
 * @param ctx Contexto HHO.
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_hho_reset(hscopt_hho_ctx *ctx);

/**
 * @brief Executa um número de iterações do HHO.
 *
 * Cada iteração executa, conceitualmente:
 * - avaliação dos agentes,
 * - atualização do rabbit (melhor solução),
 * - cálculo da energia de fuga,
 * - atualização das posições dos hawks conforme as fases
 *   de exploração e explotação definidas no HHO.
 *
 * As posições são mantidas no hipercubo [0,1) via clamp.
 *
 * @param ctx Contexto HHO.
 * @param iters Número de iterações a executar (>= 1).
 *
 * @return 0 em sucesso, valor diferente de 0 em erro.
 */
int hscopt_hho_iterate(hscopt_hho_ctx *ctx, unsigned iters);

/**
 * @brief Retorna o melhor valor da função objetivo encontrado.
 *
 * @param ctx Contexto HHO.
 * @return Melhor fitness encontrado até o momento.
 */
double hscopt_hho_best_fitness(const hscopt_hho_ctx *ctx);

/**
 * @brief Retorna o vetor de chaves da melhor solução encontrada.
 *
 * @param ctx Contexto HHO.
 * @return Ponteiro para o vetor de random keys do melhor agente.
 *
 * @note
 * - O ponteiro retornado é válido enquanto o contexto existir
 *   e não for chamada hscopt_hho_reset() ou hscopt_hho_iterate().
 */
const double *hscopt_hho_best_keys(const hscopt_hho_ctx *ctx);

/**
 * @brief Retorna o índice da iteração atual.
 *
 * @param ctx Contexto HHO.
 * @return Índice da iteração atual (inicia em 0).
 */
unsigned hscopt_hho_iteration(const hscopt_hho_ctx *ctx);

/**
 * @brief Retorna o número máximo de iterações configurado.
 *
 * @param ctx Contexto HHO.
 * @return Número máximo de iterações (T).
 */
unsigned hscopt_hho_max_iters(const hscopt_hho_ctx *ctx);

/**
 * @brief Retorna o número de agentes (hawks).
 *
 * @param ctx Contexto HHO.
 * @return Número de agentes.
 */
size_t hscopt_hho_n_agents(const hscopt_hho_ctx *ctx);

/**
 * @brief Retorna a dimensão do problema (número de chaves).
 *
 * @param ctx Contexto HHO.
 * @return Número de chaves (dimensão).
 */
size_t hscopt_hho_n_keys(const hscopt_hho_ctx *ctx);

/**
 * @brief Retorna o número máximo de threads configurado para avaliação.
 *
 * @param ctx Contexto HHO.
 * @return Número máximo de threads.
 */
unsigned hscopt_hho_max_threads(const hscopt_hho_ctx *ctx);

/**
 * @brief Avalia uma solução candidata e atualiza o rabbit se houver melhoria.
 *
 * A solução candidata é avaliada usando o decoder. Caso seu fitness seja
 * melhor (menor) que o fitness do rabbit atual, a solução é copiada para
 * o rabbit e o melhor fitness é atualizado.
 *
 * @param ctx Contexto HHO.
 * @param keys Vetor de chaves candidato (tamanho = hscopt_hho_n_keys(ctx)).
 *
 * @return
 * - 1 se o rabbit foi atualizado,
 * - 0 se a solução não melhorou,
 * - valor negativo em caso de erro.
 *
 * @note
 * - @p keys deve estar no intervalo [0,1).
 * - A função não realiza clamp automaticamente.
 * - Esta função não é thread-safe se chamada concorrentemente.
 */
int hscopt_hho_try_update_rabbit(hscopt_hho_ctx *ctx, const double *keys);

#ifdef __cplusplus
}
#endif

#endif /* !HSCOPT_HHO_H */
