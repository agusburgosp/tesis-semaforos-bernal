"""
El plan semafórico ya esta dado y sólo hay que calcular cuánto tarda el
tránsito en recorrer la red con esa configuración.

Este archivo NO toca ``modelo.py``. Arma su propio programa lineal, que es el
mismo de la tesis pero sin las variables semafóricas: como el plan es un dato,
cada movimiento tiene su capacidad ya determinada en cada capa y el problema
se reduce a un flujo de costo mínimo multiproducto. No hay variables enteras.

    min   sum_k sum_e c_e x_e^k                                       (10)
    s.a.  conservación, inyección y retorno                       (11)-(13)
          capacidad de los tramos                                     (14)
          capacidad de almacenamiento                                 (15)
          capacidad de cada movimiento según el plan                  (24)

    from instancias import bernal_este
    from problema_real import PLANES_EJEMPLO, ejecutar_real

    r = ejecutar_real(bernal_este(), PLANES_EJEMPLO)
"""

from __future__ import annotations

import time
from dataclasses import replace
from math import gcd
from typing import Dict, List, Optional, Tuple

import gurobipy as gp
from gurobipy import GRB

from modelo import Instancia, nombre_arco, nombre_nodo, preparar

Arco = Tuple[str, str]


# =============================================================================
#  El plan observado
# =============================================================================
#  Cada intersección se describe como realmente funciona: la secuencia de fases
#  con su duración en segundos, y el desfase respecto de un reloj común.
#
#  Los nombres de las fases tienen que ser los mismos que figuran en G_p de la
#  instancia, porque de ahí sale qué movimientos habilita cada una.

PLANES_EJEMPLO = {
    "B1": dict(desfase=0.0,  ciclo=[("f1", 30.0), ("f3", 20.0), ("peatonal", 10.0)]),
    "J1": dict(desfase=15.0, ciclo=[("f1", 40.0), ("f3", 20.0)]),
}


def _mcm(a: int, b: int) -> int:
    return a * b // gcd(a, b)


def periodo_comun(planes: Dict[str, dict], Delta: float) -> Tuple[float, int]:
    """Período común y cantidad de capas: el mcm de todos los ciclos."""
    H = 1
    for p, dato in planes.items():
        ciclo = sum(dur for _, dur in dato["ciclo"])
        capas = ciclo / Delta
        assert abs(capas - round(capas)) < 1e-9, \
            "El ciclo de %s dura %.1f s, que no es múltiplo de Delta = %.1f" \
            % (p, ciclo, Delta)
        H = _mcm(H, int(round(capas)))
    return H * Delta, H


def fase_activa(planes: Dict[str, dict], p: str, h: int, Delta: float) -> str:
    """Qué fase está activa en la intersección p durante la capa h."""
    dato = planes[p]
    ciclo = sum(dur for _, dur in dato["ciclo"])
    t = (h * Delta - float(dato.get("desfase", 0.0))) % ciclo
    acumulado = 0.0
    for g, dur in dato["ciclo"]:
        if acumulado - 1e-9 <= t < acumulado + dur - 1e-9:
            return g
        acumulado += dur
    raise AssertionError("No se pudo ubicar la capa %d en el ciclo de %s" % (h, p))


def expandir(planes: Dict[str, dict], Delta: float
             ) -> Tuple[float, int, Dict[Tuple[str, str, int], int]]:
    """Convierte los planes observados en y_pgh, como dato.

    Devuelve (Gamma, H, y), donde y[(p, g, h)] vale 1 si la fase g está activa
    en la capa h.
    """
    assert planes, "No hay ningún plan declarado"

    for p, dato in planes.items():
        assert dato["ciclo"], "La intersección %s tiene el ciclo vacío" % p
        for g, dur in dato["ciclo"]:
            assert dur > 0, "La fase %s de %s dura %.1f s" % (g, p, dur)
            assert abs(dur / Delta - round(dur / Delta)) < 1e-9, \
                "La fase %s de %s dura %.1f s, que no es múltiplo de Delta = %.1f" \
                % (g, p, dur, Delta)
        desfase = float(dato.get("desfase", 0.0))
        assert abs(desfase / Delta - round(desfase / Delta)) < 1e-9, \
            "El desfase de %s es %.1f s, que no es múltiplo de Delta" % (p, desfase)

    Gamma, H = periodo_comun(planes, Delta)

    y: Dict[Tuple[str, str, int], int] = {}
    for p, dato in planes.items():
        nombres = {g for g, _ in dato["ciclo"]}
        for h in range(H):
            activa = fase_activa(planes, p, h, Delta)
            for g in nombres:
                y[p, g, h] = 1 if g == activa else 0
    return Gamma, H, y


