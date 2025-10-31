#!/usr/bin/env python3
import sys
import itertools
import time


def eliminar_comentario(linea: str) -> str:
    """Elimina comentarios y espacios innecesarios de una línea."""
    return linea.split("//")[0].strip()


def leer_seccion(lineas, inicio, cantidad, parser):
    """Lee una sección con un número fijo de líneas y aplica un parser."""
    datos = []
    leidos = 0
    for i in range(inicio, len(lineas)):
        if leidos >= cantidad:
            break
        linea = eliminar_comentario(lineas[i])
        if not linea:
            continue
        try:
            datos.append(parser(linea))
            leidos += 1
        except Exception:
            print(f"Advertencia: línea ignorada -> {linea}")
    return datos


def leer_datos(nombre_archivo: str) -> dict:
    """Lee un archivo de problema y retorna un diccionario con los datos."""
    try:
        with open(nombre_archivo, 'r') as f:
            lineas = f.readlines()
    except FileNotFoundError:
        print(f"Error: No se pudo abrir el archivo '{nombre_archivo}'")
        return None

    datos = {
        'configuracion': {},
        'nodos': {},
        'hubs': {},
        'paquetes': {},
        'aristas': {}
    }

    # --- LEER CONFIGURACIÓN ---
    for i, linea in enumerate(lineas):
        linea = eliminar_comentario(linea)
        if not linea:
            continue
        if linea.startswith("NODOS"):
            datos['configuracion']['num_nodos'] = int(linea.split()[1])
        elif linea.startswith("HUBS"):
            datos['configuracion']['num_hubs'] = int(linea.split()[1])
        elif linea.startswith("PAQUETES"):
            datos['configuracion']['num_paquetes'] = int(linea.split()[1])
        elif linea.startswith("CAPACIDAD_CAMION"):
            datos['configuracion']['capacidad_camion'] = int(linea.split()[1])
        elif linea.startswith("DEPOSITO_ID"):
            datos['configuracion']['deposito_id'] = int(linea.split()[1])
            break  # Termina lectura de configuración

    # --- DETECTAR INICIOS DE SECCIONES ---
    secciones = {}
    for i, linea in enumerate(lineas):
        if "---" in linea:
            parts = linea.split("---")
            if len(parts) > 1:
                nombre = parts[1].strip().split()[0].upper()
                secciones[nombre] = i + 1

    # --- PARSERS ---
    parse_nodo = lambda l: (int(l.split()[0]), {'x': int(l.split()[1]), 'y': int(l.split()[2])})
    parse_hub = lambda l: (int(l.split()[0]), float(l.split()[1]))
    parse_paquete = lambda l: (int(l.split()[0]), {'origen': int(l.split()[1]), 'destino': int(l.split()[2])})
    parse_arista = lambda l: ((int(l.split()[0]), int(l.split()[1])), float(l.split()[2]))

    # --- LEER CADA SECCIÓN ---
    if "NODOS" in secciones:
        nodos_list = leer_seccion(lineas, secciones["NODOS"], datos['configuracion']['num_nodos'], parse_nodo)
        for id_nodo, props in nodos_list:
            tipo = 'entrega'
            if id_nodo == datos['configuracion']['deposito_id']:
                tipo = 'deposito'
            elif id_nodo in [1, 2, 3]:  # Assuming hubs are 1,2,3
                tipo = 'hub'
            datos['nodos'][id_nodo] = {**props, 'tipo': tipo}
    if "HUBS" in secciones:
        hubs_list = leer_seccion(lineas, secciones["HUBS"], datos['configuracion']['num_hubs'], parse_hub)
        for id_hub, costo in hubs_list:
            datos['hubs'][id_hub] = costo
    if "PAQUETES" in secciones:
        paquetes_list = leer_seccion(lineas, secciones["PAQUETES"], datos['configuracion']['num_paquetes'], parse_paquete)
        for id_paq, props in paquetes_list:
            datos['paquetes'][id_paq] = props
    if "ARISTAS" in secciones:
        # Las aristas pueden tener número variable → sin límite de cantidad
        aristas_list = leer_seccion(lineas, secciones["ARISTAS"], float('inf'), parse_arista)
        for edge, peso in aristas_list:
            datos['aristas'][edge] = peso
            # Assuming undirected
            if (edge[1], edge[0]) not in datos['aristas']:
                datos['aristas'][(edge[1], edge[0])] = peso

    return datos


def floyd_warshall(aristas, num_nodos):
    """Calcula las distancias mínimas entre todos los pares de nodos usando Floyd-Warshall."""
    grafo = [[float('inf')] * num_nodos for _ in range(num_nodos)]

    # Diagonal a 0
    for i in range(num_nodos):
        grafo[i][i] = 0

    # Cargar aristas (asumiendo grafo no dirigido)
    for (n1, n2), peso in aristas.items():
        grafo[n1][n2] = peso
        grafo[n2][n1] = peso

    # Aplicar Floyd-Warshall
    for k in range(num_nodos):
        for i in range(num_nodos):
            for j in range(num_nodos):
                if grafo[i][k] != float('inf') and grafo[k][j] != float('inf'):
                    grafo[i][j] = min(grafo[i][j], grafo[i][k] + grafo[k][j])

    return grafo


