"""
=========

Visualización de las soluciones del modelo de ``modelo.py``.

No calcula nada nuevo: toda la información ya está en la solución. De
``sol["x"]`` sale el flujo de cada arco en cada capa temporal y de ``sol["y"]``
si cada movimiento tiene verde o rojo. Las tres figuras son maneras distintas
de mirar esos mismos datos.

    from instancias import corredor
    from modelo import ejecutar
    from visual import graficar

    r = ejecutar(corredor())
    graficar(r, corredor=[("P1", ("e1O", "s1E")), ("P2", ("e2O", "s2E"))])

Las tres figuras:

``diagrama_estatico``
    La red con el flujo agregado de cada arco. El grosor de la línea es
    proporcional al flujo y los movimientos semaforizados van en color.

``animacion_red``
    Un cuadro por capa temporal, con los movimientos en verde o rojo según la
    fase activa y el tamaño de cada nodo proporcional a su cola. Se guarda
    como GIF.

``diagrama_espacio_tiempo``
    El diagrama clásico de coordinación: tiempo en el eje horizontal, posición
    a lo largo del corredor en el vertical, y las bandas de verde de cada
    intersección. Si el plan coordina, las bandas se alinean sobre las
    trayectorias y se ve la onda verde.
"""

from __future__ import annotations

import heapq
import math
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyArrowPatch, Rectangle

Punto = Tuple[float, float]

# --- carpetas donde se guardan las figuras -----------------------------------
#  Se resuelven relativas a la ubicación de este archivo, de modo que funcionan
#  sin importar desde dónde se corra Python. Si a una función se le pasa un
#  nombre con carpeta, esa ruta se respeta tal cual y estas no se aplican.
_BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_GIF = os.path.join(_BASE, "Visuales gif")      # animación con vehículos
CARPETA_OTROS = os.path.join(_BASE, "Visuales otros")  # las demás figuras


def _ruta(archivo: str, carpeta: str) -> str:
    """Resuelve el nombre del archivo dentro de la carpeta que corresponda."""
    if os.path.dirname(archivo):
        return archivo                     # ruta explícita: se respeta
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, archivo)


def _mostrar(ruta: str) -> str:
    """Ruta acortada para imprimir."""
    try:
        return os.path.relpath(ruta)
    except ValueError:
        return ruta


# --- colores -----------------------------------------------------------------
C_VERDE = "#2e8b57"
C_ROJO = "#c0392b"
C_CALLE = "#95a5a6"
C_FLUJO = "#2c3e50"
C_NODO = "#ffb6c1"          
C_TEXTO = "#2c3e50"

# --- geometría del subgrafo de una esquina -----------------------------------
#  Réplica de la figura de la tesis: por cada rama, el nodo de acceso queda a
#  la derecha del sentido de circulación y el de salida enfrentado.
SEP, DIST, BORDE = 0.16, 0.30, 0.55

OFFSET: Dict[Tuple[str, str], Punto] = {
    ("N", "e"): (-SEP, DIST), ("N", "s"): (SEP, DIST),
    ("S", "e"): (SEP, -DIST), ("S", "s"): (-SEP, -DIST),
    ("E", "e"): (DIST, SEP), ("E", "s"): (DIST, -SEP),
    ("O", "e"): (-DIST, -SEP), ("O", "s"): (-DIST, SEP),
}


# =============================================================================
#  Posiciones de los nodos
# =============================================================================
#  Las instancias generadas traen su geometría en el nombre de la esquina
#  ("I<fila><columna>"). Las escritas a mano no, así que se listan acá.

CENTROS_CORREDOR = {"P1": (0.0, 0.0), "P2": (1.6, 0.0),
                    "c1": (0.0, 1.2), "c2": (1.6, 1.2)}

# El corredor no usa la convención "<esquina>_e<rama>", así que se traduce.
NODOS_CORREDOR = {
    "e1O": ("P1", "e", "O"), "s1E": ("P1", "s", "E"),
    "e1S": ("P1", "e", "S"), "s1N": ("P1", "s", "N"),
    "e2O": ("P2", "e", "O"), "s2E": ("P2", "s", "E"),
    "e2N": ("P2", "e", "N"), "s2S": ("P2", "s", "S"),
}

EXTERNOS_CORREDOR = {"oO": (-0.9, -SEP), "oS": (SEP, -0.9),
                     "dE": (2.5, -SEP), "dS": (1.6 - SEP, -0.9)}

CENTROS_RED = {
    "F1": (0.0, 0.0), "F2": (0.0, -1.0), "F3": (0.0, -2.0),
    "A1": (1.0, 0.0), "A2": (1.0, -1.0), "A3": (1.0, -2.0),
    "C1": (2.0, 0.0), "C2": (2.0, -1.0), "C3": (2.0, -2.0),
    "B1": (3.0, 0.0), "B2": (3.0, -1.0), "B3": (3.0, -2.0),
}

