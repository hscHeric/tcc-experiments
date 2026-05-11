#include "packing_greedy.hpp"

#include <limits>

namespace hsc {

packing_greedy::packing_greedy(const Graph& graph)
    : graph(graph),
      evaluation_counter(std::make_shared<std::atomic<std::uint64_t>>(0)) {}

void packing_greedy::reset_evaluation_count() const {
  evaluation_counter->store(0, std::memory_order_relaxed);
}

std::uint64_t packing_greedy::get_evaluation_count() const {
  return evaluation_counter->load(std::memory_order_relaxed);
}

double packing_greedy::decode(std::span<const double> chromosome) const {
  // TODO: Implementar aqui
  (void)chromosome;
  return std::numeric_limits<double>::infinity();
}

double packing_greedy::decode(const std::vector<double>& chromosome) const {
  return decode(std::span<const double>(chromosome));
}

} // namespace hsc
