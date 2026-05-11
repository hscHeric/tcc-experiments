#include "packing_greedy.hpp"

#include "decoder/decoder_utils.hpp"

#include <algorithm>
#include <numeric>

namespace hsc {

packing_greedy::packing_greedy(const Graph& graph)
    : graph(graph),
      evaluation_counter(std::make_shared<std::atomic<std::uint64_t>>(0)) {}

void packing_greedy::reset_evaluation_count() const {
  evaluation_counter->store(0, std::memory_order_relaxed);
}

std::uint64_t packing_greedy::get_evaluation_count() const {
  return evaluation_counter->load(std::memory_order_relaxed);
}

double packing_greedy::decode(std::span<const double> chromosome) const {
  // TODO: Implementar aqui
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
  // Considera 255 como vértice não rotulado
  thread_local std::vector<uint8_t> f;
  f.assign(vertex_count, unlabeled_vertex); // Após a inicialização para o thread_local

  // closed_weight armazena a soma dos pesos na vizinhança fechada de cada
  // vértice N[v]
  thread_local std::vector<int> neighborhood_weight;
  neighborhood_weight.assign(vertex_count, 0);

  // Representa os vértice já rotulados que fora "removidos" do grafo
  thread_local std::vector<bool> removed;
  removed.assign(vertex_count, false);

  for (size_t i = 0; i < vertex_count; ++i) {
    const size_t u = priority_order[i];

    // Se o vértice u já tiver sido rotulado apenas ignore
    if (removed[u]) {
      continue;
    }

    // Rotula o vértice u com 3, seus vizinhos com 0 e os remove do grafo
    assign_unlabeled(graph, f, neighborhood_weight, u, 3);
    removed[u] = true;
    for (const size_t v : graph.get_neighbors(u)) {
      if (removed[v]) {
        continue;
      }
      assign_unlabeled(graph, f, neighborhood_weight, v, 0);
      removed[v] = true;
    }

    // Rotula os vértice isolados
    for (size_t isolated = 0; isolated < vertex_count; ++isolated) {

      // Ignora se o vértice já foi rotulado
      if (f[isolated] != unlabeled_vertex) {
        continue;
      }

      // Verifica se todos os vizinhos foram removidos do grafo
      bool all_neighbors_removed = true;
      for (const size_t v : graph.get_neighbors(isolated)) {
        if (!removed[v]) {
          all_neighbors_removed = false;
          break;
        }
      }

      if (!all_neighbors_removed) {
        continue;
      }

      // Escolhe o menor peso possivel para manter o vértice válido
      uint8_t label = 0;
      if (neighborhood_weight[isolated] < 3) {
        label = 1;
      }

      if (neighborhood_weight[isolated] < 2) {
        label = 2;
      }

      assign_label(graph, f, neighborhood_weight, isolated, label);
      removed[isolated] = true;
    }
  }

#ifndef NDEBUG
  if (!hsc::is_solution_feasible(graph, f)) {
    std::cerr << "Infeasible solution detected!" << std::endl;
    std::abort();
  }
#endif

  const double objective_value = std::accumulate(f.begin(), f.end(), 0);
  return objective_value;
}

double packing_greedy::decode(const std::vector<double>& chromosome) const {
  return decode(std::span<const double>(chromosome));
}

} // namespace hsc