#  Bernal Este. La grilla del barrio: columnas de oeste a este (Lomas, Z1,
#  La Paz, Juncal, Victoria, Tacuari, Ramella, Constitución, Z2, Almafuerte,
#  Güemes, Estrada, Espora, Z4/Z5, Roque, Dean Funes, Independencia) y filas
#  de norte a sur (Caseros, San Luis, Carabelas, Ciudadela, Roca corta, Roca,
#  Chiclana, Cramer, Uriburu). Z1 y Z2 son puntos a mitad de cuadra sobre
#  Caseros, por eso tienen columna propia.
CENTROS_BERNAL_ESTE = {
    # --- Caseros ---
    "A1": (0.0, 0.0), "Z1": (1.0, 0.0), "B1": (2.0, 0.0), "D1": (4.0, 0.0),
    "E1": (5.0, 0.0), "F1": (6.0, 0.0), "G1": (7.0, 0.0), "Z2": (8.0, 0.0),
    "H1": (9.0, 0.0), "K1": (12.0, 0.0), "L1": (14.0, 0.0),
    "M1": (15.0, 0.0), "N1": (16.0, 0.0),
    # --- San Luis ---
    "G2": (7.0, -1.0), "H2": (9.0, -1.0), "K2": (12.0, -1.0),
    "L2": (14.0, -1.0), "M2": (15.0, -1.0), "N2": (16.0, -1.0),
    # --- Carabelas ---
    "A2": (0.0, -2.0), "B2": (2.0, -2.0), "D2": (4.0, -2.0),
    "E2": (5.0, -2.0), "F2": (6.0, -2.0), "G3": (7.0, -2.0),
    "H3": (9.0, -2.0), "K3": (12.0, -2.0), "L3": (14.0, -2.0),
    "M3": (15.0, -2.0), "N3": (16.0, -2.0),
    # --- Ciudadela ---
    "A3": (0.0, -3.0), "B3": (2.0, -3.0), "D3": (4.0, -3.0),
    "E3": (5.0, -3.0), "F3": (6.0, -3.0), "G4": (7.0, -3.0),
    "H4": (9.0, -3.0), "L4": (14.0, -3.0), "M4": (15.0, -3.0),
    "N4": (16.0, -3.0),
    # --- Roca corta ---
    "A4": (0.0, -4.0), "N5": (16.0, -4.0),
    # --- Roca ---
    "A5": (0.0, -5.0), "B4": (2.0, -5.0), "C1": (3.0, -5.0),
    "D4": (4.0, -5.0), "E4": (5.0, -5.0), "F4": (6.0, -5.0),
    "G5": (7.0, -5.0), "H5": (9.0, -5.0), "L5": (14.0, -5.0),
    "M5": (15.0, -5.0), "N6": (16.0, -5.0),
    # --- Chiclana ---
    "A6": (0.0, -6.0), "B5": (2.0, -6.0), "C2": (3.0, -6.0),
    "D5": (4.0, -6.0), "E5": (5.0, -6.0), "F5": (6.0, -6.0),
    "G6": (7.0, -6.0), "H6": (9.0, -6.0), "Z12": (12.0, -6.0),
    "L6": (14.0, -6.0), "M6": (15.0, -6.0), "N7": (16.0, -6.0),
    # --- Cramer ---
    "A7": (0.0, -7.0), "B6": (2.0, -7.0), "C3": (3.0, -7.0),
    "D6": (4.0, -7.0), "E6": (5.0, -7.0), "F6": (6.0, -7.0),
    "G7": (7.0, -7.0), "H7": (9.0, -7.0), "I1": (10.0, -7.0),
    "J1": (11.0, -7.0), "K4": (12.0, -7.0), "Z5": (13.0, -7.0),
    "L7": (14.0, -7.0),
    # --- Uriburu ---
    "A8": (0.0, -8.0), "B7": (2.0, -8.0), "C4": (3.0, -8.0),
    "D7": (4.0, -8.0), "E7": (5.0, -8.0), "F7": (6.0, -8.0),
    "G8": (7.0, -8.0), "H8": (9.0, -8.0), "I2": (10.0, -8.0),
    "J2": (11.0, -8.0), "K5": (12.0, -8.0), "Z4": (13.0, -8.0),
    "L8": (14.0, -8.0), "M7": (15.0, -8.0), "N8": (16.0, -8.0),
}

EXTERNOS_RED = {
    "oF": (0.0, 0.7), "dF": (0.0, -2.7),
    "oAN": (0.8, 0.7), "dAN": (1.2, 0.7),
    "dAS": (0.8, -2.7), "oAS": (1.2, -2.7),
    "dC": (2.0, 0.7), "oC": (2.0, -2.7),
    "oB": (3.0, 0.7), "dB": (3.0, -2.7),
    "oT1": (-0.7, 0.0), "dT1": (3.7, 0.0),
    "dT2": (-0.7, -1.0), "oT2": (3.7, -1.0),
    "oT3": (-0.7, -2.0), "dT3": (3.7, -2.0),
}

#  Bernal Centro. Columnas de oeste a este: Cerrito, Zeballos, Blandengues,
#  Leandro N. Alem, Ameghino, Avellaneda, 25 de Mayo, Z9, 9 de Julio, Castro
#  Barros, Don Bosco, Zapiola. Filas de norte a sur: San Martín, Coronel
#  Pringles, Rawson, Belgrano. Z7/Z8 y Z9 son puntos a mitad de cuadra.
CENTROS_BERNAL_CENTRO = {
    # --- San Martín ---
    "X1": (0.0, 0.0), "O1": (1.0, 0.0), "Z7": (2.0, 0.0), "P1": (3.0, 0.0),
    "Q1": (4.0, 0.0), "R1": (5.0, 0.0), "S1": (6.0, 0.0), "Z9": (7.0, 0.0),
    "T1": (8.0, 0.0), "U1": (9.0, 0.0), "V1": (10.0, 0.0), "W1": (11.0, 0.0),
    # --- Coronel Pringles ---
    "X2": (0.0, -1.0), "O2": (1.0, -1.0), "Z8": (2.0, -1.0),
    "P2": (3.0, -1.0), "Q2": (4.0, -1.0), "R2": (5.0, -1.0),
    "S2": (6.0, -1.0), "W2": (11.0, -1.0),
    # --- Rawson ---
    "W3": (11.0, -2.0),
    # --- Belgrano ---
    "X3": (0.0, -3.0), "O3": (1.0, -3.0), "P3": (3.0, -3.0),
    "Q3": (4.0, -3.0), "R3": (5.0, -3.0), "S3": (6.0, -3.0),
    "T2": (8.0, -3.0), "U2": (9.0, -3.0), "V2": (10.0, -3.0),
    "W4": (11.0, -3.0),
}

