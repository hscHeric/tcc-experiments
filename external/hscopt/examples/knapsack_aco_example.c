#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

#include "hscopt/aco.h"
#include "hscopt/rng.h"
#include "knapsack_example_common.h"

int main(void) {
  const knapsack_data kp = KNAPSACK_DEFAULT_INSTANCE;

  hscopt_decode_ctx dctx = {.inst = NULL, .user = (void *)&kp, .ws = NULL};

  hscopt_rng rng;
  hscopt_rng_seed(&rng, (uint64_t)time(NULL));

  const size_t n_keys = KNAPSACK_N_ITEMS;
  const size_t archive_size = 50;
  const size_t n_ants = 60;
  const unsigned max_iters = 400;
  const unsigned max_threads = 4;
  const double q = 0.08;
  const double xi = 0.9;

  hscopt_aco_ctx *ctx =
      hscopt_aco_create(n_keys, archive_size, n_ants, max_iters, max_threads, q,
                        xi, knapsack_decoder, &dctx, &rng);
  if (!ctx) {
    fprintf(stderr, "Erro ao criar contexto ACO\n");
    return 1;
  }

  if (hscopt_aco_iterate(ctx, max_iters) != 0) {
    fprintf(stderr, "Falha na execucao ACO\n");
    hscopt_aco_destroy(ctx);
    return 1;
  }

  const double *best_keys = hscopt_aco_best_keys(ctx);
  const double best_objective = hscopt_aco_best_fitness(ctx);
  const double best_profit = -best_objective;

  size_t selected[KNAPSACK_N_ITEMS];
  size_t n_selected = 0;
  double used_weight = 0.0;
  double total_profit = 0.0;

  knapsack_decode_selected_items(best_keys, &kp, selected, &n_selected,
                                 &used_weight, &total_profit);

  printf("=== ACO | Mochila 0/1 com Random Keys ===\n");
  printf("Iteracoes: %u\n", hscopt_aco_iteration(ctx));
  printf("Melhor objetivo (min): %.4f\n", best_objective);
  printf("Lucro total: %.4f\n", best_profit);
  printf("Peso usado: %.4f / %.4f\n", used_weight, kp.capacity);
  printf("Itens escolhidos (%zu): ", n_selected);
  for (size_t i = 0; i < n_selected; ++i) {
    printf("%zu%s", selected[i], (i + 1 < n_selected) ? ", " : "\n");
  }

  hscopt_aco_destroy(ctx);
  return 0;
}
