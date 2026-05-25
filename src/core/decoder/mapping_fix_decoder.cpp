#include "mapping_fix_decoder.hpp"

#include "decoder_utils.hpp"

#include <algorithm>
#include <cstdlib>
#include <memory>
#include <numeric>
#include <span>
#include <vector>

namespace hsc {

mapping_fix_decoder::mapping_fix_decoder(const Graph& graph)
    : graph(graph),
      evaluation_counter(std::make_shared<std::atomic<std::uint64_t>>(0)) {
  const size_t vertex_count = graph.get_order();
  const size_t edge_count = graph.get_size();

  const double avg_degree =
      (vertex_count > 0) ? ((double)edge_count * 2) / vertex_count : 0.0;

  high_degree_threshold = std::max<size_t>(4, static_cast<size_t>(1.5 * avg_degree));
}

void mapping_fix_decoder::reset_evaluation_count() const {
  evaluation_counter->store(0, std::memory_order_relaxed);
}

std::uint64_t mapping_fix_decoder::get_evaluation_count() const {
  return evaluation_counter->load(std::memory_order_relaxed);
}

double mapping_fix_decoder::decode(std::span<const double> chromosome) const {
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

double mapping_fix_decoder::decode(const std::vector<double>& chromosome) const {
  return decode(std::span<const double>(chromosome));
}

bool mapping_fix_decoder::is_solution_feasible(
    const std::vector<uint8_t>& labels
) const {
  return hsc::is_solution_feasible(graph, labels);
}

std::vector<uint8_t>
mapping_fix_decoder::construct_solution(std::span<const double> chromosome) const {
  const size_t vertex_count = graph.get_order();

  // f representa a atribuição da função de dominação {3}-romana de cada vértice
  thread_local std::vector<uint8_t> f;
  f.assign(vertex_count, 0); // Após a inicialização para o thread_local

  // closed_weight armazena a soma dos pesos na vizinhança fechada de cada
  // vértice N[v]
  thread_local std::vector<int> neighborhood_weight;
  neighborhood_weight.assign(vertex_count, 0);

  for (size_t i = 0; i < vertex_count; ++i) {
    assign_label(
        graph, f, neighborhood_weight, i, static_cast<uint8_t>(chromosome[i] * 4.0)
    );
  }

  for (size_t u = 0; u < vertex_count; ++u) {
    if (is_vertex_feasible(f, neighborhood_weight, u)) {
      continue;
    }
    assign_label(graph, f, neighborhood_weight, u, 1);
    if (!is_vertex_feasible(f, neighborhood_weight, u)) {
      assign_label(graph, f, neighborhood_weight, u, 2);
    }
  }

  reduce_weight_heuristic(graph, f, neighborhood_weight);
  return f;
}

std::vector<uint8_t> hsc::mapping_fix_decoder::construct_solution(
    const std::vector<double>& chromosome
) const {
  return construct_solution(std::span<const double>(chromosome));
}
} // namespace hsc
