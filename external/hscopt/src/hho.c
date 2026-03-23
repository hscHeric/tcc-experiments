#include "hscopt/hho.h"

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

#define HAWK_PTR(ctx, agent) (&(ctx)->X[(agent) * (ctx)->dim])
#define HHO_E1(t, T) (2.0 * (1.0 - ((double)(t) / (double)(T))))
#define HHO_E0(u01) (2.0 * (u01)-1.0)

struct hscopt_hho_ctx {
  size_t dim;
  size_t n_agents;

  unsigned iter;
  unsigned max_iters;
  unsigned max_threads;
  unsigned eff_threads;

  hscopt_decoder_fn decoder;
  hscopt_decode_ctx *dctx;
  hscopt_rng *rng;

  double *X;
  double *fitness;

  double rabbit_fitness;
  double *rabbit_keys;

  double *mean_pos;
  double *tmp1;
  double *tmp2;
  double *levy;

  struct {
    int has_spare;
    double spare;
  } gauss;

  double levy_sigma;

  hscopt_allocator alloc;
};

HSCOPT_INLINE double hho_randn(hscopt_rng *rng, hscopt_hho_ctx *ctx) {
  if (ctx->gauss.has_spare) {
    ctx->gauss.has_spare = 0;
    return ctx->gauss.spare;
  }

  double u1 = hscopt_rng_next_u01(rng);
  if (u1 <= 0.0) {
    u1 = 1e-12;
  }

  const double u2 = hscopt_rng_next_u01(rng);
  const double r = sqrt(-2.0 * log(u1));
  const double theta = 2.0 * HSCOPT_PI * u2;

  ctx->gauss.spare = r * sin(theta);
  ctx->gauss.has_spare = 1;
  return r * cos(theta);
}

HSCOPT_INLINE void hho_levy(hscopt_hho_ctx *ctx) {
  const double inv_beta = 1.0 / 1.5;
  double *const HSCOPT_RESTRICT levy = ctx->levy;
  for (size_t j = 0; j < ctx->dim; ++j) {
    const double u = 0.01 * hho_randn(ctx->rng, ctx) * ctx->levy_sigma;
    double v = hho_randn(ctx->rng, ctx);
    const double av = fabs(v);
    if (av < 1e-12) {
      v = (v < 0.0 ? -1e-12 : 1e-12);
    }
    levy[j] = u / pow(fabs(v), inv_beta);
  }
}

HSCOPT_INLINE void hho_eval_all_and_update_rabbit(hscopt_hho_ctx *ctx) {
#ifdef _OPENMP
  #pragma omp parallel for num_threads(ctx->eff_threads) schedule(static)
#endif
  for (ptrdiff_t i = 0; i < (ptrdiff_t)ctx->n_agents; ++i) {
    double *const HSCOPT_RESTRICT x = HAWK_PTR(ctx, (size_t)i);
    ctx->fitness[(size_t)i] = ctx->decoder(x, ctx->dim, ctx->dctx);
  }

  for (size_t i = 0; i < ctx->n_agents; ++i) {
    if (ctx->fitness[i] < ctx->rabbit_fitness) {
      ctx->rabbit_fitness = ctx->fitness[i];
      memcpy(ctx->rabbit_keys, HAWK_PTR(ctx, i), ctx->dim * sizeof(double));
    }
  }
}

HSCOPT_INLINE void hho_mean_pos(hscopt_hho_ctx *ctx) {
  double *const HSCOPT_RESTRICT mean_pos = ctx->mean_pos;
  memset(mean_pos, 0, ctx->dim * sizeof(double));

  for (size_t i = 0; i < ctx->n_agents; ++i) {
    const double *const HSCOPT_RESTRICT x = HAWK_PTR(ctx, i);
    for (size_t j = 0; j < ctx->dim; ++j) {
      mean_pos[j] += x[j];
    }
  }

  const double inv = 1.0 / (double)ctx->n_agents;
  for (size_t j = 0; j < ctx->dim; ++j) {
    mean_pos[j] *= inv;
  }
}

