#include "graph.hpp"

#include <algorithm>
#include <fstream>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>

#include "hscopt/defs.h"

namespace {

[[nodiscard]] std::string trim(const std::string &value) {
  const auto begin = value.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) {
    return {};
  }

  const auto end = value.find_last_not_of(" \t\r\n");
  return value.substr(begin, end - begin + 1);
}

[[nodiscard]] bool is_dimacs_header(const std::string &line) {
  std::istringstream stream(line);
  std::string p;
  std::string kind;
  return (stream >> p >> kind) && p == "p" &&
         (kind == "edge" || kind == "col");
}

[[nodiscard]] std::string peek_nonempty_noncomment_line(std::ifstream &file) {
  std::string line;
  while (std::getline(file, line)) {
    const auto cleaned = trim(line);
    if (cleaned.empty() || cleaned.front() == 'c') {
      continue;
    }
    return cleaned;
  }
  return {};
}

[[nodiscard]] bool is_dimacs_file(std::ifstream &file,
                                  const std::string &filename) {
  if (filename.size() >= 4 &&
      filename.compare(filename.size() - 4, 4, ".col") == 0) {
    return true;
  }

  const auto first_line = peek_nonempty_noncomment_line(file);
  file.clear();
  file.seekg(0, std::ios::beg);
  return is_dimacs_header(first_line);
}

[[nodiscard]] const std::size_t *graph_lower_bound(
    const std::size_t *first, const std::size_t *last,
    const std::size_t value) noexcept {
  auto count = static_cast<std::size_t>(last - first);
  while (count > 0) {
    const auto step = count >> 1U;
    const auto *it = first + step;
    if (*it < value) {
      first = it + 1;
      count -= step + 1;
    } else {
      count = step;
    }
  }
  return first;
}

} // namespace

Graph::Graph(const std::string &filename) { load_from_file(filename); }

Graph Graph::read_dimacs_col(const std::string &filename) {
  std::ifstream file(filename);
  if (!file) {
    throw std::runtime_error("failed to open graph file: " + filename);
  }

  Graph graph;
  auto parsed = parse_dimacs_col_file(file, filename);
  graph.rebuild_from_edges(parsed.vertex_count, std::move(parsed.edges));
  return graph;
}

Graph::Graph(const Graph &other) { copy_from(other); }

Graph &Graph::operator=(const Graph &other) {
  if (this != &other) {
    copy_from(other);
  }
  return *this;
}

void Graph::copy_from(const Graph &other) {
  vertex_count_ = other.vertex_count_;
  edge_count_ = other.edge_count_;
  adjacency_count_ = other.adjacency_count_;
  min_degree_ = other.min_degree_;
  max_degree_ = other.max_degree_;
  deterministic_vertex_ = other.deterministic_vertex_;
  vertices_ = other.vertices_;
  isolated_vertices_ = other.isolated_vertices_;

  offsets_.reset();
  adjacency_.reset();

  if (other.offsets_) {
    offsets_ = std::make_unique<std::size_t[]>(vertex_count_ + 1);
    std::copy_n(other.offsets_.get(), vertex_count_ + 1, offsets_.get());
  }

  if (other.adjacency_) {
    adjacency_ = std::make_unique<std::size_t[]>(adjacency_count_);
    std::copy_n(other.adjacency_.get(), adjacency_count_, adjacency_.get());
  }
}

const std::size_t *Graph::offsets_data() const noexcept {
  return offsets_ ? offsets_.get() : nullptr;
}

const std::size_t *Graph::adjacency_data() const noexcept {
  return adjacency_ ? adjacency_.get() : nullptr;
}

