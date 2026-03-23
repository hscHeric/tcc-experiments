#include "hscopt/aco.h"

#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "hscopt/alloc.h"
#include "hscopt/defs.h"
#include "hscopt/rng.h"

#ifdef _OPENMP
  #include <omp.h>
#endif

#define ARCH_KEY_PTR(ctx, i) (&(ctx)->archive_keys[(i) * (ctx)->dim])
#define CAND_KEY_PTR(ctx, i) (&(ctx)->cand_keys[(i) * (ctx)->dim])

typedef struct hscopt_gauss_state {
  int has_spare;
  double spare;
} hscopt_gauss_state;

struct hscopt_aco_ctx {
  size_t dim;
  size_t archive_size;
  size_t n_ants;

  unsigned iter;
  unsigned max_iters;
  unsigned max_threads;
  unsigned eff_threads;

  double q;
  double xi;

  hscopt_decoder_fn decoder;
  hscopt_decode_ctx *dctx;

  hscopt_rng *rng_tls;
  hscopt_gauss_state *gauss_tls;

  double *archive_keys; /* [archive_size * dim] */
  double *archive_fit;  /* [archive_size], sempre ordenado crescente */
  double *cand_keys;    /* [n_ants * dim] */
  double *cand_fit;     /* [n_ants] */
  double *best_keys;    /* [dim] */
  double best_fit;
  double *cdf;      /* [archive_size], CDF dos ranks */
  double *tmp_key;  /* [dim], buffer auxiliar */

  hscopt_allocator alloc;
};

HSCOPT_INLINE double aco_randn(hscopt_aco_ctx *ctx, unsigned tid) {
  hscopt_gauss_state *gs = &ctx->gauss_tls[tid];
  hscopt_rng *rng = &ctx->rng_tls[tid];

  if (gs->has_spare) {
    gs->has_spare = 0;
    return gs->spare;
  }

  double u1 = hscopt_rng_next_u01(rng);
  if (u1 <= 0.0) {
    u1 = 1e-12;
  }

  const double u2 = hscopt_rng_next_u01(rng);
  const double r = sqrt(-2.0 * log(u1));
  const double theta = 2.0 * HSCOPT_PI * u2;

  gs->spare = r * sin(theta);
  gs->has_spare = 1;
  return r * cos(theta);
}

