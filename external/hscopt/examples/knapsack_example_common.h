#ifndef HSCOPT_KNAPSACK_EXAMPLE_COMMON_H
#define HSCOPT_KNAPSACK_EXAMPLE_COMMON_H

#include <math.h>
#include <stddef.h>

#include "hscopt/decoder.h"

#define KNAPSACK_N_ITEMS 24

typedef struct knapsack_data {
  double capacity;
  double weights[KNAPSACK_N_ITEMS];
  double profits[KNAPSACK_N_ITEMS];
} knapsack_data;

static const knapsack_data KNAPSACK_DEFAULT_INSTANCE = {
    .capacity = 45.0,
    .weights = {12,  7, 11, 8, 9, 6, 7, 3, 4, 5,  9,  6,
                10, 13, 2, 1, 4, 8, 6, 7, 3, 12, 11, 5},
    .profits = {24, 13, 23, 15, 16, 11, 13, 7, 8, 10, 17, 11,
                19, 25, 4,  2,  7,  14, 12, 13, 6, 22, 20, 9},
};

static inline void knapsack_rank_items_desc_by_key(const double *keys, size_t n,
                                                   size_t *order_out) {
  for (size_t i = 0; i < n; ++i) {
    order_out[i] = i;
  }

  for (size_t i = 1; i < n; ++i) {
    const size_t idx = order_out[i];
    const double key = keys[idx];
    size_t j = i;

    while (j > 0 && keys[order_out[j - 1]] < key) {
      order_out[j] = order_out[j - 1];
      --j;
    }
    order_out[j] = idx;
  }
}

static inline double knapsack_decoder(const double *keys, size_t n_keys,
                                      hscopt_decode_ctx *ctx) {
  const knapsack_data *kp = (const knapsack_data *)ctx->user;
  if (!kp || n_keys != KNAPSACK_N_ITEMS) {
    return INFINITY;
  }

  size_t order[KNAPSACK_N_ITEMS];
  knapsack_rank_items_desc_by_key(keys, n_keys, order);

  double total_weight = 0.0;
  double total_profit = 0.0;

  for (size_t p = 0; p < n_keys; ++p) {
    const size_t item = order[p];
    const double w = kp->weights[item];

    if (total_weight + w <= kp->capacity) {
      total_weight += w;
      total_profit += kp->profits[item];
    }
  }

  return -total_profit;
}

static inline void knapsack_decode_selected_items(
    const double *keys, const knapsack_data *kp, size_t *selected,
    size_t *n_selected, double *used_weight, double *total_profit) {
  size_t order[KNAPSACK_N_ITEMS];
  knapsack_rank_items_desc_by_key(keys, KNAPSACK_N_ITEMS, order);

  *n_selected = 0;
  *used_weight = 0.0;
  *total_profit = 0.0;

  for (size_t p = 0; p < KNAPSACK_N_ITEMS; ++p) {
    const size_t item = order[p];
    const double w = kp->weights[item];

    if (*used_weight + w <= kp->capacity) {
      selected[*n_selected] = item;
      (*n_selected)++;
      *used_weight += w;
      *total_profit += kp->profits[item];
    }
  }
}

#endif /* HSCOPT_KNAPSACK_EXAMPLE_COMMON_H */
