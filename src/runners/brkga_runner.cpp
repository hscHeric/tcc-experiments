#include <BRKGA.h>
#include <MTRand.h>
#include "../core/decoder/decoder.hpp"
#include "../core/graph/graph.hpp"
#include <iostream>

int main(int argc, char *argv[]) {
  (void)argc;
  (void)argv;

  hsc::Graph graph;
  graph.add_edge(0, 1);
  graph.add_edge(1, 2);
  graph.add_edge(0, 2);

  D1 decoder(graph);
  MTRand rng(12345UL);

  BRKGA<D1, MTRand> algorithm(
      static_cast<unsigned>(graph.get_order()),
      20,
      0.20,
      0.10,
      0.70,
      decoder,
      rng);

  algorithm.evolve(2);

  std::cout << "Best fitness: " << algorithm.getBestFitness() << '\n';
  return 0;
}
