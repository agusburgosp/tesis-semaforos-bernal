
"""
Generador de la RED de una instancia: la parte geométrica.

Produce todo lo que define la zona de estudio sin depender del tiempo ni de la
demanda: nodos, calles, sentidos de circulación, qué esquinas están
semaforizadas, qué movimientos permite cada una y el catálogo de fases.

Lo que NO produce, porque corresponde a la segunda parte: el período Gamma, la
cantidad de capas H, las cotas L_pg y U_pg (que se miden en intervalos) y las
demandas.

Convención de la malla: las esquinas se indexan por (f, c), con f creciendo
hacia el sur y c creciendo hacia el este. Las columnas se nombran con letras y
las filas con números, de modo que la esquina (0, 0) se llama "A1".

        A1 ---- B1 ---- C1 ---- D1
         |       |       |       |
        A2 ---- B2 ---- C2 ---- D2
         |       |       |       |
        A3 ---- B3 ---- C3 ---- D3

Tipos de avenida
----------------
``doble``   doble mano, con semáforo en todas sus esquinas
``tipo1``   mano única, con semáforo cada dos cuadras
``tipo2``   mano única, con semáforo en cada cuadra

Una esquina queda semaforizada si alguna de las dos líneas que la forman le
corresponde un semáforo. El resto de las líneas son calles comunes sin
semáforo.
"""

from __future__ import annotations

import os
import string
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D

Arco = Tuple[str, str]
Movimiento = Tuple[str, str]          # (rama de acceso, rama de salida)

# --- geometría ---------------------------------------------------------------
RAMAS = ["N", "S", "E", "O"]
OPUESTA = {"N": "S", "S": "N", "E": "O", "O": "E"}

# Rama hacia la que dobla a la derecha quien ingresa por cada rama: el que
# entra por el norte circula hacia el sur, y su derecha es el oeste.
DERECHA = {"N": "O", "S": "E", "E": "N", "O": "S"}
IZQUIERDA = {ra: OPUESTA[rb] for ra, rb in DERECHA.items()}

TIPOS = ("doble", "tipo1", "tipo2")   # orden en que se colocan las avenidas


# =============================================================================
#  Resultado
# =============================================================================
@dataclass
class Red:
    """Parte geométrica de una instancia, lista para que la complete la parte 2."""

    nombre: str

    # --- lo que consume ``Instancia`` ---------------------------------------
    V_ext: List[str]
    esq_libres: List[str]
    X: Dict[str, List[str]]
    movimientos: Dict[str, Dict[Arco, dict]]
    P: List[str]
    tramos: Dict[Arco, dict]
    kappa: Dict[str, float]
    G: Dict[str, List[str]]
    E_pg: Dict[Tuple[str, str], List[Arco]]

    # --- información sobre cómo se construyó --------------------------------
    filas: int = 0
    columnas: int = 0
    esquina: Dict[Tuple[int, int], str] = field(default_factory=dict)
    tipo_linea_v: Dict[int, str] = field(default_factory=dict)   # columna -> tipo o "calle"
    tipo_linea_h: Dict[int, str] = field(default_factory=dict)   # fila -> tipo o "calle"
    dir_v: Dict[int, Set[str]] = field(default_factory=dict)
    dir_h: Dict[int, Set[str]] = field(default_factory=dict)
    movs_rama: Dict[str, List[Movimiento]] = field(default_factory=dict)
    fases_rama: Dict[str, Dict[str, List[Movimiento]]] = field(default_factory=dict)

    @property
    def ramas_de_acceso(self) -> Dict[str, int]:
        """Cantidad de ramas de acceso de cada intersección semaforizada.

        Es una cota SUPERIOR de la cantidad de fases necesaria para cubrir
        todos los movimientos: una fase por rama siempre alcanza. No es el
        mínimo, porque la fase de avenida completa cubre dos ramas opuestas de
        una sola vez. En un cruce de dos avenidas de doble mano este valor da
        cuatro y bastan dos fases.

        La parte 2 la usa para dos cosas, y en ambas el error es conservador:
        al verificar que las fases entren en el período puede rechazar alguna
        instancia que sería factible, y al estimar la capacidad de un
        movimiento la subestima.
        """
        return {p: len({ra for ra, _ in self.movs_rama[p]}) for p in self.P}


