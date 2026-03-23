#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hscopt/hscopt.h"

static void *aligned_alloc_fn(size_t size, size_t alignment, void *user) {
  (void)user;
  if (alignment == 0) alignment = 64;
#if defined(_POSIX_VERSION)
  void *ptr = NULL;
  if (posix_memalign(&ptr, alignment, size) != 0) return NULL;
  return ptr;
#else
  (void)alignment;
  return malloc(size);
#endif
}

static void *aligned_calloc_fn(size_t count, size_t size, size_t alignment,
                               void *user) {
  (void)user;
  size_t total = count * size;
  void *ptr = aligned_alloc_fn(total, alignment, NULL);
  if (!ptr) return NULL;
  memset(ptr, 0, total);
  return ptr;
}

static void aligned_free_fn(void *ptr, void *user) {
  (void)user;
  free(ptr);
}

static double sum_decoder(const double *keys, size_t n_keys,
                          HSCOPT_UNUSED hscopt_decode_ctx *ctx) {
  double s = 0.0;
  for (size_t i = 0; i < n_keys; ++i) s += keys[i];
  return s;
}

int main(void) {
  hscopt_allocator alloc = {
      .alloc = aligned_alloc_fn,
      .calloc = aligned_calloc_fn,
      .free = aligned_free_fn,
      .alignment = 64,
      .user = NULL,
  };

  hscopt_rng rng;
  hscopt_rng_seed(&rng, 123);

  hscopt_hho_ctx *ctx = hscopt_hho_create_with_allocator(
      64, 64, 10, 1, sum_decoder, NULL, &rng, &alloc);
  if (!ctx) {
    fprintf(stderr, "Falha ao criar contexto com alocador customizado\n");
    return 1;
  }

  for (unsigned i = 0; i < 10; ++i) {
    if (hscopt_hho_iterate(ctx, 1) != 0) break;
  }

  printf("Best: %.6f\n", hscopt_hho_best_fitness(ctx));
  hscopt_hho_destroy(ctx);

  return 0;
}
