#!/usr/bin/env python3
import sys
import os
import math
import itertools
import time
from lector import leer_archivo,Problema

def construir_grafo_euclediano(p: Problema) -> None:
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
    dist = [fila[:] for fila in p.grafo_distancias]
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

def enumerar_subconjuntos_hubs(hubs):
    """Generador de subconjuntos de hubs. Si hay muchos hubs aplica heurística."""
    H = len(hubs)
    if H <= 15:
        # enumerar todos.

        #yield crea una función generadora que, en lugar de detenerse al terminar (como return), 
        # pausa su ejecución y guarda su estado. Cuando se vuelve a llamar, se reanuda desde donde se quedó, 
        # permitiendo generar valores uno por uno bajo demanda, sin tener que almacenar todos en memoria a la vez. 
        for mask in range(1<<H):
            yield [hubs[i] for i in range(H) if (mask>>i)&1]
    else:
        # heurística: tomar los hubs más baratos y generar combinaciones pequeñas
        hubs_ordenados = sorted(hubs, key=lambda h: h.costo_activacion)
        considerar = hubs_ordenados[:min(12, H)]
        for r in range(0, 5):  # combinaciones de tamaño 0..4
            for comb in itertools.combinations(considerar, r):
                yield list(comb)

def ruta_backtracking(p: Problema, distancia_mas_corta, active_hub_nodes):
    """Usa backtracking para encontrar la ruta óptima del camión.
    Retorna (distancia_total, ruta_lista)"""
    deposito = p.deposito_id
    destinos = frozenset(paq.id_nodo_destino for paq in p.paquetes)
    recargas = frozenset(active_hub_nodes) | {deposito}
    capacidad = p.capacidad_camion

    mejor_costo = float('inf')
    mejor_ruta = None

    def backtrack(posicion_actual, entregado, capacidad_restante, costo_actual, ruta_actual):
        nonlocal mejor_costo, mejor_ruta

        if costo_actual >= mejor_costo:
            return

        if len(entregado) == len(destinos):
            # Todos entregados, volver al depósito si no estamos ahí
            if posicion_actual != deposito:
                cost_to_depot = distancia_mas_corta[posicion_actual][deposito]
                total_cost = costo_actual + cost_to_depot
                if total_cost < mejor_costo:
                    mejor_costo = total_cost
                    mejor_ruta = ruta_actual + [deposito]
            else:
                if costo_actual < mejor_costo:
                    mejor_costo = costo_actual
                    mejor_ruta = ruta_actual[:]
            return

        # Cota inferior: suma de distancias mínimas a destinos no entregados
        no_entregado = destinos - entregado
        limite_inferior = 0.0
        for dest in no_entregado:
            min_d = min(distancia_mas_corta[loc][dest] for loc in recargas | {posicion_actual})
            limite_inferior += min_d
        if costo_actual + limite_inferior >= mejor_costo:
            return

        # Acciones: entregar a un destino no entregado si hay capacidad
        if capacidad_restante > 0:
            for dest in no_entregado:
                dist = distancia_mas_corta[posicion_actual][dest]
                costo_nuevo = costo_actual + dist
                nueva_ruta = ruta_actual + [dest]
                backtrack(dest, entregado | {dest}, capacidad_restante - 1, costo_nuevo, nueva_ruta)

        # O recargar en un punto de recarga
        for rec in recargas:
            if rec == posicion_actual:
                continue  # Ya estamos aquí, pero permitir recargar si capacidad < capacidad
            dist = distancia_mas_corta[posicion_actual][rec]
            costo_nuevo = costo_actual + dist
            nueva_ruta = ruta_actual + [rec]
            backtrack(rec, entregado, capacidad, costo_nuevo, nueva_ruta)

    backtrack(deposito, frozenset(), capacidad, 0.0, [deposito])
    return mejor_costo, mejor_ruta

def evaluar_subconjuntos_hubs(p: Problema, distancia_mas_corta, subconjunto_hubs):
    """Calcula costo total para un subconjunto de hubs activos."""
    costo_de_activacion = sum(h.costo_activacion for h in subconjunto_hubs)
    nodos_activos = [h.id_nodo for h in subconjunto_hubs]
    distancia, ruta = ruta_backtracking(p, distancia_mas_corta, nodos_activos)
    return distancia + costo_de_activacion, distancia, costo_de_activacion, ruta

def encontrar_mejor_combinacion(p: Problema, distancia_mas_corta, limite_de_tiempo=30.0):
    hubs = p.hubs
    mejor = (float('inf'), None, None, None)  # (coste, subset, detalle, ruta)
    empezar_timer = time.time()
    for subconjunto in enumerar_subconjuntos_hubs(hubs):
        if time.time() - empezar_timer > limite_de_tiempo:
            break
        coste_total, dist_solo, costo_activacion, ruta = evaluar_subconjuntos_hubs(p, distancia_mas_corta, subconjunto)
        if coste_total < mejor[0]:
            mejor = (coste_total, subconjunto, (dist_solo, costo_activacion), ruta)
    return mejor

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
    construir_grafo_euclediano(problema)

    # 2) Floyd–Warshall para distancias mínimas
    mas_corto = floyd_warshall(problema)

    # 3) probar subconjuntos de hubs y simular reparto
    tiempoDeInicio = time.time()
    mejor_coste, mejor_subconjunto, detalle, mejor_ruta = encontrar_mejor_combinacion(problema, mas_corto, limite_de_tiempo=30.0)
    transcurrido = time.time() - tiempoDeInicio

    # preparar métricas para escritura
    if mejor_subconjunto is None:
        solo_distancia = 0.0
        coste_activacion = 0.0
        mejor_ruta = [problema.deposito_id, problema.deposito_id]
        mejor_coste = float('inf')
    else:
        solo_distancia, coste_activacion = detalle

    # escribir solucion.txt en el mismo directorio del script
    salida_path = os.path.join(os.path.dirname(__file__), "solucion.txt")
    with open(salida_path, "w", encoding="utf-8") as f:
        f.write("// --- HUBS ACTIVADOS ---\n")
        if mejor_subconjunto:
            for h in mejor_subconjunto:
                f.write(f"{h.id_nodo}\n")
        f.write("\n// --- RUTA OPTIMA ---\n")
        ruta_str = " -> ".join(str(n) for n in mejor_ruta)
        f.write(ruta_str + "\n\n")
        f.write(" // --- METRICAS ---\n")
        f.write(f"COSTO_TOTAL : {mejor_coste:.2f}\n")
        f.write(f"DISTANCIA_RECORRIDA : {solo_distancia:.2f}\n")
        f.write(f"COSTO_HUBS : {coste_activacion:.2f}\n")
        f.write(f"TIEMPO_EJECUCION : {transcurrido:.6f} segundos\n")

    print("Exito")

if __name__ == "__main__":
    main()