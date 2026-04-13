#ifndef HSC_DECODER_HPP
#define HSC_DECODER_HPP

#include "../graph/graph.hpp"
#include <algorithm>
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
/**
 * Decoder D2
 * Para cada vértice v tal que l[v] <= 1, verifica-se se a soma dos rótulos
 * na sua vizinhança fechada é pelo menos 3. Caso a restrição não seja
 * satisfeita, o decoder calcula o déficit necessário para atingir esse valor.
 *
 * - Déficit = 3: casos extremos onde a vizinhança é muito fraca; o vértice
 *   recebe rótulo 2 (ou 3 se possuir vizinhos), garantindo viabilidade
 * imediata.
 *
 * - Déficit = 2: o decoder tenta primeiro utilizar vizinhos com rótulo 1,
 *   promovendo dois deles para 2. Caso isso não seja possível, busca um
 *   vizinho com rótulo 0 para elevá-lo diretamente a 2. Como fallback,
 *   o próprio vértice é ajustado para 2.
 *
 * - Déficit = 1: o ajuste mínimo é aplicado incrementando o rótulo do
 *   próprio vértice em uma unidade.
 *
 * Além disso, casos específicos são tratados para evitar soluções inválidas
 * ou ineficientes, como vértices isolados ou situações em que apenas o
 * próprio vértice pode ser ajustado.
 *
 * Assim como no D1, todas as operações de reparo apenas aumentam os rótulos,
 * garantindo que vértices previamente válidos permaneçam válidos. Isso permite
 * que o algoritmo utilize apenas uma única passagem sobre os vértices.
 *
 * O valor da função objetivo é definido como a soma dos rótulos finais.
 */
class D2 {
private:
  const hsc::Graph &graph;

public:
  explicit D2(const hsc::Graph &graph) : graph(graph) {}

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
        size_t neighbor_sum =
            l[v] +
            std::accumulate(neighbors.begin(), neighbors.end(), 0UL,
                            [&](size_t acc, size_t u) { return acc + l[u]; });

        if (neighbor_sum >= 3) {
          continue;
        }

        // O conserto deste decoder consiste em calcular quanto falta para que
        // a vizinhança esteja conforme a restrição, após isso procurar o
        // vizinho de menor rotulo e incrementar o valor calculado, caso a
        // soma do vizinho com o valor calculado seja maior que 3,
        // simplesmente define o label de v como 2
        if (neighbor_sum >= 3)
          continue;

        size_t deficit = 3 - neighbor_sum;

        if (l[v] == 0 && neighbor_sum == 1) {
          l[v] = 2;
          continue;
        }

        if (deficit == 3) {
          if (neighbors.empty()) {
            l[v] = 2;
          } else {
            l[v] = 3;
          }
          continue;
        }

        if (deficit == 2) {

          if (neighbors.empty()) {
            l[v] = 2;
            continue;
          }

          size_t count_ones = 0;
          size_t first = SIZE_MAX, second = SIZE_MAX;

          for (size_t u : neighbors) {
            if (l[u] == 1) {
              if (first == SIZE_MAX)
                first = u;
              else {
                second = u;
                count_ones = 2;
                break;
              }
              count_ones = 1;
            }
          }

          if (count_ones == 2) {
            l[first] = 2;
            l[second] = 2;
            continue;
          }

          for (size_t u : neighbors) {
            if (l[u] == 0) {
              l[u] = 2;
              continue;
            }
          }

          l[v] = 2;
          continue;
        }

        // deficit == 1
        if (deficit == 1) {
          l[v] += 1;
          continue;
        }
      }
    }
    return std::accumulate(l.begin(), l.end(), 0UL);
  }
};

#endif // !HSC_DECODER_HPP
