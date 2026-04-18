#include "decoder.hpp"
#include "graph/graph.hpp"
#include <cstdint>
#include <memory>
#include <numeric>
#include <vector>

D1::D1(const hsc::Graph &graph) : graph(graph) {}

double D1::decode(const std::vector<double> &chromosome) const {
  std::vector<uint8_t> l;
  l.reserve(chromosome.size());

  for (double x : chromosome) {
    l.push_back(static_cast<uint8_t>(x * 4));
  }

  auto vertices_set = graph.get_vertices();
  std::vector<size_t> vertices(vertices_set.begin(), vertices_set.end());
  std::sort(vertices.begin(), vertices.end());

  for (size_t v : vertices) {
    if (l[v] <= 1) {
      std::vector<size_t> neighbors = graph.get_neighbors(v);
      size_t sum = l[v] + std::accumulate(
                              neighbors.begin(), neighbors.end(), 0UL,
                              [&](size_t acc, size_t u) { return acc + l[u]; });

      if (sum < 3) {
        l[v] = 2; // Reparo trivial
      }
    }
  }
  return std::accumulate(l.begin(), l.end(), 0UL);
}

D2::D2(const hsc::Graph &graph) : graph(graph) {}

double D2::decode(const std::vector<double> &chromosome) const {
  std::vector<uint8_t> l;
  l.reserve(chromosome.size());

  for (double x : chromosome) {
    l.push_back(static_cast<uint8_t>(x * 4));
  }

  auto vertices_set = graph.get_vertices();
  std::vector<size_t> vertices(vertices_set.begin(), vertices_set.end());
  std::sort(vertices.begin(), vertices.end());

  for (size_t v : vertices) {
    if (l[v] > 1)
      continue;

    std::vector<size_t> neighbors = graph.get_neighbors(v);
    size_t neighbor_sum =
        l[v] +
        std::accumulate(neighbors.begin(), neighbors.end(), 0UL,
                        [&](size_t acc, size_t u) { return acc + l[u]; });

    if (neighbor_sum >= 3)
      continue;

    size_t deficit = 3 - neighbor_sum;

    if (l[v] == 0 && neighbor_sum == 1) {
      l[v] = 2;
      continue;
    }

    if (deficit == 3) {
      l[v] = (neighbors.empty()) ? 2 : 3;
      continue;
    }

    if (deficit == 2) {
      if (neighbors.empty()) {
        l[v] = 2;
        continue;
      }

      size_t first = SIZE_MAX, second = SIZE_MAX;
      for (size_t u : neighbors) {
        if (l[u] == 1) {
          if (first == SIZE_MAX)
            first = u;
          else {
            second = u;
            break;
          }
        }
      }

      if (second != SIZE_MAX) {
        l[first] = 2;
        l[second] = 2;
      } else {
        bool fix_found = false;
        for (size_t u : neighbors) {
          if (l[u] == 0) {
            l[u] = 2;
            fix_found = true;
            break;
          }
        }
        if (!fix_found)
          l[v] = 2;
      }
      continue;
    }

    if (deficit == 1) {
      l[v] += 1;
    }
  }
  return std::accumulate(l.begin(), l.end(), 0UL);
}

void refine_3roman_solution(const hsc::Graph &g, std::vector<uint8_t> &label) {
  const auto n = g.get_order();
  for (size_t u = 0; u < n; u++) {
    if (label[u] > 0) {
      uint8_t original_label = label[u];
      label[u]--;

      bool feasible = true;
      std::vector<size_t> check_nodes = g.get_neighbors(u);
      check_nodes.push_back(u);

      for (size_t v : check_nodes) {
        if (label[v] <= 1) {
          size_t sum_v = label[v];
          for (size_t neighbor_v : g.get_neighbors(v)) {
            sum_v += label[neighbor_v];
          }
          if (sum_v < 3) {
            feasible = false;
            break;
          }
        }
      }

      if (!feasible) {
        label[u] = original_label;
      } else {
        u--;
      }
    }
  }
}

D3::D3(const hsc::Graph &graph)
    : graph(graph),
      evaluation_counter(std::make_shared<std::atomic<std::uint64_t>>(0)) {}

double D3::decode(const std::vector<double> &chromosome) const {
  evaluation_counter->fetch_add(1, std::memory_order_relaxed);
  const size_t n = graph.get_order();

  std::vector<size_t> order(n);
  std::iota(order.begin(), order.end(), 0);
  std::sort(order.begin(), order.end(),
            [&](size_t a, size_t b) { return chromosome[a] > chromosome[b]; });

  std::vector<uint8_t> f(n, 0);

  for (size_t u : order) {
    size_t current_sum = f[u];
    for (size_t v : graph.get_neighbors(u)) {
      current_sum += f[v];
    }

    if (current_sum < 3) {
      int deficit = 3 - current_sum;
      f[u] = std::min(3, (int)f[u] + deficit);
    }
  }

  refine_3roman_solution(graph, f);

  double total_cost = 0;
  for (uint8_t val : f)
    total_cost += val;

  return total_cost;
}

void D3::reset_evaluation_count() const {
  evaluation_counter->store(0, std::memory_order_relaxed);
}

std::uint64_t D3::get_evaluation_count() const {
  return evaluation_counter->load(std::memory_order_relaxed);
}