hscopt_hho_ctx *hscopt_hho_create(size_t n_keys, size_t n_agents,
                                  unsigned max_iters, unsigned max_threads,
                                  hscopt_decoder_fn decoder,
                                  hscopt_decode_ctx *dctx, hscopt_rng *rng) {
  return hscopt_hho_create_with_allocator(n_keys, n_agents, max_iters,
                                          max_threads, decoder, dctx, rng,
                                          NULL);
}

hscopt_hho_ctx *hscopt_hho_create_with_allocator(
    size_t n_keys, size_t n_agents, unsigned max_iters, unsigned max_threads,
    hscopt_decoder_fn decoder, hscopt_decode_ctx *dctx, hscopt_rng *rng,
    const hscopt_allocator *alloc) {
  if (!decoder || !rng || n_keys == 0 || n_agents == 0 || max_iters == 0) {
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

  hscopt_hho_ctx *ctx =
      (hscopt_hho_ctx *)hscopt_calloc(&resolved, 1, sizeof(*ctx));
  if (!ctx) {
    return NULL;
  }
  ctx->alloc = resolved;

  ctx->dim = n_keys;
  ctx->n_agents = n_agents;
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
  ctx->rng = rng;

  ctx->X =
      (double *)hscopt_alloc(&ctx->alloc,
                             sizeof(double) * (n_keys * n_agents));
  ctx->fitness =
      (double *)hscopt_alloc(&ctx->alloc, sizeof(double) * n_agents);
  ctx->rabbit_keys =
      (double *)hscopt_alloc(&ctx->alloc, sizeof(double) * n_keys);
  ctx->mean_pos = (double *)hscopt_alloc(&ctx->alloc, sizeof(double) * n_keys);
  ctx->tmp1 = (double *)hscopt_alloc(&ctx->alloc, sizeof(double) * n_keys);
  ctx->tmp2 = (double *)hscopt_alloc(&ctx->alloc, sizeof(double) * n_keys);
  ctx->levy = (double *)hscopt_alloc(&ctx->alloc, sizeof(double) * n_keys);

  if (!ctx->X || !ctx->fitness || !ctx->rabbit_keys || !ctx->mean_pos ||
      !ctx->tmp1 || !ctx->tmp2 || !ctx->levy) {
    hscopt_hho_destroy(ctx);
    return NULL;
  }

  const double beta = 1.5;
  const double num = tgamma(1.0 + beta) * sin(HSCOPT_PI * beta / 2.0);
  const double den =
      tgamma((1.0 + beta) / 2.0) * beta * pow(2.0, (beta - 1.0) / 2.0);
  ctx->levy_sigma = pow(num / den, 1.0 / beta);

  ctx->gauss.has_spare = 0;
  ctx->gauss.spare = 0.0;

  if (hscopt_hho_reset(ctx) != 0) {
    hscopt_hho_destroy(ctx);
    return NULL;
  }

  return ctx;
}

void hscopt_hho_destroy(hscopt_hho_ctx *ctx) {
  if (!ctx) return;

  hscopt_free(&ctx->alloc, ctx->X);
  hscopt_free(&ctx->alloc, ctx->fitness);
  hscopt_free(&ctx->alloc, ctx->rabbit_keys);
  hscopt_free(&ctx->alloc, ctx->mean_pos);
  hscopt_free(&ctx->alloc, ctx->tmp1);
  hscopt_free(&ctx->alloc, ctx->tmp2);
  hscopt_free(&ctx->alloc, ctx->levy);
  hscopt_free(&ctx->alloc, ctx);
}

int hscopt_hho_reset(hscopt_hho_ctx *ctx) {
  if (!ctx) {
    return 1;
  }

  ctx->iter = 0;
  ctx->rabbit_fitness = INFINITY;
  ctx->gauss.has_spare = 0;
  ctx->gauss.spare = 0.0;

  memset(ctx->rabbit_keys, 0, ctx->dim * sizeof(double));

  for (size_t i = 0; i < ctx->n_agents; ++i) {
    double *const x = HAWK_PTR(ctx, i);
    for (size_t j = 0; j < ctx->dim; ++j) {
      x[j] = hscopt_rng_next_u01(ctx->rng);
    }
  }

  hho_eval_all_and_update_rabbit(ctx);
  return 0;
}

int hscopt_hho_iterate(hscopt_hho_ctx *ctx, unsigned int iters) {
  if (!ctx || iters == 0) {
    return 1;
  }
  if (ctx->iter >= ctx->max_iters || ctx->iter + iters > ctx->max_iters) {
    return 2;
  }

  for (unsigned it = 0; it < iters; ++it) {
    const double *const HSCOPT_RESTRICT rabbit = ctx->rabbit_keys;
    const double *const HSCOPT_RESTRICT mean_pos = ctx->mean_pos;
    double *const HSCOPT_RESTRICT tmp1 = ctx->tmp1;
    double *const HSCOPT_RESTRICT tmp2 = ctx->tmp2;
    const double *const HSCOPT_RESTRICT levy = ctx->levy;

    for (size_t i = 0; i < ctx->n_agents; ++i) {
      HSCOPT_CLAMP_KEY_VEC(HAWK_PTR(ctx, i), ctx->dim);
    }

    const double e1 = HHO_E1(ctx->iter, ctx->max_iters);
    hho_mean_pos(ctx);

    for (size_t i = 0; i < ctx->n_agents; ++i) {
      double *const HSCOPT_RESTRICT Xi = HAWK_PTR(ctx, i);
      const double e0 = HHO_E0(hscopt_rng_next_u01(ctx->rng));
      const double e = e1 * e0;
      const double abs_e = fabs(e);

      if (abs_e >= 1.0) {
        const double q = hscopt_rng_next_u01(ctx->rng);
        const size_t r_idx = hscopt_rng_random_index(ctx->rng, ctx->n_agents);
        const double *const Xrand = HAWK_PTR(ctx, r_idx);

        if (q >= 0.5) {
          const double r1 = hscopt_rng_next_u01(ctx->rng);
          const double r2 = hscopt_rng_next_u01(ctx->rng);
          for (size_t j = 0; j < ctx->dim; ++j) {
            const double val = Xrand[j] - r1 * fabs(Xrand[j] - 2.0 * r2 * Xi[j]);
            Xi[j] = HSCOPT_CLAMP_KEY(val);
          }
        } else {
          const double s = hscopt_rng_next_u01(ctx->rng) *
                           hscopt_rng_next_u01(ctx->rng);
          for (size_t j = 0; j < ctx->dim; ++j) {
            const double val = (rabbit[j] - mean_pos[j]) - s;
            Xi[j] = HSCOPT_CLAMP_KEY(val);
          }
        }
        continue;
      }

      const double r = hscopt_rng_next_u01(ctx->rng);

      if (r >= 0.5 && abs_e >= 0.5) {
        const double jump_strength = 2.0 * (1.0 - hscopt_rng_next_u01(ctx->rng));
        for (size_t j = 0; j < ctx->dim; ++j) {
          const double val = (rabbit[j] - Xi[j]) -
                             e * fabs(jump_strength * rabbit[j] - Xi[j]);
          Xi[j] = HSCOPT_CLAMP_KEY(val);
        }
        continue;
      }

      if (r >= 0.5 && abs_e < 0.5) {
        for (size_t j = 0; j < ctx->dim; ++j) {
          const double val = rabbit[j] - e * fabs(rabbit[j] - Xi[j]);
          Xi[j] = HSCOPT_CLAMP_KEY(val);
        }
        continue;
      }

      if (r < 0.5 && abs_e >= 0.5) {
        const double jump_strength = 2.0 * (1.0 - hscopt_rng_next_u01(ctx->rng));

        for (size_t j = 0; j < ctx->dim; ++j) {
          tmp1[j] = rabbit[j] - e * fabs(jump_strength * rabbit[j] - Xi[j]);
        }
        HSCOPT_CLAMP_KEY_VEC(tmp1, ctx->dim);

        const double fcur = ctx->decoder(Xi, ctx->dim, ctx->dctx);
        const double f1 = ctx->decoder(tmp1, ctx->dim, ctx->dctx);

        if (f1 < fcur) {
          memcpy(Xi, tmp1, ctx->dim * sizeof(double));
        } else {
          hho_levy(ctx);
          for (size_t j = 0; j < ctx->dim; ++j) {
            tmp2[j] = tmp1[j] + hho_randn(ctx->rng, ctx) * levy[j];
          }
          HSCOPT_CLAMP_KEY_VEC(tmp2, ctx->dim);

          const double f2 = ctx->decoder(tmp2, ctx->dim, ctx->dctx);
          if (f2 < fcur) {
            memcpy(Xi, tmp2, ctx->dim * sizeof(double));
          }
        }
        continue;
      }

      const double jump_strength = 2.0 * (1.0 - hscopt_rng_next_u01(ctx->rng));
      for (size_t j = 0; j < ctx->dim; ++j) {
        tmp1[j] = rabbit[j] - e * fabs(jump_strength * rabbit[j] - mean_pos[j]);
      }
      HSCOPT_CLAMP_KEY_VEC(tmp1, ctx->dim);

      const double fcur = ctx->decoder(Xi, ctx->dim, ctx->dctx);
      const double f1 = ctx->decoder(tmp1, ctx->dim, ctx->dctx);

      if (f1 < fcur) {
        memcpy(Xi, tmp1, ctx->dim * sizeof(double));
      } else {
        hho_levy(ctx);
        for (size_t j = 0; j < ctx->dim; ++j) {
          tmp2[j] = tmp1[j] + hho_randn(ctx->rng, ctx) * levy[j];
        }
        HSCOPT_CLAMP_KEY_VEC(tmp2, ctx->dim);

        const double f2 = ctx->decoder(tmp2, ctx->dim, ctx->dctx);
        if (f2 < fcur) {
          memcpy(Xi, tmp2, ctx->dim * sizeof(double));
        }
      }
    }

    hho_eval_all_and_update_rabbit(ctx);
    ++ctx->iter;
  }

  return 0;
}

double hscopt_hho_best_fitness(const hscopt_hho_ctx *ctx) {
  return ctx ? ctx->rabbit_fitness : INFINITY;
}

const double *hscopt_hho_best_keys(const hscopt_hho_ctx *ctx) {
  return ctx ? ctx->rabbit_keys : NULL;
}

unsigned hscopt_hho_iteration(const hscopt_hho_ctx *ctx) {
  return ctx ? ctx->iter : 0u;
}

unsigned hscopt_hho_max_iters(const hscopt_hho_ctx *ctx) {
  return ctx ? ctx->max_iters : 0u;
}

size_t hscopt_hho_n_agents(const hscopt_hho_ctx *ctx) {
  return ctx ? ctx->n_agents : 0u;
}

size_t hscopt_hho_n_keys(const hscopt_hho_ctx *ctx) {
  return ctx ? ctx->dim : 0u;
}

unsigned hscopt_hho_max_threads(const hscopt_hho_ctx *ctx) {
  return ctx ? ctx->eff_threads : 1u;
}

int hscopt_hho_try_update_rabbit(hscopt_hho_ctx *ctx, const double *keys) {
  if (!ctx || !keys || !ctx->decoder) {
    return -1;
  }

  const double f = ctx->decoder(keys, ctx->dim, ctx->dctx);
  if (f < ctx->rabbit_fitness) {
    ctx->rabbit_fitness = f;
    memcpy(ctx->rabbit_keys, keys, ctx->dim * sizeof(double));
    return 1;
  }

  return 0;
}
