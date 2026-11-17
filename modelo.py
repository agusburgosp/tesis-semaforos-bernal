"""

Coordinación semafórica con asignación de tráfico.
Formulación (10)-(29) implementada con Gurobi.

Este archivo NO contiene datos de ninguna instancia. Recibe un objeto
``Instancia`` (los datos crudos de la zona de estudio), deriva a partir de él
la red cíclicamente expandida en el tiempo, arma el PLEM, lo resuelve, reporta
la solución y verifica que satisfaga cada familia de restricciones.

"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import gurobipy as gp
from gurobipy import GRB

# Un arco físico es un par ordenado de nodos: (cola, cabeza)
Arco = Tuple[str, str]


# =============================================================================
#  Datos de entrada de una instancia
# =============================================================================
@dataclass
class Instancia:
    """Datos crudos de una zona de estudio.

    Contiene únicamente lo que distingue a una instancia de otra. Todo lo que
    se deduce de estos datos (la red expandida, las incidencias, las
    capacidades por intervalo) lo calcula ``preparar``.
    """

    nombre: str

    # --- período común -------------------------------------------------------
    Gamma: float                      # duración del período [s] (ciclo semafórico)
    H: int                            # cantidad de intervalos del período

    # --- geometría -----------------------------------------------------------
    V_ext: List[str]                  # nodos de ingreso y egreso de la zona
    esq_libres: List[str]             # esquinas representadas por un único nodo
    X: Dict[str, List[str]]           # X_p : nodos de acceso y salida de cada esquina
    movimientos: Dict[str, Dict[Arco, dict]]   # movimientos internos de cada esquina
    P: List[str]                      # esquinas SEMAFORIZADAS
    tramos: Dict[Arco, dict]          # calles: dict(t=segundos, u=veh/s)
    kappa: Dict[str, float]           # kappa_i : capacidad de almacenamiento del nodo

    # --- fases semafóricas ---------------------------------------------------
    G: Dict[str, List[str]]                    # G_p  : catálogo de fases
    E_pg: Dict[Tuple[str, str], List[Arco]]    # E_pg : movimientos que habilita la fase
    L: Dict[Tuple[str, str], int]              # L_pg : duración mínima [intervalos]
    U: Dict[Tuple[str, str], int]              # U_pg : duración máxima [intervalos]

    # --- demandas ------------------------------------------------------------
    K: List[str]                      # productos origen-destino
    o: Dict[str, str]                 # o_k : nodo de origen
    d: Dict[str, str]                 # d_k : nodo de destino
    D: Dict[str, float]               # D_k : demanda total por período

    # Distribución de la demanda entre las capas. Si no se indica, se reparte
    # de manera uniforme: D_kh = D_k / H.
    D_kh: Optional[Dict[Tuple[str, int], float]] = None

    # R_k : camino dirigido asignado al producto k, como la secuencia ordenada
    # de arcos físicos (a_1^k, ..., a_{m_k}^k) que lo componen.
    #
    #   R = None  -> variante con ASIGNACIÓN DE TRÁFICO: el modelo decide por
    #                dónde circula cada producto.
    #   R = {...} -> variante con CAMINOS PREFIJADOS: se agregan las
    #                restricciones (30) y (31), que confinan cada producto al
    #                subgrafo cíclicamente expandido de su recorrido.
    #
    # El diccionario NO necesita cubrir todos los productos. Los que no
    # aparecen en R conservan la asignación libre, de modo que (30) y (31) se
    # imponen sólo sobre los que sí tienen recorrido asignado. Eso permite una
    # configuración mixta: algunas demandas con camino conocido y otras cuyo
    # recorrido sigue siendo una decisión del modelo.
    R: Optional[Dict[str, List[Arco]]] = None

    # Fases que deben formar parte del plan sí o sí: se fija z_pg = 1.
    #
    # El caso típico es la fase peatonal, que no habilita ningún movimiento
    # (E_pg vacío) y por lo tanto deja la intersección entera en rojo. Como no
    # aporta a la cobertura (19) ni mejora el objetivo, el modelo nunca la
    # elegiría por su cuenta: hay que imponerla. Con L_pg = U_pg se le fija
    # además la duración exacta.
    #
    #     fases_obligatorias={"P1": ["peatonal"], "P2": ["peatonal"]}
    fases_obligatorias: Optional[Dict[str, List[str]]] = None

    # Dos fases con el mismo conjunto E_pg son, en los hechos, la misma fase
    # con otro nombre. Nada impide que el modelo las programe una a
    # continuación de la otra, y así el conjunto de movimientos recibe un
    # bloque de verde más largo que U_pg, con lo que la cota pierde sentido.
    #
    # Con este parámetro en True se agrega la restricción (22), que prohíbe que
    # dos fases equivalentes queden contiguas. Siguen pudiendo usarse las dos,
    # pero en bloques separados por al menos L_pg intervalos de otra fase.
    repetidas_no_contiguas: bool = True

    # Coordenadas del centro de cada esquina, para dibujar la red. No
    # intervienen en el modelo: son sólo para las figuras. Si se omiten,
    # visual.py intenta deducirlas del nombre de las esquinas.
    centros: Optional[Dict[str, Tuple[float, float]]] = None

    descripcion: str = ""


# =============================================================================
#  Datos derivados
# =============================================================================
@dataclass
class Datos:
    """Todo lo que se deduce de una ``Instancia`` y que el modelo necesita."""

    inst: Instancia

    Delta: float                      # duración de cada intervalo [s]
    HG: List[int]                     # H_Gamma = {0, 1, ..., H-1}: capas temporales

    V: List[str]                      # nodos de la red física
    E_p: Dict[str, List[Arco]]        # movimientos de cada intersección semaforizada
    E: List[Arco]                     # unión de todos los E_p
    A: List[Arco]                     # arcos de la red física

    l: Dict[Arco, int]                # l_a : cantidad de intervalos del arco
    tau: Dict[Arco, float]            # tau_a = l_a * Delta
    u_barra: Dict[Arco, float]        # u_barra_a = u_a * Delta

    D_kh: Dict[Tuple[str, int], float]

    A_k: Dict[str, dict]              # A_k[k][e] = (cola, cabeza, costo c_e)
    V_k: Dict[str, list]              # nodos de la red ampliada del producto k
    delta_mas: Dict[str, dict]        # arcos salientes de cada nodo
    delta_menos: Dict[str, dict]      # arcos entrantes de cada nodo

    # Sólo en la variante con caminos prefijados (R distinto de None):
    A_R: Optional[Dict[str, set]] = None   # A_k^R : arcos físicos del camino de k
    V_R: Optional[Dict[str, set]] = None   # V_k^R : nodos físicos del camino de k

    # Grupos de fases equivalentes de cada intersección, detectados por tener
    # exactamente el mismo conjunto de movimientos habilitados.
    repetidas: Optional[Dict[str, List[List[str]]]] = None

    @property
    def con_caminos(self) -> bool:
        """True si la instancia fija los recorridos (variante 2)."""
        return self.inst.R is not None

    def capa_anterior(self, h: int) -> int:
        """Capa h^- = (h-1) mod H, usada en las restricciones (20) y (21)."""
        return (h - 1) % self.inst.H


# =============================================================================
#  Utilidades de nombres
# =============================================================================
def nombre_arco(e) -> str:
    """Nombre legible del arco de la red expandida."""
    if e[0] == "tr":
        (i, j), h = e[1], e[2]
        return "tr_%s_%s_%d" % (i, j, h)
    if e[0] == "esp":
        return "esp_%s_%d" % (e[1], e[2])
    if e[0] == "in":
        return "in_%s_%d" % (e[1], e[2])
    if e[0] == "out":
        return "out_%s_%d" % (e[1], e[2])
    return "ret_%s" % (e[1],)


def nombre_nodo(v) -> str:
    """Nombre legible del nodo de la red expandida.

    Se usa para nombrar las restricciones de conservación. Evita paréntesis,
    comas y comillas, que Gurobi no admite al escribir el modelo en formato LP.
    """
    if v[0] == "N":
        return "%s_%d" % (v[1], v[2])
    return "%s_%s" % (v[0], v[1])          # ("SO", k) / ("SD", k)


def nodos(V_ext: Sequence[str],
          esq_libres: Sequence[str],
          X: Dict[str, List[str]]) -> List[str]:
    """Conjunto de nodos de la red física.

    Se expone porque las instancias lo necesitan para construir ``kappa``.
    """
    V = list(V_ext) + list(esq_libres)
    for esq in X:
        V += list(X[esq])
    return V


# =============================================================================
#  Caminos prefijados (variante 2)
# =============================================================================
def validar_camino(camino: Sequence[Arco], k: str, o_k: str, d_k: str,
                   arcos: set) -> Tuple[set, set]:
    """Comprueba que ``camino`` sea un camino dirigido de o_k a d_k.

    Sigue la definición de camino dirigido del marco teórico: una secuencia de
    arcos consecutivos cuyos nodos son todos distintos entre sí.

    Devuelve el par (A_k^R, V_k^R): el conjunto de arcos físicos del camino y
    el conjunto de nodos físicos que lo componen.
    """
    assert camino, "El camino del producto %s está vacío" % k

    for a in camino:
        assert a in arcos, \
            "El camino de %s usa el arco %s, que no pertenece a A" % (k, str(a))

    # Los arcos deben encadenarse: la cabeza de uno es la cola del siguiente
    for r in range(1, len(camino)):
        assert camino[r - 1][1] == camino[r][0], \
            "El camino de %s se corta entre %s y %s" \
            % (k, str(camino[r - 1]), str(camino[r]))

    assert camino[0][0] == o_k, \
        "El camino de %s empieza en %s y no en su origen %s" \
        % (k, camino[0][0], o_k)
    assert camino[-1][1] == d_k, \
        "El camino de %s termina en %s y no en su destino %s" \
        % (k, camino[-1][1], d_k)

    # V_k^R : nodos del recorrido, en orden
    secuencia = [camino[0][0]] + [a[1] for a in camino]
    assert len(secuencia) == len(set(secuencia)), \
        "El camino de %s repite nodos y por lo tanto no es un camino dirigido" % k

    return set(camino), set(secuencia)


def caminos_mas_cortos(inst: Instancia) -> Dict[str, List[Arco]]:
    """Camino de mínimo tiempo de tránsito a flujo libre para cada producto.

    Sirve como punto de partida para la variante con caminos prefijados: da el
    recorrido que elegiría un vehículo si no hubiera semáforos ni congestión.
    Los pesos son los tiempos de tránsito tau_a, sin considerar capacidades ni
    fases. Los caminos que devuelve pueden reemplazarse a mano.
    """
    import heapq

    Delta = inst.Gamma / inst.H

    # Peso de cada arco: su tiempo de tránsito
    peso: Dict[Arco, float] = {}
    for a, dat in inst.tramos.items():
        peso[a] = dat["t"]
    for esq in inst.movimientos:
        for a, dat in inst.movimientos[esq].items():
            peso[a] = dat["l"] * Delta

    salientes: Dict[str, List[Arco]] = {}
    for (i, j) in peso:
        salientes.setdefault(i, []).append((i, j))

    caminos: Dict[str, List[Arco]] = {}
    for k in inst.K:
        origen, destino = inst.o[k], inst.d[k]

        dist = {origen: 0.0}
        previo: Dict[str, Arco] = {}
        cola = [(0.0, origen)]
        visitados = set()

        while cola:
            dv, v = heapq.heappop(cola)
            if v in visitados:
                continue
            visitados.add(v)
            if v == destino:
                break
            for a in salientes.get(v, []):
                w = a[1]
                nueva = dv + peso[a]
                if nueva < dist.get(w, float("inf")) - 1e-12:
                    dist[w] = nueva
                    previo[w] = a
                    heapq.heappush(cola, (nueva, w))

        assert destino in dist, \
            "No existe camino de %s a %s para el producto %s" % (origen, destino, k)

        camino: List[Arco] = []
        v = destino
        while v != origen:
            a = previo[v]
            camino.append(a)
            v = a[0]
        caminos[k] = list(reversed(camino))

    return caminos


# =============================================================================
#  Derivación de la red ciclicamente expandida en el tiempo
# =============================================================================
def preparar(inst: Instancia) -> Datos:
    """Construye, a partir de los datos crudos, todo lo que consume el modelo.

    Nodos de la red expandida:
        ("N", i, h)  -> i_h
        ("SO", k)    -> superorigen del producto k
        ("SD", k)    -> superdestino del producto k

    Arcos, con su cola, su cabeza y su costo temporal c_e:
        ("tr",  a, h) -> tránsito  a_h = (i_h, j_{(h+l_a) mod H}),  c_e = tau_a
        ("esp", i, h) -> espera    w_{i,h} = (i_h, i_{(h+1) mod H}), c_e = Delta
        ("in",  k, h) -> inyección (o_k barra, o_{k,h}),             c_e = 0
        ("out", k, h) -> absorción (d_{k,h}, d_k barra),             c_e = 0
        ("ret", k)    -> retorno   r_k = (d_k barra, o_k barra),     c_e = 0
    """
    H = inst.H
    Delta = inst.Gamma / H
    HG = list(range(H))

    # --- nodos de la red física ---------------------------------------------
    V = nodos(inst.V_ext, inst.esq_libres, inst.X)
    assert len(V) == len(set(V)), "Hay nodos repetidos en V"

    # --- movimientos y arcos -------------------------------------------------
    # E_p contiene únicamente los movimientos de las esquinas SEMAFORIZADAS.
    # Los movimientos de una esquina sin semáforo, si la instancia la modela
    # como subgrafo, entran en A pero no en E: sobre ellos rige la capacidad
    # (14) y ninguna variable y los alcanza.
    E_p = {p: list(inst.movimientos[p].keys()) for p in inst.P}
    E = [a for p in inst.P for a in E_p[p]]
    mov_todos = [a for esq in inst.movimientos for a in inst.movimientos[esq]]
    A = list(inst.tramos.keys()) + mov_todos

    # --- parámetros por arco físico -----------------------------------------
    l: Dict[Arco, int] = {}           # l_a : cantidad de intervalos
    u: Dict[Arco, float] = {}         # u_a : capacidad como tasa de flujo [veh/s]
    for a, dat in inst.tramos.items():
        assert abs(dat["t"] / Delta - round(dat["t"] / Delta)) < 1e-9, \
            "El tiempo de tránsito de %s no es un múltiplo de Delta" % str(a)
        l[a], u[a] = int(round(dat["t"] / Delta)), dat["u"]
    for esq in inst.movimientos:
        for a, dat in inst.movimientos[esq].items():
            l[a], u[a] = dat["l"], dat["u"]

    # tau_a = l_a * Delta : tiempo de tránsito del arco físico a
    tau = {a: l[a] * Delta for a in A}

    # u_barra_a = u_a * Delta : flujo máximo que puede ingresar al arco durante
    # un intervalo de duración Delta
    u_barra = {a: u[a] * Delta for a in A}

    # Supuesto del modelo: ningún arco requiere un período completo
    assert all(1 <= l[a] < H for a in A), "Debe cumplirse 1 <= l_a < H para todo arco"

    # --- controles de coherencia --------------------------------------------
    for a in A:
        for i in a:
            assert i in V, "El arco %s usa el nodo %s, que no está en V" % (str(a), i)
    for i in V:
        assert i in inst.kappa, "Falta kappa para el nodo %s" % i

    assert all(1 <= inst.L[p, g] <= inst.U[p, g] <= H for p in inst.P for g in inst.G[p]), \
        "Debe cumplirse 1 <= L_pg <= U_pg <= H"

    # Toda fase debe habilitar movimientos que existan en su intersección
    for p in inst.P:
        for g in inst.G[p]:
            for a in inst.E_pg[p, g]:
                assert a in E_p[p], \
                    "La fase %s de %s habilita %s, que no es un movimiento suyo" \
                    % (g, p, str(a))

    # Ningún movimiento puede quedar fuera de todas las fases, porque la
    # restricción (19) volvería infactible el modelo
    for p in inst.P:
        for a in E_p[p]:
            assert any(a in inst.E_pg[p, g] for g in inst.G[p]), \
                "El movimiento %s de %s no aparece en ninguna fase" % (str(a), p)

    for k in inst.K:
        assert inst.o[k] in V, "El origen de %s no está en V" % k
        assert inst.d[k] in V, "El destino de %s no está en V" % k

    # --- fases obligatorias --------------------------------------------------
    for p, gs in (inst.fases_obligatorias or {}).items():
        assert p in inst.P, \
            "fases_obligatorias nombra la intersección %s, que no está en P" % p
        for g in gs:
            assert g in inst.G[p], \
                "fases_obligatorias nombra la fase %s, que no está en G[%s]" % (g, p)

    # --- demandas por capa ---------------------------------------------------
    if inst.D_kh is None:
        D_kh = {(k, h): inst.D[k] / H for k in inst.K for h in HG}
    else:
        D_kh = dict(inst.D_kh)
    for k in inst.K:
        assert abs(sum(D_kh[k, h] for h in HG) - inst.D[k]) < 1e-9, \
            "La distribución por capas de %s no suma D_k" % k

    # --- red ciclicamente expandida -----------------------------------------
    A_tr = {}                          # A^Gamma_tr : arcos de tránsito
    for a in A:
        i, j = a
        for h in HG:
            A_tr[("tr", a, h)] = (("N", i, h), ("N", j, (h + l[a]) % H), tau[a])

    A_esp = {}                         # A^Gamma_esp : arcos de espera
    for i in V:
        for h in HG:
            A_esp[("esp", i, h)] = (("N", i, h), ("N", i, (h + 1) % H), Delta)

    A_Gamma = {}                       # A^Gamma = A^Gamma_tr U A^Gamma_esp
    A_Gamma.update(A_tr)
    A_Gamma.update(A_esp)

    # Para cada producto k: red ampliada con superorigen, superdestino y retorno
    A_k, V_k = {}, {}
    for k in inst.K:
        arcos = dict(A_Gamma)
        for h in HG:
            arcos[("in", k, h)] = (("SO", k), ("N", inst.o[k], h), 0.0)
            arcos[("out", k, h)] = (("N", inst.d[k], h), ("SD", k), 0.0)
        arcos[("ret", k)] = (("SD", k), ("SO", k), 0.0)
        A_k[k] = arcos
        V_k[k] = [("N", i, h) for i in V for h in HG] + [("SO", k), ("SD", k)]

    # Incidencia: arcos salientes (delta^+) y entrantes (delta^-) de cada nodo
    delta_mas = {k: {v: [] for v in V_k[k]} for k in inst.K}
    delta_menos = {k: {v: [] for v in V_k[k]} for k in inst.K}
    for k in inst.K:
        for e, (cola, cabeza, _) in A_k[k].items():
            delta_mas[k][cola].append(e)
            delta_menos[k][cabeza].append(e)

    # --- fases equivalentes --------------------------------------------------
    #  Se agrupan las fases de cada intersección que habilitan exactamente los
    #  mismos movimientos. Son la misma fase con distinto nombre.
    repetidas: Dict[str, List[List[str]]] = {}
    for p in inst.P:
        por_movimientos: Dict[frozenset, List[str]] = {}
        for g in inst.G[p]:
            por_movimientos.setdefault(frozenset(inst.E_pg[p, g]), []).append(g)
        repetidas[p] = [gs for gs in por_movimientos.values() if len(gs) > 1]

    # --- caminos prefijados (variante 2) ------------------------------------
    A_R = V_R = None
    if inst.R is not None:
        A_R, V_R = {}, {}
        arcos = set(A)
        for k in inst.K:
            camino = inst.R.get(k)
            if camino is None:
                continue              # este producto conserva la asignación libre
            A_R[k], V_R[k] = validar_camino(camino, k, inst.o[k], inst.d[k], arcos)
        for k in inst.R:
            assert k in inst.K, "R incluye el producto %s, que no está en K" % k

    return Datos(inst=inst, Delta=Delta, HG=HG, V=V, E_p=E_p, E=E, A=A,
                 l=l, tau=tau, u_barra=u_barra, D_kh=D_kh,
                 A_k=A_k, V_k=V_k, delta_mas=delta_mas, delta_menos=delta_menos,
                 A_R=A_R, V_R=V_R, repetidas=repetidas)


# =============================================================================
#  Construcción del PLEM
# =============================================================================
def construir(dat: Datos, env: Optional[gp.Env] = None):
    """Arma el modelo (10)-(29) sobre los datos derivados.

    Devuelve el modelo de Gurobi y el diccionario de sus variables.
    """
    inst = dat.inst
    HG, K, P, G = dat.HG, inst.K, inst.P, inst.G
    E_pg, u_barra = inst.E_pg, dat.u_barra

    m = gp.Model("coordinacion_semaforica_%s" % inst.nombre, env=env)

    # -------------------------------------------------------------------------
    #  Variables de decisión
    # -------------------------------------------------------------------------

    # x^k_e >= 0 : flujo del producto k que utiliza el arco e     -- (25)
    x = {}
    for k in K:
        for e in dat.A_k[k]:
            x[k, e] = m.addVar(lb=0.0, name="x_%s_%s" % (k, nombre_arco(e)))

    # z_pg : 1 si la fase g forma parte del plan de la intersección p   -- (26)
    z = {(p, g): m.addVar(vtype=GRB.BINARY, name="z_%s_%s" % (p, g))
         for p in P for g in G[p]}

    # y_pgh : 1 si la fase g está activa en la capa h                   -- (27)
    y = {(p, g, h): m.addVar(vtype=GRB.BINARY, name="y_%s_%s_%d" % (p, g, h))
         for p in P for g in G[p] for h in HG}

    # y^on_pgh : 1 si la fase g comienza en la capa h                   -- (28)
    y_on = {(p, g, h): m.addVar(vtype=GRB.BINARY, name="yon_%s_%s_%d" % (p, g, h))
            for p in P for g in G[p] for h in HG}

    # y^off_pgh : 1 si la fase g finaliza en la capa h                  -- (29)
    y_off = {(p, g, h): m.addVar(vtype=GRB.BINARY, name="yoff_%s_%s_%d" % (p, g, h))
             for p in P for g in G[p] for h in HG}

    m.update()

    # -------------------------------------------------------------------------
    #  Función objetivo (10): tiempo total de tránsito y de espera
    # -------------------------------------------------------------------------
    m.setObjective(
        gp.quicksum(dat.A_k[k][e][2] * x[k, e] for k in K for e in dat.A_k[k]),
        GRB.MINIMIZE)

    # -------------------------------------------------------------------------
    #  Conservación de flujo (11)-(13)
    # -------------------------------------------------------------------------

    # (11) Conservación en todos los nodos de la red ampliada de cada producto.
    #      El balance es nulo en todos los nodos: la generación y la absorción
    #      del flujo quedan representadas por los arcos artificiales.
    for k in K:
        for v in dat.V_k[k]:
            m.addConstr(
                gp.quicksum(x[k, e] for e in dat.delta_mas[k][v])
                - gp.quicksum(x[k, e] for e in dat.delta_menos[k][v]) == 0,
                name="c11_conservacion_%s_%s" % (k, nombre_nodo(v)))

    # (12) Capacidad de los arcos de inyección: en cada capa, el producto k
    #      puede ingresar a lo sumo la demanda que le corresponde a esa capa.
    for k in K:
        for h in HG:
            m.addConstr(x[k, ("in", k, h)] <= dat.D_kh[k, h],
                        name="c12_inyeccion_%s_%d" % (k, h))

    # (13) El flujo del arco de retorno se fija en la demanda total del producto.
    for k in K:
        m.addConstr(x[k, ("ret", k)] == inst.D[k], name="c13_retorno_%s" % k)

    # -------------------------------------------------------------------------
    #  Capacidad de los arcos no semaforizados (14)
    # -------------------------------------------------------------------------
    for a in dat.A:
        if a in dat.E:
            continue                  # los movimientos internos se tratan en (24)
        for h in HG:
            m.addConstr(gp.quicksum(x[k, ("tr", a, h)] for k in K) <= u_barra[a],
                        name="c14_capacidad_%s_%s_%d" % (a[0], a[1], h))

    # -------------------------------------------------------------------------
    #  Capacidad de almacenamiento (15)
    # -------------------------------------------------------------------------
    #  Si kappa_i = infinito, la restricción no acota nada y se omite. Es el
    #  caso de los nodos de ingreso a la zona de estudio, donde la acumulación
    #  representa la cola que aguarda fuera de la red.
    for i in dat.V:
        if inst.kappa[i] == float("inf"):
            continue
        for h in HG:
            m.addConstr(gp.quicksum(x[k, ("esp", i, h)] for k in K) <= inst.kappa[i],
                        name="c15_almacenamiento_%s_%d" % (i, h))

    # -------------------------------------------------------------------------
    #  Activación de las fases (16)-(21)
    # -------------------------------------------------------------------------

    # (16) En cada capa temporal hay exactamente una fase activa por intersección.
    for p in P:
        for h in HG:
            m.addConstr(gp.quicksum(y[p, g, h] for g in G[p]) == 1,
                        name="c16_una_fase_activa_%s_%d" % (p, h))

    # (17) Cada fase seleccionada comienza exactamente una vez durante el período.
    for p in P:
        for g in G[p]:
            m.addConstr(gp.quicksum(y_on[p, g, h] for h in HG) == z[p, g],
                        name="c17_un_encendido_%s_%s" % (p, g))

    # (18) Cada fase seleccionada finaliza exactamente una vez durante el período.
    for p in P:
        for g in G[p]:
            m.addConstr(gp.quicksum(y_off[p, g, h] for h in HG) == z[p, g],
                        name="c18_un_apagado_%s_%s" % (p, g))

    # (19) Cobertura: cada movimiento interno pertenece al menos a una fase
    #      seleccionada, de modo que ningún movimiento queda en rojo todo el período.
    for p in P:
        for a in dat.E_p[p]:
            m.addConstr(
                gp.quicksum(z[p, g] for g in G[p] if a in E_pg[p, g]) >= 1,
                name="c19_cobertura_%s_%s_%s" % (p, a[0], a[1]))

    # (20) Detección de los encendidos.
    for p in P:
        for g in G[p]:
            for h in HG:
                m.addConstr(
                    y[p, g, h] - y[p, g, dat.capa_anterior(h)] <= y_on[p, g, h],
                    name="c20_encendido_%s_%s_%d" % (p, g, h))

    # (21) Detección de los apagados.
    for p in P:
        for g in G[p]:
            for h in HG:
                m.addConstr(
                    y[p, g, dat.capa_anterior(h)] - y[p, g, h] <= y_off[p, g, h],
                    name="c21_apagado_%s_%s_%d" % (p, g, h))

    # -------------------------------------------------------------------------
    #  Repetición no consecutiva de una misma configuración (22)
    # -------------------------------------------------------------------------
    #  Si g y g' habilitan los mismos movimientos, prohibir que g' esté activa
    #  justo después de g impide que los dos bloques se concatenen en uno solo
    #  más largo que U_pg. Las dos fases pueden seguir usándose, pero separadas.
    if inst.repetidas_no_contiguas:
        for p in P:
            for grupo in dat.repetidas[p]:
                for g in grupo:
                    for g2 in grupo:
                        if g == g2:
                            continue
                        for h in HG:
                            m.addConstr(
                                y[p, g, dat.capa_anterior(h)] + y[p, g2, h] <= 1,
                                name="c22_no_contiguas_%s_%s_%s_%d" % (p, g, g2, h))

    # -------------------------------------------------------------------------
    #  Duración de las fases (23)
    # -------------------------------------------------------------------------
    for p in P:
        for g in G[p]:
            m.addConstr(gp.quicksum(y[p, g, h] for h in HG) >= inst.L[p, g] * z[p, g],
                        name="c23a_duracion_minima_%s_%s" % (p, g))
            m.addConstr(gp.quicksum(y[p, g, h] for h in HG) <= inst.U[p, g] * z[p, g],
                        name="c23b_duracion_maxima_%s_%s" % (p, g))

    # -------------------------------------------------------------------------
    #  Fases obligatorias
    # -------------------------------------------------------------------------
    #  Se impone z_pg = 1 para que la fase forme parte del plan. Junto con
    #  (23) y L_pg = U_pg, eso le fija también la duración exacta.
    for p, gs in (inst.fases_obligatorias or {}).items():
        for g in gs:
            m.addConstr(z[p, g] == 1, name="c_obligatoria_%s_%s" % (p, g))

    # -------------------------------------------------------------------------
    #  Acoplamiento entre las fases y el flujo (24)
    # -------------------------------------------------------------------------
    #  Si el movimiento tiene verde en la capa h, el arco dispone de su capacidad
    #  u_barra_a; si tiene rojo, el lado derecho se anula y ningún producto puede
    #  utilizarlo en esa capa.
    for p in P:
        for a in dat.E_p[p]:
            for h in HG:
                m.addConstr(
                    gp.quicksum(x[k, ("tr", a, h)] for k in K)
                    <= u_barra[a] * gp.quicksum(y[p, g, h] for g in G[p]
                                                if a in E_pg[p, g]),
                    name="c24_semaforo_%s_%s_%s_%d" % (p, a[0], a[1], h))

    # -------------------------------------------------------------------------
    #  Caminos prefijados (30)-(31)
    # -------------------------------------------------------------------------
    #  Sólo en la segunda variante. Se anula el flujo del producto k en todo
    #  arco que no pertenece a su recorrido, de modo que queda confinado al
    #  subgrafo cíclicamente expandido de su camino.
    if dat.con_caminos:
        # (30) x^k_{a_h} = 0  para todo a en A \ A_k^R y toda capa h
        for k in K:
            if k not in dat.A_R:
                continue              # producto sin camino prefijado
            for a in dat.A:
                if a in dat.A_R[k]:
                    continue
                for h in HG:
                    m.addConstr(x[k, ("tr", a, h)] == 0,
                                name="c30_fuera_camino_%s_%s_%s_%d"
                                     % (k, a[0], a[1], h))

        # (31) x^k_{w_{i,h}} = 0  para todo i en V \ V_k^R y toda capa h
        for k in K:
            if k not in dat.V_R:
                continue              # producto sin camino prefijado
            for i in dat.V:
                if i in dat.V_R[k]:
                    continue
                for h in HG:
                    m.addConstr(x[k, ("esp", i, h)] == 0,
                                name="c31_espera_fuera_camino_%s_%s_%d" % (k, i, h))

    m.update()
    return m, dict(x=x, z=z, y=y, y_on=y_on, y_off=y_off)


# =============================================================================
#  Resolución
# =============================================================================
def resolver(m: gp.Model,
             tiempo_limite: float = 3600.0,
             gap: Optional[float] = None,
             hilos: Optional[int] = None,
             log: bool = True,
             archivo_log: Optional[str] = None,
             parametros: Optional[dict] = None) -> float:
    """Configura los parámetros, optimiza y devuelve el tiempo de resolución."""
    m.Params.OutputFlag = 1 if log else 0
    m.Params.TimeLimit = tiempo_limite
    if gap is not None:
        m.Params.MIPGap = gap
    if hilos is not None:
        m.Params.Threads = hilos
    if archivo_log is not None:
        m.Params.LogFile = archivo_log
    for clave, valor in (parametros or {}).items():
        m.setParam(clave, valor)

    t0 = time.perf_counter()
    m.optimize()
    return time.perf_counter() - t0


def extraer(v: dict) -> dict:
    """Lee los valores de la solución incumbente."""
    return dict(
        x={clave: var.X for clave, var in v["x"].items()},
        y={clave: int(round(var.X)) for clave, var in v["y"].items()},
        z={clave: int(round(var.X)) for clave, var in v["z"].items()},
        y_on={clave: int(round(var.X)) for clave, var in v["y_on"].items()},
        y_off={clave: int(round(var.X)) for clave, var in v["y_off"].items()},
    )


# =============================================================================
#  Reporte de la solución
# =============================================================================
def reporte(dat: Datos, sol: dict) -> None:
    inst = dat.inst
    HG, K, P, G, Delta = dat.HG, inst.K, inst.P, inst.G, dat.Delta
    vx, vy, vz, v_on = sol["x"], sol["y"], sol["z"], sol["y_on"]

    # --- Función objetivo y sus dos componentes ------------------------------
    tiempo_transito = sum(dat.A_k[k][e][2] * vx[k, e]
                          for k in K for e in dat.A_k[k] if e[0] == "tr")
    tiempo_espera = sum(dat.A_k[k][e][2] * vx[k, e]
                        for k in K for e in dat.A_k[k] if e[0] == "esp")
    objetivo = tiempo_transito + tiempo_espera
    demanda_total = sum(inst.D[k] for k in K)

    print()
    print("=" * 70)
    print("FUNCIÓN OBJETIVO (10): tiempo total de viaje")
    print("=" * 70)
    print("  Tiempo total          : %8.2f veh-segundo por período" % objetivo)
    if objetivo > 1e-9:
        print("    - tránsito          : %8.2f  (%.1f %%)"
              % (tiempo_transito, 100 * tiempo_transito / objetivo))
        print("    - espera            : %8.2f  (%.1f %%)"
              % (tiempo_espera, 100 * tiempo_espera / objetivo))
    print("  Demanda total         : %8.2f vehículos por período" % demanda_total)
    if demanda_total > 1e-9:
        print("  Tiempo medio de viaje : %8.2f segundos por vehículo"
              % (objetivo / demanda_total))

    # --- Recorridos prefijados, si los hay -----------------------------------
    if dat.con_caminos:
        print()
        print("=" * 70)
        print("CAMINOS PREFIJADOS  R_k")
        print("=" * 70)
        for k in K:
            camino = inst.R.get(k)
            if camino is None:
                print("  %-4s %s -> %s   sin camino prefijado: "
                      "asignación libre" % (k, inst.o[k], inst.d[k]))
                continue
            secuencia = [camino[0][0]] + [a[1] for a in camino]
            largo = sum(dat.tau[a] for a in camino)
            print("  %-4s %s -> %s   (%d arcos, %.0f s a flujo libre)"
                  % (k, inst.o[k], inst.d[k], len(camino), largo))
            print("       " + " -> ".join(secuencia))

    # --- Plan semafórico obtenido -------------------------------------------
    print()
    print("=" * 70)
    print("PLAN SEMAFÓRICO  (V = verde / . = rojo, una columna por capa temporal)")
    print("=" * 70)
    print("  Capas: " + "".join(str(h % 10) for h in HG)
          + "    (Gamma = %.0f s, H = %d, Delta = %.0f s)"
          % (inst.Gamma, inst.H, Delta))
    for p in P:
        print()
        equiv = ["{%s}" % ", ".join(gs) for gs in (dat.repetidas.get(p) or [])]
        print("  Intersección %s:%s" % (p, ("   fases equivalentes: " + " ".join(equiv))
                                        if equiv else ""))
        for g in G[p]:
            movs = ", ".join("%s->%s" % a for a in inst.E_pg[p, g])
            if vz[p, g] == 1:
                patron = "".join("V" if vy[p, g, h] else "." for h in HG)
                dur = sum(vy[p, g, h] for h in HG)
                inicio = [h for h in HG if v_on[p, g, h] == 1]
                print("    z=1  %-3s %s  %2d intervalos = %4.0f s  inicio en capa %d"
                      % (g, patron, dur, dur * Delta, inicio[0] if inicio else -1))
                print("            movimientos: %s" % movs)
            else:
                print("    z=0  %-3s %s  (fase no seleccionada)" % (g, "-" * inst.H))
                print("            movimientos: %s" % movs)

    # --- Verificación de la coordinación entre intersecciones ----------------
    print()
    print("=" * 70)
    print("ESTADO DE CADA MOVIMIENTO INTERNO POR CAPA TEMPORAL")
    print("=" * 70)
    for p in P:
        for a in dat.E_p[p]:
            verde = ["V" if any(vy[p, g, h] == 1 for g in G[p] if a in inst.E_pg[p, g])
                     else "." for h in HG]
            flujo = [sum(vx[k, ("tr", a, h)] for k in K) for h in HG]
            print("  %s %-22s %s   flujo total = %5.2f veh"
                  % (p, "%s->%s" % a, "".join(verde), sum(flujo)))

    # --- Asignación de tráfico: flujo agregado por arco físico ---------------
    print()
    print("=" * 70)
    print("ASIGNACIÓN DE TRÁFICO: flujo por arco físico y por producto [veh/período]")
    print("=" * 70)
    print("  %-26s" % "arco" + "".join("%8s" % k for k in K) + "%9s" % "total")
    for a in dat.A:
        fila = [sum(vx[k, ("tr", a, h)] for h in HG) for k in K]
        if sum(fila) > 1e-6:
            marca = " (movimiento)" if a in dat.E else ""
            print("  %-26s" % ("%s->%s" % a) + "".join("%8.2f" % f for f in fila)
                  + "%9.2f" % sum(fila) + marca)

    # --- Espera acumulada por nodo -------------------------------------------
    print()
    print("=" * 70)
    print("ESPERA ACUMULADA POR NODO [veh-segundo por período]")
    print("=" * 70)
    for i in dat.V:
        espera = sum(Delta * vx[k, ("esp", i, h)] for k in K for h in HG)
        if espera > 1e-6:
            cola_max = max(sum(vx[k, ("esp", i, h)] for k in K) for h in HG)
            print("  %-10s espera = %7.2f    cola máxima = %5.2f veh (kappa = %.0f)"
                  % (i, espera, cola_max, inst.kappa[i]))


# =============================================================================
#  Verificación de las restricciones
# =============================================================================
def verificar(dat: Datos, sol: dict, tol: float = 1e-6) -> int:
    """Comprueba que la solución satisface cada familia de restricciones.

    Sirve como control de que lo que resuelve el solver es efectivamente el
    modelo escrito en la tesis. Devuelve el total de incumplimientos.
    """
    inst = dat.inst
    HG, K, P, G = dat.HG, inst.K, inst.P, inst.G
    vx, vy, vz, v_on, v_off = sol["x"], sol["y"], sol["z"], sol["y_on"], sol["y_off"]

    informe = []      # (número, descripción, lista de incumplimientos)

    # (14) sum_k x^k_{a_h} <= u_barra_a  para todo a en A \ E y toda capa h
    viol = []
    for a in dat.A:
        if a in dat.E:
            continue
        for h in HG:
            flujo = sum(vx[k, ("tr", a, h)] for k in K)
            if flujo > dat.u_barra[a] + tol:
                viol.append("%s->%s en h=%d (%.3f > %.3f)"
                            % (a[0], a[1], h, flujo, dat.u_barra[a]))
    informe.append(("14", "capacidad de los arcos no semaforizados", viol))

    # (15) sum_k x^k_{w_{i,h}} <= kappa_i  para todo nodo i y toda capa h
    viol = []
    for i in dat.V:
        if inst.kappa[i] == float("inf"):
            continue
        for h in HG:
            cola = sum(vx[k, ("esp", i, h)] for k in K)
            if cola > inst.kappa[i] + tol:
                viol.append("%s en h=%d (%.3f > %.3f)" % (i, h, cola, inst.kappa[i]))
    informe.append(("15", "capacidad de almacenamiento de los nodos", viol))

    # (16) sum_g y_pgh = 1
    viol = []
    for p in P:
        for h in HG:
            activas = sum(vy[p, g, h] for g in G[p])
            if activas != 1:
                viol.append("%s en h=%d (%d fases activas)" % (p, h, activas))
    informe.append(("16", "exactamente una fase activa por capa", viol))

    # (17) sum_h y^on_pgh = z_pg
    viol = []
    for p in P:
        for g in G[p]:
            encendidos = sum(v_on[p, g, h] for h in HG)
            if encendidos != vz[p, g]:
                viol.append("%s/%s (%d encendidos, z=%d)"
                            % (p, g, encendidos, vz[p, g]))
    informe.append(("17", "un encendido por fase seleccionada", viol))

    # (18) sum_h y^off_pgh = z_pg
    viol = []
    for p in P:
        for g in G[p]:
            apagados = sum(v_off[p, g, h] for h in HG)
            if apagados != vz[p, g]:
                viol.append("%s/%s (%d apagados, z=%d)" % (p, g, apagados, vz[p, g]))
    informe.append(("18", "un apagado por fase seleccionada", viol))

    # (19) sum_{g : a en E_pg} z_pg >= 1
    viol = []
    for p in P:
        for a in dat.E_p[p]:
            cubierto = sum(vz[p, g] for g in G[p] if a in inst.E_pg[p, g])
            if cubierto < 1:
                viol.append("%s %s->%s sin fase que lo habilite" % (p, a[0], a[1]))
    informe.append(("19", "todo movimiento cubierto por alguna fase del plan", viol))

    # (20) y_pgh - y_pgh^- <= y^on_pgh
    viol = []
    for p in P:
        for g in G[p]:
            for h in HG:
                if vy[p, g, h] - vy[p, g, dat.capa_anterior(h)] > v_on[p, g, h]:
                    viol.append("%s/%s en h=%d" % (p, g, h))
    informe.append(("20", "vínculo de los encendidos con los cambios de estado", viol))

    # (21) y_pgh^- - y_pgh <= y^off_pgh
    viol = []
    for p in P:
        for g in G[p]:
            for h in HG:
                if vy[p, g, dat.capa_anterior(h)] - vy[p, g, h] > v_off[p, g, h]:
                    viol.append("%s/%s en h=%d" % (p, g, h))
    informe.append(("21", "vínculo de los apagados con los cambios de estado", viol))

    # (22) y_pgh^- + y_pg'h <= 1  para g, g' con el mismo conjunto de movimientos
    if inst.repetidas_no_contiguas and any(dat.repetidas[p] for p in P):
        viol = []
        for p in P:
            for grupo in dat.repetidas[p]:
                for g in grupo:
                    for g2 in grupo:
                        if g == g2:
                            continue
                        for h in HG:
                            if vy[p, g, dat.capa_anterior(h)] + vy[p, g2, h] > 1:
                                viol.append("%s: %s y %s contiguas en h=%d"
                                            % (p, g, g2, h))
        informe.append(("22", "repetición no consecutiva de una configuración", viol))

    # (23) L_pg z_pg <= sum_h y_pgh <= U_pg z_pg
    viol = []
    for p in P:
        for g in G[p]:
            dur = sum(vy[p, g, h] for h in HG)
            if dur < inst.L[p, g] * vz[p, g] or dur > inst.U[p, g] * vz[p, g]:
                viol.append("%s/%s (%d intervalos, z=%d, cotas [%d, %d])"
                            % (p, g, dur, vz[p, g], inst.L[p, g], inst.U[p, g]))
    informe.append(("23", "duración de cada fase dentro de sus cotas", viol))

    # (24) sum_k x^k_{a_h} <= u_barra_a * sum_{g : a en E_pg} y_pgh
    viol = []
    for p in P:
        for a in dat.E_p[p]:
            for h in HG:
                flujo = sum(vx[k, ("tr", a, h)] for k in K)
                disponible = dat.u_barra[a] * sum(vy[p, g, h] for g in G[p]
                                                  if a in inst.E_pg[p, g])
                if flujo > disponible + tol:
                    viol.append("%s %s->%s en h=%d (%.3f > %.3f)"
                                % (p, a[0], a[1], h, flujo, disponible))
    informe.append(("24", "flujo habilitado únicamente por la fase activa", viol))

    # Fases obligatorias: z_pg = 1
    if inst.fases_obligatorias:
        viol = []
        for p, gs in inst.fases_obligatorias.items():
            for g in gs:
                if vz[p, g] != 1:
                    viol.append("%s/%s (z=%d, debía ser 1)" % (p, g, vz[p, g]))
        informe.append(("--", "fases obligatorias en el plan", viol))

    # (30) y (31): sólo en la variante con caminos prefijados
    if dat.con_caminos:
        # (30) x^k_{a_h} = 0  para todo a en A \ A_k^R
        viol = []
        for k in K:
            if k not in dat.A_R:
                continue
            for a in dat.A:
                if a in dat.A_R[k]:
                    continue
                for h in HG:
                    if abs(vx[k, ("tr", a, h)]) > tol:
                        viol.append("%s en %s->%s, h=%d (%.3f)"
                                    % (k, a[0], a[1], h, vx[k, ("tr", a, h)]))
        informe.append(("30", "flujo nulo fuera de los arcos del camino", viol))

        # (31) x^k_{w_{i,h}} = 0  para todo i en V \ V_k^R
        viol = []
        for k in K:
            if k not in dat.V_R:
                continue
            for i in dat.V:
                if i in dat.V_R[k]:
                    continue
                for h in HG:
                    if abs(vx[k, ("esp", i, h)]) > tol:
                        viol.append("%s espera en %s, h=%d (%.3f)"
                                    % (k, i, h, vx[k, ("esp", i, h)]))
        informe.append(("31", "espera nula fuera de los nodos del camino", viol))

    print()
    print("=" * 70)
    print("VERIFICACIÓN DE LAS RESTRICCIONES (14)-(24)"
          + ("  Y (30)-(31)" if dat.con_caminos else ""))
    print("=" * 70)
    for numero, descripcion, viol in informe:
        estado = "OK" if not viol else "ERROR (%d)" % len(viol)
        etiqueta = ("(%s) %s " % (numero, descripcion)).ljust(62, ".")
        print("  %s %s" % (etiqueta, estado))
        for detalle in viol[:5]:
            print("        -> %s" % detalle)
        if len(viol) > 5:
            print("        -> y %d incumplimientos más" % (len(viol) - 5))

    total_viol = sum(len(v) for _, _, v in informe)
    print()
    print("  Total de incumplimientos: %d" % total_viol)

    # Consecuencia de (17) y (20): el verde de cada fase seleccionada forma un
    # único bloque consecutivo dentro del orden cíclico del período.
    bloques_partidos = []
    for p in P:
        for g in G[p]:
            if vz[p, g] == 1:
                cambios = sum(1 for h in HG
                              if vy[p, g, h] == 1 and vy[p, g, dat.capa_anterior(h)] == 0)
                if cambios != 1:
                    bloques_partidos.append("%s/%s (%d bloques)" % (p, g, cambios))
    print("  Contigüidad del verde (consecuencia de (17) y (20)): %s"
          % ("OK" if not bloques_partidos else "ERROR en %s" % bloques_partidos))

    # --- Balance de las demandas (11)-(13) -----------------------------------
    print()
    print("=" * 70)
    print("BALANCE DE LAS DEMANDAS")
    print("=" * 70)
    for k in K:
        ing = sum(vx[k, ("in", k, h)] for h in HG)
        egr = sum(vx[k, ("out", k, h)] for h in HG)
        coincide = abs(ing - inst.D[k]) < 1e-6 and abs(egr - inst.D[k]) < 1e-6
        print("  %s: ingresan %.2f y egresan %.2f de %.2f  -> %s"
              % (k, ing, egr, inst.D[k], "OK" if coincide else "ERROR"))

    return total_viol


# =============================================================================
#  Ejecución completa de una instancia
# =============================================================================
ESTADOS = {
    GRB.OPTIMAL: "Optimal",
    GRB.INFEASIBLE: "Infeasible",
    GRB.UNBOUNDED: "Unbounded",
    GRB.INF_OR_UNBD: "Infeasible o no acotado",
    GRB.TIME_LIMIT: "Límite de tiempo",
    GRB.INTERRUPTED: "Interrumpido",
    GRB.SUBOPTIMAL: "Subóptimo",
}


def ejecutar(inst: Instancia,
             tiempo_limite: float = 600.0,
             gap: Optional[float] = None,
             hilos: Optional[int] = None,
             log: bool = True,
             con_reporte: bool = True,
             con_verificacion: bool = True,
             archivo_lp: Optional[str] = None,
             env: Optional[gp.Env] = None) -> dict:
    """Prepara los datos, arma el modelo, lo resuelve y reporta la solución."""
    print()
    print("#" * 70)
    print("#  INSTANCIA: %s" % inst.nombre)
    if inst.descripcion:
        for linea in inst.descripcion.strip().splitlines():
            print("#  %s" % linea.strip())
    print("#" * 70)

    dat = preparar(inst)
    m, v = construir(dat, env=env)

    if archivo_lp:
        m.write(archivo_lp)
        print("  Modelo escrito en %s" % archivo_lp)

    if dat.con_caminos:
        fijos, total = len(dat.A_R), len(inst.K)
        variante = ("coordinación semafórica con caminos prefijados"
                    if fijos == total else
                    "mixta: %d de %d productos con camino prefijado"
                    % (fijos, total))
    else:
        variante = "asignación de tráfico y coordinación semafórica"
    print("  Variante       : %s" % variante)
    print("  Nodos físicos  : %d" % len(dat.V))
    print("  Arcos físicos  : %d  (de los cuales %d son movimientos semaforizados)"
          % (len(dat.A), len(dat.E)))
    print("  Productos      : %d" % len(inst.K))

    grupos = [(p, gs) for p in inst.P for gs in (dat.repetidas.get(p) or [])]
    if grupos:
        print("  Fases equivalentes (mismo conjunto de movimientos):")
        for p, gs in grupos:
            movs = ", ".join("%s->%s" % a for a in inst.E_pg[p, gs[0]])
            print("      %-4s {%s}   habilitan: %s" % (p, ", ".join(gs), movs))
        print("      (22) %s: no pueden programarse en bloques contiguos"
              % ("ACTIVA" if inst.repetidas_no_contiguas else "desactivada"))
    else:
        print("  Fases equivalentes: ninguna")

    print("  Variables      : %d  (%d binarias)" % (m.NumVars, m.NumBinVars))
    print("  Restricciones  : %d" % m.NumConstrs)
    print("-" * 70)

    segundos = resolver(m, tiempo_limite=tiempo_limite, gap=gap, hilos=hilos, log=log)

    print("-" * 70)
    estado = ESTADOS.get(m.Status, "Status %d" % m.Status)
    print("Estado: %s" % estado)
    print("Tiempo de resolución: %.2f segundos" % segundos)

    resumen = dict(instancia=inst.nombre, estado=estado, segundos=segundos,
                   variables=m.NumVars, binarias=m.NumBinVars,
                   restricciones=m.NumConstrs,
                   objetivo=None, cota=None, gap=None, incumplimientos=None)

    if m.SolCount == 0:
        print("El modelo no encontró ninguna solución factible.")
        if m.Status == GRB.INFEASIBLE:
            print("Para diagnosticar: m.computeIIS() y m.write('iis.ilp')")
        return resumen

    resumen["objetivo"] = m.ObjVal
    resumen["cota"] = m.ObjBound
    resumen["gap"] = m.MIPGap
    print("Objetivo: %.4f    cota: %.4f    gap: %.4f %%"
          % (m.ObjVal, m.ObjBound, 100 * m.MIPGap))

    sol = extraer(v)

    #  Cuánto del tiempo total es espera: dice si la instancia está
    #  congestionada o circula a flujo libre.
    espera = sum(dat.A_k[k][e][2] * sol["x"][k, e]
                 for k in inst.K for e in dat.A_k[k] if e[0] == "esp")
    resumen["espera"] = espera
    resumen["frac_espera"] = espera / m.ObjVal if m.ObjVal > 1e-9 else 0.0

    if con_reporte:
        reporte(dat, sol)
    if con_verificacion:
        resumen["incumplimientos"] = verificar(dat, sol)

    resumen["modelo"] = m
    resumen["datos"] = dat
    resumen["solucion"] = sol
    return resumen