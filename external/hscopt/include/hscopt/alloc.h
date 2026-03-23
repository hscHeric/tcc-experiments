#ifndef HSCOPT_ALLOC_H
#define HSCOPT_ALLOC_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file alloc.h
 * @brief Interface de alocador customizado.
 */

/**
 * @typedef hscopt_alloc_fn
 * @brief Funcao de alocacao.
 *
 * @param size Tamanho em bytes.
 * @param alignment Alinhamento desejado (0 = indiferente).
 * @param user Ponteiro de usuario opcional.
 */
typedef void *(*hscopt_alloc_fn)(size_t size, size_t alignment, void *user);

/**
 * @typedef hscopt_calloc_fn
 * @brief Funcao de alocacao zero-inicializada.
 *
 * @param count Numero de elementos.
 * @param size Tamanho de cada elemento.
 * @param alignment Alinhamento desejado (0 = indiferente).
 * @param user Ponteiro de usuario opcional.
 */
typedef void *(*hscopt_calloc_fn)(size_t count, size_t size, size_t alignment,
                                 void *user);

/**
 * @typedef hscopt_free_fn
 * @brief Funcao de liberacao.
 *
 * @param ptr Ponteiro retornado por alloc/calloc.
 * @param user Ponteiro de usuario opcional.
 */
typedef void (*hscopt_free_fn)(void *ptr, void *user);

/**
 * @struct hscopt_allocator
 * @brief Alocador customizavel usado pela biblioteca.
 */
typedef struct hscopt_allocator {
  hscopt_alloc_fn alloc;
  hscopt_calloc_fn calloc;
  hscopt_free_fn free;
  size_t alignment;
  void *user;
} hscopt_allocator;

/**
 * @brief Retorna o alocador default.
 *
 * O default usa malloc/calloc/free e ignora alignment.
 */
void hscopt_allocator_default(hscopt_allocator *out);

/**
 * @brief Define um alocador global para a biblioteca.
 *
 * Se @p alloc for NULL, restaura o alocador default (malloc/calloc/free).
 *
 * @return 0 em sucesso, valor diferente de 0 em erro.
 *
 * @note Nao e thread-safe para chamadas concorrentes com criacao de contextos.
 */
int hscopt_set_allocator(const hscopt_allocator *alloc);

/**
 * @brief Obtém o alocador global atual.
 */
void hscopt_get_allocator(hscopt_allocator *out);

/**
 * @brief Helpers inline para usar um alocador resolvido.
 */
static inline void *hscopt_alloc(const hscopt_allocator *a, size_t size) {
  return a->alloc ? a->alloc(size, a->alignment, a->user) : NULL;
}

static inline void *hscopt_calloc(const hscopt_allocator *a, size_t count,
                                  size_t size) {
  return a->calloc ? a->calloc(count, size, a->alignment, a->user) : NULL;
}

static inline void hscopt_free(const hscopt_allocator *a, void *ptr) {
  if (a->free) a->free(ptr, a->user);
}

#ifdef __cplusplus
}
#endif

#endif /* HSCOPT_ALLOC_H */
