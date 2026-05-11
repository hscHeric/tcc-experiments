#include "runtime.hpp"

#include <format>
#include <quill/Backend.h>
#include <quill/Frontend.h>
#include <quill/Logger.h>
#include <quill/sinks/ConsoleSink.h>

namespace hsc::runtime {

std::string to_iso8601_utc(const std::chrono::system_clock::time_point& time_point) {
  const auto seconds_tp =
      std::chrono::time_point_cast<std::chrono::seconds>(time_point);
  return std::format("{:%FT%TZ}", seconds_tp);
}

quill::Logger* setup_console_logger(std::string_view logger_name) {
  quill::Backend::start();
  auto console_sink =
      quill::Frontend::create_or_get_sink<quill::ConsoleSink>("console");
  return quill::Frontend::create_or_get_logger(
      std::string(logger_name), std::move(console_sink)
  );
}

} // namespace hsc::runtime
