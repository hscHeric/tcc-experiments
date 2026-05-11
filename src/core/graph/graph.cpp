#include "graph.hpp"

#include <algorithm>
#include <fstream>
#include <limits>
#include <random>
#include <stdexcept>

namespace hsc {

void Graph::add_vertex(size_t vertex) {
  adj_list.try_emplace(vertex);
}

void Graph::add_edge(size_t source, size_t destination) {
  if (source == destination)
    return;

  add_vertex(source);
  add_vertex(destination);

  if (edge_exists(source, destination))
    return;

  adj_list[source].push_back(destination);
  adj_list[destination].push_back(source);
}

std::size_t Graph::get_order() const noexcept {
  return adj_list.size();
}

std::size_t Graph::get_size() const noexcept {
  std::size_t count = 0;
  for (const auto& [vertex, neighbors] : adj_list) {
    count += neighbors.size();
  }
  return count / 2;
}

std::size_t Graph::get_vertex_degree(size_t vertex) const {
  auto it = adj_list.find(vertex);
  if (it == adj_list.end()) {
    throw std::out_of_range("Vertex " + std::to_string(vertex) + " not found");
  }
  return it->second.size();
}

std::size_t Graph::get_min_degree() const {
  if (adj_list.empty())
    throw std::runtime_error("Empty graph context");

  std::size_t min_deg = std::numeric_limits<std::size_t>::max();
  for (const auto& [_, neighbors] : adj_list) {
    min_deg = std::min(min_deg, neighbors.size());
  }
  return min_deg;
}

std::size_t Graph::get_max_degree() const {
  if (adj_list.empty())
    throw std::runtime_error("Empty graph context");

  std::size_t max_deg = 0;
  for (const auto& [_, neighbors] : adj_list) {
    max_deg = std::max(max_deg, neighbors.size());
  }
  return max_deg;
}

const std::vector<size_t>& Graph::get_neighbors(size_t vertex) const {
  return adj_list.at(vertex);
}

bool Graph::vertex_exists(size_t vertex) const noexcept {
  return adj_list.contains(vertex);
}

bool Graph::edge_exists(size_t u, size_t v) const {
  auto it = adj_list.find(u);
  if (it == adj_list.end())
    return false;

  return std::find(it->second.begin(), it->second.end(), v) != it->second.end();
}

void Graph::delete_vertex(size_t vertex) {
  auto it = adj_list.find(vertex);
  if (it == adj_list.end())
    return;

  for (const auto& neighbor : it->second) {
    std::erase(adj_list[neighbor], vertex);
  }
  adj_list.erase(it);
}

float Graph::get_density() const noexcept {
  const auto n = static_cast<float>(get_order());
  if (n < 2)
    return 0.0f;
  return (static_cast<float>(get_size()) * 2.0f) / (n * (n - 1.0f));
}

std::unordered_set<size_t> Graph::get_isolated_vertices() const {
  std::unordered_set<size_t> isolated;
  for (const auto& [vertex, neighbors] : adj_list) {
    if (neighbors.empty())
      isolated.insert(vertex);
  }
  return isolated;
}

std::unordered_set<size_t> Graph::get_vertices() const {
  std::unordered_set<size_t> vertices;
  vertices.reserve(adj_list.size());
  for (const auto& [vertex, _] : adj_list) {
    vertices.insert(vertex);
  }
  return vertices;
}

size_t Graph::choose_random_vertex() const {
  if (adj_list.empty())
    throw std::runtime_error("Cannot pick from empty graph");

  static std::random_device rd;
  static std::mt19937 gen(rd());

  std::uniform_int_distribution<std::size_t> dist(0, adj_list.size() - 1);
  auto it = std::next(adj_list.begin(), dist(gen));
  return it->first;
}

std::ostream& operator<<(std::ostream& os, const Graph& graph) {
  for (const auto& [vertex, neighbors] : graph.adj_list) {
    os << vertex << " ----> ";
    for (const auto& neighbor : neighbors) {
      os << neighbor << " ";
    }
    os << '\n';
  }
  return os;
}

Graph load_graph(const std::filesystem::path& path) {
  std::ifstream file(path);
  if (!file.is_open()) {
    throw std::runtime_error("Não foi possível abrir o arquivo: " + path.string());
  }

  Graph g;
  std::string line;
  size_t n_header = 0;
  bool is_dimacs = false;
  bool header_found = false;

  struct Edge {
    size_t u, v;
  };
  std::vector<Edge> temp_edges;
  size_t min_label = std::numeric_limits<size_t>::max();

  while (std::getline(file, line)) {
    if (line.empty())
      continue;

    line.erase(0, line.find_first_not_of(" \t"));
    if (line.empty() || line[0] == 'c')
      continue;

    std::stringstream ss(line);
    char tag;

    if (line[0] == 'p') {
      std::string p, type;
      size_t m_header;
      ss >> p >> type >> n_header >> m_header;
      if (type == "edge" || type == "col") {
        is_dimacs = true;
        header_found = true;
      }
      continue;
    }

    if (is_dimacs && line[0] == 'e') {
      size_t u, v;
      ss >> tag >> u >> v;
      temp_edges.push_back({u, v});
      min_label = std::min({min_label, u, v});
    } else if (!is_dimacs) {
      if (!header_found) {
        size_t m_unused;
        ss >> n_header >> m_unused;
        header_found = true;
      } else {
        size_t u, v;
        if (ss >> u >> v) {
          temp_edges.push_back({u, v});
          min_label = std::min({min_label, u, v});
        }
      }
    }
  }

  if (!header_found) {
    throw std::runtime_error("Header do grafo não encontrado.");
  }

  bool should_offset = (min_label == 1);

  for (size_t i = 0; i < n_header; ++i) {
    g.add_vertex(i);
  }

  for (const auto& edge : temp_edges) {
    size_t u = should_offset ? edge.u - 1 : edge.u;
    size_t v = should_offset ? edge.v - 1 : edge.v;
    g.add_edge(u, v);
  }

  return g;
}

} // namespace hsc
