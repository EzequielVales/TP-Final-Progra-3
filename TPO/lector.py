#!/usr/bin/env python3

import sys
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Nodo:
    id: int
    x: int
    y: int


@dataclass
class Hub:
    id_nodo: int
    costo_activacion: float


@dataclass
class Paquete:
    id: int
    id_nodo_origen: int
    id_nodo_destino: int


class Problema:
    def __init__(self):
        self.num_nodos: int = 0
        self.num_hubs: int = 0
        self.num_paquetes: int = 0
        self.capacidad_camion: int = 0
        self.deposito_id: int = 0
        
        self.nodos: List[Nodo] = []
        self.hubs: List[Hub] = []
        self.paquetes: List[Paquete] = []
        self.grafo_distancias: List[List[float]] = []


def eliminar_comentario(linea: str) -> str:
    """Elimina comentarios de una línea."""
    if "//" in linea:
        return linea[:linea.index("//")].strip()
    return linea.strip()


def leer_archivo(nombre_archivo: str) -> Optional[Problema]:
    """Lee un archivo de problema y retorna un objeto Problema."""
    try:
        with open(nombre_archivo, 'r') as f:
            lineas = f.readlines()
    except FileNotFoundError:
        print(f"Error: No se pudo abrir el archivo '{nombre_archivo}'")
        return None

    p = Problema()

    # --- LEER CONFIGURACIÓN (primeras líneas) ---
    idx = 0
    while idx < len(lineas):
        linea = eliminar_comentario(lineas[idx])
        
        if not linea:
            idx += 1
            continue
        
        if linea.startswith("NODOS"):
            p.num_nodos = int(linea.split()[1])
        elif linea.startswith("HUBS"):
            p.num_hubs = int(linea.split()[1])
        elif linea.startswith("PAQUETES"):
            p.num_paquetes = int(linea.split()[1])
        elif linea.startswith("CAPACIDAD_CAMION"):
            p.capacidad_camion = int(linea.split()[1])
        elif linea.startswith("DEPOSITO_ID"):
            p.deposito_id = int(linea.split()[1])
            idx += 1
            break  # <-- BREAK aquí después de encontrar DEPOSITO_ID
        
        idx += 1

    # Inicializar matriz de distancias
    p.grafo_distancias = [[0.0 for _ in range(p.num_nodos)] for _ in range(p.num_nodos)]

    # --- ENCONTRAR Y LEER CADA SECCIÓN ---
    
    # Buscar encabezado de NODOS
    start_nodos = -1
    for i in range(idx, len(lineas)):
        if "NODOS" in lineas[i] and "---" in lineas[i]:
            start_nodos = i + 1
            break
    
    # Leer NODOS
    if start_nodos > 0:
        nodos_leidos = 0
        for i in range(start_nodos, len(lineas)):
            if nodos_leidos >= p.num_nodos:
                break
            linea = eliminar_comentario(lineas[i])
            if not linea:
                continue
            try:
                partes = linea.split()
                nodo = Nodo(id=int(partes[0]), x=int(partes[1]), y=int(partes[2]))
                p.nodos.append(nodo)
                nodos_leidos += 1
            except (ValueError, IndexError):
                pass

    # Buscar encabezado de HUBS
    start_hubs = -1
    for i in range(len(lineas)):
        if "HUBS" in lineas[i] and "---" in lineas[i]:
            start_hubs = i + 1
            break
    
    # Leer HUBS
    if start_hubs > 0:
        hubs_leidos = 0
        for i in range(start_hubs, len(lineas)):
            if hubs_leidos >= p.num_hubs:
                break
            linea = eliminar_comentario(lineas[i])
            if not linea:
                continue
            try:
                partes = linea.split()
                hub = Hub(id_nodo=int(partes[0]), costo_activacion=float(partes[1]))
                p.hubs.append(hub)
                hubs_leidos += 1
            except (ValueError, IndexError):
                pass

    # Buscar encabezado de PAQUETES
    start_paquetes = -1
    for i in range(len(lineas)):
        if "PAQUETES" in lineas[i] and "---" in lineas[i]:
            start_paquetes = i + 1
            break
    
    # Leer PAQUETES
    if start_paquetes > 0:
        paquetes_leidos = 0
        for i in range(start_paquetes, len(lineas)):
            if paquetes_leidos >= p.num_paquetes:
                break
            linea = eliminar_comentario(lineas[i])
            if not linea:
                continue
            try:
                partes = linea.split()
                paquete = Paquete(id=int(partes[0]), 
                                 id_nodo_origen=int(partes[1]), 
                                 id_nodo_destino=int(partes[2]))
                p.paquetes.append(paquete)
                paquetes_leidos += 1
            except (ValueError, IndexError):
                pass

    # Buscar encabezado de ARISTAS
    start_aristas = -1
    for i in range(len(lineas)):
        if "ARISTAS" in lineas[i] and "---" in lineas[i]:
            start_aristas = i + 1
            break
    
    # Leer ARISTAS
    if start_aristas > 0:
        for i in range(start_aristas, len(lineas)):
            linea = eliminar_comentario(lineas[i])
            if not linea:
                continue
            try:
                partes = linea.split()
                if len(partes) >= 3:
                    u, v, peso = int(partes[0]), int(partes[1]), float(partes[2])
                    if u < p.num_nodos and v < p.num_nodos:
                        p.grafo_distancias[u][v] = peso
                        p.grafo_distancias[v][u] = peso
            except (ValueError, IndexError):
                pass

    return p


