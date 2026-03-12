#include "app_stub_common.hpp"

int main(int argc, char **argv) {
  return run_stub_app(
      {
          .algorithm_name = "hho_rvns",
          .status_message =
              "stub only: reserve this entry point for an HHO + RVNS pipeline",
      },
      argc, argv);
}
