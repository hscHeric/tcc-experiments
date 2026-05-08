#include "decoder.hpp"
#include "graph/graph.hpp"
#include <cstddef>
#include <cstdint>
#include <memory>
#include <numeric>
#include <unistd.h>
#include <vector>

Roman3DominationDecoder::Roman3DominationDecoder(const hsc::Graph &graph)
    : graph(graph),
      evaluation_counter(std::make_shared<std::atomic<std::uint64_t>>(0)) {}

void Roman3DominationDecoder::reset_evaluation_count() const {
  evaluation_counter->store(0, std::memory_order_relaxed);
}

std::uint64_t Roman3DominationDecoder::get_evaluation_count() const {
  return evaluation_counter->load(std::memory_order_relaxed);
}

static void reduce_weight_heuristic(const hsc::Graph &graph,
                                    std::vector<uint8_t> &f,
                                    std::vector<int> &neighborhood_weight) {
  const size_t vertex_count = graph.get_order();

  auto is_feasible = [&](size_t u) {
    if (f[u] == 0) {
      return neighborhood_weight[u] >= 3;
    }

    if (f[u] == 1) {
      return neighborhood_weight[u] >= 2;
    }

    return true;
  };

  // Atualiza o peso da vizinhança dos vizinhos de u
  auto apply_delta = [&](size_t u, int delta) {
    for (size_t v : graph.get_neighbors(u)) {
      neighborhood_weight[v] += delta;
    }
  };

  bool improved = true;
  while (improved) {
    improved = false;

    // Percorre todos os vértices
    for (size_t u = 0; u < vertex_count; ++u) {
      // Não é possível reduzir vértices rotulados com 0
      if (f[u] == 0) {
        continue;
      }

      const int old_label = f[u];
      const int new_label = old_label - 1;
      const int delta = new_label - old_label;

      f[u] = new_label;
      apply_delta(u, delta);
      bool valid = true;

      // Verifica a viabilidade de u e seus vizinhos
      if (!is_feasible(u)) {
        valid = false;
      }
      for (size_t v : graph.get_neighbors(u)) {

        if (!is_feasible(v)) {
          valid = false;
          break;
        }
      }

      if (!valid) {
        f[u] = old_label;
        apply_delta(u, -delta);
      } else {
        improved = true;
      }
    }
  }
}

double
Roman3DominationDecoder::decode(const std::vector<double> &chromosome) const {
  evaluation_counter->fetch_add(1, std::memory_order_relaxed);

  const size_t vertex_count = graph.get_order();

  // Define a ordem de prioridade dos vértices com base nos valores do
  // cromossomo
  // Vértices com chaves maiores são posicionados primeiro (ordem decrescente)
  thread_local std::vector<size_t> priority_order(vertex_count);
  priority_order.reserve(vertex_count);

  std::iota(priority_order.begin(), priority_order.end(), 0);
  std::sort(priority_order.begin(), priority_order.end(),
            [&](size_t u, size_t v) { return chromosome[u] > chromosome[v]; });

  // f representa a atribuição da função de dominação {3}-romana de cada vértice
  thread_local std::vector<uint8_t> f;
  f.assign(vertex_count, 0); // Após a inicialização para o thread_local

  // closed_weight armazena a soma dos pesos na vizinhança fechada de cada
  // vértice N[v]
  thread_local std::vector<int> neighborhood_weight;
  neighborhood_weight.assign(vertex_count, 0);

  // Atualiza o rótulo do vértice e propaga a contribuição da vizinhança fechada
  auto assign_label = [&](size_t u, int new_label) {
    const int delta = new_label - f[u];

    f[u] = new_label;

    for (size_t v : graph.get_neighbors(u)) {
      neighborhood_weight[v] += delta;
    }
  };

  // Verifica se o vértice safisfaz a restrição do problema
  auto is_feasible = [&](size_t u) {
    if (f[u] == 0) {
      return neighborhood_weight[u] >= 3;
    }

    if (f[u] == 1) {
      return neighborhood_weight[u] >= 2;
    }

    return true;
  };

  // Construção gulosa
  for (size_t i = 0; i < vertex_count; ++i) {
    const size_t u = priority_order[i];

    if (is_feasible(u)) {
      continue;
    }

    // Seleciona o label do vértice de forma gulosa
    // Escolhendo o menor label que mantenha a solução viavel
    assign_label(u, 1);
    if (!is_feasible(u)) {
      assign_label(u, 2);
    }
    if (!is_feasible(u)) {

      assign_label(u, 3);
    }
  }

  // Percorre todos os vértices incrementando o restante até que a solução seja
  // viavel
  // Observe que é impossive deixar a solução inviavel pois estou sempre
  // incrementando
  for (size_t u = 0; u < vertex_count; ++u) {
    while (!is_feasible(u)) {
      if (f[u] < 3) {
        assign_label(u, f[u] + 1);
      } else {
        break;
      }
    }
  }

  // Tenta reduzir o peso sem perder a viabilidade
  reduce_weight_heuristic(graph, f, neighborhood_weight);
  if (!is_solution_feasible(f)) {
    std::cerr << "Infeasible solution detected!" << std::endl;
    std::abort();
  }

  const double objective_value = std::accumulate(f.begin(), f.end(), 0);

  return objective_value;
}

