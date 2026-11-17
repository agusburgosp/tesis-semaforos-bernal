"""
Segunda parte del generador: toma una ``Red`` de ``generador_red.py`` y la
completa con el período, las capas temporales, las cotas de duración y las
demandas, devolviendo una ``Instancia`` lista para resolver.

    from generador_red import generar_red
    from generador_demandas import generar_demandas
    from modelo import ejecutar

    red = generar_red(filas=4, columnas=5, avenidas_v=dict(doble=1), inicio_v=2)
    inst = generar_demandas(red, nivel="intermedia", semilla=1)
    ejecutar(inst)

Los tres niveles de demanda
---------------------------
Combinan dos perillas independientes:

``cobertura``   qué fracción de los nodos de ingreso genera demanda
``saturacion``  qué fracción de la capacidad efectiva se carga

===========  ==========  ===========  ==========================================
nivel        cobertura   saturación   idea
===========  ==========  ===========  ==========================================
poca            0.40        0.20      algunos ingresos y poco volumen
intermedia      0.70        0.50      algunos ingresos con volumen apreciable
completa        1.00        0.75      todos los ingresos y la red bastante cargada
===========  ==========  ===========  ==========================================

Las dos se pueden fijar a mano y pisan al nivel.

El sesgo hacia las avenidas
---------------------------
El sesgo está en los EXTREMOS de cada demanda, no en su recorrido. Un par
origen-destino recibe más puntaje cuanto más de sus dos puntas nace o muere
sobre una avenida, y en segundo lugar cuántas de esas puntas desembocan
directamente en una intersección semaforizada. Ese puntaje decide qué ingresos
se activan, qué destino se sortea para cada origen y cuánto volumen recibe.

No se impone que el tránsito circule por la avenida: en la variante con
asignación de tráfico el recorrido lo elige el modelo. Lo que se reproduce es
que la mayor parte de los viajes empieza o termina sobre una avenida, como en
una red real.
"""

from __future__ import annotations

import heapq
import random
import re
from typing import Dict, List, Optional, Sequence, Set, Tuple

from generador_red import Red, tipo_de_giro
from modelo import Instancia

Arco = Tuple[str, str]

# =============================================================================
#  Niveles de demanda
# =============================================================================
NIVELES: Dict[str, Dict[str, float]] = {
    "poca":       dict(cobertura=0.40, saturacion=0.20, productos_por_origen=1),
    "intermedia": dict(cobertura=0.70, saturacion=0.50, productos_por_origen=1),
    "completa":   dict(cobertura=1.00, saturacion=0.75, productos_por_origen=2),
}


# =============================================================================
#  Clasificación de los arcos
# =============================================================================
def _coordenadas(red: Red) -> Dict[str, Tuple[int, int]]:
    """Esquina -> (fila, columna)."""
    return {p: fc for fc, p in red.esquina.items()}


def _esquina_de_nodo(nodo: str, esquinas: Set[str]) -> Optional[str]:
    """Esquina a la que pertenece un nodo de acceso, de salida o único."""
    if nodo in esquinas:
        return nodo
    if "_" in nodo:
        base = nodo.rsplit("_", 1)[0]
        if base in esquinas:
            return base
    return None


def clasificar_arcos(red: Red) -> Dict[Arco, str]:
    """Etiqueta cada arco físico como 'avenida', 'calle' o 'movimiento'.

    Un tramo pertenece a una avenida si la línea que lo contiene es de
    cualquiera de los tres tipos de avenida. Los movimientos internos se
    etiquetan aparte porque no pertenecen a ninguna línea: representan el paso
    por una intersección semaforizada.
    """
    coord = _coordenadas(red)
    esquinas = set(coord)
    clase: Dict[Arco, str] = {}

    for p in red.P:
        for a in red.movimientos[p]:
            clase[a] = "movimiento"

    for a in red.tramos:
        i, j = a
        ei, ej = _esquina_de_nodo(i, esquinas), _esquina_de_nodo(j, esquinas)
        if ei and ej:                                  # entre dos esquinas
            (fi, ci), (fj, cj) = coord[ei], coord[ej]
            tipo = red.tipo_linea_v[ci] if ci == cj else red.tipo_linea_h[fi]
        else:                                          # una punta es el borde
            externo = i if ei is None else j
            # el último carácter del nombre indica el sentido y con él la
            # orientación de la línea: S o N son verticales, E u O horizontales
            sentido = externo[-1]
            etiqueta = externo[1:-1]
            if sentido in ("S", "N"):
                columna = next((c for c in red.tipo_linea_v
                                if _letra(red, c) == etiqueta), None)
                tipo = red.tipo_linea_v.get(columna, "calle")
            else:
                fila = int(etiqueta) - 1 if etiqueta.isdigit() else None
                tipo = red.tipo_linea_h.get(fila, "calle")
        clase[a] = "calle" if tipo == "calle" else "avenida"

    return clase


