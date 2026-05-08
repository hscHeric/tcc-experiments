#ifndef HSC_DECODER_HPP
#define HSC_DECODER_HPP

#include "../graph/graph.hpp"
#include <atomic>
#include <hscopt/decoder.h>
#include <memory>
#include <vector>

#define HSCOPT_MAKE_DECODER_ADAPTER(name, type)                                \
  extern "C" double name(const double *keys, std::size_t n,                    \
                         hscopt_decode_ctx *ctx) {                             \
    const auto *decoder =                                                      \
        static_cast<const type *>(ctx != nullptr ? ctx->user : nullptr);       \
    if (decoder == nullptr || keys == nullptr) {                               \
      return std::numeric_limits<double>::infinity();                          \
    }                                                                          \
    return decoder->decode(std::vector<double>(keys, keys + n));               \
  }

class Roman3DominationDecoder {
private:
  const hsc::Graph &graph;
  std::shared_ptr<std::atomic<std::uint64_t>> evaluation_counter;

public:
  explicit Roman3DominationDecoder(const hsc::Graph &graph);
  double decode(const std::vector<double> &chromosome) const;
  void reset_evaluation_count() const;
  [[nodiscard]] std::uint64_t get_evaluation_count() const;

  [[nodiscard]] std::vector<uint8_t>
  construct_solution(const std::vector<double> &chromosome) const;

  [[nodiscard]] bool
  is_solution_feasible(const std::vector<uint8_t> &labels) const;
};

#endif // HSC_DECODER_HPP
