#include "decoder/decoder.hpp"
#include "graph/graph.hpp"
#include <BRKGA.h>
#include <CLI/CLI.hpp>
#include <MTRand.h>
#include <chrono>
#include <filesystem>
#include <format>
#include <fstream>
#include <limits>
#include <nlohmann/json.hpp>
#include <nlohmann/json_fwd.hpp>
#include <quill/Backend.h>
#include <quill/Frontend.h>
#include <quill/LogMacros.h>
#include <quill/Logger.h>
#include <quill/sinks/ConsoleSink.h>
#include <string>

namespace fs = std::filesystem;
using json = nlohmann::json;

enum class stop_reason { max_generations, stagnation, time_limit };

struct brkga_params {
  fs::path input_file{};
  fs::path output_file{};
  unsigned attempts = 1;
  unsigned p_population = 2000;
  double pe_elite_fraction = 0.15;
  double pm_mutant_fraction = 0.20;
  double rhoe_inheritance_prob = 0.70;
  unsigned k_populations = 4;
  unsigned max_threads = 8;
  unsigned max_generations = 2000;
  unsigned max_time_seconds = 900;
  unsigned max_stagnation = 500;
  unsigned exchange_m = 2;
  unsigned exchange_interval = 100;
};

static std::string
to_iso8601_utc(const std::chrono::system_clock::time_point &time_point) {
  const auto seconds_tp =
      std::chrono::time_point_cast<std::chrono::seconds>(time_point);
  return std::format("{:%FT%TZ}", seconds_tp);
}

static std::string stop_reason_to_string(stop_reason reason) {
  switch (reason) {
  case stop_reason::max_generations:
    return "max_generations";
  case stop_reason::stagnation:
    return "stagnation";
  case stop_reason::time_limit:
    return "time_limit";
  }

  return "unknown";
}

// inicializacão do logger
quill::Logger *setup_logger() {
  quill::Backend::start();
  auto console_sink =
      quill::Frontend::create_or_get_sink<quill::ConsoleSink>("sink_id_1");
  return quill::Frontend::create_or_get_logger("root", std::move(console_sink));
}

// validação dos parâmetros do BRKGA
static inline void validate_brkga_params(const brkga_params &p) {
  const double pe = p.pe_elite_fraction;
  const double pm = p.pm_mutant_fraction;

  if (pe <= 0.0 || pm <= 0.0) {
    throw CLI::ValidationError("Elite e mutantes devem ser > 0");
  }

  if (pe + pm >= 1.0) {
    throw CLI::ValidationError(std::format(
        "Inválido: pe + pm deve ser < 1.0 (atual = {:.3f})", pe + pm));
  }

  if (p.rhoe_inheritance_prob <= 0.0 || p.rhoe_inheritance_prob >= 1.0) {
    throw CLI::ValidationError("Rho deve estar no intervalo (0, 1)");
  }

  unsigned p_e = static_cast<unsigned>(p.pe_elite_fraction * p.p_population);
  if (p.k_populations > 1 && p.exchange_m >= p_e) {
    throw CLI::ValidationError(std::format(
        "Erro: exchange_m ({}) deve ser menor que o tamanho da elite ({})",
        p.exchange_m, p_e));
  }
}