def imprimir_problema(p: Problema) -> None:
    """Imprime un resumen del problema cargado."""
    print("\n============== RESUMEN DEL PROBLEMA CARGADO ===============")
    
    print("\n--- CONFIGURACION ---")
    print(f"Total de Nodos:\t\t{p.num_nodos}")
    print(f"Total de Hubs:\t\t{p.num_hubs}")
    print(f"Total de Paquetes:\t{p.num_paquetes}")
    print(f"Capacidad del Camión:\t{p.capacidad_camion}")
    print(f"ID del Depósito:\t\t{p.deposito_id}")
    
    print("\n--- NODOS ---")
    for nodo in p.nodos:
        print(f"  Nodo {nodo.id:2d}: (x={nodo.x:4d}, y={nodo.y:4d})")
    
    print("\n--- HUBS ---")
    for hub in p.hubs:
        print(f"  Hub en Nodo {hub.id_nodo:2d}: Costo de Activación = {hub.costo_activacion:.2f}")
    
    print("\n--- PAQUETES ---")
    for paquete in p.paquetes:
        print(f"  Paquete {paquete.id:2d}: Origen={paquete.id_nodo_origen} -> Destino={paquete.id_nodo_destino}")
    
    print("\n--- MUESTRA DEL GRAFO (MATRIZ DE ADYACENCIA) ---")
    
    print("      ", end="")
    for j in range(min(10, p.num_nodos)):
        print(f"{j:7d} ", end="")
    print()
    
    print("----", end="")
    for j in range(min(10, p.num_nodos)):
        print("--------", end="")
    print()
    
    for i in range(min(10, p.num_nodos)):
        print(f"{i:4d}| ", end="")
        for j in range(min(10, p.num_nodos)):
            print(f"{p.grafo_distancias[i][j]:7.2f} ", end="")
        print()
    
    print("===========================================================\n")


def main():
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <nombre_del_archivo.txt>")
        sys.exit(1)

    nombre_archivo = sys.argv[1]
    print(f"Leyendo el archivo de problema: {nombre_archivo}")

    problema = leer_archivo(nombre_archivo)
    if problema is None:
        print("\n>> Hubo un error al leer o procesar el archivo. Revisa el formato.")
        sys.exit(1)

    print("\n¡Archivo leído y procesado con éxito!")
    imprimir_problema(problema)
    print("Memoria liberada correctamente.")


if __name__ == "__main__":
    main()