def _letra(red: Red, c: int) -> str:
    """Etiqueta de la columna c, tal como aparece en los nombres externos."""
    from generador_red import _etiqueta_columna
    return _etiqueta_columna(c)


# =============================================================================
#  Caminos a flujo libre
# =============================================================================
def _red_dirigida(red: Red, Delta: float):
    """Pesos y lista de adyacencia de la red física, con tiempos de tránsito."""
    peso: Dict[Arco, float] = {}
    for a, dat in red.tramos.items():
        peso[a] = dat["t"]
    for p in red.P:
        for a, dat in red.movimientos[p].items():
            peso[a] = dat["l"] * Delta
    salientes: Dict[str, List[Arco]] = {}
    for a in peso:
        salientes.setdefault(a[0], []).append(a)
    return peso, salientes


def _camino(peso, salientes, origen: str, destino: str):
    """Camino de mínimo tiempo de tránsito. Devuelve (costo, lista de arcos)."""
    dist = {origen: 0.0}
    previo: Dict[str, Arco] = {}
    cola = [(0.0, origen)]
    visto: Set[str] = set()
    while cola:
        dv, v = heapq.heappop(cola)
        if v in visto:
            continue
        visto.add(v)
        if v == destino:
            break
        for a in salientes.get(v, []):
            nueva = dv + peso[a]
            if nueva < dist.get(a[1], float("inf")) - 1e-12:
                dist[a[1]] = nueva
                previo[a[1]] = a
                heapq.heappush(cola, (nueva, a[1]))
    if destino not in dist:
        return None, None
    camino, v = [], destino
    while v != origen:
        a = previo[v]
        camino.append(a)
        v = a[0]
    return dist[destino], list(reversed(camino))


# =============================================================================
#  Clasificación de los nodos del borde
# =============================================================================
def linea_de_externo(red: Red, nodo: str) -> Optional[Tuple[str, int]]:
    """Línea a la que pertenece un nodo del borde: ('v', columna) o ('h', fila).

    Los nombres son "o" o "d" seguidos de la etiqueta de la línea y del sentido:
    "oBS" es el ingreso a la columna B en sentido sur, "o3E" el de la fila 3
    hacia el este.
    """
    sentido, etiqueta = nodo[-1], nodo[1:-1]
    if sentido in ("S", "N"):
        for c in red.tipo_linea_v:
            if _letra(red, c) == etiqueta:
                return ("v", c)
    elif etiqueta.isdigit():
        fila = int(etiqueta) - 1
        if fila in red.tipo_linea_h:
            return ("h", fila)
    return None


def tipo_de_externo(red: Red) -> Dict[str, str]:
    """Nodo del borde -> 'avenida' o 'calle', según la línea que lo contiene."""
    tipos = {}
    for v in red.V_ext:
        ln = linea_de_externo(red, v)
        if ln is None:
            tipos[v] = "calle"
            continue
        orient, idx = ln
        t = red.tipo_linea_v[idx] if orient == "v" else red.tipo_linea_h[idx]
        tipos[v] = "calle" if t == "calle" else "avenida"
    return tipos


def toca_semaforo(red: Red) -> Dict[str, bool]:
    """Nodo del borde -> si la esquina con la que conecta está semaforizada."""
    coord = _coordenadas(red)
    esquinas = set(coord)
    vecino = {}
    for (i, j) in red.tramos:
        if i in red.V_ext:
            vecino[i] = j
        if j in red.V_ext:
            vecino[j] = i
    salida = {}
    for v in red.V_ext:
        w = vecino.get(v)
        esq = _esquina_de_nodo(w, esquinas) if w else None
        salida[v] = bool(esq and esq in red.P)
    return salida


def puntaje(origen: str, destino: str,
            tipo_ext: Dict[str, str], semaforo_ext: Dict[str, bool],
            peso_avenida: float, peso_semaforo: float) -> float:
    """Puntaje de un par origen-destino según dónde nace y dónde muere.

    Cuenta cuántas de las dos puntas están sobre una avenida y, en segundo
    lugar, cuántas desembocan en una intersección semaforizada. Una demanda
    que va de una avenida a otra avenida recibe el máximo; una que nace y
    muere en calles internas, el mínimo.
    """
    n_av = (tipo_ext.get(origen) == "avenida") + (tipo_ext.get(destino) == "avenida")
    n_sem = int(semaforo_ext.get(origen, False)) + int(semaforo_ext.get(destino, False))
    return 1.0 + peso_avenida * n_av / 2.0 + peso_semaforo * n_sem / 2.0


