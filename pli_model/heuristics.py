from __future__ import annotations
from typing import Dict, Set
import networkx as nx
import random

Labeling = Dict[int, int]  # v -> {0,1,2,3}


def trivial(G: nx.Graph) -> Labeling:
    """
    Heurística trivial:
    todos os vértices recebem rótulo 2.
    """
    return {v: 2 for v in G.nodes()}


def h1(G: nx.Graph) -> Labeling:
    """
    Escolhe vértice v não rotulado com maior grau
    Rotula v com 3
    Rotula todos os vizinhos não rotulados de v com 0
    Rotula com 2 todos os vértices não rotulados que já têm todos os vizinhos rotulados
    Repete até rotular todos os vértices
    """
    n = G.number_of_nodes()

    rotulados = {v: False for v in G.nodes()}
    f = {v: -1 for v in G.nodes()}
    num_rotulados = 0

    while num_rotulados < n:
        # Encontra vértice não rotulado com maior grau
        candidatos = [v for v in G.nodes() if not rotulados[v]]

        if not candidatos:
            break

        # Escolhe o vértice com maior grau entre os não rotulados
        v = max(candidatos, key=lambda x: G.degree(x))

        # Rotula v com 3
        f[v] = 3
        rotulados[v] = True
        num_rotulados += 1

        # Rotula todos os vizinhos não rotulados de v com 0
        for x in G.neighbors(v):
            if not rotulados[x]:
                f[x] = 0
                rotulados[x] = True
                num_rotulados += 1

        # Rotula com 2 os vértices que têm todos os vizinhos já rotulados
        for w in list(G.nodes()):
            if not rotulados[w]:
                vizinhos_w = list(G.neighbors(w))
                if all(rotulados[u] for u in vizinhos_w):
                    f[w] = 2
                    rotulados[w] = True
                    num_rotulados += 1

    for v in G.nodes():
        if f[v] == -1:
            f[v] = 2

    return f


def h2(G: nx.Graph) -> Labeling:
    """
    H1 do artigo do algoritmo genético - Procedure 1
    """
    n = G.number_of_nodes()
    rotulados = {v: False for v in G.nodes()}
    f = {v: -1 for v in G.nodes()}
    num_rotulados = 0

    while num_rotulados < n:
        # Seleciona vértice aleatoriamente entre os não rotulados
        candidatos = [v for v in G.nodes() if not rotulados[v]]
        if not candidatos:
            break

        u = random.choice(candidatos)
        neighbors_u = list(G.neighbors(u))

        # Caso 1: vértice isolado
        if len(neighbors_u) == 0:
            f[u] = 2
            rotulados[u] = True
            num_rotulados += 1

        # Caso 2: todos os vizinhos já foram rotulados
        elif all(rotulados[v] for v in neighbors_u):
            f[u] = 1
            rotulados[u] = True
            num_rotulados += 1

        # Caso 3: ainda há vizinhos não rotulados
        else:
            f[u] = 0
            rotulados[u] = True
            num_rotulados += 1

            # Escolhe um vizinho não rotulado para receber rótulo 3
            unvisited_neighbors = [v for v in neighbors_u if not rotulados[v]]
            if unvisited_neighbors:
                v = random.choice(unvisited_neighbors)
                f[v] = 3
                rotulados[v] = True
                num_rotulados += 1

                # Os demais vizinhos não rotulados recebem rótulo 2
                for w in neighbors_u:
                    if not rotulados[w] and w != v:
                        f[w] = 2
                        rotulados[w] = True
                        num_rotulados += 1

    # Garantia final
    for v in G.nodes():
        if f[v] == -1:
            f[v] = 2

    return f


def h3(G: nx.Graph) -> Labeling:
    """
    H2 do artigo do algoritmo genético
    """
    n = G.number_of_nodes()
    rotulados = {v: False for v in G.nodes()}
    f = {v: -1 for v in G.nodes()}
    num_rotulados = 0

    while num_rotulados < n:
        # Seleciona vértice aleatoriamente entre os não rotulados
        candidatos = [v for v in G.nodes() if not rotulados[v]]
        if not candidatos:
            break

        u = random.choice(candidatos)
        neighbors_u = list(G.neighbors(u))

        # Caso 1: todos os vizinhos já foram rotulados
        if all(rotulados[v] for v in neighbors_u):
            f[u] = 2
            rotulados[u] = True
            num_rotulados += 1

        # Caso 2: ainda há vizinhos não rotulados
        else:
            f[u] = 3
            rotulados[u] = True
            num_rotulados += 1

            # Rotula todos os vizinhos não rotulados com 0
            for v in neighbors_u:
                if not rotulados[v]:
                    f[v] = 0
                    rotulados[v] = True
                    num_rotulados += 1

    # Garantia final
    for v in G.nodes():
        if f[v] == -1:
            f[v] = 2

    return f
