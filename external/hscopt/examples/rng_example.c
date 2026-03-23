#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#include "hscopt/rng.h"

/*
 * Exemplo de uso do gerador de números aleatórios  da hscopt.
 *
 * Demonstra:
 * - inicialização com seed
 * - geração de inteiros aleatórios
 * - geração de doubles em [0,1)
 *
 * Compile (exemplo):
 *  gcc rng_example.c -I../include ../src/rng.c -o example_rng
 */

int main(void) {
  hscopt_rng rng;
  hscopt_rng_seed(&rng, 42ULL);  // Seed da resposta para tudo

  printf("=== Teste 1: Próximos 64 bits (uint64_t) ===\n");
  for (int i = 0; i < 3; ++i) {
    printf("  Rand %d: %" PRIu64 "\n", i, hscopt_rng_next_u64(&rng));
  }

  printf("\n=== Teste 2: Doubles Uniformes [0,1) ===\n");
  for (int i = 0; i < 3; ++i) {
    printf("  Double %d: %.10f\n", i, hscopt_rng_next_u01(&rng));
  }

  printf("\n=== Teste 3: Índices Uniformes (Lemire's Method) ===\n");
  size_t limites[] = {10, 100, 1000, 7};
  for (int i = 0; i < 4; ++i) {
    size_t n = limites[i];
    size_t r = hscopt_rng_random_index(&rng, n);
    printf("  Range [0, %zu): %zu\n", n, r);
  }

  printf("\n=== Teste 4: Jump (Subsequência de 2^128) ===\n");
  printf("  Estado antes do jump: %" PRIu64 "\n", hscopt_rng_next_u64(&rng));
  hscopt_rng_jump(&rng);
  printf("  Estado após jump:     %" PRIu64 " (Deve ser muito diferente)\n",
         hscopt_rng_next_u64(&rng));

  printf("\n=== Teste 5: Long Jump (Subsequência de 2^192) ===\n");
  hscopt_rng_long_jump(&rng);
  printf("  Estado após long_jump: %" PRIu64 "\n", hscopt_rng_next_u64(&rng));

  return 0;
}
