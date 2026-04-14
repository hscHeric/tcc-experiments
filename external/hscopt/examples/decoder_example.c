/*
 * decoder_example.c
 *
 * Mostra o fluxo básico:
 * RNG -> random keys -> decoder -> valor objetivo
 */

#include <stdio.h>
#include <stdlib.h>

#include "hscopt/decoder.h"
#include "hscopt/rng.h"

static double sum_decoder(const double *keys, size_t n_keys,
                          HSCOPT_UNUSED hscopt_decode_ctx *ctx) {
  double s = 0.0;
  for (size_t i = 0; i < n_keys; ++i) s += keys[i];
  return s;
}

int main(void) {
  const size_t n_keys = 20;

  double *keys = (double *)malloc(n_keys * sizeof(*keys));
  if (!keys) return 1;

  hscopt_rng rng;
  hscopt_rng_seed(&rng, 123456789ULL);

  for (size_t i = 0; i < n_keys; ++i) keys[i] = hscopt_rng_next_u01(&rng);

  hscopt_decode_ctx ctx = {.inst = NULL, .user = NULL, .ws = NULL};

  double obj = sum_decoder(keys, n_keys, &ctx);
  printf("obj = %.17g\n", obj);

  free(keys);
  return 0;
}
