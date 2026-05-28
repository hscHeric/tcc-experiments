#include "decoder/decoder.hpp"
#include "graph/graph.hpp"
#include "runtime/runtime.hpp"

#include <CLI/CLI.hpp>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <hscopt/hho.h>
#include <hscopt/rng.h>
#include <hscopt/rvns.h>
#include <iostream>
#include <limits>
#include <nlohmann/json.hpp>
#include <quill/LogMacros.h>
#include <quill/Logger.h>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;
using json = nlohmann::json;

HSCOPT_MAKE_DECODER_ADAPTER(hscopt_decoder_adapter, hsc::decoder)

enum class stop_reason { max_iterations, stagnation, time_limit };

struct hho_rvns_params {
  fs::path input_file{};
  fs::path output_file{};
  unsigned attempts = 1;
  size_t agents = 120;
  unsigned max_threads = 8;
  unsigned max_iterations = 5000;
  unsigned max_time_seconds = 900;
  unsigned max_stagnation = 1500;
  unsigned local_search_start = 100;
  unsigned local_search_interval = 50;
  unsigned rvns_iterations = 100;
  size_t rvns_k_max = 12;
  uint64_t seed = 0;
};

static std::string stop_reason_to_string(stop_reason reason) {
  switch (reason) {
  case stop_reason::max_iterations:
    return "max_iterations";
  case stop_reason::stagnation:
    return "stagnation";
  case stop_reason::time_limit:
    return "time_limit";
  }
  return "unknown";
}

static void validate_params(const hho_rvns_params& p) {
  if (p.agents == 0) {
    throw CLI::ValidationError("agents deve ser > 0");
  }
  if (p.rvns_k_max == 0 && p.rvns_iterations > 0) {
    throw CLI::ValidationError("rvns_k_max deve ser > 0");
  }
  if (p.local_search_start == 0 && p.rvns_iterations > 0) {
    throw CLI::ValidationError("local_search_start deve ser > 0");
  }
  if (p.local_search_interval == 0 && p.rvns_iterations > 0) {
    throw CLI::ValidationError("local_search_interval deve ser > 0");
  }
}

static void run_rvns_from_hho(
    hscopt_hho_ctx* hho,
    size_t n_keys,
    const hho_rvns_params& params,
    hscopt_decoder_fn decoder_fn,
    hscopt_decode_ctx* dctx,
    uint64_t seed
) {
  hscopt_rng rvns_rng;
  hscopt_rng_seed(&rvns_rng, seed);

  hscopt_rvns_ctx* rvns = hscopt_rvns_create(
      n_keys,
      params.rvns_k_max,
      params.rvns_iterations,
      params.max_threads,
      decoder_fn,
      dctx,
      &rvns_rng,
      hscopt_hho_best_keys(hho)
  );
  if (rvns == nullptr) {
    throw std::runtime_error("falha ao criar contexto RVNS");
  }

  if (hscopt_rvns_iterate(rvns, params.rvns_iterations) != 0) {
    hscopt_rvns_destroy(rvns);
    throw std::runtime_error("falha ao executar RVNS");
  }

  hscopt_hho_try_update_rabbit(hho, hscopt_rvns_best_keys(rvns));
  hscopt_rvns_destroy(rvns);
}