# =============================================================================
#  Nombres
# =============================================================================
def _nombre_esquina(f: int, c: int) -> str:
    """Letra de la columna más número de la fila: (0, 0) -> 'A1'."""
    letras = string.ascii_uppercase
    if c < len(letras):
        letra = letras[c]
    else:
        letra = letras[c // len(letras) - 1] + letras[c % len(letras)]
    return "%s%d" % (letra, f + 1)


def _etiqueta_columna(c: int) -> str:
    return _nombre_esquina(0, c)[:-1]


def acc(esq: str, rama: str) -> str:
    """Nodo de acceso a la esquina por la rama indicada."""
    return "%s_e%s" % (esq, rama)


def sal(esq: str, rama: str) -> str:
    """Nodo de salida de la esquina hacia la rama indicada."""
    return "%s_s%s" % (esq, rama)


# =============================================================================
#  Movimientos permitidos
# =============================================================================
def tipo_de_giro(ra: str, rb: str) -> str:
    """Clasifica el movimiento que entra por ``ra`` y sale hacia ``rb``."""
    if rb == OPUESTA[ra]:
        return "recto"
    if rb == DERECHA[ra]:
        return "derecha"
    return "izquierda"


def movimientos_permitidos(entrantes: Set[str], salientes: Set[str]) -> List[Movimiento]:
    """Movimientos de una esquina, según sus ramas de acceso y de salida.

    Criterio por defecto:

    * el giro en U nunca se admite;
    * el movimiento recto y el giro a la derecha siempre se admiten, si la
      rama de salida existe;
    * el giro a la izquierda de ``ra`` hacia ``rb`` se admite únicamente si no
      cruza ninguna corriente. Lo impiden dos situaciones: que la rama opuesta
      a ``ra`` sea entrante, porque entonces hay tránsito de frente; o que la
      propia ``rb`` sea entrante, porque entonces al doblar se cruza la
      corriente que viene de esa calle.

    Con este criterio, una esquina sobre una avenida de doble mano no admite
    giros a la izquierda, mientras que el cruce de dos calles de mano única sí
    puede admitirlos.
    """
    movs: List[Movimiento] = []
    for ra in sorted(entrantes):
        for rb in sorted(salientes):
            if ra == rb:
                continue                      # giro en U
            giro = tipo_de_giro(ra, rb)
            if giro == "izquierda":
                if OPUESTA[ra] in entrantes:  # corriente opuesta de frente
                    continue
                if rb in entrantes:           # se cruza la corriente de rb
                    continue
            movs.append((ra, rb))
    return movs


# =============================================================================
#  Fases
# =============================================================================
def fases_permitidas(movs: Sequence[Movimiento],
                     entrantes: Set[str]) -> Dict[str, List[Movimiento]]:
    """Catálogo de configuraciones compatibles de una esquina.

    Se generan dos familias, ambas libres de conflictos por construcción:

    * una fase por rama de acceso, con todos sus movimientos. Dos movimientos
      que llegan por la misma rama nunca se cruzan entre sí. Estas fases solas
      ya cubren todos los movimientos de la esquina.
    * para cada par de ramas opuestas que sean ambas entrantes, la fase que
      habilita los dos movimientos rectos junto con sus giros a la derecha.
      Es la configuración de "avenida completa": dos corrientes opuestas que
      siguen derecho no se cruzan, y un giro a la derecha tampoco cruza a la
      corriente opuesta.

    Los nombres son la rama o el par de ramas: "N", "O", "NS".
    """
    fases: Dict[str, List[Movimiento]] = {}

    for ra in sorted(entrantes):
        lista = [m for m in movs if m[0] == ra]
        if lista:
            fases[ra] = lista

    vistos = set()
    for ra in sorted(entrantes):
        op = OPUESTA[ra]
        if op not in entrantes or (op, ra) in vistos:
            continue
        vistos.add((ra, op))
        lista = [m for m in movs
                 if m[0] in (ra, op) and tipo_de_giro(m[0], m[1]) in ("recto", "derecha")]
        if lista and list(lista) not in [list(v) for v in fases.values()]:
            fases["".join(sorted((ra, op)))] = lista

    return fases


# =============================================================================
#  Generador
# =============================================================================
def generar_red(filas: int,
                columnas: int,
                avenidas_v: Optional[Dict[str, int]] = None,
                separacion_v: int = 2,
                inicio_v: int = 0,
                avenidas_h: Optional[Dict[str, int]] = None,
                separacion_h: int = 2,
                inicio_h: int = 0,
                cuadra: float = 15.0,
                u_calle: float = 1.0,
                u_recto: float = 1.0,
                u_giro: float = 0.5,
                kappa_acceso: float = 20.0,
                kappa_libre: float = 20.0,
                kappa_salida: float = 0.0,
                kappa_ingreso: float = float("inf"),
                kappa_egreso: float = 0.0,
                copias_por_fase: int = 2,
                sentidos_v: Optional[Dict[int, str]] = None,
                sentidos_h: Optional[Dict[int, str]] = None,
                movimientos_extra: Optional[Dict[str, List[Movimiento]]] = None,
                movimientos_quitar: Optional[Dict[str, List[Movimiento]]] = None,
                fases_extra: Optional[Dict[str, Dict[str, List[Movimiento]]]] = None,
                fases_reemplazo: Optional[Dict[str, Dict[str, List[Movimiento]]]] = None,
                semaforos_extra: Sequence[str] = (),
                semaforos_quitar: Sequence[str] = (),
                nombre: Optional[str] = None) -> Red:
    """Construye la red de una malla de ``filas`` x ``columnas`` esquinas.

    Avenidas
    --------
    ``avenidas_v`` y ``avenidas_h`` son diccionarios con la cantidad de cada
    tipo, por ejemplo ``dict(doble=1, tipo1=2)``. Se colocan en ese orden
    (primero las de doble mano, después las de tipo 1 y por último las de tipo
    2), empezando en la línea ``inicio`` y separadas por ``separacion`` cuadras.
    Las líneas restantes son calles comunes, sin semáforo.

    Sentidos
    --------
    Alternan como en una malla de manos únicas: las columnas pares bajan y las
    impares suben, las filas pares van al este y las impares al oeste. Las
    avenidas de doble mano tienen los dos sentidos. Con ``sentidos_v`` y
    ``sentidos_h`` se puede forzar el sentido de una línea: por ejemplo
    ``sentidos_v={2: "N"}`` o ``sentidos_h={1: "EO"}``.

    Puntos donde intervenir a mano
    ------------------------------
    ``movimientos_extra`` / ``movimientos_quitar``
        Agregan o quitan movimientos de una esquina, como
        ``{"B2": [("O", "N")]}``. Sirve para habilitar un giro a la izquierda
        que el criterio general descarta.
    ``fases_extra``
        Agrega fases a una esquina: ``{"B2": {"mi_fase": [("N", "S")]}}``.
    ``fases_reemplazo``
        Reemplaza por completo el catálogo de una esquina.
    ``semaforos_extra`` / ``semaforos_quitar``
        Semaforizan o desemaforizan esquinas puntuales.
    ``copias_por_fase``
        Cuántas copias de cada configuración se incluyen en G_p. Con 2, cada
        configuración aparece dos veces con distinto nombre, de modo que puede
        recibir dos bloques de verde separados en el período. La restricción
        (22) impide que esos bloques queden contiguos.
    """
    avenidas_v = dict(avenidas_v or {})
    avenidas_h = dict(avenidas_h or {})
    sv, sh = dict(sentidos_v or {}), dict(sentidos_h or {})
    mov_extra = {k: list(v) for k, v in (movimientos_extra or {}).items()}
    mov_quitar = {k: list(v) for k, v in (movimientos_quitar or {}).items()}

    # -------------------------------------------------------------------------
    #  1. Ubicación y tipo de cada línea
    # -------------------------------------------------------------------------
    def colocar(cuenta: Dict[str, int], separacion: int, inicio: int,
                total: int, orientacion: str) -> Dict[int, str]:
        secuencia = [t for t in TIPOS for _ in range(cuenta.get(t, 0))]
        tipos = {}
        for n, t in enumerate(secuencia):
            idx = inicio + n * separacion
            assert 0 <= idx < total, (
                "La avenida %s número %d cae en la línea %s %d, fuera de la malla"
                % (t, n + 1, orientacion, idx))
            tipos[idx] = t
        return tipos

    tipo_v = colocar(avenidas_v, separacion_v, inicio_v, columnas, "vertical")
    tipo_h = colocar(avenidas_h, separacion_h, inicio_h, filas, "horizontal")

    tipo_linea_v = {c: tipo_v.get(c, "calle") for c in range(columnas)}
    tipo_linea_h = {f: tipo_h.get(f, "calle") for f in range(filas)}

    # -------------------------------------------------------------------------
    #  2. Sentido de cada línea
    # -------------------------------------------------------------------------
    def dir_vertical(c: int) -> Set[str]:
        if c in sv:
            return set(sv[c])
        if tipo_linea_v[c] == "doble":
            return {"S", "N"}
        return {"S"} if c % 2 == 0 else {"N"}

    def dir_horizontal(f: int) -> Set[str]:
        if f in sh:
            return set(sh[f])
        if tipo_linea_h[f] == "doble":
            return {"E", "O"}
        return {"E"} if f % 2 == 0 else {"O"}

    dir_v = {c: dir_vertical(c) for c in range(columnas)}
    dir_h = {f: dir_horizontal(f) for f in range(filas)}

    # -------------------------------------------------------------------------
    #  3. Ramas de acceso y de salida de cada esquina
    # -------------------------------------------------------------------------
    esquina = {(f, c): _nombre_esquina(f, c)
               for f in range(filas) for c in range(columnas)}

    entrantes: Dict[str, Set[str]] = {}
    salientes: Dict[str, Set[str]] = {}
    for f in range(filas):
        for c in range(columnas):
            ent, sl = set(), set()
            for s in dir_h[f]:
                ent.add("O" if s == "E" else "E")
                sl.add("E" if s == "E" else "O")
            for s in dir_v[c]:
                ent.add("N" if s == "S" else "S")
                sl.add("S" if s == "S" else "N")
            entrantes[esquina[f, c]], salientes[esquina[f, c]] = ent, sl

    # -------------------------------------------------------------------------
    #  4. Qué esquinas llevan semáforo
    # -------------------------------------------------------------------------
    #  doble y tipo2: semáforo en todas las esquinas de la línea.
    #  tipo1: semáforo cada dos cuadras, empezando por la primera esquina.
    def hay_semaforo(tipo: str, posicion: int) -> bool:
        if tipo in ("doble", "tipo2"):
            return True
        if tipo == "tipo1":
            return posicion % 2 == 0
        return False

    semaforizadas: Set[str] = set()
    for f in range(filas):
        for c in range(columnas):
            p = esquina[f, c]
            if hay_semaforo(tipo_linea_v[c], f) or hay_semaforo(tipo_linea_h[f], c):
                semaforizadas.add(p)
    semaforizadas |= set(semaforos_extra)
    semaforizadas -= set(semaforos_quitar)

    # -------------------------------------------------------------------------
    #  5. Movimientos de cada esquina semaforizada
    # -------------------------------------------------------------------------
    movs_rama: Dict[str, List[Movimiento]] = {}
    for p in sorted(semaforizadas):
        lista = movimientos_permitidos(entrantes[p], salientes[p])
        for m in mov_extra.get(p, []):
            assert m[0] in entrantes[p] and m[1] in salientes[p], \
                "El movimiento %s no es posible en %s con sus ramas" % (str(m), p)
            if m not in lista:
                lista.append(m)
        for m in mov_quitar.get(p, []):
            if m in lista:
                lista.remove(m)
        assert lista, "La esquina %s quedó sin movimientos" % p
        movs_rama[p] = sorted(lista)

    P = sorted(movs_rama)
    esq_libres = sorted(esquina[f, c] for f in range(filas) for c in range(columnas)
                        if esquina[f, c] not in semaforizadas)

    # X_p y los movimientos como arcos entre nodos
    X: Dict[str, List[str]] = {}
    movimientos: Dict[str, Dict[Arco, dict]] = {}
    for p in P:
        ramas_acc = sorted({ra for ra, _ in movs_rama[p]})
        ramas_sal = sorted({rb for _, rb in movs_rama[p]})
        X[p] = [acc(p, r) for r in ramas_acc] + [sal(p, r) for r in ramas_sal]
        movimientos[p] = {
            (acc(p, ra), sal(p, rb)): dict(
                l=1, u=u_recto if tipo_de_giro(ra, rb) == "recto" else u_giro)
            for ra, rb in movs_rama[p]}

    # -------------------------------------------------------------------------
    #  6. Las calles
    # -------------------------------------------------------------------------
    tramos: Dict[Arco, dict] = {}
    V_ext: List[str] = []
    ingresos: Set[str] = set()
    egresos: Set[str] = set()

    def n_acc(f: int, c: int, rama: str) -> str:
        p = esquina[f, c]
        return acc(p, rama) if p in semaforizadas else p

    def n_sal(f: int, c: int, rama: str) -> str:
        p = esquina[f, c]
        return sal(p, rama) if p in semaforizadas else p

    def calle(origen: str, destino: str) -> None:
        tramos[(origen, destino)] = dict(t=cuadra, u=u_calle)

    # --- filas ---------------------------------------------------------------
    for f in range(filas):
        for s in sorted(dir_h[f]):
            if s == "E":
                orden, r_ent, r_sal = list(range(columnas)), "O", "E"
            else:
                orden, r_ent, r_sal = list(range(columnas - 1, -1, -1)), "E", "O"
            o_ext, d_ext = "o%d%s" % (f + 1, s), "d%d%s" % (f + 1, s)
            V_ext += [o_ext, d_ext]
            ingresos.add(o_ext)
            egresos.add(d_ext)
            calle(o_ext, n_acc(f, orden[0], r_ent))
            for a, b in zip(orden, orden[1:]):
                calle(n_sal(f, a, r_sal), n_acc(f, b, r_ent))
            calle(n_sal(f, orden[-1], r_sal), d_ext)

    # --- columnas ------------------------------------------------------------
    for c in range(columnas):
        letra = _etiqueta_columna(c)
        for s in sorted(dir_v[c]):
            if s == "S":
                orden, r_ent, r_sal = list(range(filas)), "N", "S"
            else:
                orden, r_ent, r_sal = list(range(filas - 1, -1, -1)), "S", "N"
            o_ext, d_ext = "o%s%s" % (letra, s), "d%s%s" % (letra, s)
            V_ext += [o_ext, d_ext]
            ingresos.add(o_ext)
            egresos.add(d_ext)
            calle(o_ext, n_acc(orden[0], c, r_ent))
            for a, b in zip(orden, orden[1:]):
                calle(n_sal(a, c, r_sal), n_acc(b, c, r_ent))
            calle(n_sal(orden[-1], c, r_sal), d_ext)

    # -------------------------------------------------------------------------
    #  7. Capacidad de almacenamiento
    # -------------------------------------------------------------------------
    kappa: Dict[str, float] = {}
    for i in list(V_ext) + list(esq_libres) + [n for p in P for n in X[p]]:
        if i in ingresos:
            kappa[i] = kappa_ingreso
        elif i in egresos:
            kappa[i] = kappa_egreso
        elif i in esq_libres:
            kappa[i] = kappa_libre
        elif "_e" in i:
            kappa[i] = kappa_acceso
        else:
            kappa[i] = kappa_salida

    # -------------------------------------------------------------------------
    #  8. Fases
    # -------------------------------------------------------------------------
    fases_rama: Dict[str, Dict[str, List[Movimiento]]] = {}
    for p in P:
        if fases_reemplazo and p in fases_reemplazo:
            base = {g: list(movs) for g, movs in fases_reemplazo[p].items()}
        else:
            base = fases_permitidas(movs_rama[p], entrantes[p])
            for g, movs in (fases_extra or {}).get(p, {}).items():
                base[g] = list(movs)
        for g, movs in base.items():
            for m in movs:
                assert m in movs_rama[p], \
                    "La fase %s de %s habilita %s, que no es movimiento suyo" \
                    % (g, p, str(m))
        union = {m for movs in base.values() for m in movs}
        assert union == set(movs_rama[p]), \
            "El catálogo de %s no cubre todos sus movimientos: falta %s" \
            % (p, sorted(set(movs_rama[p]) - union))
        fases_rama[p] = base

    # Copias: cada configuración aparece ``copias_por_fase`` veces
    G: Dict[str, List[str]] = {}
    E_pg: Dict[Tuple[str, str], List[Arco]] = {}
    for p in P:
        nombres = []
        for g, movs in sorted(fases_rama[p].items()):
            for n in range(1, copias_por_fase + 1):
                gn = "%s%d" % (g, n)
                nombres.append(gn)
                E_pg[p, gn] = [(acc(p, ra), sal(p, rb)) for ra, rb in movs]
        G[p] = nombres

    return Red(
        nombre=nombre or "malla%dx%d" % (filas, columnas),
        V_ext=V_ext, esq_libres=esq_libres, X=X,
        movimientos=movimientos, P=P, tramos=tramos, kappa=kappa,
        G=G, E_pg=E_pg,
        filas=filas, columnas=columnas, esquina=esquina,
        tipo_linea_v=tipo_linea_v, tipo_linea_h=tipo_linea_h,
        dir_v=dir_v, dir_h=dir_h,
        movs_rama=movs_rama, fases_rama=fases_rama)


# =============================================================================
#  Resumen
# =============================================================================
def describir(red: Red, con_fases: bool = True,
              mapa: bool = True, archivo: Optional[str] = None) -> None:
    """Imprime cómo quedó la red generada y, si se pide, dibuja su mapa."""
    FLECHA = {"S": "v", "N": "^", "E": ">", "O": "<"}

    print()
    print("=" * 70)
    print("RED GENERADA: %s" % red.nombre)
    print("=" * 70)
    print("  Malla            : %d filas x %d columnas = %d esquinas"
          % (red.filas, red.columnas, red.filas * red.columnas))
    print("  Semaforizadas    : %d de %d" % (len(red.P), red.filas * red.columnas))
    print("  Nodos            : %d   arcos: %d  (de los cuales %d son movimientos)"
          % (len(red.kappa), len(red.tramos) + sum(len(m) for m in red.movimientos.values()),
             sum(len(m) for m in red.movimientos.values())))

    print()
    print("  Columnas:")
    for c in sorted(red.dir_v):
        print("    %-3s %-6s  sentido %s"
              % (_etiqueta_columna(c), red.tipo_linea_v[c],
                 " ".join(FLECHA[s] for s in sorted(red.dir_v[c]))))
    print("  Filas:")
    for f in sorted(red.dir_h):
        print("    %-3d %-6s  sentido %s"
              % (f + 1, red.tipo_linea_h[f],
                 " ".join(FLECHA[s] for s in sorted(red.dir_h[f]))))

    print()
    print("  Esquinas (* = semaforizada):")
    for f in range(red.filas):
        fila = "    "
        for c in range(red.columnas):
            p = red.esquina[f, c]
            fila += "%-6s" % ("%s%s" % (p, "*" if p in red.P else " "))
        print(fila)

    if mapa:
        ruta = dibujar(red, archivo)
        if ruta:
            print()
            print("  mapa: %s" % _mostrar(ruta))

    if not con_fases:
        return

    print()
    print("  Movimientos y fases de cada intersección semaforizada:")
    for p in red.P:
        movs = ", ".join("%s->%s" % m for m in red.movs_rama[p])
        print()
        print("    %s   movimientos: %s" % (p, movs))
        print("       ramas de acceso: %d  (una fase por rama alcanza para "
              "cubrir todos los movimientos)" % red.ramas_de_acceso[p])
        for g, lista in sorted(red.fases_rama[p].items()):
            copias = [gn for gn in red.G[p] if gn.rstrip("0123456789") == g]
            print("       %-4s %-34s copias: %s"
                  % (g, ", ".join("%s->%s" % m for m in lista), ", ".join(copias)))


# =============================================================================
#  Mapa de la red
# =============================================================================
#  Dibuja la geometría: las calles con su sentido, qué esquinas tienen semáforo
#  y qué línea es avenida. No interviene el tiempo ni la demanda.

C_CALLE = "#95a5a6"          # calle común
C_TIPO1 = "#e67e22"          # avenida de mano única, semáforo cada dos cuadras
C_TIPO2 = "#d35400"          # avenida de mano única, semáforo cada cuadra
C_DOBLE = "#2c3e50"          # avenida de doble mano
C_SEMAFORO = "#2e8b57"
C_TEXTO = "#2c3e50"

_COLOR_TIPO = {"calle": C_CALLE, "tipo1": C_TIPO1,
               "tipo2": C_TIPO2, "doble": C_DOBLE}
_ANCHO_TIPO = {"calle": 1.4, "tipo1": 2.6, "tipo2": 2.6, "doble": 3.2}

CARRIL = 0.07                # separación entre los dos sentidos de una avenida
BORDE = 0.55                 # cuánto sobresalen las puntas del borde

#  Carpeta donde se guardan las imágenes. Se resuelve relativa a la ubicación
#  de este archivo, de modo que funciona sin importar desde dónde se corra
#  Python. Si se pasa una ruta con carpeta, esa ruta se respeta tal cual.
CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Visuales red")


def _ruta(archivo: Optional[str], predeterminado: str) -> str:
    """Resuelve el nombre del archivo dentro de la carpeta de imágenes."""
    nombre = archivo or predeterminado
    if os.path.dirname(nombre):
        return nombre                      # ruta explícita: se respeta
    os.makedirs(CARPETA, exist_ok=True)
    return os.path.join(CARPETA, nombre)


def _mostrar(ruta: str) -> str:
    """Ruta acortada para imprimir."""
    try:
        return os.path.relpath(ruta)
    except ValueError:
        return ruta


def dibujar(red: Red, archivo: Optional[str] = None,
            con_nombres: bool = True,
            con_externos: bool = True,
            escala: float = 1.6) -> Optional[str]:
    """Dibuja el mapa de la red y lo guarda como PNG.

    Las flechas muestran el sentido de circulación; una avenida de doble mano
    aparece con sus dos carriles. Las esquinas semaforizadas se marcan con un
    círculo relleno y las demás con uno hueco.
    """

    archivo = _ruta(archivo, "%s_mapa.png" % red.nombre)
    F, C = red.filas, red.columnas
    pos = {(f, c): (float(c), -float(f)) for f in range(F) for c in range(C)}

    fig, ax = plt.subplots(figsize=(escala * (C + 1.6), escala * (F + 1.6)))

    def flecha(p0, p1, color, ancho, alfa=0.95):
        ax.add_patch(FancyArrowPatch(
            p0, p1, arrowstyle="-|>", mutation_scale=11, linewidth=ancho,
            color=color, alpha=alfa, shrinkA=9, shrinkB=9, zorder=1))

    # --- columnas ------------------------------------------------------------
    for c in range(C):
        tipo = red.tipo_linea_v[c]
        color, ancho = _COLOR_TIPO[tipo], _ANCHO_TIPO[tipo]
        for s in sorted(red.dir_v[c]):
            dx = -CARRIL if s == "S" else CARRIL
            orden = range(F) if s == "S" else range(F - 1, -1, -1)
            orden = list(orden)
            for a, b in zip(orden, orden[1:]):
                flecha((pos[a, c][0] + dx, pos[a, c][1]),
                       (pos[b, c][0] + dx, pos[b, c][1]), color, ancho)
            if con_externos:
                ini, fin = orden[0], orden[-1]
                signo = 1.0 if s == "S" else -1.0
                flecha((pos[ini, c][0] + dx, pos[ini, c][1] + signo * BORDE),
                       (pos[ini, c][0] + dx, pos[ini, c][1]), color, ancho, 0.5)
                flecha((pos[fin, c][0] + dx, pos[fin, c][1]),
                       (pos[fin, c][0] + dx, pos[fin, c][1] - signo * BORDE),
                       color, ancho, 0.5)

    # --- filas ---------------------------------------------------------------
    for f in range(F):
        tipo = red.tipo_linea_h[f]
        color, ancho = _COLOR_TIPO[tipo], _ANCHO_TIPO[tipo]
        for s in sorted(red.dir_h[f]):
            dy = -CARRIL if s == "E" else CARRIL
            orden = list(range(C)) if s == "E" else list(range(C - 1, -1, -1))
            for a, b in zip(orden, orden[1:]):
                flecha((pos[f, a][0], pos[f, a][1] + dy),
                       (pos[f, b][0], pos[f, b][1] + dy), color, ancho)
            if con_externos:
                ini, fin = orden[0], orden[-1]
                signo = -1.0 if s == "E" else 1.0
                flecha((pos[f, ini][0] + signo * BORDE, pos[f, ini][1] + dy),
                       (pos[f, ini][0], pos[f, ini][1] + dy), color, ancho, 0.5)
                flecha((pos[f, fin][0], pos[f, fin][1] + dy),
                       (pos[f, fin][0] - signo * BORDE, pos[f, fin][1] + dy),
                       color, ancho, 0.5)

    # --- esquinas ------------------------------------------------------------
    for f in range(F):
        for c in range(C):
            p = red.esquina[f, c]
            x, y = pos[f, c]
            semaforizada = p in red.P
            ax.plot(x, y, "o", markersize=16,
                    color=C_SEMAFORO if semaforizada else "white",
                    markeredgecolor=C_TEXTO,
                    markeredgewidth=1.5 if semaforizada else 1.0, zorder=4)
            if con_nombres:
                ax.text(x, y, p, fontsize=6.5, ha="center", va="center", zorder=5,
                        color="white" if semaforizada else C_TEXTO,
                        fontweight="bold" if semaforizada else "normal")

    # --- etiquetas de las líneas --------------------------------------------
    for c in range(C):
        ax.text(c, 0.95, _etiqueta_columna(c), fontsize=9, ha="center",
                va="bottom", color=_COLOR_TIPO[red.tipo_linea_v[c]],
                fontweight="bold")
    for f in range(F):
        ax.text(-1.05, -f, "%d" % (f + 1), fontsize=9, ha="right", va="center",
                color=_COLOR_TIPO[red.tipo_linea_h[f]], fontweight="bold")

    # --- referencias ---------------------------------------------------------
    usados = set(red.tipo_linea_v.values()) | set(red.tipo_linea_h.values())
    etiqueta = {"calle": "calle común (sin semáforo)",
                "tipo1": "avenida mano única, semáforo cada 2 cuadras",
                "tipo2": "avenida mano única, semáforo cada cuadra",
                "doble": "avenida doble mano, semáforo en cada esquina"}
    refs = [Line2D([0], [0], color=_COLOR_TIPO[t], lw=_ANCHO_TIPO[t],
                   label=etiqueta[t]) for t in TIPOS + ("calle",) if t in usados]
    refs.append(Line2D([0], [0], marker="o", color="none", label="esquina semaforizada",
                       markerfacecolor=C_SEMAFORO, markeredgecolor=C_TEXTO,
                       markersize=10))
    refs.append(Line2D([0], [0], marker="o", color="none", label="esquina sin semáforo",
                       markerfacecolor="white", markeredgecolor=C_TEXTO,
                       markersize=8))
    ax.legend(handles=refs, loc="upper center", bbox_to_anchor=(0.5, -0.01),
              fontsize=8, frameon=False, ncol=2)

    ax.set_title("%s — %d x %d esquinas, %d semaforizadas"
                 % (red.nombre, F, C, len(red.P)), fontsize=12)
    ax.set_xlim(-1.3, C - 1 + 1.0)
    ax.set_ylim(-(F - 1) - 1.0, 1.3)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(archivo, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return archivo


def dibujar_esquina(red: Red, p: str, archivo: Optional[str] = None,
                    escala: float = 4.0) -> Optional[str]:
    """Dibuja el subgrafo de una intersección semaforizada.

    Muestra sus nodos de acceso y de salida con los movimientos internos, con
    la misma geometría de la figura de la tesis: el nodo de acceso queda a la
    derecha del sentido de circulación y el de salida enfrentado.
    """

    assert p in red.P, "%s no es una intersección semaforizada" % p
    archivo = _ruta(archivo, "%s_%s.png" % (red.nombre, p))

    SEP, DIST, EXT = 0.20, 0.46, 0.42
    OFFSET = {("N", "e"): (-SEP, DIST), ("N", "s"): (SEP, DIST),
              ("S", "e"): (SEP, -DIST), ("S", "s"): (-SEP, -DIST),
              ("E", "e"): (DIST, SEP), ("E", "s"): (DIST, -SEP),
              ("O", "e"): (-DIST, -SEP), ("O", "s"): (-DIST, SEP)}
    HACIA = {"N": (0.0, 1.0), "S": (0.0, -1.0), "E": (1.0, 0.0), "O": (-1.0, 0.0)}
    C_ACCESO, C_SALIDA = "#ffb6c1", "#e8e8e8"

    ramas_acc = sorted({ra for ra, _ in red.movs_rama[p]})
    ramas_sal = sorted({rb for _, rb in red.movs_rama[p]})

    fig, ax = plt.subplots(figsize=(escala, escala * 1.15))
    coord = {}
    for r in ramas_acc:
        coord["e", r] = OFFSET[r, "e"]
    for r in ramas_sal:
        coord["s", r] = OFFSET[r, "s"]

    # tramos que entran y salen de la esquina
    for (tipo, r), (x, y) in coord.items():
        dx, dy = HACIA[r]
        lejos = (x + dx * EXT, y + dy * EXT)
        p0, p1 = (lejos, (x, y)) if tipo == "e" else ((x, y), lejos)
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=10,
                                     linewidth=1.8, color=C_CALLE, alpha=0.7,
                                     shrinkA=7, shrinkB=7, zorder=1))

    # movimientos internos
    for ra, rb in red.movs_rama[p]:
        giro = tipo_de_giro(ra, rb)
        color = {"recto": C_DOBLE, "derecha": C_SEMAFORO,
                 "izquierda": C_TIPO2}[giro]
        ax.add_patch(FancyArrowPatch(
            coord["e", ra], coord["s", rb], arrowstyle="-|>", mutation_scale=12,
            linewidth=2.2, color=color, alpha=0.9, shrinkA=11, shrinkB=11,
            connectionstyle="arc3,rad=0.22", zorder=2))

    for (tipo, r), (x, y) in coord.items():
        ax.plot(x, y, "o", markersize=19,
                color=C_ACCESO if tipo == "e" else C_SALIDA,
                markeredgecolor=C_TEXTO, markeredgewidth=1.1, zorder=3)
        ax.text(x, y, "%s%s" % (tipo, r), fontsize=8, ha="center", va="center",
                zorder=4, color=C_TEXTO, fontweight="bold")

    refs = [Line2D([0], [0], color=C_DOBLE, lw=2.2, label="recto"),
            Line2D([0], [0], color=C_SEMAFORO, lw=2.2, label="giro a la derecha"),
            Line2D([0], [0], color=C_TIPO2, lw=2.2, label="giro a la izquierda"),
            Line2D([0], [0], marker="o", color="none", label="nodo de acceso",
                   markerfacecolor=C_ACCESO, markeredgecolor=C_TEXTO, markersize=10),
            Line2D([0], [0], marker="o", color="none", label="nodo de salida",
                   markerfacecolor=C_SALIDA, markeredgecolor=C_TEXTO, markersize=10)]
    ax.legend(handles=refs, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              fontsize=7.5, frameon=False, ncol=2)

    lineas = ["%s: %s" % (g, ", ".join("%s>%s" % m for m in lista))
              for g, lista in sorted(red.fases_rama[p].items())]
    ax.set_title("%s   ·   accesos %s   ·   salidas %s\n%s"
                 % (p, " ".join(ramas_acc), " ".join(ramas_sal),
                    "\n".join(lineas)), fontsize=8)
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(archivo, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return archivo