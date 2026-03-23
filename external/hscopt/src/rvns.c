#include "hscopt/rvns.h"

#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "hscopt/alloc.h"
#include "hscopt/decoder.h"
#include "hscopt/rng.h"

#define CAND_PTR(ctx, tid) (&(ctx)->cand_keys[(size_t)(tid) * (ctx)->dim])

struct hscopt_rvns_ctx {
  size_t dim;                 // tamanho do vetor de chaves aleatórias
  size_t k_max;               // pertubação máxima
  unsigned iter;              // iteração atual
  unsigned max_iters;         // número máximo de iterações
  unsigned max_threads;       // número máximo de threads
  unsigned eff_threads;       // número real de threads usadas
  hscopt_decoder_fn decoder;  // decoder
  hscopt_decode_ctx *dctx;    // contexto do decder
  hscopt_rng *rng_tls;        // vetor de rng[eff_threads]
  double *x;                  // melhor atual
  double fx;                  // melhor função objetivo
  double *best;               // melhor global
  double fbest;               // função objetivo do melhor global
  double *cand_keys;          // candidatos de tamanho [dim * eff_threads]
  double *cand_fit;           // candidatos de tamanho [eff_threads]

  hscopt_allocator alloc;
};

int hscopt_rvns_reset(hscopt_rvns_ctx *ctx, const double *initial_keys) {
  if (!ctx) {
    return 1;  // erro ctx null
  }

  ctx->iter = 0;
  if (initial_keys) {
    memcpy(ctx->x, initial_keys, ctx->dim * sizeof(double));
    for (size_t i = 0; i < ctx->dim; ++i) {
      ctx->x[i] = HSCOPT_CLAMP_KEY(ctx->x[i]);
    }
  } else {
    for (size_t i = 0; i < ctx->dim; ++i) {
      ctx->x[i] = hscopt_rng_next_u01(&ctx->rng_tls[0]);
    }
  }

  ctx->fx = ctx->decoder(ctx->x, ctx->dim, ctx->dctx);
  memcpy(ctx->best, ctx->x, ctx->dim * sizeof(double));
  ctx->fbest = ctx->fx;

  return 0;
}

void hscopt_rvns_destroy(hscopt_rvns_ctx *ctx) {
  if (!ctx) return;
  hscopt_free(&ctx->alloc, ctx->rng_tls);
  hscopt_free(&ctx->alloc, ctx->x);
  hscopt_free(&ctx->alloc, ctx->best);
  hscopt_free(&ctx->alloc, ctx->cand_keys);
  hscopt_free(&ctx->alloc, ctx->cand_fit);
  hscopt_free(&ctx->alloc, ctx);
}

hscopt_rvns_ctx *hscopt_rvns_create(
    size_t n_keys, size_t k_max, unsigned max_iters, unsigned max_threads,
    hscopt_decoder_fn decoder, hscopt_decode_ctx *dctx, hscopt_rng *rng,
    const double *initial_keys) {
  return hscopt_rvns_create_with_allocator(
      n_keys, k_max, max_iters, max_threads, decoder, dctx, rng, initial_keys,
      NULL);
}

hscopt_rvns_ctx *hscopt_rvns_create_with_allocator(
    size_t n_keys, size_t k_max, unsigned max_iters, unsigned max_threads,
    hscopt_decoder_fn decoder, hscopt_decode_ctx *dctx, hscopt_rng *rng,
    const double *initial_keys, const hscopt_allocator *alloc) {
  if (!decoder || !rng || max_iters == 0 || k_max == 0 || n_keys == 0) {
    return NULL;
  }

  hscopt_allocator resolved;
  if (alloc) {
    if (!alloc->alloc || !alloc->calloc || !alloc->free) {
      return NULL;
    }
    resolved = *alloc;
  } else {
    hscopt_get_allocator(&resolved);
  }

  hscopt_rvns_ctx *ctx =
      (hscopt_rvns_ctx *)hscopt_calloc(&resolved, 1, sizeof(*ctx));
  if (!ctx) {
    return NULL;
  };
  ctx->alloc = resolved;

  ctx->dim = n_keys;
  ctx->k_max = k_max;
  ctx->iter = 0;
  ctx->max_iters = max_iters;
  ctx->max_threads = (max_threads == 0u ? 1u : max_threads);

#ifdef _OPENMP
  ctx->eff_threads = (max_threads == 0u ? 1u : max_threads);
#else
  ctx->eff_threads = 1u;
#endif /* ifdef _OPENMP */

  ctx->decoder = decoder;
  ctx->dctx = dctx;
  ctx->x = (double *)hscopt_alloc(&ctx->alloc, n_keys * sizeof(double));
  ctx->best = (double *)hscopt_alloc(&ctx->alloc, n_keys * sizeof(double));
  ctx->cand_keys = (double *)hscopt_alloc(
      &ctx->alloc, (size_t)ctx->eff_threads * n_keys * sizeof(double));
  ctx->cand_fit = (double *)hscopt_alloc(
      &ctx->alloc, (size_t)ctx->eff_threads * sizeof(double));

  if (!ctx->x || !ctx->best || !ctx->cand_keys || !ctx->cand_fit) {
    hscopt_rvns_destroy(ctx);
    return NULL;
  }

  // alocação das instâncias de RNG
  ctx->rng_tls = (hscopt_rng *)hscopt_calloc(
      &ctx->alloc, (size_t)ctx->eff_threads, sizeof(hscopt_rng));
  if (!ctx->rng_tls) {
    hscopt_rvns_destroy(ctx);
    return NULL;
  }

  ctx->rng_tls[0] = *rng;
  for (unsigned i = 1; i < ctx->eff_threads; ++i) {
    ctx->rng_tls[i] = ctx->rng_tls[i - 1];
    hscopt_rng_long_jump(&ctx->rng_tls[i]);
  }

  if (hscopt_rvns_reset(ctx, initial_keys) != 0) {
    hscopt_rvns_destroy(ctx);
    return NULL;
  }

  return ctx;
}

