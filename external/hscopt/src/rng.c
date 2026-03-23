#include "hscopt/rng.h"

#include <stddef.h>
#include <stdint.h>

static inline uint64_t hscopt_rotl64(uint64_t x, int k) {
  return (x << k) | (x >> (64 - k));
}

/* splitmix64 para expandir seed 64-bit em 4 words */
static inline uint64_t hscopt_splitmix64_next(uint64_t *x) {
  uint64_t z = (*x += UINT64_C(0x9E3779B97F4A7C15));
  z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);
  z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);
  return z ^ (z >> 31);
}

void hscopt_rng_seed(hscopt_rng *rng, uint64_t seed) {
  if (!rng) return;

  /* splitmix64 funciona com seed=0 também, mas garantimos estado != 0 no fim */
  uint64_t x = seed;

  rng->s[0] = hscopt_splitmix64_next(&x);
  rng->s[1] = hscopt_splitmix64_next(&x);
  rng->s[2] = hscopt_splitmix64_next(&x);
  rng->s[3] = hscopt_splitmix64_next(&x);

  /* xoshiro exige que o estado não seja todo zero */
  if ((rng->s[0] | rng->s[1] | rng->s[2] | rng->s[3]) == 0) {
    rng->s[0] = UINT64_C(0x1);
  }
}

uint64_t hscopt_rng_next_u64(hscopt_rng *rng) {
  /* você pode trocar por assert(rng) se preferir */
  if (!rng) return 0;

  uint64_t *s = rng->s;

  const uint64_t result = hscopt_rotl64(s[1] * UINT64_C(5), 7) * UINT64_C(9);
  const uint64_t t = s[1] << 17;

  s[2] ^= s[0];
  s[3] ^= s[1];
  s[1] ^= s[2];
  s[0] ^= s[3];

  s[2] ^= t;
  s[3] = hscopt_rotl64(s[3], 45);

  return result;
}

void hscopt_rng_jump(hscopt_rng *rng) {
  if (!rng) return;

  static const uint64_t JUMP[4] = {
      UINT64_C(0x180ec6d33cfd0aba),
      UINT64_C(0xd5a61266f0c9392c),
      UINT64_C(0xa9582618e03fc9aa),
      UINT64_C(0x39abdc4529b1661c),
  };

  uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;

  for (size_t i = 0; i < 4; i++) {
    for (int b = 0; b < 64; b++) {
      if (JUMP[i] & (UINT64_C(1) << b)) {
        s0 ^= rng->s[0];
        s1 ^= rng->s[1];
        s2 ^= rng->s[2];
        s3 ^= rng->s[3];
      }
      (void)hscopt_rng_next_u64(rng);
    }
  }

  rng->s[0] = s0;
  rng->s[1] = s1;
  rng->s[2] = s2;
  rng->s[3] = s3;
}

void hscopt_rng_long_jump(hscopt_rng *rng) {
  if (!rng) return;

  static const uint64_t LONG_JUMP[4] = {
      UINT64_C(0x76e15d3efefdcbbf),
      UINT64_C(0xc5004e441c522fb3),
      UINT64_C(0x77710069854ee241),
      UINT64_C(0x39109bb02acbe635),
  };

  uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;

  for (size_t i = 0; i < 4; i++) {
    for (int b = 0; b < 64; b++) {
      if (LONG_JUMP[i] & (UINT64_C(1) << b)) {
        s0 ^= rng->s[0];
        s1 ^= rng->s[1];
        s2 ^= rng->s[2];
        s3 ^= rng->s[3];
      }
      (void)hscopt_rng_next_u64(rng);
    }
  }

  rng->s[0] = s0;
  rng->s[1] = s1;
  rng->s[2] = s2;
  rng->s[3] = s3;
}
