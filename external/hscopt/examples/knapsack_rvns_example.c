#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

#include "hscopt/rng.h"
#include "hscopt/rvns.h"
#include "knapsack_example_common.h"

int main(void) {
  const knapsack_data kp = KNAPSACK_DEFAULT_INSTANCE;

  hscopt_decode_ctx dctx = {.inst = NULL, .user = (void *)&kp, .ws = NULL};

  hscopt_rng rng;
  hscopt_rng_seed(&rng, (uint64_t)time(NULL));

  const size_t n_keys = KNAPSACK_N_ITEMS;
  const size_t k_max = 8;
  const unsigned max_iters = 1000;
  const unsigned max_threads = 4;

  hscopt_rvns_ctx *ctx =
      hscopt_rvns_create(n_keys, k_max, max_iters, max_threads,
                         knapsack_decoder, &dctx, &rng, NULL);
  if (!ctx) {
    fprintf(stderr, "Erro ao criar contexto RVNS\n");
    return 1;
  }

  if (hscopt_rvns_iterate(ctx, max_iters) != 0) {
    fprintf(stderr, "Falha na execucao RVNS\n");
    hscopt_rvns_destroy(ctx);
    return 1;
  }

  const double *best_keys = hscopt_rvns_best_keys(ctx);
  const double best_objective = hscopt_rvns_best_fitness(ctx);
  const double best_profit = -best_objective;

  size_t selected[KNAPSACK_N_ITEMS];
  size_t n_selected = 0;
  double used_weight = 0.0;
  double total_profit = 0.0;

  knapsack_decode_selected_items(best_keys, &kp, selected, &n_selected,
                                 &used_weight, &total_profit);

  printf("=== RVNS | Mochila 0/1 com Random Keys ===\n");
  printf("Iteracoes: %u\n", hscopt_rvns_iteration(ctx));
  printf("Melhor objetivo (min): %.4f\n", best_objective);
  printf("Lucro total: %.4f\n", best_profit);
  printf("Peso usado: %.4f / %.4f\n", used_weight, kp.capacity);
  printf("Itens escolhidos (%zu): ", n_selected);
  for (size_t i = 0; i < n_selected; ++i) {
    printf("%zu%s", selected[i], (i + 1 < n_selected) ? ", " : "\n");
  }

  hscopt_rvns_destroy(ctx);
  return 0;
}