Graph::ParsedGraphData Graph::parse_graph_file(const std::string &filename) {
  std::ifstream file(filename);
  if (!file) {
    throw std::runtime_error("failed to open graph file: " + filename);
  }

  ParsedGraphData parsed;

  if (is_dimacs_file(file, filename)) {
    return parse_dimacs_col_file(file, filename);
  }

  std::string header_line;
  while (std::getline(file, header_line)) {
    header_line = trim(header_line);
    if (!header_line.empty()) {
      break;
    }
  }

  if (header_line.empty()) {
    throw std::runtime_error("empty graph file: " + filename);
  }

  std::istringstream header_stream(header_line);
  std::size_t ignored_edge_count = 0;
  if (!(header_stream >> parsed.vertex_count >> ignored_edge_count)) {
    throw std::runtime_error("invalid n m header in " + filename);
  }

  std::vector<std::pair<std::size_t, std::size_t>> raw_edges;
  std::vector<std::size_t> labels;
  std::string line;

  while (std::getline(file, line)) {
    const auto cleaned = trim(line);
    if (cleaned.empty()) {
      continue;
    }

    std::istringstream stream(cleaned);
    std::size_t u = 0;
    std::size_t v = 0;
    if (!(stream >> u >> v) || u == v) {
      continue;
    }

    raw_edges.emplace_back(u, v);
    labels.push_back(u);
    labels.push_back(v);
  }

  std::sort(labels.begin(), labels.end());
  labels.erase(std::unique(labels.begin(), labels.end()), labels.end());

  std::unordered_map<std::size_t, std::size_t> remap;
  remap.reserve(labels.size());
  for (std::size_t i = 0; i < labels.size(); ++i) {
    remap.emplace(labels[i], i);
  }

  parsed.edges.reserve(raw_edges.size());
  for (const auto &[u, v] : raw_edges) {
    parsed.edges.emplace_back(remap.at(u), remap.at(v));
  }

  parsed.vertex_count = std::max(parsed.vertex_count, labels.size());
  return parsed;
}

Graph::ParsedGraphData Graph::parse_dimacs_col_file(std::ifstream &file,
                                                    const std::string &filename) {
  ParsedGraphData parsed;
  std::string line;
  bool saw_header = false;
  bool saw_edge = false;
  bool zero_based = false;
  std::size_t min_label = std::numeric_limits<std::size_t>::max();

  file.clear();
  file.seekg(0, std::ios::beg);

  while (std::getline(file, line)) {
    const auto cleaned = trim(line);
    if (cleaned.empty() || cleaned.front() == 'c') {
      continue;
    }

    std::istringstream stream(cleaned);
    std::string tag;
    stream >> tag;

    if (tag == "p") {
      std::string kind;
      std::size_t ignored_edge_count = 0;
      if (!(stream >> kind >> parsed.vertex_count >> ignored_edge_count) ||
          (kind != "edge" && kind != "col")) {
        throw std::runtime_error("invalid DIMACS header in " + filename);
      }
      saw_header = true;
      continue;
    }

    if (tag != "e") {
      continue;
    }

    std::size_t u = 0;
    std::size_t v = 0;
    if (!(stream >> u >> v) || u == v) {
      continue;
    }

    saw_edge = true;
    min_label = std::min(min_label, std::min(u, v));
    zero_based = min_label == 0;
    parsed.edges.emplace_back(u, v);
  }

  if (!saw_header) {
    throw std::runtime_error("missing DIMACS header in " + filename);
  }

  if (!saw_edge) {
    return parsed;
  }

  for (auto &[u, v] : parsed.edges) {
    if (!zero_based) {
      if (u == 0 || v == 0) {
        throw std::runtime_error("invalid 1-based DIMACS edge in " + filename);
      }
      --u;
      --v;
    }

    if (u >= parsed.vertex_count || v >= parsed.vertex_count) {
      throw std::runtime_error("edge endpoint out of range in " + filename);
    }
  }

  return parsed;
}

std::uint64_t Graph::mix64(std::uint64_t value) noexcept {
  value ^= value >> 30U;
  value *= 0xbf58476d1ce4e5b9ULL;
  value ^= value >> 27U;
  value *= 0x94d049bb133111ebULL;
  value ^= value >> 31U;
  return value;
}

std::uint64_t Graph::compute_graph_fingerprint(
    std::size_t vertex_count, std::size_t edge_count, std::size_t min_degree,
    std::size_t max_degree, const std::size_t *adjacency_begin,
    const std::size_t *adjacency_end) noexcept {
  std::uint64_t hash = 0x9e3779b97f4a7c15ULL;
  hash ^= mix64(static_cast<std::uint64_t>(vertex_count));
  hash ^= mix64(static_cast<std::uint64_t>(edge_count) + 0x100000001b3ULL);
  hash ^= mix64(static_cast<std::uint64_t>(max_degree) << 1U);
  hash ^= mix64(static_cast<std::uint64_t>(min_degree) << 7U);
  if (adjacency_begin != adjacency_end) {
    hash ^= mix64(static_cast<std::uint64_t>(*adjacency_begin) << 17U);
    hash ^= mix64(static_cast<std::uint64_t>(*(adjacency_end - 1)) << 29U);
  }
  return hash;
}

