#!/usr/bin/env python3
import sys
import os
import math
import itertools
import time
from lector import leer_archivo, imprimir_problema, Problema

def build_euclidean_graph(p: Problema) -> None:
    """Construye grafo completo con distancias euclidianas entre nodos."""
    n = p.num_nodos
    p.grafo_distancias = [[0.0]*n for _ in range(n)]
    for i in range(n):
        xi, yi = p.nodos[i].x, p.nodos[i].y
        for j in range(i+1, n):
            xj, yj = p.nodos[j].x, p.nodos[j].y
            d = math.hypot(xi - xj, yi - yj)
            p.grafo_distancias[i][j] = d
            p.grafo_distancias[j][i] = d

def floyd_warshall(p: Problema):
    """Calcula y retorna la matriz de distancias mínimas entre todos los pares."""
    n = p.num_nodos
    # copia
    dist = [row[:] for row in p.grafo_distancias]
    for k in range(n):
        dk = dist[k]
        for i in range(n):
            di = dist[i]
            ik = di[k]
            if ik == float('inf'):
                continue
            for j in range(n):
                nd = ik + dk[j]
                if nd < di[j]:
                    di[j] = nd
    return dist

def enumerate_hub_subsets(hubs, max_enumerate=1<<15):
    """Generador de subconjuntos de hubs. Si hay muchos hubs aplica heurística."""
    H = len(hubs)
    if H <= 15:
        # enumerar todos
        for mask in range(1<<H):
            yield [hubs[i] for i in range(H) if (mask>>i)&1]
    else:
        # heurística: tomar los hubs más baratos y generar combinaciones pequeñas
        hubs_sorted = sorted(hubs, key=lambda h: h.costo_activacion)
        consider = hubs_sorted[:min(12, H)]
        for r in range(0, 5):  # combinaciones de tamaño 0..4
            for comb in itertools.combinations(consider, r):
                yield list(comb)

def backtracking_route(p: Problema, shortest_dist, active_hub_nodes):
    """Usa backtracking para encontrar la ruta óptima del camión.
    Retorna (distancia_total, ruta_lista)"""
    deposito = p.deposito_id
    destinos = frozenset(paq.id_nodo_destino for paq in p.paquetes)
    recargas = frozenset(active_hub_nodes) | {deposito}
    capacidad = p.capacidad_camion

    best_cost = float('inf')
    best_route = None

    def backtrack(current_loc, delivered, rem_cap, cost_so_far, route_so_far):
        nonlocal best_cost, best_route

        if cost_so_far >= best_cost:
            return

        if len(delivered) == len(destinos):
            # Todos entregados, volver al depósito si no estamos ahí
            if current_loc != deposito:
                cost_to_depot = shortest_dist[current_loc][deposito]
                total_cost = cost_so_far + cost_to_depot
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_route = route_so_far + [deposito]
            else:
                if cost_so_far < best_cost:
                    best_cost = cost_so_far
                    best_route = route_so_far[:]
            return

        # Cota inferior: suma de distancias mínimas a destinos no entregados
        undelivered = destinos - delivered
        lower_bound = 0.0
        for dest in undelivered:
            min_d = min(shortest_dist[loc][dest] for loc in recargas | {current_loc})
            lower_bound += min_d
        if cost_so_far + lower_bound >= best_cost:
            return

        # Acciones: entregar a un destino no entregado si hay capacidad
        if rem_cap > 0:
            for dest in undelivered:
                dist = shortest_dist[current_loc][dest]
                new_cost = cost_so_far + dist
                new_route = route_so_far + [dest]
                backtrack(dest, delivered | {dest}, rem_cap - 1, new_cost, new_route)

        # O recargar en un punto de recarga
        for rec in recargas:
            if rec == current_loc:
                continue  # Ya estamos aquí, pero permitir recargar si capacidad < capacidad
            dist = shortest_dist[current_loc][rec]
            new_cost = cost_so_far + dist
            new_route = route_so_far + [rec]
            backtrack(rec, delivered, capacidad, new_cost, new_route)

    backtrack(deposito, frozenset(), capacidad, 0.0, [deposito])
    return best_cost, best_route

def evaluate_hub_subset(p: Problema, shortest_dist, subset_hubs):
    """Calcula costo total para un subconjunto de hubs activos."""
    activation_cost = sum(h.costo_activacion for h in subset_hubs)
    active_nodes = [h.id_nodo for h in subset_hubs]
    distancia, ruta = backtracking_route(p, shortest_dist, active_nodes)
    return distancia + activation_cost, distancia, activation_cost, ruta

def find_best_configuration(p: Problema, shortest_dist, time_limit=30.0):
    hubs = p.hubs
    best = (float('inf'), None, None, None)  # (coste, subset, detalle, ruta)
    start_t = time.time()
    for subset in enumerate_hub_subsets(hubs):
        if time.time() - start_t > time_limit:
            break
        total_cost, dist_only, act_cost, ruta = evaluate_hub_subset(p, shortest_dist, subset)
        if total_cost < best[0]:
            best = (total_cost, subset, (dist_only, act_cost), ruta)
    return best

def main():
    if len(sys.argv) != 2:
        print("Fallo")
        sys.exit(1)

    nombre = sys.argv[1]
    if not nombre.lower().endswith('.txt'):
        nombre = nombre + '.txt'

    # intentar como ruta relativa al directorio del script si no existe en cwd
    if not os.path.isabs(nombre) and not os.path.exists(nombre):
        posible = os.path.join(os.path.dirname(__file__), nombre)
        if os.path.exists(posible):
            nombre = posible

    problema = leer_archivo(nombre)
    if problema is None:
        print("Fallo")
        sys.exit(1)

    # 1) construir grafo euclidiano completo
    build_euclidean_graph(problema)

    # 2) Floyd–Warshall para distancias mínimas
    shortest = floyd_warshall(problema)

    # 3) probar subconjuntos de hubs y simular reparto
    start_time = time.time()
    mejor_coste, mejor_subset, detalle, mejor_ruta = find_best_configuration(problema, shortest, time_limit=30.0)
    elapsed = time.time() - start_time

    # preparar métricas para escritura
    if mejor_subset is None:
        dist_only = 0.0
        act_cost = 0.0
        mejor_ruta = [problema.deposito_id, problema.deposito_id]
        mejor_coste = float('inf')
    else:
        dist_only, act_cost = detalle

    # escribir solucion.txt en el mismo directorio del script
    salida_path = os.path.join(os.path.dirname(__file__), "solucion.txt")
    with open(salida_path, "w", encoding="utf-8") as f:
        f.write("// --- HUBS ACTIVADOS ---\n")
        if mejor_subset:
            for h in mejor_subset:
                f.write(f"{h.id_nodo}\n")
        f.write("\n// --- RUTA OPTIMA ---\n")
        ruta_str = " -> ".join(str(n) for n in mejor_ruta)
        f.write(ruta_str + "\n\n")
        f.write(" // --- METRICAS ---\n")
        f.write(f"COSTO_TOTAL : {mejor_coste:.2f}\n")
        f.write(f"DISTANCIA_RECORRIDA : {dist_only:.2f}\n")
        f.write(f"COSTO_HUBS : {act_cost:.2f}\n")
        f.write(f"TIEMPO_EJECUCION : {elapsed:.6f} segundos\n")

    print("Exito")

if __name__ == "__main__":
    main()