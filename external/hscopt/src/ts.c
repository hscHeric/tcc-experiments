#include "hscopt/ts.h"

#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "hscopt/defs.h"
#include "hscopt/rng.h"

#ifdef _OPENMP
  #include <omp.h>
#endif

#define TS_CAND_PTR(ctx, i) (&(ctx)->cand_keys[(i) * (ctx)->dim])

struct hscopt_ts_ctx {
  size_t dim;
  size_t neighborhood_size;

  unsigned tabu_tenure;
  unsigned iter;
  unsigned max_iters;
  unsigned max_threads;
  unsigned eff_threads;

  hscopt_decoder_fn decoder;
  hscopt_decode_ctx *dctx;

  hscopt_rng *rng_tls;

  double *x;
  double fx;

  double *best;
  double fbest;

  double *cand_keys;
  double *cand_fit;
  size_t *cand_move_idx;
  unsigned *tabu_until;
};

HSCOPT_INLINE void ts_init_solution(double *HSCOPT_RESTRICT dst, size_t dim,
                                    const double *initial_keys,
                                    hscopt_rng *rng) {
  if (initial_keys) {
    memcpy(dst, initial_keys, dim * sizeof(double));
    HSCOPT_CLAMP_KEY_VEC(dst, dim);
    return;
  }

  for (size_t i = 0; i < dim; ++i) {
    dst[i] = hscopt_rng_next_u01(rng);
  }
}

HSCOPT_INLINE void ts_generate_candidate(hscopt_ts_ctx *ctx,
                                         double *HSCOPT_RESTRICT dst,
                                         size_t *move_idx, unsigned tid) {
  memcpy(dst, ctx->x, ctx->dim * sizeof(double));

  const size_t j = hscopt_rng_random_index(&ctx->rng_tls[tid], ctx->dim);
  dst[j] = hscopt_rng_next_u01(&ctx->rng_tls[tid]);
  *move_idx = j;
}

hscopt_ts_ctx *hscopt_ts_create(size_t n_keys, size_t neighborhood_size,
                                unsigned tabu_tenure, unsigned max_iters,
                                unsigned max_threads,
                                hscopt_decoder_fn decoder,
                                hscopt_decode_ctx *dctx, hscopt_rng *rng,
                                const double *initial_keys) {
  if (!decoder || !rng || n_keys == 0 || neighborhood_size == 0 ||
      max_iters == 0 || tabu_tenure == 0) {
    return NULL;
  }

  hscopt_ts_ctx *ctx = (hscopt_ts_ctx *)calloc(1, sizeof(*ctx));
  if (!ctx) {
    return NULL;
  }

  ctx->dim = n_keys;
  ctx->neighborhood_size = neighborhood_size;
  ctx->tabu_tenure = tabu_tenure;
  ctx->iter = 0;
  ctx->max_iters = max_iters;
  ctx->max_threads = (max_threads == 0u ? 1u : max_threads);
#ifdef _OPENMP
  ctx->eff_threads = ctx->max_threads;
#else
  ctx->eff_threads = 1u;
#endif
  ctx->decoder = decoder;
  ctx->dctx = dctx;

  ctx->x = (double *)malloc(n_keys * sizeof(double));
  ctx->best = (double *)malloc(n_keys * sizeof(double));
  ctx->cand_keys =
      (double *)malloc(neighborhood_size * n_keys * sizeof(double));
  ctx->cand_fit = (double *)malloc(neighborhood_size * sizeof(double));
  ctx->cand_move_idx = (size_t *)malloc(neighborhood_size * sizeof(size_t));
  ctx->tabu_until = (unsigned *)calloc(n_keys, sizeof(unsigned));
  ctx->rng_tls =
      (hscopt_rng *)calloc((size_t)ctx->eff_threads, sizeof(hscopt_rng));

  if (!ctx->x || !ctx->best || !ctx->cand_keys || !ctx->cand_fit ||
      !ctx->cand_move_idx || !ctx->tabu_until || !ctx->rng_tls) {
    hscopt_ts_destroy(ctx);
    return NULL;
  }

  ctx->rng_tls[0] = *rng;
  for (unsigned t = 1; t < ctx->eff_threads; ++t) {
    ctx->rng_tls[t] = ctx->rng_tls[t - 1];
    hscopt_rng_long_jump(&ctx->rng_tls[t]);
  }

  if (hscopt_ts_reset(ctx, initial_keys) != 0) {
    hscopt_ts_destroy(ctx);
    return NULL;
  }

  return ctx;
}

