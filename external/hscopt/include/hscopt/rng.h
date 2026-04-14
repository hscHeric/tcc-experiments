#ifndef HSCOPT_RNG_H
#define HSCOPT_RNG_H

#include <stddef.h>
#include <stdint.h>

#include "hscopt/defs.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file rng.h
 * @brief API pública do gerador de números pseudoaleatórios.
 */

/**
 * @struct hscopt_rng
 * @brief Estrutura do gerador de números pseudoaleatórios.
 *
 * Armazena o estado interno do RNG (xoshiro256**).
 * O conteúdo da estrutura não deve ser acessado diretamente pelo usuário.
 */
typedef struct hscopt_rng {
  uint64_t s[4];
} hscopt_rng;

/**
 * @brief Inicializa o RNG com uma semente.
 *
 * Esta função inicializa o estado interno do gerador a partir de uma
 * semente de 64 bits.
 *
 * @param rng Ponteiro para o RNG.
 * @param seed Valor da semente.
 */
void hscopt_rng_seed(hscopt_rng *rng, uint64_t seed);

/**
 * @brief Gera o próximo número pseudoaleatório de 64 bits.
 *
 * @param rng Ponteiro para o RNG.
 * @return Valor pseudoaleatório no intervalo [0, 2^64 − 1].
 */
uint64_t hscopt_rng_next_u64(hscopt_rng *rng);

/**
 * @brief Avança o estado do RNG para uma subsequência distante.
 *
 * Útil para criar subsequências estatisticamente independentes,
 * por exemplo, em ambientes paralelos.
 *
 * @param rng Ponteiro para o RNG.
 */
void hscopt_rng_jump(hscopt_rng *rng);

/**
 * @brief Avança o estado do RNG para uma subsequência ainda mais distante.
 *
 * Garante separação ainda maior entre subsequências do gerador.
 *
 * @param rng Ponteiro para o RNG.
 */
void hscopt_rng_long_jump(hscopt_rng *rng);

/**
 * @brief Gera um número real uniforme em [0,1).
 *
 * O valor retornado possui precisão de 53 bits, adequada para
 * operações em ponto flutuante do tipo double.
 *
 * @param rng Ponteiro para o RNG.
 * @return Número pseudoaleatório no intervalo [0,1).
 */
HSCOPT_INLINE double hscopt_rng_next_u01(hscopt_rng *rng) {
  return (hscopt_rng_next_u64(rng) >> 11) *
         (1.0 / 9007199254740992.0); /* 2^53 */
}

/**
 * @brief Gera um índice inteiro uniforme no intervalo [0, n).
 *
 * Esta função utiliza multiplicação em 128 bits para evitar viés
 * de módulo (*modulo bias*), garantindo distribuição uniforme.
 *
 * @param rng Ponteiro para o RNG.
 * @param n Limite superior exclusivo do intervalo.
 * @return Índice pseudoaleatório no intervalo [0, n).
 *
 * @note
 * - Se @p n == 0, o valor retornado é 0.
 */
HSCOPT_INLINE size_t hscopt_rng_random_index(hscopt_rng *rng, size_t n) {
  if (HSCOPT_UNLIKELY(n == 0)) return 0;

  uint64_t x = hscopt_rng_next_u64(rng);
  __uint128_t m = (__uint128_t)x * (__uint128_t)n;
  uint64_t l = (uint64_t)m;

  if (HSCOPT_UNLIKELY(l < (uint64_t)n)) {
    // Calcula o threshold: (2^64 % n)
    uint64_t t = -((uint64_t)n) % (uint64_t)n;
    while (l < t) {
      x = hscopt_rng_next_u64(rng);
      m = (__uint128_t)x * (__uint128_t)n;
      l = (uint64_t)m;
    }
  }

  return (size_t)(m >> 64);
}

#ifdef __cplusplus
}
#endif

#endif /* HSCOPT_RNG_H */
