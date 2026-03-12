#ifndef METAHEURISTIC_GRAPH_HPP
#define METAHEURISTIC_GRAPH_HPP

/**
 * @file graph.hpp
 * @brief Grafo não direcionado em CSR com foco em consultas determinísticas.
 */

#include <cstddef>
#include <cstdint>
#include <iosfwd>
#include <memory>
#include <string>
#include <utility>
#include <vector>

class Graph {
public:
  /**
   * @brief Visão leve sobre a adjacência de um vértice.
   *
   * Não realiza alocação nem cópia. Apenas referencia a fatia correspondente
   * dentro do armazenamento CSR do grafo.
   */
  class NeighborView {
  public:
    /// Iterador constante sobre os vizinhos.
    using const_iterator = const std::size_t *;

    /**
     * @brief Constrói uma visão vazia.
     */
    constexpr NeighborView() noexcept = default;

    /**
     * @brief Constrói uma visão sobre um bloco contíguo de vizinhos.
     * @param data Ponteiro para o primeiro vizinho.
     * @param size Número de vizinhos.
     */
    constexpr NeighborView(const std::size_t *data, std::size_t size) noexcept
        : data_(data), size_(size) {}

    /**
     * @brief Retorna iterador para o primeiro vizinho.
     */
    [[nodiscard]] constexpr const_iterator begin() const noexcept {
      return data_;
    }

    /**
     * @brief Retorna iterador para o fim da sequência de vizinhos.
     */
    [[nodiscard]] constexpr const_iterator end() const noexcept {
      return data_ + size_;
    }

    /**
     * @brief Acessa o vizinho na posição @p index.
     * @param index Índice local da adjacência.
     * @return Referência constante ao vizinho.
     */
    [[nodiscard]] constexpr const std::size_t &operator[](
        std::size_t index) const noexcept {
      return data_[index];
    }

    /**
     * @brief Retorna o ponteiro bruto para o início da adjacência.
     */
    [[nodiscard]] constexpr const std::size_t *data() const noexcept {
      return data_;
    }

    /**
     * @brief Retorna o número de vizinhos.
     */
    [[nodiscard]] constexpr std::size_t size() const noexcept { return size_; }

    /**
     * @brief Indica se a adjacência está vazia.
     */
    [[nodiscard]] constexpr bool empty() const noexcept { return size_ == 0; }

  private:
    const std::size_t *data_{nullptr};
    std::size_t size_{0};
  };

  /**
   * @brief Constrói um grafo vazio.
   */
  Graph() = default;

  /**
   * @brief Constrói um grafo a partir de um arquivo.
   * @param filename Caminho do arquivo de instância.
   *
   * Detecta automaticamente entre DIMACS `.col` e o formato legado `n m`.
   */
  explicit Graph(const std::string &filename);

  /**
   * @brief Lê explicitamente um arquivo DIMACS `.col`.
   * @param filename Caminho do arquivo.
   * @return Grafo carregado e normalizado.
   *
   * Suporta instâncias 0-based e 1-based.
   */
  [[nodiscard]] static Graph read_dimacs_col(const std::string &filename);

  /**
   * @brief Constrói uma cópia profunda do grafo.
   * @param other Grafo de origem.
   */
  Graph(const Graph &other);

  /**
   * @brief Atribui uma cópia profunda do grafo.
   * @param other Grafo de origem.
   * @return Referência para este objeto.
   */
  Graph &operator=(const Graph &other);
  Graph(Graph &&) noexcept = default;
  Graph &operator=(Graph &&) noexcept = default;
  ~Graph() = default;

  /**
   * @brief Garante a existência do vértice @p vertex.
   * @param vertex Índice do vértice.
   *
   * Se necessário, reconstroi o CSR para expandir o grafo até `vertex + 1`.
   */
  void add_vertex(std::size_t vertex);

  /**
   * @brief Adiciona uma aresta não direcionada.
   * @param source Primeiro extremo.
   * @param destination Segundo extremo.
   *
   * Laços são ignorados. O CSR é reconstruído para preservar as invariantes.
   */
  void add_edge(std::size_t source, std::size_t destination);

