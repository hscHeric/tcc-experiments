#include <stddef.h>
#include <stdio.h>
#include <time.h>

#include "hscopt/hho.h"
#include "hscopt/rng.h"

static double sum_decoder(const double *keys, size_t n_keys,
                          HSCOPT_UNUSED hscopt_decode_ctx *ctx) {
  double total = 0;
  for (size_t i = 0; i < n_keys; ++i) {
    if (i % 2 == 0) {
      total += 2.0 * keys[i];
    } else {
      total -= (0.5 * keys[i]);
    }
  }

  return total;
}

int main(void) {
  size_t dim = 100;
  size_t n_agents = 1000;
  unsigned max_iters = 1000;
  unsigned threads = 8;

  hscopt_rng rng;
  hscopt_rng_seed(&rng, (size_t)time(NULL));

  hscopt_hho_ctx *ctx = hscopt_hho_create(dim, n_agents, max_iters, threads,
                                          sum_decoder, NULL, &rng);

  if (!ctx) {
    fprintf(stderr, "Erro ao criar contexto HHO\n");
    return 1;
  }

  printf("Iteracao\tMelhor Fitness\tMelhor Chave[0]\n");

  for (unsigned i = 0; i < max_iters; ++i) {
    int status = hscopt_hho_iterate(ctx, 1);

    if (status != 0) {
      printf("\nErro na iteracao %u (Status: %d)\n", i, status);
      break;
    }

    double current_best = hscopt_hho_best_fitness(ctx);
    const double *keys = hscopt_hho_best_keys(ctx);

    printf("%u\t\t%.6f\t%.4f\n", hscopt_hho_iteration(ctx), current_best,
           keys[0]);
  }
  printf("Resultado Final: %.6f\n", hscopt_hho_best_fitness(ctx));

  hscopt_hho_destroy(ctx);

  return 0;
}