EXTERNOS_BERNAL_CENTRO = {
    "oX1": (-0.60, -0.16), "dX1": (-0.60, 0.16), "oW1": (11.60, -0.16),
    "dW1": (11.60, 0.16), "oX2": (-0.60, -1.00), "oW2": (11.60, -1.00),
    "dW3": (11.60, -2.00), "dX3": (-0.60, -3.00), "oZ10": (11.60, -2.84),
    "dZ10": (11.60, -3.16), "oQ1": (3.84, 0.60), "dZ9": (7.16, 0.60),
    "oZ6": (0.16, -3.60), "dZ6": (-0.16, -3.60), "dO3": (1.00, -3.60),
    "oP3": (3.00, -3.60), "dQ3": (4.00, -3.60), "oR3": (5.16, -3.60),
    "dR3": (4.84, -3.60), "dS3": (6.00, -3.60), "oT2": (8.00, -3.60),
    "dU2": (9.00, -3.60), "oV2": (10.00, -3.60), "oW4": (11.16, -3.60),
    "dW4": (10.84, -3.60),
}

def _partir(nodo: str) -> Optional[Tuple[str, str, str]]:
    """Separa '<esquina>_e<rama>' en (esquina, tipo, rama)."""
    if "_" not in nodo:
        return None
    base, marca = nodo.rsplit("_", 1)
    if len(marca) >= 2 and marca[0] in ("e", "s") and marca[1:] in ("N", "S", "E", "O"):
        return base, marca[0], marca[1:]
    return None

def _centros(inst) -> Dict[str, Punto]:
    """Centro de cada esquina de la instancia."""
    if inst.nombre.startswith("corredor"):
        return dict(CENTROS_CORREDOR)
    if inst.nombre.startswith("bernal-centro"):
        return dict(CENTROS_BERNAL_CENTRO)
    if inst.nombre.startswith("bernal-este"):
        return dict(CENTROS_BERNAL_ESTE)
    if inst.nombre.startswith("red"):
        return dict(CENTROS_RED)

    # Instancias generadas por generador_red: la esquina se llama con la letra
    # de su columna y el número de su fila, por ejemplo "B2" o "AA12".
    centros = {}
    esquinas = list(inst.X) + list(inst.esq_libres)
    for p in esquinas:
        m = re.fullmatch(r"([A-Z]+)(\d+)", p)
        if m:
            columna = 0
            for letra in m.group(1):
                columna = columna * 26 + (ord(letra) - ord("A") + 1)
            centros[p] = (float(columna - 1), -float(int(m.group(2)) - 1))
    return centros


def posiciones(inst) -> Dict[str, Punto]:
    """Coordenadas de todos los nodos de la red física.

    Los nodos del subgrafo de una esquina se ubican alrededor de su centro
    siguiendo la geometría de la figura de la tesis. Los nodos externos se
    colocan más allá del nodo al que se conectan, en la misma dirección.
    """
    from modelo import nodos as _nodos

    centros = _centros(inst)
    pos: Dict[str, Punto] = {}

    # --- nodos de las esquinas ----------------------------------------------
    for i in _nodos(inst.V_ext, inst.esq_libres, inst.X):
        if i in inst.esq_libres:
            if i in centros:
                pos[i] = centros[i]
            continue
        partes = NODOS_CORREDOR.get(i) or _partir(i)
        if partes is None:
            continue
        esq, tipo, rama = partes
        if esq not in centros:
            continue
        dx, dy = OFFSET[rama, tipo]
        cx, cy = centros[esq]
        pos[i] = (cx + dx, cy + dy)

    # --- nodos externos ------------------------------------------------------
    tabla = {}

    if inst.nombre.startswith("corredor"):
        tabla = EXTERNOS_CORREDOR
    elif inst.nombre.startswith("bernal-centro"):
        tabla = EXTERNOS_BERNAL_CENTRO
    elif inst.nombre.startswith("red"):
        tabla = EXTERNOS_RED

    vecino = {}
    for (i, j) in inst.tramos:
        if i in inst.V_ext:
            vecino[i] = j
        if j in inst.V_ext:
            vecino[j] = i

    for e in inst.V_ext:
        if e in tabla:
            pos[e] = tabla[e]
            continue
        j = vecino.get(e)
        if j is None or j not in pos:
            continue
        partes = NODOS_CORREDOR.get(j) or _partir(j)
        base = centros.get(partes[0]) if partes else centros.get(j, pos[j])
        dx, dy = pos[j][0] - base[0], pos[j][1] - base[1]
        norma = math.hypot(dx, dy)
        if norma < 1e-9:                 # la esquina es un nodo único
            cx = sum(p[0] for p in centros.values()) / max(len(centros), 1)
            cy = sum(p[1] for p in centros.values()) / max(len(centros), 1)
            dx, dy = pos[j][0] - cx, pos[j][1] - cy
            norma = max(math.hypot(dx, dy), 1e-9)
        pos[e] = (pos[j][0] + BORDE * dx / norma, pos[j][1] + BORDE * dy / norma)

    return pos


