#include "app_stub_common.hpp"

int main(int argc, char **argv) {
  return run_stub_app(
      {
          .algorithm_name = "aco_ts",
          .status_message =
              "stub only: reserve this entry point for an ACO + Tabu Search pipeline",
      },
      argc, argv);
}