void Graph::load_from_file(const std::string &filename) {
  auto parsed = parse_graph_file(filename);
  rebuild_from_edges(parsed.vertex_count, std::move(parsed.edges));
}

void Graph::rebuild_from_edges(
    std::size_t vertex_count,
    std::vector<std::pair<std::size_t, std::size_t>> edges) {
  vertex_count_ = vertex_count;
  edge_count_ = 0;
  adjacency_count_ = 0;
  min_degree_ = 0;
  max_degree_ = 0;
  deterministic_vertex_ = 0;
  vertices_.resize(vertex_count_);
  std::iota(vertices_.begin(), vertices_.end(), std::size_t{0});
  isolated_vertices_.clear();

  offsets_.reset();
  adjacency_.reset();

  if (vertex_count_ == 0) {
    return;
  }

  edges.erase(std::remove_if(edges.begin(), edges.end(),
                             [vertex_count](const auto &edge) {
                               return edge.first == edge.second ||
                                      edge.first >= vertex_count ||
                                      edge.second >= vertex_count;
                             }),
              edges.end());

  for (auto &[u, v] : edges) {
    if (u > v) {
      std::swap(u, v);
    }
  }

  std::sort(edges.begin(), edges.end());
  edges.erase(std::unique(edges.begin(), edges.end()), edges.end());
  edge_count_ = edges.size();

  offsets_ = std::make_unique<std::size_t[]>(vertex_count_ + 1);
  std::fill_n(offsets_.get(), vertex_count_ + 1, std::size_t{0});

  for (const auto &[u, v] : edges) {
    ++offsets_[u + 1];
    ++offsets_[v + 1];
  }

  std::partial_sum(offsets_.get(), offsets_.get() + vertex_count_ + 1,
                   offsets_.get());
  adjacency_count_ = offsets_[vertex_count_];
  if (adjacency_count_ > 0) {
    adjacency_ = std::make_unique<std::size_t[]>(adjacency_count_);
  }

  auto cursor = std::make_unique<std::size_t[]>(vertex_count_ + 1);
  std::copy_n(offsets_.get(), vertex_count_ + 1, cursor.get());

  for (const auto &[u, v] : edges) {
    adjacency_[cursor[u]++] = v;
    adjacency_[cursor[v]++] = u;
  }

  min_degree_ = std::numeric_limits<std::size_t>::max();
  max_degree_ = 0;

  for (std::size_t vertex = 0; vertex < vertex_count_; ++vertex) {
    auto *begin = adjacency_.get() + offsets_[vertex];
    auto *end = adjacency_.get() + offsets_[vertex + 1];
    std::sort(begin, end);

    const auto degree = static_cast<std::size_t>(end - begin);
    min_degree_ = std::min(min_degree_, degree);
    max_degree_ = std::max(max_degree_, degree);
    if (degree == 0) {
      isolated_vertices_.push_back(vertex);
    }
  }

  deterministic_vertex_ = static_cast<std::size_t>(
      compute_graph_fingerprint(vertex_count_, edge_count_, min_degree_,
                                max_degree_, adjacency_.get(),
                                adjacency_.get() + adjacency_count_) %
      vertex_count_);
}

void Graph::collect_edges(
    std::vector<std::pair<std::size_t, std::size_t>> &edges) const {
  edges.clear();
  edges.reserve(edge_count_);
  for (std::size_t u = 0; u < vertex_count_; ++u) {
    const auto neighbors = get_neighbors(u);
    for (const auto v : neighbors) {
      if (u < v) {
        edges.emplace_back(u, v);
      }
    }
  }
}

void Graph::add_vertex(std::size_t vertex) {
  if (vertex < vertex_count_) {
    return;
  }

  std::vector<std::pair<std::size_t, std::size_t>> edges;
  collect_edges(edges);
  rebuild_from_edges(vertex + 1, std::move(edges));
}

