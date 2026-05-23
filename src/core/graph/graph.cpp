#include "graph.hpp"

#include <algorithm>
#include <fstream>
#include <limits>
#include <random>
#include <stdexcept>
#include <sstream>

namespace hsc {

void Graph::add_vertex(size_t vertex) {
  if (vertex >= adj_list.size()) {
    adj_list.resize(vertex + 1);
    active_vertices.resize(vertex + 1, 0);
  }

  if (!active_vertices[vertex]) {
    active_vertices[vertex] = 1;
    ++vertex_count;
  }
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
  ++edge_count;
}

std::size_t Graph::get_vertex_degree(size_t vertex) const {
  if (!vertex_exists(vertex)) {
    throw std::out_of_range("Vertex " + std::to_string(vertex) + " not found");
  }
  return adj_list[vertex].size();
}

std::size_t Graph::get_min_degree() const {
  if (vertex_count == 0)
    throw std::runtime_error("Empty graph context");

  std::size_t min_deg = std::numeric_limits<std::size_t>::max();
  for (size_t vertex = 0; vertex < adj_list.size(); ++vertex) {
    if (active_vertices[vertex]) {
      min_deg = std::min(min_deg, adj_list[vertex].size());
    }
  }
  return min_deg;
}

std::size_t Graph::get_max_degree() const {
  if (vertex_count == 0)
    throw std::runtime_error("Empty graph context");

  std::size_t max_deg = 0;
  for (size_t vertex = 0; vertex < adj_list.size(); ++vertex) {
    if (active_vertices[vertex]) {
      max_deg = std::max(max_deg, adj_list[vertex].size());
    }
  }
  return max_deg;
}

bool Graph::edge_exists(size_t u, size_t v) const {
  if (!vertex_exists(u) || !vertex_exists(v))
    return false;

  const auto& neighbors = adj_list[u];
  return std::find(neighbors.begin(), neighbors.end(), v) != neighbors.end();
}

void Graph::delete_vertex(size_t vertex) {
  if (!vertex_exists(vertex))
    return;

  for (const auto& neighbor : adj_list[vertex]) {
    std::erase(adj_list[neighbor], vertex);
  }
  edge_count -= adj_list[vertex].size();
  adj_list[vertex].clear();
  active_vertices[vertex] = 0;
  --vertex_count;
}

float Graph::get_density() const noexcept {
  const auto n = static_cast<float>(get_order());
  if (n < 2)
    return 0.0f;
  return (static_cast<float>(get_size()) * 2.0f) / (n * (n - 1.0f));
}

std::unordered_set<size_t> Graph::get_isolated_vertices() const {
  std::unordered_set<size_t> isolated;
  for (size_t vertex = 0; vertex < adj_list.size(); ++vertex) {
    if (active_vertices[vertex] && adj_list[vertex].empty()) {
      isolated.insert(vertex);
    }
  }
  return isolated;
}

std::unordered_set<size_t> Graph::get_vertices() const {
  std::unordered_set<size_t> vertices;
  vertices.reserve(vertex_count);
  for (size_t vertex = 0; vertex < active_vertices.size(); ++vertex) {
    if (active_vertices[vertex]) {
      vertices.insert(vertex);
    }
  }
  return vertices;
}

size_t Graph::choose_random_vertex() const {
  if (vertex_count == 0)
    throw std::runtime_error("Cannot pick from empty graph");

  static std::random_device rd;
  static std::mt19937 gen(rd());

  std::uniform_int_distribution<std::size_t> dist(0, vertex_count - 1);
  std::size_t selected = dist(gen);

  for (size_t vertex = 0; vertex < active_vertices.size(); ++vertex) {
    if (active_vertices[vertex] && selected-- == 0) {
      return vertex;
    }
  }

  throw std::runtime_error("Failed to pick a random vertex");
}

std::ostream& operator<<(std::ostream& os, const Graph& graph) {
  for (size_t vertex = 0; vertex < graph.adj_list.size(); ++vertex) {
    if (!graph.active_vertices[vertex]) {
      continue;
    }

    os << vertex << " ----> ";
    const auto& neighbors = graph.adj_list[vertex];
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
