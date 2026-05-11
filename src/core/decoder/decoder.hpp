#ifndef HSC_DECODER_HPP
#define HSC_DECODER_HPP

#include "incremental_greedy.hpp"

#include <hscopt/decoder.h>

/**
 * @brief Gera um adapter com ABI C para classes de decoder em C++.
 *
 * A biblioteca hscopt recebe um ponteiro de função com assinatura
 * hscopt_decoder_fn. Os decoders do projeto são objetos C++, então esta macro
 * cria a ponte entre (keys, tamanho, contexto) e decoder.decode(span).
 *
 * O uso de std::span é intencional: ele evita copiar o cromossomo dentro do
 * loop quente de avaliação.
 *
 * A instância ativa do decoder deve ser armazenada em ctx->user.
 */
#define HSCOPT_MAKE_DECODER_ADAPTER(name, type)                                        \
  extern "C" double name(const double* keys, std::size_t n, hscopt_decode_ctx* ctx) {  \
    const auto* decoder =                                                              \
        static_cast<const type*>(ctx != nullptr ? ctx->user : nullptr);                \
    if (decoder == nullptr || keys == nullptr) {                                       \
      return std::numeric_limits<double>::infinity();                                  \
    }                                                                                  \
    return decoder->decode(std::span<const double>(keys, n));                          \
  }

namespace hsc {

/**
 * @brief Implementação ativa de decoder usada por todos os runners.
 *
 * Para testar outra implementação, inclua o header dela acima e altere este
 * alias junto com decoder_name. Os runners dependem apenas de hsc::decoder, logo
 * a escolha é feita em tempo de compilação, sem virtual dispatch e sem branch a
 * cada avaliação.
 */
using decoder = incremental_greedy;

inline constexpr const char* decoder_name = "greedy_construction";

} // namespace hsc

#endif // HSC_DECODER_HPP
