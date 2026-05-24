#include "incremental_greedy.hpp"

#include "decoder_utils.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <numeric>
#include <span>
#include <vector>

namespace hsc {

incremental_greedy::incremental_greedy(const Graph& graph)
    : graph(graph),
      evaluation_counter(std::make_shared<std::atomic<std::uint64_t>>(0)) {
  const size_t vertex_count = graph.get_order();
  const size_t edge_count = graph.get_size();

  const double avg_degree =
      (vertex_count > 0) ? ((double)edge_count * 2) / vertex_count : 0.0;

  high_degree_threshold = std::max<size_t>(4, static_cast<size_t>(1.5 * avg_degree));
}

void incremental_greedy::reset_evaluation_count() const {
  evaluation_counter->store(0, std::memory_order_relaxed);
}

std::uint64_t incremental_greedy::get_evaluation_count() const {
  return evaluation_counter->load(std::memory_order_relaxed);
}

double incremental_greedy::decode(std::span<const double> chromosome) const {
  evaluation_counter->fetch_add(1, std::memory_order_relaxed);
  std::vector<uint8_t> solution = construct_solution(chromosome);

#ifdef DEBUG
  if (!hsc::is_solution_feasible(graph, solution)) {
    std::cerr << "Solução inviável foi encontrada\n";
    exit(1);
  }
#endif // DEBUG

  return std::accumulate(solution.begin(), solution.end(), 0.0);
}

double incremental_greedy::decode(const std::vector<double>& chromosome) const {
  return decode(std::span<const double>(chromosome));
}

bool incremental_greedy::is_solution_feasible(
    const std::vector<uint8_t>& labels
) const {
  return hsc::is_solution_feasible(graph, labels);
}

std::vector<uint8_t>
incremental_greedy::construct_solution(std::span<const double> chromosome) const {

  const size_t vertex_count = graph.get_order();

  // Define a ordem de prioridade dos vértices com base nos valores do
  // cromossomo
  // Vértices com chaves maiores são posicionados primeiro (ordem decrescente)
  thread_local std::vector<size_t> priority_order;
  priority_order.resize(vertex_count);

  std::iota(priority_order.begin(), priority_order.end(), 0);
  std::sort(priority_order.begin(), priority_order.end(), [&](size_t u, size_t v) {
    return chromosome[u] > chromosome[v];
  });

  // f representa a atribuição da função de dominação {3}-romana de cada vértice
  thread_local std::vector<uint8_t> f;
  f.assign(vertex_count, 0); // Após a inicialização para o thread_local

  // closed_weight armazena a soma dos pesos na vizinhança fechada de cada
  // vértice N[v]
  thread_local std::vector<int> neighborhood_weight;
  neighborhood_weight.assign(vertex_count, 0);

  // Construção gulosa
  for (size_t i = 0; i < vertex_count; ++i) {
    const size_t u = priority_order[i];

    if (is_vertex_feasible(f, neighborhood_weight, u)) {
      continue;
    }

    if (graph.get_vertex_degree(u) >= high_degree_threshold) {
      assign_label(graph, f, neighborhood_weight, u, 3);
      continue;
    }

    // Seleciona o label do vértice de forma gulosa
    // Escolhendo o menor label que mantenha a solução viavel
    assign_label(graph, f, neighborhood_weight, u, 1);
    if (!is_vertex_feasible(f, neighborhood_weight, u)) {
      assign_label(graph, f, neighborhood_weight, u, 2);
    }
  }

  // destroy - repair
  thread_local std::vector<uint8_t> f_backup;
  thread_local std::vector<int> neighborhood_weight_backup;
  f_backup = f;
  neighborhood_weight_backup = neighborhood_weight;

  std::mt19937_64 rng(compute_chromosome_seed(chromosome));
  for (size_t u = 0; u < vertex_count; ++u) {
    if (rng() & 1ULL) {
      assign_label(graph, f, neighborhood_weight, u, 3);
      for (size_t vertex : graph.get_neighbors(u)) {
        assign_label(graph, f, neighborhood_weight, vertex, 0);
      }
    }
  }

  // repair
  for (size_t u = 0; u < vertex_count; ++u) {
    if (!is_vertex_feasible(f, neighborhood_weight, u)) {
      assign_label(graph, f, neighborhood_weight, u, 1);
      if (!is_vertex_feasible(f, neighborhood_weight, u)) {
        assign_label(graph, f, neighborhood_weight, u, 2);
      }
    }
  }

  double f_objective = std::accumulate(f.begin(), f.end(), 0.0);
  double f_backup_objective = std::accumulate(f_backup.begin(), f_backup.end(), 0.0);

  if (f_backup_objective < f_objective) {
    return f_backup;
  }
  return f;
}

std::vector<uint8_t>
incremental_greedy::construct_solution(const std::vector<double>& chromosome) const {
  return construct_solution(std::span<const double>(chromosome));
}
} // namespace hsc