# =============================================================================
#  Generador
# =============================================================================
def generar_demandas(red: Red,
                     nivel: str = "intermedia",
                     Gamma: float = 60.0,
                     H: int = 12,
                     L: int = 2,
                     U: int = 8,
                     cobertura: Optional[float] = None,
                     saturacion: Optional[float] = None,
                     productos_por_origen: Optional[int] = None,
                     peso_avenida: float = 3.0,
                     peso_semaforo: float = 1.5,
                     caminos: bool = False,
                     fraccion_prefijada: float = 0.7,
                     semilla: int = 0,
                     nombre: Optional[str] = None,
                     descripcion: Optional[str] = None) -> Instancia:
    """Completa una ``Red`` con demandas y devuelve una ``Instancia``.

    Parámetros temporales
    ---------------------
    ``Gamma``, ``H``  período y cantidad de capas; Delta = Gamma / H
    ``L``, ``U``      cotas de duración de cada fase, en intervalos

    Se comprueba que el tiempo de una cuadra sea múltiplo de Delta y que el
    mínimo de fases de cada intersección entre en el período.

    Demandas
    --------
    ``nivel``         "poca", "intermedia" o "completa"
    ``cobertura``     fracción de los ingresos con demanda; pisa al nivel
    ``saturacion``    fracción de la capacidad efectiva que se carga
    ``peso_avenida``  cuánto se privilegian los pares que usan avenidas
    ``peso_semaforo`` cuánto se privilegian los que cruzan semáforos

    Caminos prefijados
    ------------------
    ``caminos``             si es True se fija el recorrido de una parte
    ``fraccion_prefijada``  qué fracción de los productos queda con camino
                            fijo, elegidos entre los de mayor puntaje, o sea
                            los que circulan por las avenidas
    """
    assert nivel in NIVELES, "El nivel debe ser uno de %s" % list(NIVELES)
    preset = NIVELES[nivel]
    cobertura = preset["cobertura"] if cobertura is None else cobertura
    saturacion = preset["saturacion"] if saturacion is None else saturacion
    por_origen = (int(preset["productos_por_origen"])
                  if productos_por_origen is None else productos_por_origen)

    rng = random.Random(semilla)
    Delta = Gamma / H

    # -------------------------------------------------------------------------
    #  1. Comprobaciones de compatibilidad entre la red y el tiempo
    # -------------------------------------------------------------------------
    for a, dat in red.tramos.items():
        cociente = dat["t"] / Delta
        assert abs(cociente - round(cociente)) < 1e-9, (
            "El tiempo de una cuadra (%.1f s) no es múltiplo de Delta = %.3f s. "
            "Elegí H de modo que Gamma/H divida a %.1f." % (dat["t"], Delta, dat["t"]))
        assert 1 <= round(cociente) < H, (
            "Una cuadra ocupa %d de las %d capas: debe ser al menos 1 y menor que H."
            % (round(cociente), H))

    assert 1 <= L <= U <= H, "Debe cumplirse 1 <= L <= U <= H"
    apretadas = {p: n for p, n in red.ramas_de_acceso.items() if n * L > H}
    assert not apretadas, (
        "Estas intersecciones no entran en el período: %s. "
        "Necesitan cubrir sus ramas con fases de al menos L = %d intervalos, "
        "y H = %d no alcanza. Subí H o bajá L."
        % (", ".join("%s (%d ramas)" % (p, n) for p, n in sorted(apretadas.items())),
           L, H))

    # -------------------------------------------------------------------------
    #  2. Ingresos, egresos y clasificación de los arcos
    # -------------------------------------------------------------------------
    ingresos = sorted(v for v in red.V_ext if v.startswith("o"))
    egresos = sorted(v for v in red.V_ext if v.startswith("d"))
    tipo_ext = tipo_de_externo(red)
    semaforo_ext = toca_semaforo(red)
    peso, salientes = _red_dirigida(red, Delta)

    # -------------------------------------------------------------------------
    #  3. Puntaje de cada par origen-destino alcanzable
    # -------------------------------------------------------------------------
    pares: Dict[Tuple[str, str], dict] = {}
    for o in ingresos:
        for d in egresos:
            costo, camino = _camino(peso, salientes, o, d)
            if camino is None:
                continue
            pares[o, d] = dict(costo=costo, camino=camino,
                               puntaje=puntaje(o, d, tipo_ext, semaforo_ext,
                                               peso_avenida, peso_semaforo))
    assert pares, "Ningún ingreso alcanza un egreso: la red está desconectada"

    # -------------------------------------------------------------------------
    #  4. Qué ingresos generan demanda
    # -------------------------------------------------------------------------
    #  Se ordenan por el mejor puntaje que puede lograr cada origen y se toman
    #  los primeros según la cobertura, de modo que con cobertura parcial
    #  quedan seleccionados los que alimentan las avenidas.
    mejor_de = {o: max((p["puntaje"] for (oo, _), p in pares.items() if oo == o),
                       default=0.0) for o in ingresos}
    activos = [o for o in ingresos if mejor_de[o] > 0]
    activos.sort(key=lambda o: (-mejor_de[o], o))
    cuantos = max(1, int(round(cobertura * len(activos))))
    activos = sorted(activos[:cuantos])

    # -------------------------------------------------------------------------
    #  5. Elección de los destinos, con el puntaje como sesgo
    # -------------------------------------------------------------------------
    K, o_k, d_k, camino_k, puntaje_k = [], {}, {}, {}, {}
    for origen in activos:
        candidatos = [(d, pares[origen, d]) for (oo, d) in pares if oo == origen]
        if not candidatos:
            continue
        candidatos.sort(key=lambda t: (-t[1]["puntaje"], t[0]))
        pesos = [c[1]["puntaje"] ** 2 for c in candidatos]   # sesgo marcado
        elegidos: List[str] = []
        for _ in range(min(por_origen, len(candidatos))):
            disponibles = [(d, inf, w) for (d, inf), w in zip(candidatos, pesos)
                           if d not in elegidos]
            total = sum(w for _, _, w in disponibles)
            corte, acum = rng.random() * total, 0.0
            for d, inf, w in disponibles:
                acum += w
                if acum >= corte:
                    elegidos.append(d)
                    k = "k%d" % (len(K) + 1)
                    K.append(k)
                    o_k[k], d_k[k] = origen, d
                    camino_k[k], puntaje_k[k] = inf["camino"], inf["puntaje"]
                    break

    assert K, "No se pudo formar ningún producto"

    # -------------------------------------------------------------------------
    #  6. Dimensionamiento de las demandas
    # -------------------------------------------------------------------------
    #  La capacidad efectiva de un arco durante un período es su capacidad por
    #  intervalo multiplicada por la cantidad de intervalos. En los movimientos
    #  semaforizados se descuenta la proporción del período en la que están en
    #  rojo, estimada como la cantidad de ramas de acceso de la intersección:
    #  con una fase por rama, cada movimiento recibe alrededor de esa fracción.
    cap: Dict[Arco, float] = {}
    for a, dat in red.tramos.items():
        cap[a] = dat["u"] * Delta * H
    for p in red.P:
        divisor = max(red.ramas_de_acceso[p], 1)
        for a, dat in red.movimientos[p].items():
            cap[a] = dat["u"] * Delta * H / divisor

    #  Se parte de un volumen proporcional al puntaje, acotado por el cuello de
    #  botella del propio camino, y luego se escala hasta que ningún arco
    #  compartido supere la saturación buscada.
    D = {k: saturacion * min(cap[a] for a in camino_k[k]) * puntaje_k[k]
            / max(puntaje_k.values())
         for k in K}

    for _ in range(50):
        carga: Dict[Arco, float] = {}
        for k in K:
            for a in camino_k[k]:
                carga[a] = carga.get(a, 0.0) + D[k]
        peor, factor = None, 1.0
        for a, total in carga.items():
            permitido = saturacion * cap[a]
            if total > permitido + 1e-9 and permitido / total < factor:
                peor, factor = a, permitido / total
        if peor is None:
            break
        for k in K:
            if peor in camino_k[k]:
                D[k] *= factor
    else:
        print("  Aviso: el ajuste de las demandas no convergió en 50 pasadas. "
              "Algunos arcos quedan por encima de la saturación buscada.")

    D = {k: max(round(D[k], 1), 0.1) for k in K}

    # -------------------------------------------------------------------------
    #  7. Caminos prefijados
    # -------------------------------------------------------------------------
    #  Se fijan primero las demandas PASANTES de una avenida, es decir las que
    #  entran por una punta de una avenida y salen por la otra: su itinerario
    #  es el más previsible de todos, porque nadie que atraviese la avenida de
    #  punta a punta evalúa desviarse. Después, las de mayor puntaje. El resto
    #  conserva la asignación libre.
    R = None
    if caminos:
        def pasante(k: str) -> bool:
            lo = linea_de_externo(red, o_k[k])
            ld = linea_de_externo(red, d_k[k])
            return (lo is not None and lo == ld
                    and o_k[k][-1] == d_k[k][-1]
                    and tipo_ext.get(o_k[k]) == "avenida")

        orden = sorted(K, key=lambda k: (not pasante(k), -puntaje_k[k], k))
        cuantos = max(1, int(round(fraccion_prefijada * len(K))))
        K_R = sorted(orden[:cuantos])
        R = {k: camino_k[k] for k in K_R}

    # -------------------------------------------------------------------------
    #  8. La instancia
    # -------------------------------------------------------------------------
    base = nombre or "%s-%s" % (red.nombre, nivel)
    if caminos:
        base += "-caminos"

    return Instancia(
        nombre=base,
        descripcion=descripcion or (
            "Malla de %d x %d con %d intersecciones semaforizadas. "
            "Demanda %s: cobertura %.2f, saturación %.2f, semilla %d."
            % (red.filas, red.columnas, len(red.P), nivel,
               cobertura, saturacion, semilla)),
        Gamma=Gamma, H=H,
        V_ext=red.V_ext, esq_libres=red.esq_libres, X=red.X,
        movimientos=red.movimientos, P=red.P, tramos=red.tramos,
        kappa=red.kappa, G=red.G, E_pg=red.E_pg,
        L={(p, g): L for p in red.P for g in red.G[p]},
        U={(p, g): U for p in red.P for g in red.G[p]},
        K=K, o=o_k, d=d_k, D=D,
        R=R,
        repetidas_no_contiguas=True)