# =============================================================================
#  Preparación: la misma red, con el período común
# =============================================================================
def preparar_real(inst: Instancia, planes: Dict[str, dict],
                  Delta: float = 5.0, escalar_demanda: bool = True):
    """Adapta la instancia al período común y devuelve (datos, y, instancia).

    La red es exactamente la misma: sólo cambian Gamma y H, y con ellos la
    cantidad de capas de la red expandida. Las demandas se reescalan para que
    el flujo por hora no cambie.
    """
    Gamma, H = periodo_comun(planes, Delta)

    for p in inst.P:
        assert p in planes, \
            "Falta el plan de la intersección %s, que está en P" % p
    for p, dato in planes.items():
        assert p in inst.P, "El plan nombra %s, que no es una intersección de P" % p
        for g, _ in dato["ciclo"]:
            assert g in inst.G[p], \
                "El plan de %s usa la fase %s, que no está en G[%s]" % (p, g, p)

    factor = Gamma / inst.Gamma if escalar_demanda else 1.0
    nueva = replace(inst,
                    nombre=inst.nombre + "-real",
                    Gamma=Gamma, H=H,
                    D={k: inst.D[k] * factor for k in inst.K},
                    D_kh=None)

    dat = preparar(nueva)
    _, _, y = expandir(planes, Delta)
    return dat, y, nueva


# =============================================================================
#  El programa lineal
# =============================================================================
def construir_flujo(dat, y, env: Optional[gp.Env] = None):
    """Arma el flujo de costo mínimo con las capacidades que impone el plan."""
    inst = dat.inst
    HG, K, P, G, E_pg = dat.HG, inst.K, inst.P, inst.G, inst.E_pg

    m = gp.Model("problema_real_%s" % inst.nombre, env=env)

    # x^k_e >= 0 : flujo del producto k sobre el arco e
    x = {}
    for k in K:
        for e in dat.A_k[k]:
            x[k, e] = m.addVar(lb=0.0, name="x_%s_%s" % (k, nombre_arco(e)))
    m.update()

    # (10) tiempo total de tránsito y de espera
    m.setObjective(
        gp.quicksum(dat.A_k[k][e][2] * x[k, e] for k in K for e in dat.A_k[k]),
        GRB.MINIMIZE)

    # (11) conservación en todos los nodos de la red ampliada
    for k in K:
        for v in dat.V_k[k]:
            m.addConstr(
                gp.quicksum(x[k, e] for e in dat.delta_mas[k][v])
                - gp.quicksum(x[k, e] for e in dat.delta_menos[k][v]) == 0,
                name="c11_conservacion_%s_%s" % (k, nombre_nodo(v)))

    # (12) la inyección de cada capa no supera la demanda de esa capa
    for k in K:
        for h in HG:
            m.addConstr(x[k, ("in", k, h)] <= dat.D_kh[k, h],
                        name="c12_inyeccion_%s_%d" % (k, h))

    # (13) toda la demanda del producto entra a la red
    for k in K:
        m.addConstr(x[k, ("ret", k)] == inst.D[k], name="c13_retorno_%s" % k)

    # (14) capacidad de los tramos
    for a in dat.A:
        if a in dat.E:
            continue
        for h in HG:
            m.addConstr(gp.quicksum(x[k, ("tr", a, h)] for k in K) <= dat.u_barra[a],
                        name="c14_capacidad_%s_%s_%d" % (a[0], a[1], h))

    # (15) capacidad de almacenamiento
    for i in dat.V:
        if inst.kappa[i] == float("inf"):
            continue
        for h in HG:
            m.addConstr(gp.quicksum(x[k, ("esp", i, h)] for k in K) <= inst.kappa[i],
                        name="c15_almacenamiento_%s_%d" % (i, h))

    # (24) capacidad de cada movimiento: el plan dice si está en verde
    for p in P:
        for a in dat.E_p[p]:
            for h in HG:
                verde = sum(y.get((p, g, h), 0) for g in G[p] if a in E_pg[p, g])
                m.addConstr(
                    gp.quicksum(x[k, ("tr", a, h)] for k in K)
                    <= dat.u_barra[a] * verde,
                    name="c24_semaforo_%s_%s_%s_%d" % (p, a[0], a[1], h))

    #  (30)-(31) los productos de R quedan atados a su recorrido: el flujo es
    #  nulo sobre todo arco ajeno al camino y la espera, sobre todo nodo que no
    #  figura en él.
    R = getattr(inst, "R", None) or {}
    for k, camino in R.items():
        arcos = set(camino)
        nodos_camino = {i for a in camino for i in a}
        for a in dat.A:
            if a in arcos:
                continue
            for h in HG:
                if (k, ("tr", a, h)) in x:
                    m.addConstr(x[k, ("tr", a, h)] == 0,
                                name="c30_%s_%s_%s_%d" % (k, a[0], a[1], h))
        for i in dat.V:
            if i in nodos_camino:
                continue
            for h in HG:
                if (k, ("esp", i, h)) in x:
                    m.addConstr(x[k, ("esp", i, h)] == 0,
                                name="c31_%s_%s_%d" % (k, i, h))
    if R:
        print("  Caminos prefijados: %d de %d productos (%s)"
              % (len(R), len(K), ", ".join(sorted(R))))

    m.update()
    return m, x