def calcularMejorCamino(datos, grafo):
    """Encuentra la mejor combinación de hubs activados y ruta del camión para minimizar el costo total."""
    deposito = datos['configuracion']['deposito_id']
    hubs = list(datos['hubs'].keys())
    capacidad = datos['configuracion']['capacidad_camion']
    costosHubs = datos['hubs']

    # Agrupar paquetes por destino
    paquetesPorNodo = {}
    for id_paq, paq in datos['paquetes'].items():
        dest = paq['destino']
        paquetesPorNodo[dest] = paquetesPorNodo.get(dest, 0) + 1

    # Inicializar mejores valores
    mejor_costo = float('inf')
    mejor_hubs = []
    mejor_dist = 0
    mejor_ruta = []

    def backtrack(index, activados):
        nonlocal mejor_costo, mejor_hubs, mejor_dist, mejor_ruta
        if index == len(hubs):
            # calcular costo
            hubs_act = [h for h in hubs if activados[h]]
            costo_h = sum(costosHubs[h] for h in hubs_act)
            dist_total = 0
            ruta = [deposito]
            # Agrupar destinos en viajes
            destinos = sorted(paquetesPorNodo.keys())
            viajes = []
            i = 0
            while i < len(destinos):
                viaje = []
                suma = 0
                while i < len(destinos) and suma + paquetesPorNodo[destinos[i]] <= capacidad:
                    viaje.append(destinos[i])
                    suma += paquetesPorNodo[destinos[i]]
                    i += 1
                viajes.append(viaje)
            # Para cada viaje, calcular distancia y ruta
            for viaje in viajes:
                if not viaje:
                    continue
                # elegir mejor punto_partida
                min_costo_viaje = float('inf')
                mejor_punto = deposito
                for punto in [deposito] + hubs_act:
                    dist_viaje = grafo[punto][viaje[0]]
                    for j in range(len(viaje)-1):
                        dist_viaje += grafo[viaje[j]][viaje[j+1]]
                    dist_viaje += grafo[viaje[-1]][deposito]
                    if dist_viaje < min_costo_viaje:
                        min_costo_viaje = dist_viaje
                        mejor_punto = punto
                dist_total += min_costo_viaje
                # agregar a ruta
                if mejor_punto != deposito:
                    ruta.append(mejor_punto)
                for d in viaje:
                    ruta.append(d)
                ruta.append(deposito)
            costo_total = dist_total + costo_h
            if costo_total < mejor_costo:
                mejor_costo = costo_total
                mejor_hubs = hubs_act[:]
                mejor_dist = dist_total
                mejor_ruta = ruta[:]
            return

        # no activar
        backtrack(index + 1, activados)
        # activar
        activados[hubs[index]] = True
        backtrack(index + 1, activados)
        activados[hubs[index]] = False

    activados = {h: False for h in hubs}
    backtrack(0, activados)

    ruta_optima = mejor_ruta
    costo_total = mejor_costo
    distancia_recorrida = mejor_dist
    costo_hubs = costo_total - distancia_recorrida
    return ruta_optima, mejor_hubs, costo_total, distancia_recorrida, costo_hubs


def main():
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <nombre_del_archivo.txt>")
        sys.exit(1)

    nombre_archivo = sys.argv[1]

    start_time = time.time()

    datos = leer_datos(nombre_archivo)
    if datos is None:
        print("\n>> Hubo un error al leer o procesar el archivo. Revisa el formato.")
        sys.exit(1)

    # Calcular distancias mínimas usando Floyd-Warshall
    num_nodos = datos['configuracion']['num_nodos']
    grafo = floyd_warshall(datos['aristas'], num_nodos)

    # Calcular la mejor ruta
    ruta_optima, mejor_hubs, costo_total, distancia_recorrida, costo_hubs = calcularMejorCamino(datos, grafo)

    end_time = time.time()
    tiempo_ejecucion = end_time - start_time

    # Escribir a solucion.txt
    with open('solucion.txt', 'w') as f:
        f.write("// --- HUBS ACTIVADOS ---\n")
        for hub in mejor_hubs:
            f.write(f"{hub}\n")
        f.write("\n// --- RUTA OPTIMA ---\n")
        f.write(" -> ".join(map(str, ruta_optima)) + "\n")
        f.write("\n// --- METRICAS ---\n")
        f.write(f"COSTO_TOTAL: {costo_total:.2f}\n")
        f.write(f"DISTANCIA_RECORRIDA: {distancia_recorrida:.2f}\n")
        f.write(f"COSTO_HUBS: {costo_hubs:.2f}\n")
        f.write(f"TIEMPO_EJECUCION: {tiempo_ejecucion:.6f} segundos\n")


if __name__ == "__main__":
    main()
