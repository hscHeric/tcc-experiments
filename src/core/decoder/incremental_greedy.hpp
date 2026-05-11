#ifndef HSC_GREEDY_CONSTRUCTION_HPP
#define HSC_GREEDY_CONSTRUCTION_HPP

#include "../graph/graph.hpp"

#include <atomic>
#include <cstdint>
#include <memory>
#include <span>
#include <vector>

namespace hsc {

class incremental_greedy {
private:
  const Graph& graph;
  std::shared_ptr<std::atomic<std::uint64_t>> evaluation_counter;

public:
  explicit incremental_greedy(const Graph& graph);

  double decode(std::span<const double> chromosome) const;
  double decode(const std::vector<double>& chromosome) const;

  void reset_evaluation_count() const;
  [[nodiscard]] std::uint64_t get_evaluation_count() const;

  [[nodiscard]] std::vector<uint8_t>
  construct_solution(std::span<const double> chromosome) const;

  [[nodiscard]] std::vector<uint8_t>
  construct_solution(const std::vector<double>& chromosome) const;

  [[nodiscard]] bool is_solution_feasible(const std::vector<uint8_t>& labels) const;
};

} // namespace hsc

#endif // HSC_GREEDY_CONSTRUCTION_HPP