HSCOPT_INLINE size_t aco_upper_bound(const double *HSCOPT_RESTRICT arr, size_t n,
                                     double val) {
  size_t lo = 0;
  size_t hi = n;
  while (lo < hi) {
    const size_t mid = lo + ((hi - lo) >> 1);
    if (arr[mid] <= val) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  return lo;
}

HSCOPT_INLINE int aco_build_rank_cdf(hscopt_aco_ctx *ctx) {
  if (!ctx || ctx->archive_size == 0) {
    return 1;
  }

  const size_t k = ctx->archive_size;
  const double qk = ctx->q * (double)k;

  if (qk <= 1e-12) {
    ctx->cdf[0] = 1.0;
    for (size_t i = 1; i < k; ++i) {
      ctx->cdf[i] = 1.0;
    }
    return 0;
  }

  const double inv_two_qk2 = 1.0 / (2.0 * qk * qk);
  double sum = 0.0;

  for (size_t l = 0; l < k; ++l) {
    const double ll = (double)l;
    sum += exp(-(ll * ll) * inv_two_qk2);
    ctx->cdf[l] = sum;
  }

  if (sum <= 0.0 || !isfinite(sum)) {
    return 2;
  }

  const double inv_sum = 1.0 / sum;
  for (size_t l = 0; l < k; ++l) {
    ctx->cdf[l] *= inv_sum;
  }
  ctx->cdf[k - 1] = 1.0;
  return 0;
}

HSCOPT_INLINE size_t aco_choose_rank(hscopt_aco_ctx *ctx, unsigned tid) {
  const double u = hscopt_rng_next_u01(&ctx->rng_tls[tid]);
  size_t lo = 0;
  size_t hi = ctx->archive_size - 1;
  while (lo < hi) {
    const size_t mid = lo + ((hi - lo) >> 1);
    if (u <= ctx->cdf[mid]) {
      hi = mid;
    } else {
      lo = mid + 1;
    }
  }
  return lo;
}

HSCOPT_INLINE void aco_insert_sorted_prefix(
    hscopt_aco_ctx *ctx, size_t used, const double *HSCOPT_RESTRICT keys,
    double fit) {
  size_t pos = used;
  if (used > 0 && fit < ctx->archive_fit[used - 1]) {
    pos = aco_upper_bound(ctx->archive_fit, used, fit);
  }

  if (pos < used) {
    memmove(&ctx->archive_fit[pos + 1], &ctx->archive_fit[pos],
            (used - pos) * sizeof(double));

    memmove(ARCH_KEY_PTR(ctx, pos + 1), ARCH_KEY_PTR(ctx, pos),
            (used - pos) * ctx->dim * sizeof(double));
  }

  ctx->archive_fit[pos] = fit;
  memcpy(ARCH_KEY_PTR(ctx, pos), keys, ctx->dim * sizeof(double));
}

HSCOPT_INLINE void aco_insert_full_archive(
    hscopt_aco_ctx *ctx, const double *HSCOPT_RESTRICT keys, double fit) {
  const size_t k = ctx->archive_size;
  if (fit >= ctx->archive_fit[k - 1]) {
    return;
  }

  const size_t pos = aco_upper_bound(ctx->archive_fit, k, fit);
  if (pos >= k) {
    return;
  }

  if (pos + 1 < k) {
    memmove(&ctx->archive_fit[pos + 1], &ctx->archive_fit[pos],
            (k - 1 - pos) * sizeof(double));

    memmove(ARCH_KEY_PTR(ctx, pos + 1), ARCH_KEY_PTR(ctx, pos),
            (k - 1 - pos) * ctx->dim * sizeof(double));
  }

  ctx->archive_fit[pos] = fit;
  memcpy(ARCH_KEY_PTR(ctx, pos), keys, ctx->dim * sizeof(double));
}

HSCOPT_INLINE void aco_construct_candidate(hscopt_aco_ctx *ctx,
                                           double *HSCOPT_RESTRICT dst,
                                           unsigned tid) {
  const size_t k = ctx->archive_size;
  const size_t n = ctx->dim;
  const size_t chosen = aco_choose_rank(ctx, tid);
  const double *const HSCOPT_RESTRICT chosen_keys = ARCH_KEY_PTR(ctx, chosen);

  for (size_t d = 0; d < n; ++d) {
    const double mu = chosen_keys[d];
    double sigma = 0.0;

    if (k > 1) {
      double sum_dist = 0.0;
      for (size_t e = 0; e < k; ++e) {
        if (e == chosen) continue;
        const double *const HSCOPT_RESTRICT e_keys = ARCH_KEY_PTR(ctx, e);
        sum_dist += fabs(e_keys[d] - mu);
      }
      sigma = ctx->xi * (sum_dist / (double)(k - 1));
    }

    if (sigma < 1e-12) {
      sigma = 1e-3;
    }

    double sampled = mu;
    int accepted = 0;
    for (int tries = 0; tries < 24; ++tries) {
      sampled = mu + sigma * aco_randn(ctx, tid);
      if (sampled >= 0.0 && sampled < 1.0) {
        accepted = 1;
        break;
      }
    }

    dst[d] = accepted ? sampled : HSCOPT_CLAMP_KEY(sampled);
  }
}

HSCOPT_INLINE int aco_init_archive(hscopt_aco_ctx *ctx) {
  const size_t k = ctx->archive_size;

  for (size_t t = 0; t < ctx->eff_threads; ++t) {
    ctx->gauss_tls[t].has_spare = 0;
    ctx->gauss_tls[t].spare = 0.0;
  }

  for (size_t i = 0; i < k; ++i) {
    double *const HSCOPT_RESTRICT tmp_key = ctx->tmp_key;
    for (size_t d = 0; d < ctx->dim; ++d) {
      tmp_key[d] = hscopt_rng_next_u01(&ctx->rng_tls[0]);
    }

    const double fit = ctx->decoder(tmp_key, ctx->dim, ctx->dctx);
    aco_insert_sorted_prefix(ctx, i, tmp_key, fit);
  }

  ctx->best_fit = ctx->archive_fit[0];
  memcpy(ctx->best_keys, ARCH_KEY_PTR(ctx, 0), ctx->dim * sizeof(double));
  return 0;
}

hscopt_aco_ctx *hscopt_aco_create(size_t n_keys, size_t archive_size,
                                  size_t n_ants, unsigned max_iters,
                                  unsigned max_threads, double q, double xi,
                                  hscopt_decoder_fn decoder,
                                  hscopt_decode_ctx *dctx, hscopt_rng *rng) {
  return hscopt_aco_create_with_allocator(n_keys, archive_size, n_ants,
                                          max_iters, max_threads, q, xi,
                                          decoder, dctx, rng, NULL);
}

hscopt_aco_ctx *hscopt_aco_create_with_allocator(
    size_t n_keys, size_t archive_size, size_t n_ants, unsigned max_iters,
    unsigned max_threads, double q, double xi, hscopt_decoder_fn decoder,
    hscopt_decode_ctx *dctx, hscopt_rng *rng, const hscopt_allocator *alloc) {
  if (!decoder || !rng || n_keys == 0 || archive_size == 0 || n_ants == 0 ||
      max_iters == 0 || q < 0.0 || xi < 0.0) {
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

  hscopt_aco_ctx *ctx =
      (hscopt_aco_ctx *)hscopt_calloc(&resolved, 1, sizeof(*ctx));
  if (!ctx) {
    return NULL;
  }
  ctx->alloc = resolved;

  ctx->dim = n_keys;
  ctx->archive_size = archive_size;
  ctx->n_ants = n_ants;
  ctx->iter = 0;
  ctx->max_iters = max_iters;
  ctx->max_threads = (max_threads == 0u ? 1u : max_threads);
#ifdef _OPENMP
  ctx->eff_threads = ctx->max_threads;
#else
  ctx->eff_threads = 1u;
#endif
  ctx->q = q;
  ctx->xi = xi;
  ctx->decoder = decoder;
  ctx->dctx = dctx;

  ctx->archive_keys =
      (double *)hscopt_alloc(&ctx->alloc,
                             archive_size * n_keys * sizeof(double));
  ctx->archive_fit =
      (double *)hscopt_alloc(&ctx->alloc, archive_size * sizeof(double));
  ctx->cand_keys =
      (double *)hscopt_alloc(&ctx->alloc, n_ants * n_keys * sizeof(double));
  ctx->cand_fit = (double *)hscopt_alloc(&ctx->alloc, n_ants * sizeof(double));
  ctx->best_keys = (double *)hscopt_alloc(&ctx->alloc, n_keys * sizeof(double));
  ctx->cdf = (double *)hscopt_alloc(&ctx->alloc, archive_size * sizeof(double));
  ctx->tmp_key = (double *)hscopt_alloc(&ctx->alloc, n_keys * sizeof(double));
  ctx->rng_tls = (hscopt_rng *)hscopt_calloc(&ctx->alloc, ctx->eff_threads,
                                             sizeof(hscopt_rng));
  ctx->gauss_tls = (hscopt_gauss_state *)hscopt_calloc(
      &ctx->alloc, ctx->eff_threads, sizeof(hscopt_gauss_state));

  if (!ctx->archive_keys || !ctx->archive_fit || !ctx->cand_keys ||
      !ctx->cand_fit || !ctx->best_keys || !ctx->cdf || !ctx->tmp_key ||
      !ctx->rng_tls || !ctx->gauss_tls) {
    hscopt_aco_destroy(ctx);
    return NULL;
  }

  ctx->rng_tls[0] = *rng;
  for (unsigned t = 1; t < ctx->eff_threads; ++t) {
    ctx->rng_tls[t] = ctx->rng_tls[t - 1];
    hscopt_rng_long_jump(&ctx->rng_tls[t]);
  }

  if (hscopt_aco_reset(ctx) != 0) {
    hscopt_aco_destroy(ctx);
    return NULL;
  }

  return ctx;
}

void hscopt_aco_destroy(hscopt_aco_ctx *ctx) {
  if (!ctx) return;

  hscopt_free(&ctx->alloc, ctx->archive_keys);
  hscopt_free(&ctx->alloc, ctx->archive_fit);
  hscopt_free(&ctx->alloc, ctx->cand_keys);
  hscopt_free(&ctx->alloc, ctx->cand_fit);
  hscopt_free(&ctx->alloc, ctx->best_keys);
  hscopt_free(&ctx->alloc, ctx->cdf);
  hscopt_free(&ctx->alloc, ctx->tmp_key);
  hscopt_free(&ctx->alloc, ctx->rng_tls);
  hscopt_free(&ctx->alloc, ctx->gauss_tls);
  hscopt_free(&ctx->alloc, ctx);
}

int hscopt_aco_reset(hscopt_aco_ctx *ctx) {
  if (!ctx) {
    return 1;
  }

  ctx->iter = 0;
  ctx->best_fit = INFINITY;
  memset(ctx->best_keys, 0, ctx->dim * sizeof(double));

  if (aco_init_archive(ctx) != 0) {
    return 2;
  }

  if (aco_build_rank_cdf(ctx) != 0) {
    return 3;
  }

  return 0;
}

int hscopt_aco_iterate(hscopt_aco_ctx *ctx, unsigned iters) {
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
    for (ptrdiff_t ai = 0; ai < (ptrdiff_t)ctx->n_ants; ++ai) {
      unsigned tid = 0;
#ifdef _OPENMP
      tid = (unsigned)omp_get_thread_num();
#endif
      double *const HSCOPT_RESTRICT cand = CAND_KEY_PTR(ctx, (size_t)ai);
      aco_construct_candidate(ctx, cand, tid);
      ctx->cand_fit[(size_t)ai] = ctx->decoder(cand, ctx->dim, ctx->dctx);
    }

    for (size_t i = 0; i < ctx->n_ants; ++i) {
      const double fit = ctx->cand_fit[i];
      if (fit < ctx->best_fit) {
        ctx->best_fit = fit;
        memcpy(ctx->best_keys, CAND_KEY_PTR(ctx, i), ctx->dim * sizeof(double));
      }

      aco_insert_full_archive(ctx, CAND_KEY_PTR(ctx, i), fit);
    }

    ++ctx->iter;
  }

  return 0;
}

double hscopt_aco_best_fitness(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->best_fit : INFINITY;
}

const double *hscopt_aco_best_keys(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->best_keys : NULL;
}

unsigned hscopt_aco_iteration(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->iter : 0u;
}

unsigned hscopt_aco_max_iters(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->max_iters : 0u;
}

size_t hscopt_aco_n_keys(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->dim : 0u;
}

size_t hscopt_aco_archive_size(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->archive_size : 0u;
}

size_t hscopt_aco_n_ants(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->n_ants : 0u;
}

unsigned hscopt_aco_max_threads(const hscopt_aco_ctx *ctx) {
  return ctx ? ctx->eff_threads : 1u;
}