void hscopt_ts_destroy(hscopt_ts_ctx *ctx) {
  if (!ctx) return;

  free(ctx->x);
  free(ctx->best);
  free(ctx->cand_keys);
  free(ctx->cand_fit);
  free(ctx->cand_move_idx);
  free(ctx->tabu_until);
  free(ctx->rng_tls);
  free(ctx);
}

int hscopt_ts_reset(hscopt_ts_ctx *ctx, const double *initial_keys) {
  if (!ctx) {
    return 1;
  }

  ctx->iter = 0;
  memset(ctx->tabu_until, 0, ctx->dim * sizeof(unsigned));

  ts_init_solution(ctx->x, ctx->dim, initial_keys, &ctx->rng_tls[0]);
  ctx->fx = ctx->decoder(ctx->x, ctx->dim, ctx->dctx);
  memcpy(ctx->best, ctx->x, ctx->dim * sizeof(double));
  ctx->fbest = ctx->fx;

  return 0;
}

int hscopt_ts_iterate(hscopt_ts_ctx *ctx, unsigned iters) {
  if (!ctx || iters == 0) {
    return 1;
  }

  if (ctx->iter >= ctx->max_iters || ctx->iter + iters > ctx->max_iters) {
    return 2;
  }

  for (unsigned it = 0; it < iters; ++it) {
#ifdef _OPENMP
  #pragma omp parallel for num_threads(ctx->eff_threads) schedule(static)
#endif
    for (ptrdiff_t ci = 0; ci < (ptrdiff_t)ctx->neighborhood_size; ++ci) {
      unsigned tid = 0;
#ifdef _OPENMP
      tid = (unsigned)omp_get_thread_num();
#endif
      double *const HSCOPT_RESTRICT cand = TS_CAND_PTR(ctx, (size_t)ci);
      ts_generate_candidate(ctx, cand, &ctx->cand_move_idx[(size_t)ci], tid);
      ctx->cand_fit[(size_t)ci] = ctx->decoder(cand, ctx->dim, ctx->dctx);
    }

    size_t fallback_idx = 0;
    double fallback_fit = ctx->cand_fit[0];
    size_t chosen_idx = (size_t)-1;
    double chosen_fit = INFINITY;

    for (size_t i = 0; i < ctx->neighborhood_size; ++i) {
      const double fit = ctx->cand_fit[i];
      const size_t move = ctx->cand_move_idx[i];

      if (fit < fallback_fit) {
        fallback_fit = fit;
        fallback_idx = i;
      }

      const int admissible =
          (ctx->iter >= ctx->tabu_until[move]) || (fit < ctx->fbest);
      if (admissible && fit < chosen_fit) {
        chosen_fit = fit;
        chosen_idx = i;
      }
    }

    if (chosen_idx == (size_t)-1) {
      chosen_idx = fallback_idx;
      chosen_fit = fallback_fit;
    }

    memcpy(ctx->x, TS_CAND_PTR(ctx, chosen_idx), ctx->dim * sizeof(double));
    ctx->fx = chosen_fit;
    ctx->tabu_until[ctx->cand_move_idx[chosen_idx]] =
        ctx->iter + ctx->tabu_tenure + 1u;

    if (ctx->fx < ctx->fbest) {
      ctx->fbest = ctx->fx;
      memcpy(ctx->best, ctx->x, ctx->dim * sizeof(double));
    }

    ++ctx->iter;
  }

  return 0;
}

double hscopt_ts_best_fitness(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->fbest : INFINITY;
}

const double *hscopt_ts_best_keys(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->best : NULL;
}

double hscopt_ts_current_fitness(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->fx : INFINITY;
}

const double *hscopt_ts_current_keys(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->x : NULL;
}

unsigned hscopt_ts_iteration(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->iter : 0u;
}

unsigned hscopt_ts_max_iters(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->max_iters : 0u;
}

size_t hscopt_ts_n_keys(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->dim : 0u;
}

size_t hscopt_ts_neighborhood_size(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->neighborhood_size : 0u;
}

unsigned hscopt_ts_tabu_tenure(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->tabu_tenure : 0u;
}

unsigned hscopt_ts_max_threads(const hscopt_ts_ctx *ctx) {
  return ctx ? ctx->eff_threads : 1u;
}

int hscopt_ts_try_update_best(hscopt_ts_ctx *ctx, const double *keys) {
  if (!ctx || !keys || !ctx->decoder) {
    return -1;
  }

  const double f = ctx->decoder(keys, ctx->dim, ctx->dctx);
  if (f < ctx->fbest) {
    ctx->fbest = f;
    memcpy(ctx->best, keys, ctx->dim * sizeof(double));
    return 1;
  }

  return 0;
}
