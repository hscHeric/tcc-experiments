#ifndef HSC_DECODER_HPP
#define HSC_DECODER_HPP

#include "graph.hpp"
#include <cstddef>
#include <cstdint>
#include <numeric>
#include <vector>

/**
 * Decoder D1
 *
 * Este decoder mapeia um cromossomo de chaves aleatórias (valores reais no
 * intervalo [0,1)) para uma solução discreta viável do problema, representada
 * por um vetor de rótulos l ∈ {0,1,2,3}^n.
 *
 * Inicialmente, cada gene do cromossomo é discretizado por meio da
 * transformação l[i] = floor(4 * chromosome[i]), produzindo uma solução
 * candidata.
 *
 * Em seguida, o decoder garante a viabilidade da solução com base na seguinte
 * restrição: para todo vértice v tal que l[v] <= 1, a soma dos rótulos na sua
 * vizinhança fechada (incluindo o próprio vértice) deve ser pelo menos 3.
 *
 * O procedimento percorre os vértices em ordem crescente e, para cada vértice
 * que viola a restrição, aplica um reparo simples atribuindo l[v] = 2, que é o
 * menor valor capaz de garantir a satisfação da condição de forma imediata.
 *
 * Como o reparo apenas aumenta valores de rótulos, a soma das vizinhanças nunca
 * diminui, garantindo que vértices previamente válidos permaneçam válidos ao
 * longo do processo. Dessa forma, uma única passagem sobre os vértices é
 * suficiente para obter uma solução viável.
 *
 * Por fim, o valor da função objetivo é dado pela soma dos rótulos dos
 * vértices.
 */
class D1 {
private:
  const hsc::Graph &graph;

public:
  explicit D1(const hsc::Graph &graph) : graph(graph) {}

  double decode(const std::vector<double> &chromosome) const {
    // if (chromosome.size() != graph.get_order()) {
    //   throw std::invalid_argument(
    //       "Erro: o tamanho do cromossomo (" +
    //       std::to_string(chromosome.size()) +
    //       ") é diferente do número de vértices do grafo (" +
    //       std::to_string(graph.get_order()) + ").");
    // }

    // Vetor de rótulos discretizados
    std::vector<uint8_t> l;
    l.reserve(chromosome.size());

    for (size_t i = 0; i < chromosome.size(); ++i) {
      double x = chromosome[i];

      // Validação do domínio [0,1)
      // if (x < 0.0 || x >= 1.0) {
      //   throw std::out_of_range(
      //       "Erro: valor do cromossomo fora do intervalo [0,1) na posição " +
      //       std::to_string(i) + ". Valor encontrado: " + std::to_string(x));
      // }

      l.push_back(static_cast<uint8_t>(x * 4));
    }

    // Obter vértices ordenados
    // O graph.get_vertices() não garante a ordem, embora eu acredite que fato
    // do algoritmo de inserção ser deterministico faz a ordem ser sempre a
    // mesma, estou fazendo esse procedimento para ter certeza
    auto vertices_set = graph.get_vertices();
    std::vector<size_t> vertices(vertices_set.begin(), vertices_set.end());
    std::sort(vertices.begin(), vertices.end());

    for (unsigned long v : vertices) {
      if (l[v] <= 1) {
        std::vector<size_t> neighbors = graph.get_neighbors(v);
        size_t sum = l[v] + std::accumulate(neighbors.begin(), neighbors.end(),
                                            0UL, [&](size_t acc, size_t u) {
                                              return acc + l[u];
                                            });

        if (sum < 3) {
          // Aqui é o conserto mais trivial em que eu pego um valor que é
          // inválido e troco por 2 que é o menor valro que é sempre válido para
          // o problema
          l[v] = 2;
        }
      }
    }

    return std::accumulate(l.begin(), l.end(), 0UL);
  }
};

#endif // !HSC_DECODER_HPP
