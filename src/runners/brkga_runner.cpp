#include "decoder/decoder.hpp"
#include "graph/graph.hpp"
#include <BRKGA.h>
#include <CLI/CLI.hpp>
#include <MTRand.h>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <format>
#include <iostream>
#include <limits>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>

namespace fs = std::filesystem;

struct brkga_params {
  fs::path input_file{};
  fs::path output_file{};
  unsigned p_population = 1000;
  double pe_elite_fraction = 0.20;
  double pm_mutant_fraction = 0.10;
  double rhoe_inheritance_prob = 0.70;
  unsigned k_populations = 1;
  unsigned max_threads = 1;
  unsigned max_generations = 1000;
  unsigned max_time_seconds = 0;
  unsigned max_stagnation = 0;
  unsigned exchange_m = 2;
  unsigned exchange_interval = 100;
};

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
  std::ios_base::sync_with_stdio(false);

  // logger
  auto logger = spdlog::stdout_color_mt("console");
  spdlog::set_default_logger(logger);
  spdlog::set_level(spdlog::level::info);

  brkga_params params;

  CLI::App app{"BRKGA para o Problema da Dominação 3-Romana em Grafos"};

  argv = app.ensure_utf8(argv);

  app.add_option("-i,--input", params.input_file, "Arquivo de entrada")
      ->required()
      ->check(CLI::ExistingFile);

  app.add_option("-o,--output", params.output_file, "Arquivo de saída")
      ->required();

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

    spdlog::info("Config carregada com sucesso");
  } catch (const CLI::ValidationError &e) {
    spdlog::error("{}: {}", e.get_name(), e.what());
    return 1;
  } catch (const CLI::ParseError &e) {
    return app.exit(e);
  }

  // inicialização do rng
  auto seed = static_cast<unsigned long>(
      std::chrono::steady_clock::now().time_since_epoch().count());
  MTRand rng(seed);

  // leitura do grafo e inicialização do algoritmo
  auto g = hsc::load_graph(params.input_file);
  D2 decoder(g);
  BRKGA<D2, MTRand> brkga(g.get_order(), params.p_population,
                          params.pe_elite_fraction, params.pm_mutant_fraction,
                          params.rhoe_inheritance_prob, decoder, rng,
                          params.k_populations, params.max_threads);

  // loop principal da evolução
  auto start_time = std::chrono::high_resolution_clock::now();
  unsigned generation = 1;
  unsigned stagnation_counter = 0;
  double best_fitness = std::numeric_limits<double>::infinity();
  while (generation < params.max_generations) {
    brkga.evolve();

    if (params.k_populations > 1 &&
        (generation % params.exchange_interval == 0)) [[unlikely]] {
      brkga.exchangeElite(params.exchange_m);
    }

    double current_best = brkga.getBestFitness();
    if (current_best < best_fitness) {
      best_fitness = current_best;
      stagnation_counter = 0;
      printf("Melhorou: %f", brkga.getBestFitness());
    } else {
      stagnation_counter++;
    }

    // verificação dos criterios de parada
    auto now = std::chrono::high_resolution_clock::now();
    auto elapsed =
        std::chrono::duration_cast<std::chrono::seconds>(now - start_time)
            .count();
    if (stagnation_counter >= params.max_stagnation) {
      break;
    }
    if (elapsed >= params.max_time_seconds) {
      break;
    }

    generation++;
  }

  std::cout << generation << std::endl;
  printf("%.0f\n", brkga.getBestFitness());
  return 0;
}
