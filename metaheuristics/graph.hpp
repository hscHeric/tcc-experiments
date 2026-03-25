#ifndef HSC_GRAPH_HPP
#define HSC_GRAPH_HPP

#include <iostream>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace hsc {

class Graph {
public:
  /** @brief Construtor padrão.
   Inicializa um grafo vazio sem vértices ou arestas.
   */
  Graph() = default;

  /**
   @brief Construtor por intervalo (range-based).
   @tparam InputIt Tipo do iterador de entrada (deve apontar para std::pair ou
   similar).
   @param first Iterador para o início do intervalo de arestas.
   @param last Iterador para o fim do intervalo de arestas.
   */
  template <typename InputIt> Graph(InputIt first, InputIt last) {
    for (; first != last; ++first) {
      add_edge(first->first, first->second);
    }
  }

  /**
   @brief Adiciona um novo vértice ao grafo.
   @param vertex O identificador único do vértice a ser inserido.
   */
  void add_vertex(size_t vertex);

  /**
   @brief Cria uma aresta não direcionada entre dois vértices.
   @details Se os vértices fornecidos não existirem no grafo, eles serão
   criados.
   @param source Identificador do primeiro vértice.
   @param destination Identificador do segundo vértice.
   */
  void add_edge(size_t source, size_t destination);

  /**
   @brief Remove um vértice e todas as arestas associadas a ele.
   @param vertex O identificador do vértice a ser removido.
   */
  void delete_vertex(size_t vertex);

  /** @brief Obtém o número total de vértices no grafo.
   @return std::size_t A ordem do grafo.
   */
  [[nodiscard]] std::size_t get_order() const noexcept;

  /** @brief Obtém o número total de arestas únicas no grafo.
   @return std::size_t O tamanho do grafo.
   */
  [[nodiscard]] std::size_t get_size() const noexcept;

  /** @brief Calcula a densidade do grafo.
   @return float Valor entre 0.0 e 1.0 representando a densidade.
   */
  [[nodiscard]] float get_density() const noexcept;

  /**
   @brief Retorna o grau de um vértice específico.
   @param vertex O identificador do vértice.
   @return std::size_t Número de arestas incidentes no vértice.
   @exception std::out_of_range Lançada se o vértice não existir no grafo.
   */
  [[nodiscard]] std::size_t get_vertex_degree(size_t vertex) const;

  /** @brief Encontra o grau do vértice com menos conexões.
   @return std::size_t O valor do grau mínimo.
   @exception std::runtime_error Lançada se o grafo estiver vazio.
   */
  [[nodiscard]] std::size_t get_min_degree() const;

  /** @brief Encontra o grau do vértice com mais conexões.
   @return std::size_t O valor do grau máximo.
   @exception std::runtime_error Lançada se o grafo estiver vazio.
   */
  [[nodiscard]] std::size_t get_max_degree() const;

  /** @brief Acessa a lista de vizinhos de um vértice.
   @param vertex O identificador do vértice.
   @return const std::vector<size_t>& Referência constante para o vetor
   de adjacência.
   */
  [[nodiscard]] const std::vector<size_t> &get_neighbors(size_t vertex) const;

  /** @brief Identifica vértices que não possuem arestas.
   @return std::unordered_set<size_t> Conjunto de IDs de vértices
   isolados.
   */
  [[nodiscard]] std::unordered_set<size_t> get_isolated_vertices() const;

  /** @brief Retorna todos os vértices presentes no grafo.
   @return std::unordered_set<size_t> Conjunto de todos os IDs de
   vértices.
   */
  [[nodiscard]] std::unordered_set<size_t> get_vertices() const;

  /** @brief Verifica se existe uma conexão direta entre dois vértices.
   @param u Identificador do primeiro vértice.
   @param v Identificador do segundo vértice.
   @return bool True se a aresta existir, False caso contrário.
   */
  [[nodiscard]] bool edge_exists(size_t u, size_t v) const;

  /** @brief Verifica a presença de um vértice no grafo.
   @param vertex Identificador do vértice.
   @return bool True se o vértice existir.
   */
  [[nodiscard]] bool vertex_exists(size_t vertex) const noexcept;

  /** @brief Escolhe um vértice aleatório dentre os existentes.
   @return size_t O ID do vértice selecionado.
   @exception std::runtime_error Lançada se o grafo estiver vazio.
   */
  [[nodiscard]] size_t choose_random_vertex() const;

  /** @brief Sobrecarga para saída em fluxo (impressão).
   @param os Fluxo de saída.
   @param graph Instância do grafo a ser impressa.
   @return std::ostream& Referência ao fluxo de saída.
   */
  friend std::ostream &operator<<(std::ostream &os, const Graph &graph);

private:
  std::unordered_map<size_t, std::vector<size_t>>
      adj_list; ///< Estrutura de dados principal (Hash Map de Listas).
};

} // namespace hsc

#endif