void Graph::add_edge(std::size_t source, std::size_t destination) {
  if (source == destination) {
    return;
  }

  std::vector<std::pair<std::size_t, std::size_t>> edges;
  collect_edges(edges);
  edges.emplace_back(source, destination);
  rebuild_from_edges(std::max(vertex_count_, std::max(source, destination) + 1),
                     std::move(edges));
}

void Graph::delete_vertex(std::size_t vertex) {
  if (HSCOPT_UNLIKELY(!vertex_exists(vertex))) {
    throw std::out_of_range("vertex does not exist");
  }

  std::vector<std::pair<std::size_t, std::size_t>> edges;
  edges.reserve(edge_count_);

  for (std::size_t u = 0; u < vertex_count_; ++u) {
    if (u == vertex) {
      continue;
    }

    const auto neighbors = get_neighbors(u);
    for (const auto v : neighbors) {
      if (u < v && v != vertex) {
        edges.emplace_back((u > vertex) ? (u - 1) : u,
                           (v > vertex) ? (v - 1) : v);
      }
    }
  }

  rebuild_from_edges(vertex_count_ - 1, std::move(edges));
}

std::size_t Graph::get_order() const noexcept { return vertex_count_; }

std::size_t Graph::get_size() const noexcept { return edge_count_; }

float Graph::get_density() const noexcept {
  if (HSCOPT_UNLIKELY(vertex_count_ < 2)) {
    return 0.0F;
  }

  const auto denominator =
      static_cast<float>(vertex_count_) * static_cast<float>(vertex_count_ - 1);
  return static_cast<float>(2 * edge_count_) / denominator;
}

std::size_t Graph::get_vertex_degree(std::size_t vertex) const {
  if (HSCOPT_UNLIKELY(!vertex_exists(vertex))) {
    throw std::out_of_range("vertex does not exist");
  }
  return offsets_[vertex + 1] - offsets_[vertex];
}

std::size_t Graph::get_min_degree() const {
  if (HSCOPT_UNLIKELY(vertex_count_ == 0)) {
    throw std::runtime_error("empty graph does not have a minimum degree");
  }
  return min_degree_;
}

std::size_t Graph::get_max_degree() const {
  if (HSCOPT_UNLIKELY(vertex_count_ == 0)) {
    throw std::runtime_error("empty graph does not have a maximum degree");
  }
  return max_degree_;
}

Graph::NeighborView Graph::get_neighbors(std::size_t vertex) const {
  if (HSCOPT_UNLIKELY(!vertex_exists(vertex))) {
    throw std::out_of_range("vertex does not exist");
  }
  return NeighborView(adjacency_data() + offsets_[vertex],
                      offsets_[vertex + 1] - offsets_[vertex]);
}

bool Graph::vertex_exists(std::size_t vertex) const noexcept {
  return vertex < vertex_count_;
}

bool Graph::edge_exists(std::size_t u, std::size_t v) const {
  if (HSCOPT_UNLIKELY(!vertex_exists(u) || !vertex_exists(v))) {
    throw std::out_of_range("edge endpoint does not exist");
  }
  if (u == v) {
    return false;
  }

  const auto begin = adjacency_data() + offsets_[u];
  const auto end = adjacency_data() + offsets_[u + 1];
  const auto *it = graph_lower_bound(begin, end, v);
  return it != end && *it == v;
}

const std::vector<std::size_t> &Graph::get_vertices() const noexcept {
  return vertices_;
}

const std::vector<std::size_t> &Graph::get_isolated_vertices() const noexcept {
  return isolated_vertices_;
}

std::size_t Graph::choose_random_vertex() const {
  if (HSCOPT_UNLIKELY(vertex_count_ == 0)) {
    throw std::runtime_error("graph is empty");
  }
  return deterministic_vertex_;
}

std::ostream &operator<<(std::ostream &os, const Graph &graph) {
  for (std::size_t vertex = 0; vertex < graph.vertex_count_; ++vertex) {
    os << vertex << " ----> ";
    for (std::size_t index = graph.offsets_[vertex];
         index < graph.offsets_[vertex + 1]; ++index) {
      os << graph.adjacency_[index] << ' ';
    }
    os << '\n';
  }
  return os;
}
