#ifndef HSCOPT_H
#define HSCOPT_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * hscopt - Biblioteca de metaheurísticas para otimização combinatória
 *
 * Autor: Heric da Silva Cruz
 */

#include "aco.h"
#include "decoder.h"
#include "defs.h"
#include "hho.h"
#include "rng.h"
#include "rvns.h"
#include "ts.h"

#define HSCOPT_VERSION_MAJOR 1
#define HSCOPT_VERSION_MINOR 0
#define HSCOPT_VERSION_PATCH 0
#define HSCOPT_VERSION_STRING "1.0.0"

#define HSCOPT_VERSION_ENCODE(MAJ, MIN, PAT) \
  (((MAJ) << 16) | ((MIN) << 8) | (PAT))

#ifdef __cplusplus
}
#endif

#endif  // !HSCOPT_H
