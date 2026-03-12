# Grafo CSR em C++

## Objetivo

A classe [Graph](/home/hscheric/Work/tcc-experiments/metaheuristic/graph.hpp) foi projetada para:
- leitura determinística
- consultas rápidas
- armazenamento compacto em CSR
- uso principal em cenários de leitura, não de atualização frequente

## Layout

O grafo usa:
- `offsets_`: início e fim da adjacência de cada vértice
- `adjacency_`: lista contígua de vizinhos

Esse layout equivale a CSR para grafo não direcionado.

## Invariantes

Após o carregamento:
- os vértices ficam normalizados em `0..n-1`
- a adjacência de cada vértice fica ordenada
- não há laços
- não há arestas duplicadas
- `edge_exists(u, v)` pode usar busca binária

## Formatos suportados

### DIMACS `.col`

Suporta:
- arquivos `1-based`
- arquivos `0-based`

Regras:
- comentários `c ...` são ignorados
- header aceito: `p edge n m` ou `p col n m`
- arestas `e u v`
- laços são ignorados

API específica:

```cpp
Graph g = Graph::read_dimacs_col("instancia.col");
```

O construtor geral também detecta `.col` automaticamente:

```cpp
Graph g("instancia.col");
```

### Formato legado

Formato:

```text
n m
u v
u v
```

Nesse caso os rótulos originais são relabelados deterministicamente para `0..k-1`, e o número final de vértices é `max(n_header, k)`.

## API principal

### Consultas

- `get_order()`
- `get_size()`
- `get_density()`
- `get_vertex_degree(v)`
- `get_min_degree()`
- `get_max_degree()`
- `get_neighbors(v)`
- `vertex_exists(v)`
- `edge_exists(u, v)`
- `get_vertices()`
- `get_isolated_vertices()`
- `choose_random_vertex()`

### Operações mutáveis

- `add_vertex(v)`
- `add_edge(u, v)`
- `delete_vertex(v)`

Essas operações existem, mas reconstroem o CSR. Portanto, são corretas, porém não são o caminho otimizado do módulo.

## Observações de uso

- `choose_random_vertex()` é determinístico
- `get_neighbors()` retorna uma visão leve (`NeighborView`) sem alocação
- o módulo é apropriado para decoders e heurísticas que consultam muito o grafo

## Testes realizados

Antes da limpeza dos testes temporários, o grafo foi validado em todas as instâncias da pasta `data/instances`, incluindo:
- faixa `0..n-1`
- vértices faltantes
- contagem de arestas
- graus mínimo e máximo
- densidade
- consistência da adjacência