int main(int argc, char* argv[]) {
  [[maybe_unused]] auto* logger = hsc::runtime::setup_console_logger();
  hho_rvns_params params;

  CLI::App app{"HHO com RVNS para Dominação 3-Romana em Grafos"};
  argv = app.ensure_utf8(argv);

  app.add_option("-i,--input", params.input_file, "Arquivo de entrada")
      ->required()
      ->check(CLI::ExistingFile);
  app.add_option("-o,--output", params.output_file, "Arquivo de saída")->required();
  app.add_option("-a,--attempts", params.attempts)
      ->check(CLI::Range(1, 1'000'000))
      ->capture_default_str();
  app.add_option("--agents", params.agents, "Número de hawks")
      ->check(CLI::Range(1, 1'000'000));
  app.add_option("-t,--threads", params.max_threads)->capture_default_str();
  app.add_option("--iters", params.max_iterations)->capture_default_str();
  app.add_option("--time", params.max_time_seconds)->check(CLI::NonNegativeNumber);
  app.add_option("--stagnation", params.max_stagnation)->check(CLI::NonNegativeNumber);
  app.add_option(
      "--ls-start,--local-search-start",
      params.local_search_start,
      "Primeira iteração em que o RVNS será executado"
  );
  app.add_option(
      "--ls-int,--local-search-interval",
      params.local_search_interval,
      "Intervalo da busca local RVNS"
  );
  app.add_option("--rvns-iters", params.rvns_iterations, "Iterações do RVNS");
  app.add_option("--rvns-k", params.rvns_k_max, "Maior vizinhança RVNS");
  auto* seed_option = app.add_option("--seed", params.seed, "Seed base para o RNG");

  try {
    app.parse(argc, argv);
    if (params.max_stagnation == 0) {
      params.max_stagnation = params.max_iterations;
    }
    if (params.max_time_seconds == 0) {
      params.max_time_seconds = std::numeric_limits<unsigned>::max();
    }
    validate_params(params);
  } catch (const CLI::ParseError& e) {
    return app.exit(e);
  }

  LOG_INFO(logger, "Iniciando HHO+RVNS para: {}", params.input_file.string());
  auto g = hsc::load_graph(params.input_file);
  hsc::decoder decoder(g);
  hscopt_decode_ctx dctx{};
  dctx.user = &decoder;

  const auto seed_base =
      seed_option->count() > 0
          ? params.seed
          : static_cast<uint64_t>(
                std::chrono::steady_clock::now().time_since_epoch().count()
            );
  double global_best_fitness = std::numeric_limits<double>::infinity();

  json output_json = {
      {"algorithm", "HHO+RVNS"},
      {"decoder", hsc::decoder_name},
      {"graph", params.input_file.filename().string()},
      {"input_file", params.input_file.string()},
      {"executed_at", hsc::runtime::to_iso8601_utc(std::chrono::system_clock::now())},
      {"parameters",
       {{"attempts", params.attempts},
        {"agents", params.agents},
        {"threads", params.max_threads},
        {"max_iterations", params.max_iterations},
        {"max_time_seconds", params.max_time_seconds},
        {"max_stagnation", params.max_stagnation},
        {"local_search_start", params.local_search_start},
        {"local_search_interval", params.local_search_interval},
        {"rvns_iterations", params.rvns_iterations},
        {"rvns_k_max", params.rvns_k_max},
        {"seed", seed_base}}},
      {"attempts", json::array()}
  };

  for (unsigned attempt = 1; attempt <= params.attempts; ++attempt) {
    const auto attempt_seed = seed_base + attempt - 1;
    hscopt_rng rng;
    hscopt_rng_seed(&rng, attempt_seed);
    decoder.reset_evaluation_count();

    LOG_INFO(
        logger, "Tentativa {}/{} | seed={}", attempt, params.attempts, attempt_seed
    );

    hscopt_hho_ctx* hho = hscopt_hho_create(
        g.get_order(),
        params.agents,
        params.max_iterations,
        params.max_threads,
        hscopt_decoder_adapter,
        &dctx,
        &rng
    );
    if (hho == nullptr) {
      LOG_ERROR(logger, "Falha ao criar contexto HHO");
      return 1;
    }

    auto start_time = std::chrono::high_resolution_clock::now();
    auto wall_clock_start = std::chrono::system_clock::now();
    unsigned stagnation_counter = 0;
    double best_fitness = hscopt_hho_best_fitness(hho);
    stop_reason reason = stop_reason::max_iterations;
    json convergence = json::array();

    for (unsigned iteration = 1; iteration <= params.max_iterations; ++iteration) {
      if (hscopt_hho_iterate(hho, 1) != 0) {
        hscopt_hho_destroy(hho);
        LOG_ERROR(logger, "Falha na iteração HHO {}", iteration);
        return 1;
      }

      if (params.rvns_iterations > 0 && iteration >= params.local_search_start &&
          (iteration - params.local_search_start) % params.local_search_interval == 0) {
        try {
          run_rvns_from_hho(
              hho,
              g.get_order(),
              params,
              hscopt_decoder_adapter,
              &dctx,
              attempt_seed + iteration
          );
        } catch (const std::runtime_error& e) {
          hscopt_hho_destroy(hho);
          LOG_ERROR(logger, "{}", e.what());
          return 1;
        }
      }

      const double current_best = hscopt_hho_best_fitness(hho);
      if (current_best < best_fitness) {
        best_fitness = current_best;
        stagnation_counter = 0;
        const auto now = std::chrono::high_resolution_clock::now();
        const auto elapsed_ms =
            std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time)
                .count();
        convergence.push_back(
            {{"iteration", iteration},
             {"elapsed_ms", elapsed_ms},
             {"elapsed_seconds", static_cast<double>(elapsed_ms) / 1000.0},
             {"best_fitness", best_fitness},
             {"evaluations", decoder.get_evaluation_count()}}
        );
        LOG_INFO(
            logger,
            "Tentativa {} | Iteração {:>4}: Novo melhor fitness = {:.2f}",
            attempt,
            iteration,
            best_fitness
        );
      } else {
        stagnation_counter++;
      }

      const auto now = std::chrono::high_resolution_clock::now();
      const auto elapsed =
          std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count();
      if (stagnation_counter >= params.max_stagnation) {
        reason = stop_reason::stagnation;
        break;
      }
      if (elapsed >= params.max_time_seconds) {
        reason = stop_reason::time_limit;
        break;
      }
    }

    const auto end_time = std::chrono::high_resolution_clock::now();
    const auto elapsed_ms =
        std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time)
            .count();
    const auto iterations = hscopt_hho_iteration(hho);
    const auto evaluations = decoder.get_evaluation_count();
    global_best_fitness = std::min(global_best_fitness, best_fitness);

    output_json["attempts"].push_back(
        {{"attempt", attempt},
         {"seed", attempt_seed},
         {"executed_at", hsc::runtime::to_iso8601_utc(wall_clock_start)},
         {"final_solution_value", best_fitness},
         {"evaluations", evaluations},
         {"total_runtime_ms", elapsed_ms},
         {"total_runtime_seconds", static_cast<double>(elapsed_ms) / 1000.0},
         {"iterations", iterations},
         {"stop_reason", stop_reason_to_string(reason)},
         {"convergence", convergence}}
    );

    hscopt_hho_destroy(hho);
  }

  output_json["best_fitness_global"] = global_best_fitness;

  std::error_code ec;
  if (const fs::path parent = params.output_file.parent_path(); !parent.empty()) {
    fs::create_directories(parent, ec);
    if (ec) {
      LOG_ERROR(
          logger,
          "Falha ao criar diretório de saída '{}': {}",
          parent.string(),
          ec.message()
      );
      return 1;
    }
  }

  std::ofstream output_stream(params.output_file);
  if (!output_stream) {
    LOG_ERROR(
        logger, "Falha ao abrir arquivo de saída: {}", params.output_file.string()
    );
    return 1;
  }
  output_stream << output_json.dump(2) << '\n';
  if (!output_stream) {
    return 1;
  }

#ifdef NDEBUG
  std::cout << global_best_fitness << '\n';
#endif

  return 0;
}