# =============================================================================
#  Resumen
# =============================================================================
def describir_demandas(inst: Instancia, red: Red) -> None:
    """Imprime las demandas generadas y dónde nace y muere cada una."""
    Delta = inst.Gamma / inst.H
    tipo_ext = tipo_de_externo(red)
    semaforo_ext = toca_semaforo(red)
    peso, salientes = _red_dirigida(red, Delta)

    def etiqueta(v: str) -> str:
        if tipo_ext.get(v) == "avenida":
            return "avenida"
        return "semáforo" if semaforo_ext.get(v) else "calle"

    print()
    print("=" * 70)
    print("DEMANDAS: %s" % inst.nombre)
    print("=" * 70)
    print("  Gamma = %.0f s   H = %d   Delta = %.1f s" % (inst.Gamma, inst.H, Delta))
    print("  Productos     : %d" % len(inst.K))
    print("  Demanda total : %.1f veh/período  (%.0f veh/h)"
          % (sum(inst.D.values()), sum(inst.D.values()) * 3600 / inst.Gamma))
    if inst.R:
        print("  Con camino prefijado: %d de %d" % (len(inst.R), len(inst.K)))

    print()
    print("  %-5s %-16s %-16s %9s %8s" % ("k", "origen", "destino", "veh/per", "viaje s"))
    for k in inst.K:
        _, camino = _camino(peso, salientes, inst.o[k], inst.d[k])
        fijo = "  (fijo)" if inst.R and k in inst.R else ""
        print("  %-5s %-16s %-16s %9.1f %8.0f%s"
              % (k,
                 "%s (%s)" % (inst.o[k], etiqueta(inst.o[k])),
                 "%s (%s)" % (inst.d[k], etiqueta(inst.d[k])),
                 inst.D[k], sum(peso[a] for a in camino), fijo))

    # --- reparto del volumen segun donde nace y muere -----------------------
    total = sum(inst.D.values())
    reparto = {2: 0.0, 1: 0.0, 0: 0.0}
    for k in inst.K:
        n = ((tipo_ext.get(inst.o[k]) == "avenida")
             + (tipo_ext.get(inst.d[k]) == "avenida"))
        reparto[n] += inst.D[k]

    if total > 0:
        print()
        print("  Volumen segun cuantas puntas estan sobre una avenida:")
        for n, texto in [(2, "las dos"), (1, "una"), (0, "ninguna")]:
            print("    %-8s %7.1f veh  (%3.0f %%)"
                  % (texto, reparto[n], 100 * reparto[n] / total))

    # --- demandas pasantes de una avenida -----------------------------------
    pasantes = [k for k in inst.K
                if linea_de_externo(red, inst.o[k]) is not None
                and linea_de_externo(red, inst.o[k]) == linea_de_externo(red, inst.d[k])
                and tipo_ext.get(inst.o[k]) == "avenida"]
    if pasantes:
        print()
        print("  Pasantes de una avenida (entran por una punta y salen por la otra): %s"
              % ", ".join(pasantes))