# =============================================================================
#  Lecturas de la solución
# =============================================================================
def flujo(dat, sol, a, h: Optional[int] = None) -> float:
    """Flujo total sobre el arco físico ``a``, en la capa ``h`` o en todo el período."""
    capas = dat.HG if h is None else [h]
    return sum(sol["x"][k, ("tr", a, hh)]
               for k in dat.inst.K for hh in capas)


def cola(dat, sol, i: str, h: int) -> float:
    """Flujo que permanece en espera en el nodo ``i`` entre las capas h y h+1."""
    return sum(sol["x"][k, ("esp", i, h)] for k in dat.inst.K)


def en_verde(inst, sol, p: str, a, h: int) -> bool:
    """True si el movimiento ``a`` de la intersección ``p`` tiene verde en la capa h."""
    return any(sol["y"][p, g, h] == 1 for g in inst.G[p] if a in inst.E_pg[p, g])


def _esquina_de(inst, a) -> Optional[str]:
    """Intersección semaforizada a la que pertenece el movimiento ``a``, si la hay."""
    for p in inst.P:
        if a in inst.movimientos.get(p, {}):
            return p
    return None


def _dijkstra(dat, origen: str, destino: str) -> float:
    """Tiempo de tránsito mínimo entre dos nodos físicos."""
    salientes: Dict[str, List] = {}
    for a in dat.A:
        salientes.setdefault(a[0], []).append(a)
    dist = {origen: 0.0}
    cola_pq = [(0.0, origen)]
    visto = set()
    while cola_pq:
        dv, v = heapq.heappop(cola_pq)
        if v in visto:
            continue
        visto.add(v)
        if v == destino:
            return dv
        for a in salientes.get(v, []):
            nueva = dv + dat.tau[a]
            if nueva < dist.get(a[1], float("inf")) - 1e-12:
                dist[a[1]] = nueva
                heapq.heappush(cola_pq, (nueva, a[1]))
    return dist.get(destino, 0.0)


# =============================================================================
#  1. Diagrama estático
# =============================================================================

def diagrama_estatico(inst, dat, sol, archivo: str = "red.png",
                      figsize: Optional[Punto] = None) -> str:
    """Dibuja la red con el flujo agregado de cada arco durante el período."""
    archivo = _ruta(archivo, CARPETA_OTROS)
    pos = posiciones(inst)
    if figsize is None:                  # la figura crece con la red
        ancho = max(q[0] for q in pos.values()) - min(q[0] for q in pos.values())
        alto = max(q[1] for q in pos.values()) - min(q[1] for q in pos.values())
        figsize = (max(11.0, 1.5 * ancho + 2.0), max(5.0, 1.5 * alto + 2.0))
    fig, ax = plt.subplots(figsize=figsize)

    flujos = {a: flujo(dat, sol, a) for a in dat.A}
    maximo = max(flujos.values()) or 1.0

    for a in dat.A:
        if a[0] not in pos or a[1] not in pos:
            continue
        f = flujos[a]
        p = _esquina_de(inst, a)
        ancho = 0.6 + 4.0 * f / maximo
        color = C_FLUJO if p is None else C_VERDE
        alfa = 0.25 if f < 1e-6 else 0.9
        ax.add_patch(FancyArrowPatch(
            pos[a[0]], pos[a[1]], arrowstyle="-|>", mutation_scale=11,
            linewidth=ancho, color=color, alpha=alfa,
            shrinkA=7, shrinkB=7,
            connectionstyle="arc3,rad=0.06" if p else "arc3,rad=0"))
        if f > 1e-6 and p is None and a in inst.tramos:
            mx = (pos[a[0]][0] + pos[a[1]][0]) / 2
            my = (pos[a[0]][1] + pos[a[1]][1]) / 2
            ax.text(mx, my, "%.1f" % f, fontsize=6.5, color=C_TEXTO,
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white",
                              ec="none", alpha=0.75))

    for i, (x, y) in pos.items():
        externo = i in inst.V_ext
        ax.plot(x, y, "o", markersize=9 if externo else 4,
                color="white", markeredgecolor=C_TEXTO, markeredgewidth=0.8,
                zorder=3)
        if externo:
            ax.text(x, y - 0.11, i, fontsize=6, ha="center", va="top",
                    color=C_TEXTO, zorder=4)

    #  Una sola etiqueta por esquina, en su centro.
    for esq, (x, y) in _centros(inst).items():
        ax.text(x, y, esq, fontsize=7, fontweight="bold", ha="center",
                va="center", color=C_TEXTO, zorder=5,
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none",
                          alpha=0.8))

    ax.set_title("%s — flujo por arco [veh/período]\n"
                 "verde: movimientos semaforizados" % inst.nombre, fontsize=11)
    xs = [q[0] for q in pos.values()]
    ys = [q[1] for q in pos.values()]
    ax.set_xlim(min(xs) - 0.4, max(xs) + 0.4)
    ax.set_ylim(min(ys) - 0.4, max(ys) + 0.4)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(archivo, dpi=160)
    plt.close(fig)
    return archivo


