#include "hscopt/alloc.h"

#include <stdlib.h>

static void *hscopt_default_alloc(size_t size, size_t alignment, void *user) {
  (void)alignment;
  (void)user;
  return malloc(size);
}

static void *hscopt_default_calloc(size_t count, size_t size, size_t alignment,
                                   void *user) {
  (void)alignment;
  (void)user;
  return calloc(count, size);
}

static void hscopt_default_free(void *ptr, void *user) {
  (void)user;
  free(ptr);
}

static hscopt_allocator g_allocator = {
    .alloc = hscopt_default_alloc,
    .calloc = hscopt_default_calloc,
    .free = hscopt_default_free,
    .alignment = 0,
    .user = NULL,
};

void hscopt_allocator_default(hscopt_allocator *out) {
  if (!out) return;
  *out = g_allocator;
}

int hscopt_set_allocator(const hscopt_allocator *alloc) {
  if (!alloc) {
    g_allocator.alloc = hscopt_default_alloc;
    g_allocator.calloc = hscopt_default_calloc;
    g_allocator.free = hscopt_default_free;
    g_allocator.alignment = 0;
    g_allocator.user = NULL;
    return 0;
  }
  if (!alloc->alloc || !alloc->calloc || !alloc->free) return 1;
  g_allocator = *alloc;
  return 0;
}

void hscopt_get_allocator(hscopt_allocator *out) {
  if (!out) return;
  *out = g_allocator;
}
