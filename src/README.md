# Organização de `src`

Este diretório contém o código C++ do projeto.

## `core`

Código compartilhado entre os executáveis:

- `graph/`: estrutura de grafo e leitura das instâncias.
- `decoder/`: implementações de decoder e seleção da implementação ativa.
- `runtime/`: utilitários compartilhados de execução, como logger e formatação
  de data/hora.

## `core/decoder`

Arquivos principais:

- `greedy_construction.hpp/.cpp`: decoder de construção gulosa para dominação
  3-romana.
- `decoder.hpp`: ponto único para escolher qual implementação será usada pelos
  runners e macro que adapta um decoder C++ para a ABI C esperada pela
  biblioteca `hscopt`.

Para testar outra implementação de decoder:

1. Crie `meu_decoder.hpp/.cpp` em `src/core/decoder`.
2. Implemente a mesma interface pública:

   ```cpp
   double decode(std::span<const double> chromosome) const;
   void reset_evaluation_count() const;
   std::uint64_t get_evaluation_count() const;
   ```

3. Altere `decoder.hpp`:

   ```cpp
   using decoder = meu_decoder;
   inline constexpr const char *decoder_name = "meu_decoder";
   ```

Essa troca é feita em tempo de compilação. Os runners continuam usando
`hsc::decoder`, evitando `virtual`, `std::function` ou `switch` dentro do loop de
avaliação.

## `runners`

Executáveis de experimentos. Eles devem conter apenas:

- parsing de CLI;
- validação de parâmetros;
- execução do algoritmo;
- escrita do JSON de saída.

Regra prática: lógica compartilhada deve ficar em `core`, não duplicada nos
runners.