bool Roman3DominationDecoder::is_solution_feasible(
    const std::vector<uint8_t> &labels) const {

  const size_t vertex_count = graph.get_order();

  if (labels.size() != vertex_count) {
    return false;
  }

  for (size_t u = 0; u < vertex_count; ++u) {
    if (labels[u] > 3) {
      return false;
    }

    int neighbor_sum = 0;

    for (size_t v : graph.get_neighbors(u)) {
      neighbor_sum += labels[v];
    }

    if (labels[u] == 0 && neighbor_sum < 3) {
      return false;
    }

    if (labels[u] == 1 && neighbor_sum < 2) {
      return false;
    }
  }

  return true;
}

std::vector<uint8_t> Roman3DominationDecoder::construct_solution(
    const std::vector<double> &chromosome) const {

  const size_t vertex_count = graph.get_order();

  // Define a ordem de prioridade dos vértices com base nos valores do
  // cromossomo
  // Vértices com chaves maiores são posicionados primeiro (ordem decrescente)
  thread_local std::vector<size_t> priority_order(vertex_count);
  priority_order.reserve(vertex_count);

  std::iota(priority_order.begin(), priority_order.end(), 0);
  std::sort(priority_order.begin(), priority_order.end(),
            [&](size_t u, size_t v) { return chromosome[u] > chromosome[v]; });

  // f representa a atribuição da função de dominação {3}-romana de cada vértice
  thread_local std::vector<uint8_t> f;
  f.assign(vertex_count, 0); // Após a inicialização para o thread_local

  // closed_weight armazena a soma dos pesos na vizinhança fechada de cada
  // vértice N[v]
  thread_local std::vector<int> neighborhood_weight;
  neighborhood_weight.assign(vertex_count, 0);

  // Atualiza o rótulo do vértice e propaga a contribuição da vizinhança fechada
  auto assign_label = [&](size_t u, int new_label) {
    const int delta = new_label - f[u];

    f[u] = new_label;

    for (size_t v : graph.get_neighbors(u)) {
      neighborhood_weight[v] += delta;
    }
  };

  // Verifica se o vértice safisfaz a restrição do problema
  auto is_feasible = [&](size_t u) {
    if (f[u] == 0) {
      return neighborhood_weight[u] >= 3;
    }

    if (f[u] == 1) {
      return neighborhood_weight[u] >= 2;
    }

    return true;
  };

  // Construção gulosa
  for (size_t i = 0; i < vertex_count; ++i) {
    const size_t u = priority_order[i];

    if (is_feasible(u)) {
      continue;
    }

    // Seleciona o label do vértice de forma gulosa
    // Escolhendo o menor label que mantenha a solução viavel
    assign_label(u, 1);
    if (!is_feasible(u)) {
      assign_label(u, 2);
    }
    if (!is_feasible(u)) {

      assign_label(u, 3);
    }
  }

  // Percorre todos os vértices incrementando o restante até que a solução seja
  // viavel
  // Observe que é impossive deixar a solução inviavel pois estou sempre
  // incrementando
  for (size_t u = 0; u < vertex_count; ++u) {
    while (!is_feasible(u)) {
      if (f[u] < 3) {
        assign_label(u, f[u] + 1);
      } else {
        break;
      }
    }
  }

  // Tenta reduzir o peso sem perder a viabilidade
  reduce_weight_heuristic(graph, f, neighborhood_weight);

  return f;
}
