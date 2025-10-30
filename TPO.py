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

def simulate_routes_cost(p: Problema, shortest_dist, active_hub_nodes, capacidad):
    """Simula rutas del camión de forma greedy para servir todos los paquetes.
    Retorna (distancia_total, ruta_lista)"""
    deposito = p.deposito_id
    destinos = [paq.id_nodo_destino for paq in p.paquetes]
    pendientes = list(destinos)
    distancia_total = 0.0
    # puntos de recarga permitidos
    recargas = set(active_hub_nodes) | {deposito}

    # función auxiliar para distancia entre dos nodos
    def d(a,b): return shortest_dist[a][b]

    current_start = deposito
    route = [deposito]
    # mientras queden paquetes por entregar
    while pendientes:
        # cargar hasta capacidad: elegir por proximidad al punto de partida (greedy)
        trip = []
        carga = 0
        remaining = pendientes[:]
        # seleccionar destinos más cercanos a current_start hasta llenar
        remaining.sort(key=lambda x: d(current_start, x))
        while carga < capacidad and remaining:
            node = remaining.pop(0)
            trip.append(node)
            pendientes.remove(node)
            carga += 1

        # recorrer el trip en orden greedy (nearest neighbor)
        pos = current_start
        for dest in trip:
            distancia_total += d(pos, dest)
            route.append(dest)
            pos = dest
        # al terminar el trip, volver al punto de recarga más cercano (debe ser depósito o hub activo)
        mejor_recarga = min(recargas, key=lambda r: d(pos, r))
        distancia_total += d(pos, mejor_recarga)
        # si la recarga es diferente del punto actual, anotar en la ruta
        if route[-1] != mejor_recarga:
            route.append(mejor_recarga)
        current_start = mejor_recarga

    # asegurar que la ruta termine en el depósito
    if route[-1] != deposito:
        distancia_total += d(route[-1], deposito)
        route.append(deposito)

    return distancia_total, route

def evaluate_hub_subset(p: Problema, shortest_dist, subset_hubs):
    """Calcula costo total para un subconjunto de hubs activos."""
    activation_cost = sum(h.costo_activacion for h in subset_hubs)
    active_nodes = [h.id_nodo for h in subset_hubs]
    distancia, ruta = simulate_routes_cost(p, shortest_dist, active_nodes, p.capacidad_camion)
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