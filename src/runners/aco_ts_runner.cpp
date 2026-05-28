#include "decoder/decoder.hpp"
#include "graph/graph.hpp"
#include "runtime/runtime.hpp"

#include <CLI/CLI.hpp>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <hscopt/aco.h>
#include <hscopt/rng.h>
#include <hscopt/ts.h>
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

struct aco_ts_params {
  fs::path input_file{};
  fs::path output_file{};
  unsigned attempts = 1;
  size_t archive_size = 100;
  size_t ants = 120;
  double q = 0.08;
  double xi = 0.90;
  unsigned max_threads = 8;
  unsigned max_iterations = 5000;
  unsigned max_time_seconds = 900;
  unsigned max_stagnation = 1500;
  unsigned local_search_start = 100;
  unsigned local_search_interval = 50;
  unsigned ts_iterations = 100;
  size_t ts_neighborhood_size = 128;
  unsigned ts_tabu_tenure = 10;
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

static void validate_params(const aco_ts_params& p) {
  if (p.q <= 0.0 || p.xi <= 0.0) {
    throw CLI::ValidationError("q e xi devem ser > 0");
  }
  if (p.archive_size == 0 || p.ants == 0) {
    throw CLI::ValidationError("archive_size e ants devem ser > 0");
  }
  if (p.local_search_start == 0 && p.ts_iterations > 0) {
    throw CLI::ValidationError("local_search_start deve ser > 0");
  }
  if (p.local_search_interval == 0 && p.ts_iterations > 0) {
    throw CLI::ValidationError("local_search_interval deve ser > 0");
  }
}

static void run_tabu_search_from_aco(
    hscopt_aco_ctx* aco,
    size_t n_keys,
    const aco_ts_params& params,
    hscopt_decoder_fn decoder_fn,
    hscopt_decode_ctx* dctx,
    uint64_t seed
) {
  hscopt_rng ts_rng;
  hscopt_rng_seed(&ts_rng, seed);

  hscopt_ts_ctx* ts = hscopt_ts_create(
      n_keys,
      params.ts_neighborhood_size,
      params.ts_tabu_tenure,
      params.ts_iterations,
      params.max_threads,
      decoder_fn,
      dctx,
      &ts_rng,
      hscopt_aco_best_keys(aco)
  );
  if (ts == nullptr) {
    throw std::runtime_error("falha ao criar contexto TS");
  }

  if (hscopt_ts_iterate(ts, params.ts_iterations) != 0) {
    hscopt_ts_destroy(ts);
    throw std::runtime_error("falha ao executar TS");
  }

  hscopt_aco_try_update_best(aco, hscopt_ts_best_keys(ts));
  hscopt_ts_destroy(ts);
}

int main(int argc, char* argv[]) {
  [[maybe_unused]] auto* logger = hsc::runtime::setup_console_logger();
  aco_ts_params params;

  CLI::App app{"ACO com Tabu Search para Dominação 3-Romana em Grafos"};
  argv = app.ensure_utf8(argv);

  app.add_option("-i,--input", params.input_file, "Arquivo de entrada")
      ->required()
      ->check(CLI::ExistingFile);
  app.add_option("-o,--output", params.output_file, "Arquivo de saída")->required();
  app.add_option("-a,--attempts", params.attempts)
      ->check(CLI::Range(1, 1'000'000))
      ->capture_default_str();
  app.add_option("--archive", params.archive_size, "Tamanho do arquivo ACO")
      ->check(CLI::Range(1, 1'000'000));
  app.add_option("--ants", params.ants, "Formigas por iteração")
      ->check(CLI::Range(1, 1'000'000));
  app.add_option("--q", params.q, "Parâmetro q do ACO")->check(CLI::PositiveNumber);
  app.add_option("--xi", params.xi, "Parâmetro xi do ACO")->check(CLI::PositiveNumber);
  app.add_option("-t,--threads", params.max_threads)->capture_default_str();
  app.add_option("--iters", params.max_iterations)->capture_default_str();
  app.add_option("--time", params.max_time_seconds)->check(CLI::NonNegativeNumber);
  app.add_option("--stagnation", params.max_stagnation)->check(CLI::NonNegativeNumber);
  app.add_option(
      "--ls-start,--local-search-start",
      params.local_search_start,
      "Primeira iteração em que o TS será executado"
  );
  app.add_option(
      "--ls-int,--local-search-interval",
      params.local_search_interval,
      "Intervalo da busca local TS"
  );
  app.add_option("--ts-iters", params.ts_iterations, "Iterações do TS");
  app.add_option("--ts-neigh", params.ts_neighborhood_size, "Tamanho da vizinhança TS");
  app.add_option("--ts-tenure", params.ts_tabu_tenure, "Tenure tabu");
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

  LOG_INFO(logger, "Iniciando ACO+TS para: {}", params.input_file.string());
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
      {"algorithm", "ACO+TS"},
      {"decoder", hsc::decoder_name},
      {"graph", params.input_file.filename().string()},
      {"input_file", params.input_file.string()},
      {"executed_at", hsc::runtime::to_iso8601_utc(std::chrono::system_clock::now())},
      {"parameters",
       {{"attempts", params.attempts},
        {"archive_size", params.archive_size},
        {"ants", params.ants},
        {"q", params.q},
        {"xi", params.xi},
        {"threads", params.max_threads},
        {"max_iterations", params.max_iterations},
        {"max_time_seconds", params.max_time_seconds},
        {"max_stagnation", params.max_stagnation},
        {"local_search_start", params.local_search_start},
        {"local_search_interval", params.local_search_interval},
        {"ts_iterations", params.ts_iterations},
        {"ts_neighborhood_size", params.ts_neighborhood_size},
        {"ts_tabu_tenure", params.ts_tabu_tenure},
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

    hscopt_aco_ctx* aco = hscopt_aco_create(
        g.get_order(),
        params.archive_size,
        params.ants,
        params.max_iterations,
        params.max_threads,
        params.q,
        params.xi,
        hscopt_decoder_adapter,
        &dctx,
        &rng
    );
    if (aco == nullptr) {
      LOG_ERROR(logger, "Falha ao criar contexto ACO");
      return 1;
    }

    auto start_time = std::chrono::high_resolution_clock::now();
    auto wall_clock_start = std::chrono::system_clock::now();
    unsigned stagnation_counter = 0;
    double best_fitness = hscopt_aco_best_fitness(aco);
    stop_reason reason = stop_reason::max_iterations;
    json convergence = json::array();

    for (unsigned iteration = 1; iteration <= params.max_iterations; ++iteration) {
      if (hscopt_aco_iterate(aco, 1) != 0) {
        hscopt_aco_destroy(aco);
        LOG_ERROR(logger, "Falha na iteração ACO {}", iteration);
        return 1;
      }

      if (params.ts_iterations > 0 && iteration >= params.local_search_start &&
          (iteration - params.local_search_start) % params.local_search_interval == 0) {
        try {
          run_tabu_search_from_aco(
              aco,
              g.get_order(),
              params,
              hscopt_decoder_adapter,
              &dctx,
              attempt_seed + iteration
          );
        } catch (const std::runtime_error& e) {
          hscopt_aco_destroy(aco);
          LOG_ERROR(logger, "{}", e.what());
          return 1;
        }
      }

      const double current_best = hscopt_aco_best_fitness(aco);
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
    const auto iterations = hscopt_aco_iteration(aco);
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

    hscopt_aco_destroy(aco);
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