double hscopt_rvns_best_fitness(const hscopt_rvns_ctx *ctx) {
  return ctx ? ctx->fbest : INFINITY;
}

const double *hscopt_rvns_best_keys(const hscopt_rvns_ctx *ctx) {
  return ctx ? ctx->best : NULL;
}

unsigned hscopt_rvns_iteration(const hscopt_rvns_ctx *ctx) {
  return ctx ? ctx->iter : 0u;
}

size_t hscopt_rvns_n_keys(const hscopt_rvns_ctx *ctx) {
  return ctx ? ctx->dim : 0u;
}

size_t hscopt_rvns_k_max(const hscopt_rvns_ctx *ctx) {
  return ctx ? ctx->k_max : 0u;
}

unsigned hscopt_rvns_max_threads(const hscopt_rvns_ctx *ctx) {
  return ctx ? ctx->eff_threads : 1u;
}

// Shaking em N_k(x), primeiro copia x para y e pertuba k posições
HSCOPT_INLINE void rvns_shake(double *HSCOPT_RESTRICT y,
                              const double *HSCOPT_RESTRICT x, size_t dim,
                              size_t k, hscopt_rng *rng) {
  memcpy(y, x, dim * sizeof(double));
  if (k > dim) k = dim;
  for (size_t t = 0; t < k; ++t) {
    size_t j = (size_t)(hscopt_rng_next_u01(rng) * (double)dim);
    if (j >= dim) j = dim - 1;
    y[j] = HSCOPT_CLAMP_KEY(hscopt_rng_next_u01(rng));
  }
}

int hscopt_rvns_iterate(hscopt_rvns_ctx *ctx, unsigned iters) {
  if (!ctx || iters == 0) {
    return 1;  // o núemro de itereações executadas não pode ser 0
  }

  if (ctx->iter >= ctx->max_iters) {
    return 2;  // iter já ultrapassou o maximo de iterações
  }
  if (ctx->iter + iters > ctx->max_iters) {
    return 2;  // passa o máximo ao executar as iterações solicitadas
  }

  for (unsigned it = 0; it < iters; ++it) {
    size_t k = 1;  // nível da pertubação

    while (k <= ctx->k_max) {
#ifdef _OPENMP
#pragma omp parallel for num_threads(ctx->eff_threads)
#endif
      for (int tid_i = 0; tid_i < (int)ctx->eff_threads; ++tid_i) {
        const unsigned tid = (unsigned)tid_i;
        double *const HSCOPT_RESTRICT y = CAND_PTR(ctx, tid);
        rvns_shake(y, ctx->x, ctx->dim, k, &ctx->rng_tls[tid]);
        ctx->cand_fit[tid] = ctx->decoder(y, ctx->dim, ctx->dctx);
      }

      unsigned best_tid = 0;
      double fy_best = ctx->cand_fit[0];
      for (unsigned tid = 1; tid < ctx->eff_threads; ++tid) {
        const double fy = ctx->cand_fit[tid];
        if (fy < fy_best) {
          fy_best = fy;
          best_tid = tid;
        }
      }

      if (fy_best < ctx->fx) {
        memcpy(ctx->x, CAND_PTR(ctx, best_tid), ctx->dim * sizeof(double));
        ctx->fx = fy_best;

        if (ctx->fx < ctx->fbest) {
          ctx->fbest = ctx->fx;
          memcpy(ctx->best, ctx->x, ctx->dim * sizeof(double));
        }

        k = 1; /* volta para N_1 */
      } else {
        ++k;
      }
    }

    ++ctx->iter;
  }
  return 0;
}