# =============================================================================
#  2. Animación por capa temporal
# =============================================================================
def animacion_red(inst, dat, sol, archivo: str = "red.gif",
                  fps: int = 2, figsize: Punto = (11, 8)) -> str:
    """Un cuadro por capa: verde/rojo de cada movimiento y cola de cada nodo."""
    archivo = _ruta(archivo, CARPETA_OTROS)
    pos = posiciones(inst)
    H, Delta = inst.H, dat.Delta

    picos = {a: max(flujo(dat, sol, a, h) for h in dat.HG) for a in dat.A}
    tope = max(picos.values()) or 1.0
    cola_max = max([cola(dat, sol, i, h) for i in dat.V for h in dat.HG] + [1.0])
    cola_max = max(cola_max, 1e-9)

    fig, ax = plt.subplots(figsize=figsize)

    def cuadro(h: int):
        ax.clear()
        for a in dat.A:
            if a[0] not in pos or a[1] not in pos:
                continue
            p = _esquina_de(inst, a)
            f = flujo(dat, sol, a, h)
            if p is None:
                color, alfa = C_CALLE, 0.55
            elif en_verde(inst, sol, p, a, h):
                color, alfa = C_VERDE, 0.95
            else:
                color, alfa = C_ROJO, 0.5
            ancho = 0.8 + 4.5 * f / tope
            ax.add_patch(FancyArrowPatch(
                pos[a[0]], pos[a[1]], arrowstyle="-|>", mutation_scale=11,
                linewidth=ancho, color=color, alpha=alfa,
                shrinkA=7, shrinkB=7,
                connectionstyle="arc3,rad=0.06" if p else "arc3,rad=0"))

        for i, (x, y) in pos.items():
            q = max(cola(dat, sol, i, h), 0.0)   # el solver puede devolver -1e-16
            tam = 5 + 14 * (q / cola_max) ** 0.5
            ax.plot(x, y, "o", markersize=tam, color=C_NODO,
                    markeredgecolor=C_TEXTO, markeredgewidth=0.7, zorder=3)
            ax.text(x, y - 0.12, i, fontsize=5.5, ha="center", va="top",
                    color=C_TEXTO, zorder=4)

        ax.set_title("%s — capa %d de %d   (t = %.0f a %.0f s del ciclo)\n"
                     "verde/rojo: estado del movimiento   ·   "
                     "tamaño del nodo: cola"
                     % (inst.nombre, h, H - 1, h * Delta, (h + 1) * Delta),
                     fontsize=11)
        ax.set_aspect("equal")
        ax.axis("off")
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        ax.set_xlim(min(xs) - 0.4, max(xs) + 0.4)
        ax.set_ylim(min(ys) - 0.4, max(ys) + 0.4)

    anim = FuncAnimation(fig, cuadro, frames=H, interval=1000 // max(fps, 1))
    anim.save(archivo, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return archivo


# =============================================================================
#  3. Diagrama espacio-tiempo
# =============================================================================
def diagrama_espacio_tiempo(inst, dat, sol,
                            corredor: Sequence[Tuple[str, tuple]],
                            archivo: str = "espacio_tiempo.png",
                            ciclos: int = 2,
                            figsize: Punto = (11, 6)) -> str:
    """Diagrama de coordinación a lo largo de un corredor.

    ``corredor`` es la lista ordenada de los movimientos pasantes de cada
    intersección, por ejemplo::

        [("P1", ("e1O", "s1E")), ("P2", ("e2O", "s2E"))]

    El eje vertical mide el tiempo de tránsito acumulado desde la primera
    intersección, de modo que la trayectoria de un vehículo que no se detiene
    es una recta a 45 grados. Si las bandas de verde se alinean sobre esas
    rectas, el plan produce una onda verde.
    """
    archivo = _ruta(archivo, CARPETA_OTROS)
    H, Delta, Gamma = inst.H, dat.Delta, inst.Gamma

    # --- posición de cada intersección sobre el corredor ---------------------
    y: List[float] = []
    acumulado = 0.0
    for n, (p, a) in enumerate(corredor):
        y.append(acumulado)
        acumulado += dat.tau[a]
        if n + 1 < len(corredor):
            siguiente = corredor[n + 1][1]
            acumulado += _dijkstra(dat, a[1], siguiente[0])

    fig, ax = plt.subplots(figsize=figsize)
    alto = max(acumulado * 0.035, 1.2)

    # --- bandas de verde y de rojo -------------------------------------------
    for (p, a), yp in zip(corredor, y):
        for ciclo in range(ciclos):
            for h in dat.HG:
                t0 = ciclo * Gamma + h * Delta
                verde_ahora = en_verde(inst, sol, p, a, h)
                ax.barh(yp, Delta, left=t0, height=alto,
                        color=C_VERDE if verde_ahora else C_ROJO,
                        alpha=0.95 if verde_ahora else 0.35,
                        edgecolor="none", zorder=2)


    # --- trayectorias: un vehículo que no se detiene avanza a 45 grados ------
    atras = int(math.ceil(acumulado / Gamma))
    for ciclo in range(-atras, ciclos + 1):
        for h in dat.HG:
            if not en_verde(inst, sol, corredor[0][0], corredor[0][1], h):
                continue
            t0 = ciclo * Gamma + h * Delta
            ax.plot([t0, t0 + acumulado], [0, acumulado],
                    color=C_TEXTO, linewidth=0.7, alpha=0.35, zorder=3)

    ax.set_xlim(0, ciclos * Gamma)
    ax.set_ylim(-2 * alto, acumulado + 2 * alto)
    ax.set_yticks(y)
    ax.set_yticklabels(["%s\n%s→%s  (%.0f s)" % (p, a[0], a[1], yp)
                        for (p, a), yp in zip(corredor, y)], fontsize=8)
    ax.set_xlabel("tiempo dentro del período [s]")
    ax.set_ylabel("posición sobre el corredor\n(tiempo de tránsito acumulado)")
    ax.set_title("%s — diagrama espacio-tiempo\n"
                 "las rectas son trayectorias sin detenciones; si cruzan "
                 "todas las bandas en verde, hay onda verde" % inst.nombre,
                 fontsize=11)
    for c in range(1, ciclos):
        ax.axvline(c * Gamma, color=C_TEXTO, linewidth=0.8, linestyle="--",
                   alpha=0.4)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(archivo, dpi=160)
    plt.close(fig)
    return archivo


# =============================================================================
#  Atajo
# =============================================================================
def graficar(resumen: dict, prefijo: Optional[str] = None,
             corredor: Optional[Sequence[Tuple[str, tuple]]] = None,
             vehiculos: bool = False,
             segundos_por_capa: float = 1.5,
             sufijo: str = "") -> List[str]:
    """Genera las figuras a partir del resultado de ``ejecutar``.

    ``resumen`` es el diccionario que devuelve ``modelo.ejecutar``. Si se pasa
    ``corredor`` se agrega el diagrama espacio-tiempo.

    Los archivos se llaman ``<prefijo>_<figura><sufijo>.<ext>``. El sufijo
    sirve para distinguir versiones de una misma instancia sin pisarlas: por
    ejemplo ``sufijo="_postprocesado"`` da ``red_vehiculos_postprocesado.gif``.
    """
    if "datos" not in resumen:
        print("La instancia no tiene solución: no hay nada que graficar.")
        return []

    dat, sol = resumen["datos"], resumen["solucion"]
    inst = dat.inst
    prefijo = prefijo or inst.nombre

    archivos = [
        diagrama_estatico(inst, dat, sol, "%s_red%s.png" % (prefijo, sufijo)),
        animacion_red(inst, dat, sol, "%s_animacion%s.gif" % (prefijo, sufijo))]
    if corredor:
        archivos.append(diagrama_espacio_tiempo(
            inst, dat, sol, corredor,
            "%s_espacio_tiempo%s.png" % (prefijo, sufijo)))
    if vehiculos:
        describir_caminos(dat, sol)
        archivos.append(animacion_vehiculos(
            inst, dat, sol, "%s_vehiculos%s.gif" % (prefijo, sufijo),
            segundos_por_capa=segundos_por_capa))

    for a in archivos:
        print("  figura: %s" % _mostrar(a))
    return archivos


# =============================================================================
#  Detección automática del corredor
# =============================================================================
def corredor_automatico(inst, dat) -> List[Tuple[str, tuple]]:
    """Encuentra el eje con más intersecciones semaforizadas en línea.

    Busca, para cada sentido de circulación, las intersecciones que tienen el
    movimiento recto correspondiente y que están alineadas, y devuelve la
    cadena más larga. Sirve para no tener que declarar el corredor a mano en
    cada instancia. Si no encuentra ninguna cadena de al menos dos
    intersecciones, devuelve una lista vacía.
    """
    pos = posiciones(inst)
    centros = _centros(inst)

    def rama_de(nodo):
        partes = NODOS_CORREDOR.get(nodo) or _partir(nodo)
        return partes[2] if partes else None

    mejor: List[Tuple[str, tuple]] = []
    for ra, rb, eje in [("O", "E", "x"), ("E", "O", "x"),
                        ("N", "S", "y"), ("S", "N", "y")]:
        pasantes = {}
        for p in inst.P:
            if p not in centros:
                continue
            for a in dat.E_p[p]:
                if rama_de(a[0]) == ra and rama_de(a[1]) == rb:
                    pasantes[p] = a
                    break

        # se agrupan por la coordenada perpendicular al sentido
        grupos: Dict[float, List[str]] = {}
        for p in pasantes:
            clave = round(centros[p][1] if eje == "x" else centros[p][0], 3)
            grupos.setdefault(clave, []).append(p)

        for _, lista in grupos.items():
            if eje == "x":
                lista.sort(key=lambda p: centros[p][0], reverse=(ra == "E"))
            else:
                lista.sort(key=lambda p: centros[p][1], reverse=(ra == "N"))
            cadena = [(p, pasantes[p]) for p in lista]
            if len(cadena) > len(mejor):
                mejor = cadena

    return mejor if len(mejor) >= 2 else []


# =============================================================================
#  Descomposición del flujo en caminos
# =============================================================================
def descomponer(dat, sol, k: str, tol: float = 1e-7):
    """Descompone la circulación del producto k en caminos con su flujo.

    La solución x^k es una circulación sobre la red ampliada: se conserva en
    todos los nodos y cierra por el arco de retorno. Toda circulación se
    descompone en caminos del superorigen al superdestino, más eventuales
    ciclos que se cancelan.

    Como los nodos de la red expandida son pares (nodo físico, capa temporal),
    cada camino de la descomposición YA ES una trayectoria: dice en qué capa
    el flujo está en cada nodo, y los arcos de espera que atraviesa son los
    intervalos en los que estuvo detenido. No hay nada que simular.

    Devuelve una lista de pares (flujo, camino), donde el camino es la lista
    ordenada de arcos de la red expandida.
    """
    resid = {e: v for (kk, e), v in sol["x"].items()
             if kk == k and v > tol and e[0] != "ret"}
    origen, destino = ("SO", k), ("SD", k)

    caminos = []
    while any(e[0] == "in" and v > tol for e, v in resid.items()):
        camino: List = []
        indice = {origen: 0}
        v = origen

        while v != destino:
            salida = None
            for e in dat.delta_mas[k][v]:
                if e[0] != "ret" and resid.get(e, 0.0) > tol:
                    salida = e
                    break
            if salida is None:
                break                     # sin continuación: se abandona
            camino.append(salida)
            w = dat.A_k[k][salida][1]

            if w in indice:               # se cerró un ciclo: se cancela
                corte = indice[w]
                ciclo = camino[corte:]
                cuello = min(resid[e] for e in ciclo)
                for e in ciclo:
                    resid[e] -= cuello
                    if resid[e] <= tol:
                        resid.pop(e, None)
                for e in ciclo:
                    indice.pop(dat.A_k[k][e][1], None)
                camino = camino[:corte]
                v = w
                continue

            indice[w] = len(camino)
            v = w

        if v != destino or not camino:
            break

        cuello = min(resid[e] for e in camino)
        for e in camino:
            resid[e] -= cuello
            if resid[e] <= tol:
                resid.pop(e, None)
        caminos.append((cuello, camino))

    return caminos


def describir_caminos(dat, sol, maximo: int = 8) -> None:
    """Imprime la descomposición del óptimo en caminos, producto por producto."""
    inst = dat.inst
    print()
    print("=" * 70)
    print("DESCOMPOSICIÓN DEL FLUJO ÓPTIMO EN CAMINOS")
    print("=" * 70)
    for k in inst.K:
        caminos = descomponer(dat, sol, k)
        print("  %s: %s -> %s, %.2f veh/período en %d camino(s)"
              % (k, inst.o[k], inst.d[k], inst.D[k], len(caminos)))
        for f, camino in sorted(caminos, key=lambda c: -c[0])[:maximo]:
            nodos_fis, esperas, salida = [], 0, None
            for e in camino:
                if e[0] == "tr":
                    if not nodos_fis:
                        nodos_fis.append(e[1][0])
                    nodos_fis.append(e[1][1])
                elif e[0] == "esp":
                    esperas += 1
                elif e[0] == "in":
                    salida = e[2]
            viaje = sum(dat.A_k[k][e][2] for e in camino)
            print("     %5.2f veh  sale en capa %2d  viaje %5.1f s "
                  "(%d intervalos de espera)" % (f, salida, viaje, esperas))
            print("            " + " ".join(nodos_fis))
        if len(caminos) > maximo:
            print("     y %d camino(s) más" % (len(caminos) - maximo))


# =============================================================================
#  Animación con vehículos
# =============================================================================
def _trayectoria(dat, camino, pos) -> Optional[List[tuple]]:
    """Convierte un camino de la red expandida en segmentos (t0, t1, p0, p1, espera, nodo)."""
    segs, t = [], None
    for e in camino:
        if e[0] == "in":
            t = e[2] * dat.Delta          # la capa en la que ingresa
            continue
        if e[0] in ("out", "ret"):
            continue
        if e[0] == "tr":
            a = e[1]
            if a[0] not in pos or a[1] not in pos:
                return None
            segs.append((t, t + dat.tau[a], pos[a[0]], pos[a[1]], False, None))
            t += dat.tau[a]
        else:                             # arco de espera: la cola
            i = e[1]
            if i not in pos:
                return None
            segs.append((t, t + dat.Delta, pos[i], pos[i], True, i))
            t += dat.Delta
    return segs or None


def animacion_vehiculos(inst, dat, sol, archivo: str = "vehiculos.gif",
                        cuanto: float = 0.2,
                        segundos_por_capa: float = 1.5,
                        cuadros_por_capa: int = 6,
                        figsize: Punto = (11, 8)) -> str:
    """Anima la solución mostrando vehículos que circulan y hacen cola.

    Cada punto representa ``cuanto`` vehículos de un camino de la
    descomposición, de modo que todos los puntos corresponden a flujo real de
    la solución óptima.

    Importante: en el modelo la cola no ocupa espacio. Está acotada por
    kappa_i pero no se extiende sobre el tramo anterior ni lo bloquea antes de
    llenarse. Por eso los vehículos detenidos se apilan sobre el nodo de
    acceso y no estirados cuadra arriba: dibujarlos así sugeriría un bloqueo
    aguas arriba que la formulación no representa.

    Velocidad
    ---------
    ``segundos_por_capa``
        Cuántos segundos de animación dura cada capa temporal. Subirlo hace el
        GIF más lento sin cambiar la cantidad de cuadros. Con 1.5 y H = 12, un
        ciclo completo dura 18 segundos.
    ``cuadros_por_capa``
        Cuántos cuadros se dibujan dentro de cada capa. Sólo afecta lo suave
        que se ve el movimiento, no la velocidad.

    Los vehículos detenidos se dibujan con borde negro y los que circulan con
    borde blanco, de modo que se distingue de un vistazo quién está esperando.
    """
    archivo = _ruta(archivo, CARPETA_GIF)
    pos = posiciones(inst)
    Gamma, Delta, H = inst.Gamma, dat.Delta, inst.H

    colores = plt.get_cmap("tab10")
    vehiculos = []                        # (segs, t_ini, t_fin, color)
    for n, k in enumerate(inst.K):
        color = colores(n % 10)
        for f, camino in descomponer(dat, sol, k):
            segs = _trayectoria(dat, camino, pos)
            if segs is None:
                continue
            cuantos = int(round(f / cuanto))
            if cuantos == 0:
                continue
            for j in range(cuantos):
                corr = j * Delta / cuantos       # se reparten dentro del intervalo
                movidos = [(a + corr, b + corr, p0, p1, esp, nod)
                           for (a, b, p0, p1, esp, nod) in segs]
                vehiculos.append((movidos, movidos[0][0], movidos[-1][1], color))

    if not vehiculos:
        raise ValueError("No se pudo construir ninguna trayectoria: "
                         "faltan posiciones de nodos.")

    xs = [q[0] for q in pos.values()]
    ys = [q[1] for q in pos.values()]
    fig, ax = plt.subplots(figsize=figsize)
    total = H * cuadros_por_capa
    fps = max(1, int(round(cuadros_por_capa / max(segundos_por_capa, 1e-6))))

    def ubicar(segs, tt):
        for (a, b, p0, p1, esp, nod) in segs:
            if a <= tt < b:
                r = 0.0 if b - a < 1e-9 else (tt - a) / (b - a)
                return (p0[0] + r * (p1[0] - p0[0]),
                        p0[1] + r * (p1[1] - p0[1])), esp, nod
        return None, False, None

    def cuadro(n: int):
        ax.clear()
        t = n * Gamma / total

        # --- la red de fondo, con el estado de cada movimiento --------------
        h = min(int(t / Delta), H - 1)
        for a in dat.A:
            if a[0] not in pos or a[1] not in pos:
                continue
            p = _esquina_de(inst, a)
            if p is None:
                color, alfa, ancho = C_CALLE, 0.35, 1.6
            elif en_verde(inst, sol, p, a, h):
                color, alfa, ancho = C_VERDE, 1.0, 5.0
            else:
                color, alfa, ancho = C_ROJO, 0.9, 5.0
            ax.add_patch(FancyArrowPatch(
                pos[a[0]], pos[a[1]], arrowstyle="-", linewidth=ancho,
                color=color, alpha=alfa, shrinkA=4, shrinkB=4,
                connectionstyle="arc3,rad=0.06" if p else "arc3,rad=0"))

        for i, (x, y) in pos.items():
            ax.plot(x, y, "o", markersize=3.5, color=C_TEXTO, alpha=0.5, zorder=2)

        # --- semaforo de cada acceso: verde si alguno de sus movimientos pasa -
        for p in inst.P:
            for i in {a[0] for a in dat.E_p[p]}:
                if i not in pos:
                    continue
                pasa = any(en_verde(inst, sol, p, a, h)
                           for a in dat.E_p[p] if a[0] == i)
                ax.plot(pos[i][0], pos[i][1], "o", markersize=11,
                        color=C_VERDE if pasa else C_ROJO,
                        markeredgecolor="white", markeredgewidth=1.2, zorder=4)

        # --- los vehículos ---------------------------------------------------
        detenidos: Dict[str, int] = {}
        for segs, t_ini, t_fin, color in vehiculos:
            for m in range(int((t_fin - t_ini) / Gamma) + 2):
                tt = t + m * Gamma
                if not (t_ini <= tt < t_fin):
                    continue
                punto, esperando, nodo = ubicar(segs, tt)
                if punto is None:
                    continue
                if esperando and nodo is not None:
                    # los detenidos se apilan sobre el nodo, sin ocupar la cuadra
                    idx = detenidos.get(nodo, 0)
                    detenidos[nodo] = idx + 1
                    fila, col = divmod(idx, 3)
                    punto = (punto[0] + (col - 1) * 0.045,
                             punto[1] - 0.045 - fila * 0.045)
                ax.plot(punto[0], punto[1], "o", markersize=5.5, color=color,
                        markeredgecolor="black" if esperando else "white",
                        markeredgewidth=0.9 if esperando else 0.5, zorder=5)

        for nodo, cuantos in detenidos.items():
            if cuantos >= 3:
                ax.text(pos[nodo][0] + 0.10, pos[nodo][1] - 0.06,
                        "%d" % cuantos, fontsize=7, color=C_TEXTO, zorder=6)

        # --- reloj del ciclo -------------------------------------------------
        for hh in dat.HG:
            ax.add_patch(Rectangle(
                (0.02 + 0.96 * hh / H, 0.01), 0.96 / H * 0.92, 0.022,
                transform=ax.transAxes, clip_on=False, zorder=8,
                facecolor=C_TEXTO if hh == h else "#dcdcdc", edgecolor="none"))
        ax.text(0.02, 0.045, "capa 0", transform=ax.transAxes, fontsize=6,
                color=C_TEXTO, zorder=8)
        ax.text(0.98, 0.045, "capa %d" % (H - 1), transform=ax.transAxes,
                fontsize=6, color=C_TEXTO, ha="right", zorder=8)

        ax.set_title("%s — t = %4.1f s del ciclo (capa %d de %d)\n"
                     "cada punto = %.1f veh   ·   borde negro = detenido   ·   "
                     "el círculo grande de cada acceso es su semáforo"
                     % (inst.nombre, t, h, H - 1, cuanto), fontsize=10)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(min(xs) - 0.4, max(xs) + 0.4)
        ax.set_ylim(min(ys) - 0.4, max(ys) + 0.4)

    anim = FuncAnimation(fig, cuadro, frames=total, interval=1000 // max(fps, 1))
    anim.save(archivo, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return archivo