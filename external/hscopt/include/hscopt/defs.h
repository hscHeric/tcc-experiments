#ifndef HSCOPT_DEFS_H
#define HSCOPT_DEFS_H

#include <stddef.h>

/**
 * @file defs.h
 * @brief Macros e utilitários comuns da biblioteca.
 */

#if defined(__GNUC__) || defined(__clang__)

  /**
   * @brief Define uma função como `static inline` e força inlining quando
   * suportado.
   */
  #define HSCOPT_INLINE static inline __attribute__((always_inline))

  /**
   * @brief Marca símbolo como potencialmente não utilizado (evita warning).
   */
  #define HSCOPT_UNUSED __attribute__((unused))

  /**
   * @brief Indica ao compilador que a condição é provavelmente verdadeira.
   * @param x Expressão booleana.
   */
  #define HSCOPT_LIKELY(x) __builtin_expect(!!(x), 1)

  /**
   * @brief Indica ao compilador que a condição é provavelmente falsa.
   * @param x Expressão booleana.
   */
  #define HSCOPT_UNLIKELY(x) __builtin_expect(!!(x), 0)
#if defined(__cplusplus)
  #define HSCOPT_RESTRICT __restrict__
#else
  #define HSCOPT_RESTRICT restrict
#endif
#else
  // FALLBACKS
  #define HSCOPT_INLINE static inline
  #define HSCOPT_UNUSED
  #define HSCOPT_LIKELY(x) (x)
  #define HSCOPT_UNLIKELY(x) (x)
  #if defined(__cplusplus)
    #define HSCOPT_RESTRICT __restrict__
  #else
    #define HSCOPT_RESTRICT restrict
  #endif
#endif

/**
 * @brief Restringe um valor ao intervalo [lo, hi].
 * @param x Valor.
 * @param lo Limite inferior.
 * @param hi Limite superior.
 */
#define HSCOPT_CLAMP(x, lo, hi) ((x) < (lo) ? (lo) : ((x) > (hi) ? (hi) : (x)))

/**
 * @brief Clamp específico para random keys no intervalo [0, 1).
 *
 * Usa um limite superior ligeiramente menor que 1.0 para evitar representar 1.0
 * devido a arredondamento.
 *
 * @param x Valor.
 */
#define HSCOPT_CLAMP_KEY(x) HSCOPT_CLAMP((x), 0.0, (1.0 - 1e-15))

/**
 * @brief Clamp de vetor para random keys no intervalo [0, 1).
 *
 * @param x Ponteiro para o vetor.
 * @param n Tamanho do vetor.
 */
#define HSCOPT_CLAMP_KEY_VEC(x, n)         \
  do {                                     \
    for (size_t _i = 0; _i < (n); ++_i) {  \
      (x)[_i] = HSCOPT_CLAMP_KEY((x)[_i]); \
    }                                      \
  } while (0)

/**
 * @brief Troca dois valores (swap) de um tipo explícito.
 * @param type Tipo das variáveis.
 * @param a Primeiro valor.
 * @param b Segundo valor.
 */
#define HSCOPT_SWAP(type, a, b) \
  do {                          \
    type _tmp = (a);            \
    (a) = (b);                  \
    (b) = _tmp;                 \
  } while (0)

/**
 * @brief Constante pi em double
 */
#define HSCOPT_PI 3.14159265358979323846

#endif /* HSCOPT_DEFS_H */
