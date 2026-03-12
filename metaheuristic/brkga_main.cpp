#include "app_stub_common.hpp"

int main(int argc, char **argv) {
  return run_stub_app(
      {
          .algorithm_name = "brkga",
          .status_message =
              "stub only: BRKGA is not exposed by the current hscopt API yet",
      },
      argc, argv);
}