# =============================================================================
#  Reporte
# =============================================================================
def reporte_real(dat, y, vx) -> None:
    inst = dat.inst
    HG, K, P, G, Delta = dat.HG, inst.K, inst.P, inst.G, dat.Delta

    transito = sum(dat.A_k[k][e][2] * vx[k, e]
                   for k in K for e in dat.A_k[k] if e[0] == "tr")
    espera = sum(dat.A_k[k][e][2] * vx[k, e]
                 for k in K for e in dat.A_k[k] if e[0] == "esp")
    objetivo = transito + espera
    demanda = sum(inst.D[k] for k in K)

    print()
    print("=" * 70)
    print("TIEMPO DE VIAJE CON EL PLAN OBSERVADO")
    print("=" * 70)
    print("  Tiempo total          : %10.2f veh-segundo por período" % objetivo)
    if objetivo > 1e-9:
        print("    - tránsito          : %10.2f  (%.1f %%)"
              % (transito, 100 * transito / objetivo))
        print("    - espera            : %10.2f  (%.1f %%)"
              % (espera, 100 * espera / objetivo))
    print("  Demanda total         : %10.2f vehículos por período" % demanda)
    if demanda > 1e-9:
        print("  Tiempo medio de viaje : %10.2f segundos por vehículo"
              % (objetivo / demanda))
        print("  Demora media          : %10.2f segundos por vehículo"
              % (espera / demanda))

    # --- el plan, capa por capa ---------------------------------------------
    print()
    print("=" * 70)
    print("PLAN OBSERVADO  (V = verde / . = rojo)")
    print("=" * 70)
    for p in P:
        print()
        print("  Intersección %s:" % p)
        for g in G[p]:
            if not any(y.get((p, g, h), 0) for h in HG):
                continue
            patron = "".join("V" if y.get((p, g, h), 0) else "." for h in HG)
            dur = sum(y.get((p, g, h), 0) for h in HG)
            print("    %-10s %s  %2d capas = %4.0f s"
                  % (g, patron, dur, dur * Delta))

    # --- dónde se pierde el tiempo ------------------------------------------
    print()
    print("=" * 70)
    print("DEMORA POR NODO [veh-segundo por período]")
    print("=" * 70)
    filas = []
    for i in dat.V:
        e = sum(Delta * vx[k, ("esp", i, h)] for k in K for h in HG)
        if e > 1e-6:
            cola = max(sum(vx[k, ("esp", i, h)] for k in K) for h in HG)
            filas.append((e, i, cola))
    for e, i, cola in sorted(filas, reverse=True)[:25]:
        lleno = "  <-- cola llena" if cola > inst.kappa[i] - 1e-6 else ""
        print("  %-12s demora = %9.2f    cola máxima = %6.2f veh (kappa = %.0f)%s"
              % (i, e, cola, inst.kappa[i], lleno))
    if len(filas) > 25:
        print("  y %d nodo(s) más con demora" % (len(filas) - 25))


# =============================================================================
#  Ejecución completa
# =============================================================================
ESTADOS = {
    GRB.OPTIMAL: "Optimal", GRB.INFEASIBLE: "Infeasible",
    GRB.UNBOUNDED: "Unbounded", GRB.INF_OR_UNBD: "Infeasible o no acotado",
    GRB.TIME_LIMIT: "Límite de tiempo", GRB.INTERRUPTED: "Interrumpido",
    GRB.SUBOPTIMAL: "Subóptimo",
}


