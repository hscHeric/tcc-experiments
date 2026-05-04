#ifndef HSC_DECODER_HPP
#define HSC_DECODER_HPP

#include "../graph/graph.hpp"
#include <atomic>
#include <cstddef>
#include <hscopt/decoder.h>
#include <limits>
#include <memory>
#include <vector>

#define HSCOPT_MAKE_DECODER_ADAPTER(name, type)                                \
  extern "C" double name(const double *keys, std::size_t n,                    \
                         hscopt_decode_ctx *ctx) {                             \
    const auto *decoder =                                                      \
        static_cast<const type *>(ctx != nullptr ? ctx->user : nullptr);        \
    if (decoder == nullptr || keys == nullptr) {                                \
      return std::numeric_limits<double>::infinity();                           \
    }                                                                          \
    return decoder->decode(std::vector<double>(keys, keys + n));                \
  }

/**
 * @brief Decoder D1: Mapeia cromossomos [0,1) para rótulos {0,1,2,3}
 * com reparo trivial l[v]=2 em caso de violação.
 */
class D1 {
private:
  const hsc::Graph &graph;

public:
  explicit D1(const hsc::Graph &graph);
  double decode(const std::vector<double> &chromosome) const;
};

/**
 * @brief Decoder D2: Mapeia cromossomos [0,1) com lógica de reparo
 * baseada em déficit para otimizar o peso total.
 */
class D2 {
private:
  const hsc::Graph &graph;

public:
  explicit D2(const hsc::Graph &graph);
  double decode(const std::vector<double> &chromosome) const;
};

class D3 {
private:
  const hsc::Graph &graph;
  std::shared_ptr<std::atomic<std::uint64_t>> evaluation_counter;

public:
  explicit D3(const hsc::Graph &graph);
  double decode(const std::vector<double> &chromosome) const;
  void reset_evaluation_count() const;
  [[nodiscard]] std::uint64_t get_evaluation_count() const;
};

#endif // HSC_DECODER_HPP
