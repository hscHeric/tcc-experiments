#ifndef HSC_RUNTIME_HPP
#define HSC_RUNTIME_HPP

#include <chrono>
#include <quill/Logger.h>
#include <string>
#include <string_view>

namespace hsc::runtime {

/**
 * @brief Formata um timestamp de system_clock como ISO-8601 em UTC.
 */
[[nodiscard]] std::string
to_iso8601_utc(const std::chrono::system_clock::time_point& time_point);

/**
 * @brief Inicializa o backend do quill e retorna um logger de console.
 */
[[nodiscard]] quill::Logger*
setup_console_logger(std::string_view logger_name = "root");

} // namespace hsc::runtime

#endif // HSC_RUNTIME_HPP