def ejecutar_real(inst: Instancia, planes: Dict[str, dict],
                  Delta: float = 5.0,
                  escalar_demanda: bool = True,
                  tiempo_limite: float = 600.0,
                  log: bool = True,
                  con_reporte: bool = True,
                  env: Optional[gp.Env] = None) -> dict:
    """Resuelve el flujo sobre la red con el plan semafórico dado."""
    print()
    print("#" * 70)
    print("#  PROBLEMA REAL: %s" % inst.nombre)
    print("#  El plan semafórico está dado; sólo se resuelve el flujo.")
    print("#" * 70)

    dat, y, nueva = preparar_real(inst, planes, Delta, escalar_demanda)

    print("  Delta          : %.1f s" % Delta)
    print("  Gamma          : %.0f s   (mcm de los ciclos declarados)" % nueva.Gamma)
    print("  H              : %d capas" % nueva.H)
    for p in sorted(planes):
        ciclo = sum(dur for _, dur in planes[p]["ciclo"])
        print("      %-6s ciclo %3.0f s, desfase %3.0f s, se repite %d vez/veces"
              % (p, ciclo, planes[p].get("desfase", 0.0),
                 round(nueva.Gamma / ciclo)))
    if escalar_demanda and abs(nueva.Gamma - inst.Gamma) > 1e-9:
        print("  Demandas reescaladas por %.2f para conservar el flujo por hora"
              % (nueva.Gamma / inst.Gamma))
    print("  Nodos físicos  : %d" % len(dat.V))
    print("  Arcos físicos  : %d  (%d movimientos semaforizados)"
          % (len(dat.A), len(dat.E)))
    print("  Productos      : %d" % len(nueva.K))

    m, x = construir_flujo(dat, y, env=env)
    print("  Variables      : %d  (ninguna entera: es un programa lineal)"
          % m.NumVars)
    print("  Restricciones  : %d" % m.NumConstrs)
    print("-" * 70)

    m.Params.OutputFlag = 1 if log else 0
    m.Params.TimeLimit = tiempo_limite
    t0 = time.perf_counter()
    m.optimize()
    segundos = time.perf_counter() - t0

    print("-" * 70)
    estado = ESTADOS.get(m.Status, "Status %d" % m.Status)
    print("Estado: %s" % estado)
    print("Tiempo de resolución: %.2f segundos" % segundos)

    resumen = dict(instancia=nueva.nombre, estado=estado, segundos=segundos,
                   variables=m.NumVars, restricciones=m.NumConstrs,
                   objetivo=None, datos=dat)

    if m.SolCount == 0:
        print("No hay solución factible: con este plan el tránsito no entra "
              "en la red.")
        if m.Status == GRB.INFEASIBLE:
            print("Para diagnosticar: m.computeIIS() y m.write('iis.ilp')")
        resumen["modelo"] = m
        return resumen

    vx = {clave: var.X for clave, var in x.items()}
    resumen["objetivo"] = m.ObjVal
    print("Tiempo total de viaje: %.4f veh-segundo por período" % m.ObjVal)

    if con_reporte:
        reporte_real(dat, y, vx)

    #  La solución se devuelve con la misma forma que la de ``modelo.ejecutar``,
    #  de modo que ``visual.graficar`` la acepta sin cambios.
    sol = dict(
        x=vx,
        y={(p, g, h): y.get((p, g, h), 0)
           for p in nueva.P for g in nueva.G[p] for h in dat.HG},
        z={(p, g): 1 if any(y.get((p, g, h), 0) for h in dat.HG) else 0
           for p in nueva.P for g in nueva.G[p]})
    sol["y_on"] = {(p, g, h): int(sol["y"][p, g, h] == 1
                                  and sol["y"][p, g, dat.capa_anterior(h)] == 0)
                   for p in nueva.P for g in nueva.G[p] for h in dat.HG}
    sol["y_off"] = {(p, g, h): int(sol["y"][p, g, dat.capa_anterior(h)] == 1
                                   and sol["y"][p, g, h] == 0)
                    for p in nueva.P for g in nueva.G[p] for h in dat.HG}

    resumen["modelo"] = m
    resumen["solucion"] = sol
    return resumen


# =============================================================================
#  Comparación con el plan óptimo
# =============================================================================
def comparar_con_optimo(inst: Instancia, planes: Dict[str, dict],
                        Delta: float = 5.0, **kw) -> None:
    """Resuelve las dos variantes y muestra cuánto se ganaría optimizando.

    La del plan observado y la que diseña el plan, sobre la misma red y las
    mismas demandas. La diferencia es lo que aporta la coordinación.
    """
    from modelo import ejecutar

    real = ejecutar_real(inst, planes, Delta=Delta, con_reporte=False, **kw)
    opt = ejecutar(real["datos"].inst, con_reporte=False, con_verificacion=False,
                   **{k: v for k, v in kw.items() if k != "escalar_demanda"})

    print()
    print("=" * 70)
    print("PLAN OBSERVADO CONTRA PLAN ÓPTIMO")
    print("=" * 70)
    if real["objetivo"] is None or opt["objetivo"] is None:
        print("  Alguna de las dos variantes no tiene solución.")
        return
    a, b = real["objetivo"], opt["objetivo"]
    print("  Con el plan observado : %10.2f veh-segundo" % a)
    print("  Con el plan óptimo    : %10.2f veh-segundo" % b)
    print("  Diferencia            : %10.2f  (%.1f %% menos)"
          % (a - b, 100 * (a - b) / a if a > 1e-9 else 0.0))