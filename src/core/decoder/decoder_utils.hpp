#ifndef HSC_DECODER_UTILS_HPP
#define HSC_DECODER_UTILS_HPP

#include "graph/graph.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace hsc {

/**
 * @brief Calcula o peso da vizinhança aberta de cada vértice.
 *
 * Para cada vértice u, o valor retornado em neighborhood_weight[u] é a soma
 * dos rótulos atribuídos aos vizinhos de u. Esse vetor é usado pelos decoders
 * para verificar as restrições locais sem recalcular a vizinhança inteira a
 * cada movimento.
 *
 * labels deve ter o mesmo tamanho que graph.get_order().
 */
[[nodiscard]] static inline std::vector<int>
compute_neighborhood_weight(const Graph& graph, std::span<const uint8_t> labels) {
  const size_t vertex_count = graph.get_order();

  // Vetor de peso da vizinhança aberta de cada vértice
  std::vector<int> neighborhood_weight(vertex_count, 0);

  for (size_t u = 0; u < vertex_count; ++u) {

    for (size_t v : graph.get_neighbors(u)) {
      neighborhood_weight[u] += labels[v];
    }
  }

  return neighborhood_weight;
}

/**
 * @brief Atualiza o rótulo de um vértice e propaga o delta para seus vizinhos.
 *
 * A função mantém neighborhood_weight consistente com labels após mudar o
 * rótulo de u. Como o peso armazenado é de vizinhança aberta, apenas os
 * vizinhos de u recebem o delta; o peso de u não muda por causa do próprio
 * rótulo.
 *
 * labels e neighborhood_weight devem estar sincronizados antes da chamada.
 */
inline void assign_label(
    const Graph& graph,
    std::span<uint8_t> labels,
    std::span<int> neighborhood_weight,
    const size_t u,
    const uint8_t new_label
) {

  const int delta = static_cast<int>(new_label) - static_cast<int>(labels[u]);

  labels[u] = new_label;

  for (const size_t v : graph.get_neighbors(u)) {
    neighborhood_weight[v] += delta;
  }
}

/**
 * @brief Verifica se um vértice satisfaz a restrição local do problema.
 *
 * A decisão usa o rótulo atual de u e o peso já calculado da sua vizinhança
 * aberta. Vértices com rótulo 0 exigem peso de vizinhança pelo menos 3,
 * vértices com rótulo 1 exigem pelo menos 2, e rótulos 2 ou 3 já satisfazem a
 * restrição local.
 */
[[nodiscard]] inline bool is_vertex_feasible(
    std::span<const uint8_t> labels,
    std::span<const int> neighborhood_weight,
    const size_t u
) {

  if (labels[u] == 0) {
    return neighborhood_weight[u] >= 3;
  }

  if (labels[u] == 1) {
    return neighborhood_weight[u] >= 2;
  }

  return true;
}

/**
 * @brief Verifica se uma rotulação completa é viável para o grafo.
 *
 * A solução é rejeitada quando o tamanho de labels não coincide com a ordem do
 * grafo, quando algum rótulo está fora do domínio [0, 3], ou quando alguma
 * restrição local da vizinhança aberta é violada.
 */
[[nodiscard]] inline bool
is_solution_feasible(const Graph& graph, std::span<const uint8_t> labels) {

  const size_t vertex_count = graph.get_order();

  if (labels.size() != vertex_count) {
    return false;
  }

  const auto neighborhood_weight = compute_neighborhood_weight(graph, labels);

  for (size_t u = 0; u < vertex_count; ++u) {

    if (labels[u] > 3) {
      return false;
    }

    if (!is_vertex_feasible(labels, neighborhood_weight, u)) {
      return false;
    }
  }

  return true;
}

void reduce_weight_heuristic(
    const Graph& graph, std::span<uint8_t> labels, std::span<int> neighborhood_weight
);

/**
 * @brief Tenta reduzir gulosa e incrementalmente o peso total da solução.
 *
 * A heurística percorre os vértices tentando diminuir cada rótulo em uma
 * unidade. O movimento é mantido apenas se o vértice alterado e todos os seus
 * vizinhos continuam viáveis. Como assign_label atualiza os pesos de
 * vizinhança de forma incremental, cada teste evita recomputar toda a solução.
 *
 * Ao final, labels e neighborhood_weight representam a melhor solução obtida
 * por esse processo local.
 */
inline void reduce_weight_heuristic(
    const Graph& graph, std::span<uint8_t> labels, std::span<int> neighborhood_weight
) {

  const size_t vertex_count = graph.get_order();

  bool improved = true;

  while (improved) {

    improved = false;

    for (size_t u = 0; u < vertex_count; ++u) {

      // Vértices rotulados com 0 não podem ser reduzidos
      if (labels[u] == 0) {
        continue;
      }

      const uint8_t old_label = labels[u];

      const uint8_t new_label = old_label - 1;

      // Aplica o novo rotulo ao vértice
      assign_label(graph, labels, neighborhood_weight, u, new_label);

      bool feasible = true;

      // Verifica se o vértice ficou válidos
      if (!is_vertex_feasible(labels, neighborhood_weight, u)) {
        feasible = false;
      }

      // Verifica se os vizinhos ficaram válidos
      for (const size_t v : graph.get_neighbors(u)) {
        if (!is_vertex_feasible(labels, neighborhood_weight, v)) {
          feasible = false;
          break;
        }
      }

      // Reverte o movimento se a solução não segue as restrições do problema
      if (!feasible) {
        assign_label(graph, labels, neighborhood_weight, u, old_label);
      } else {
        improved = true;
      }
    }
  }
}

} // namespace hsc
#endif // !HSC_DECODER_UTILS_HPP
