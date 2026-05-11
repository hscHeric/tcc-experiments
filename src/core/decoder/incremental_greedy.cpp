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
      evaluation_counter(std::make_shared<std::atomic<std::uint64_t>>(0)) {}

void incremental_greedy::reset_evaluation_count() const {
  evaluation_counter->store(0, std::memory_order_relaxed);
}

std::uint64_t incremental_greedy::get_evaluation_count() const {
  return evaluation_counter->load(std::memory_order_relaxed);
}

double incremental_greedy::decode(std::span<const double> chromosome) const {
  evaluation_counter->fetch_add(1, std::memory_order_relaxed);

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

    // Seleciona o label do vértice de forma gulosa
    // Escolhendo o menor label que mantenha a solução viavel
    assign_label(graph, f, neighborhood_weight, u, 1);
    if (!is_vertex_feasible(f, neighborhood_weight, u)) {
      assign_label(graph, f, neighborhood_weight, u, 2);
    }
    if (!is_vertex_feasible(f, neighborhood_weight, u)) {

      assign_label(graph, f, neighborhood_weight, u, 3);
    }
  }

  // Percorre todos os vértices incrementando o restante até que a solução seja
  // viavel
  // Observe que é impossive deixar a solução inviavel pois estou sempre
  // incrementando
  for (size_t u = 0; u < vertex_count; ++u) {
    while (!is_vertex_feasible(f, neighborhood_weight, u)) {
      if (f[u] < 3) {
        assign_label(graph, f, neighborhood_weight, u, f[u] + 1);
      } else {
        break;
      }
    }
  }

  // Tenta reduzir o peso sem perder a viabilidade
  reduce_weight_heuristic(graph, f, neighborhood_weight);

#ifndef NDEBUG
  if (!hsc::is_solution_feasible(graph, f)) {
    std::cerr << "Infeasible solution detected!" << std::endl;
    std::abort();
  }
#endif

  const double objective_value = std::accumulate(f.begin(), f.end(), 0);

  return objective_value;
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

    // Seleciona o label do vértice de forma gulosa
    // Escolhendo o menor label que mantenha a solução viavel
    assign_label(graph, f, neighborhood_weight, u, 1);
    if (!is_vertex_feasible(f, neighborhood_weight, u)) {
      assign_label(graph, f, neighborhood_weight, u, 2);
    }
    if (!is_vertex_feasible(f, neighborhood_weight, u)) {

      assign_label(graph, f, neighborhood_weight, u, 3);
    }
  }

  // Percorre todos os vértices incrementando o restante até que a solução seja
  // viavel
  // Observe que é impossive deixar a solução inviavel pois estou sempre
  // incrementando
  for (size_t u = 0; u < vertex_count; ++u) {
    while (!is_vertex_feasible(f, neighborhood_weight, u)) {
      if (f[u] < 3) {
        assign_label(graph, f, neighborhood_weight, u, f[u] + 1);
      } else {
        break;
      }
    }
  }

  // Tenta reduzir o peso sem perder a viabilidade
  reduce_weight_heuristic(graph, f, neighborhood_weight);

  return f;
}

std::vector<uint8_t>
incremental_greedy::construct_solution(const std::vector<double>& chromosome) const {
  return construct_solution(std::span<const double>(chromosome));
}
} // namespace hsc
