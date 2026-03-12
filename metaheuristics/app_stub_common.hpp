#ifndef METAHEURISTICS_APP_STUB_COMMON_HPP
#define METAHEURISTICS_APP_STUB_COMMON_HPP

/**
 * @file app_stub_common.hpp
 * @brief Utilitários compartilhados para os executáveis stub de metaheurística.
 */

#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>

#include "graph.hpp"
#include "hscopt/hscopt.h"

/**
 * @brief Configuração mínima para um executável stub.
 */
struct StubAppConfig {
  /// Nome lógico do algoritmo.
  std::string algorithm_name;
  /// Mensagem explicando o estado atual do stub.
  std::string status_message;
};

/**
 * @brief Executa um stub de metaheurística.
 * @param config Configuração textual do stub.
 * @param argc Número de argumentos.
 * @param argv Vetor de argumentos.
 * @return Código de saída do processo.
 *
 * Se um arquivo de grafo for informado, o stub o carrega e imprime métricas
 * básicas para validar integração com a biblioteca de grafo.
 */
inline int run_stub_app(const StubAppConfig &config, int argc, char **argv) {
  std::cout << "algorithm=" << config.algorithm_name << '\n';
  std::cout << "status=" << config.status_message << '\n';
  std::cout << "hscopt_version=" << HSCOPT_VERSION_STRING << '\n';

  if (argc < 2) {
    std::cout << "usage: " << argv[0] << " <graph-file>\n";
    return 0;
  }

  const std::filesystem::path path(argv[1]);
  if (!std::filesystem::exists(path)) {
    std::cerr << "error: graph file not found: " << path << '\n';
    return 1;
  }

  const Graph graph(path.string());
  std::cout << "graph=" << path << '\n';
  std::cout << "order=" << graph.get_order() << '\n';
  std::cout << "size=" << graph.get_size() << '\n';
  std::cout << "density=" << graph.get_density() << '\n';
  std::cout << "next_step=replace this stub with the real metaheuristic pipeline\n";

  return 0;
}

#endif