int main(int argc, char *argv[]) {
  [[maybe_unused]] auto *logger = setup_logger();
  brkga_params params;

  CLI::App app{"BRKGA para o Problema da Dominação 3-Romana em Grafos"};

  argv = app.ensure_utf8(argv);

  app.add_option("-i,--input", params.input_file, "Arquivo de entrada")
      ->required()
      ->check(CLI::ExistingFile);

  app.add_option("-o,--output", params.output_file, "Arquivo de saída")
      ->required();

  app.add_option("-a,--attempts", params.attempts,
                 "Numero de tentativas independentes por instancia")
      ->check(CLI::Range(1, 1'000'000))
      ->capture_default_str();

  app.add_option("-p,--pop", params.p_population, "Tamanho da população")
      ->check(CLI::Range(10, 1'000'000));

  app.add_option("-e,--elite", params.pe_elite_fraction, "Fração elite")
      ->check(CLI::Range(0.10, 0.25));

  app.add_option("-m,--mutants", params.pm_mutant_fraction, "Fração mutantes")
      ->check(CLI::Range(0.10, 0.30));

  app.add_option("-r,--rho", params.rhoe_inheritance_prob,
                 "Probabilidade de herança elite")
      ->check(CLI::Range(0.51, 0.99));

  app.add_option("-K,--populations", params.k_populations,
                 "Populações independentes")
      ->capture_default_str();

  app.add_option("-t,--threads", params.max_threads)->capture_default_str();

  app.add_option("-g,--gens", params.max_generations)->capture_default_str();

  app.add_option("--time", params.max_time_seconds, "Tempo máximo")
      ->check(CLI::NonNegativeNumber);

  app.add_option("--stagnation", params.max_stagnation, "Estagnação máxima")
      ->check(CLI::NonNegativeNumber);
  app.add_option("--x-m", params.exchange_m, "M: individuos elite migrantes")

      ->default_val(2);
  app.add_option("--x-int", params.exchange_interval, "Intervalo de migracao")
      ->default_val(100);

  try {
    app.parse(argc, argv);
    if (params.max_stagnation == 0) {
      params.max_stagnation = params.max_generations;
    }
    if (params.max_time_seconds == 0) {
      params.max_time_seconds = std::numeric_limits<unsigned>::max();
    }
    validate_brkga_params(params);
  } catch (const CLI::ValidationError &e) {
    return 1;
  } catch (const CLI::ParseError &e) {
    return app.exit(e);
  }

  LOG_INFO(logger, "Iniciando algoritmo para: {}", params.input_file.string());
  auto g = hsc::load_graph(params.input_file);
  D3 decoder(g);
  const auto seed_base = static_cast<unsigned long>(
      std::chrono::steady_clock::now().time_since_epoch().count());

  double global_best_fitness = std::numeric_limits<double>::infinity();
  json output_json = {
      {"algorithm", "BRKGA"},
      {"graph", params.input_file.filename().string()},
      {"input_file", params.input_file.string()},
      {"executed_at", to_iso8601_utc(std::chrono::system_clock::now())},
      {"parameters",
       {{"attempts", params.attempts},
        {"population", params.p_population},
        {"elite_fraction", params.pe_elite_fraction},
        {"mutant_fraction", params.pm_mutant_fraction},
        {"inheritance_probability", params.rhoe_inheritance_prob},
        {"populations", params.k_populations},
        {"threads", params.max_threads},
        {"max_generations", params.max_generations},
        {"max_time_seconds", params.max_time_seconds},
        {"max_stagnation", params.max_stagnation},
        {"exchange_m", params.exchange_m},
        {"exchange_interval", params.exchange_interval}}},
      {"attempts", json::array()}};

  for (unsigned attempt = 1; attempt <= params.attempts; ++attempt) {
    const auto attempt_seed = seed_base + (attempt - 1);
    MTRand rng(attempt_seed);
    decoder.reset_evaluation_count();
    BRKGA<D3, MTRand> brkga(g.get_order(), params.p_population,
                            params.pe_elite_fraction, params.pm_mutant_fraction,
                            params.rhoe_inheritance_prob, decoder, rng,
                            params.k_populations, params.max_threads);

    LOG_INFO(logger, "Tentativa {}/{} | seed={}", attempt, params.attempts,
             attempt_seed);

    auto start_time = std::chrono::high_resolution_clock::now();
    auto wall_clock_start = std::chrono::system_clock::now();
    unsigned generation = 1;
    unsigned stagnation_counter = 0;
    double best_fitness = std::numeric_limits<double>::infinity();
    stop_reason reason = stop_reason::max_generations;
    json convergence = json::array();

    while (generation < params.max_generations) {
      brkga.evolve();

      if (params.k_populations > 1 &&
          (generation % params.exchange_interval == 0)) [[unlikely]] {
        brkga.exchangeElite(params.exchange_m);
        LOG_DEBUG(logger, "Tentativa {}: elite migrada na geração {}", attempt,
                  generation);
      }

      double current_best = brkga.getBestFitness();
      if (current_best < best_fitness) {
        best_fitness = current_best;
        stagnation_counter = 0;
        const auto now = std::chrono::high_resolution_clock::now();
        const auto elapsed_ms =
            std::chrono::duration_cast<std::chrono::milliseconds>(now -
                                                                  start_time)
                .count();
        convergence.push_back(
            {{"generation", generation},
             {"elapsed_ms", elapsed_ms},
             {"elapsed_seconds", static_cast<double>(elapsed_ms) / 1000.0},
             {"best_fitness", best_fitness},
             {"evaluations", decoder.get_evaluation_count()}});
        LOG_INFO(logger,
                 "Tentativa {} | Geração {:>4}: Novo melhor fitness = {:.2f}",
                 attempt, generation, best_fitness);
      } else {
        stagnation_counter++;
      }

      auto now = std::chrono::high_resolution_clock::now();
      auto elapsed =
          std::chrono::duration_cast<std::chrono::seconds>(now - start_time)
              .count();
      if (stagnation_counter >= params.max_stagnation) {
        reason = stop_reason::stagnation;
        break;
      }
      if (elapsed >= params.max_time_seconds) {
        reason = stop_reason::time_limit;
        break;
      }

      generation++;
    }

    const auto end_time = std::chrono::high_resolution_clock::now();
    const auto elapsed_ms =
        std::chrono::duration_cast<std::chrono::milliseconds>(end_time -
                                                              start_time)
            .count();
    const auto iterations =
        best_fitness == std::numeric_limits<double>::infinity()
            ? 0U
            : generation - 1;
    const auto evaluations = decoder.get_evaluation_count();

    global_best_fitness = std::min(global_best_fitness, best_fitness);
    LOG_INFO(
        logger,
        "Tentativa {} concluída. Geração final: {} | Melhor Fitness: {:.0f}",
        attempt, iterations, best_fitness);

    output_json["attempts"].push_back(
        {{"attempt", attempt},
         {"seed", attempt_seed},
         {"executed_at", to_iso8601_utc(wall_clock_start)},
         {"final_solution_value", best_fitness},
         {"evaluations", evaluations},
         {"total_runtime_ms", elapsed_ms},
         {"total_runtime_seconds", static_cast<double>(elapsed_ms) / 1000.0},
         {"iterations", iterations},
         {"stop_reason", stop_reason_to_string(reason)},
         {"convergence", convergence}});
  }

  LOG_INFO(logger,
           "Execução concluída. Tentativas: {} | Melhor fitness global: {:.0f}",
           params.attempts, global_best_fitness);
  output_json["best_fitness_global"] = global_best_fitness;

  std::error_code ec;
  if (const fs::path parent = params.output_file.parent_path();
      !parent.empty()) {
    fs::create_directories(parent, ec);
    if (ec) {
      LOG_ERROR(logger, "Falha ao criar diretório de saída '{}': {}",
                parent.string(), ec.message());
      return 1;
    }
  }

  std::ofstream output_stream(params.output_file);
  if (!output_stream) {
    LOG_ERROR(logger, "Falha ao abrir arquivo de saída: {}",
              params.output_file.string());
    return 1;
  }

  output_stream << output_json.dump(2) << '\n';
  output_stream.close();

  if (!output_stream) {
    LOG_ERROR(logger, "Falha ao gravar arquivo JSON: {}",
              params.output_file.string());
    return 1;
  }

  return 0;
}