  /**
   * @brief Remove um vértice e relabela os índices subsequentes.
   * @param vertex Vértice a remover.
   */
  void delete_vertex(std::size_t vertex);

  /**
   * @brief Retorna o número de vértices.
   */
  [[nodiscard]] std::size_t get_order() const noexcept;

  /**
   * @brief Retorna o número de arestas não direcionadas.
   */
  [[nodiscard]] std::size_t get_size() const noexcept;

  /**
   * @brief Retorna a densidade do grafo.
   */
  [[nodiscard]] float get_density() const noexcept;

  /**
   * @brief Retorna o grau de um vértice.
   * @param vertex Índice do vértice.
   */
  [[nodiscard]] std::size_t get_vertex_degree(std::size_t vertex) const;

  /**
   * @brief Retorna o menor grau do grafo.
   */
  [[nodiscard]] std::size_t get_min_degree() const;

  /**
   * @brief Retorna o maior grau do grafo.
   */
  [[nodiscard]] std::size_t get_max_degree() const;

  /**
   * @brief Retorna uma visão sobre a adjacência de um vértice.
   * @param vertex Índice do vértice.
   */
  [[nodiscard]] NeighborView get_neighbors(std::size_t vertex) const;

  /**
   * @brief Verifica se o vértice existe.
   * @param vertex Índice do vértice.
   */
  [[nodiscard]] bool vertex_exists(std::size_t vertex) const noexcept;

  /**
   * @brief Verifica se a aresta não direcionada existe.
   * @param u Primeiro extremo.
   * @param v Segundo extremo.
   */
  [[nodiscard]] bool edge_exists(std::size_t u, std::size_t v) const;

  /**
   * @brief Retorna os vértices normalizados `0..n-1`.
   */
  [[nodiscard]] const std::vector<std::size_t> &get_vertices() const noexcept;

  /**
   * @brief Retorna os vértices isolados.
   */
  [[nodiscard]] const std::vector<std::size_t> &
  get_isolated_vertices() const noexcept;

  /**
   * @brief Retorna um vértice determinístico derivado do fingerprint do grafo.
   */
  [[nodiscard]] std::size_t choose_random_vertex() const;

  /**
   * @brief Imprime a lista de adjacência do grafo.
   * @param os Stream de saída.
   * @param graph Grafo a imprimir.
   * @return Stream de saída.
   */
  friend std::ostream &operator<<(std::ostream &os, const Graph &graph);

private:
  struct ParsedGraphData {
    std::size_t vertex_count{0};
    std::vector<std::pair<std::size_t, std::size_t>> edges;
  };

  void copy_from(const Graph &other);
  void load_from_file(const std::string &filename);
  void rebuild_from_edges(
      std::size_t vertex_count,
      std::vector<std::pair<std::size_t, std::size_t>> edges);
  void collect_edges(
      std::vector<std::pair<std::size_t, std::size_t>> &edges) const;

  [[nodiscard]] const std::size_t *offsets_data() const noexcept;
  [[nodiscard]] const std::size_t *adjacency_data() const noexcept;

  [[nodiscard]] static ParsedGraphData parse_graph_file(
      const std::string &filename);
  [[nodiscard]] static ParsedGraphData parse_dimacs_col_file(
      std::ifstream &file, const std::string &filename);
  [[nodiscard]] static std::uint64_t mix64(std::uint64_t value) noexcept;
  [[nodiscard]] static std::uint64_t compute_graph_fingerprint(
      std::size_t vertex_count, std::size_t edge_count,
      std::size_t min_degree, std::size_t max_degree,
      const std::size_t *adjacency_begin,
      const std::size_t *adjacency_end) noexcept;

  std::size_t vertex_count_{0};
  std::size_t edge_count_{0};
  std::size_t adjacency_count_{0};
  std::size_t min_degree_{0};
  std::size_t max_degree_{0};
  std::size_t deterministic_vertex_{0};
  std::unique_ptr<std::size_t[]> offsets_;
  std::unique_ptr<std::size_t[]> adjacency_;
  std::vector<std::size_t> vertices_;
  std::vector<std::size_t> isolated_vertices_;
};

#endif
