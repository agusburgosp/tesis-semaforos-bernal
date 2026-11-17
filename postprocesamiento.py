"""
====================

Relocalización de las colas sobre una solución óptima.

El modelo es indiferente al lugar donde se produce la demora: como todos los
arcos de espera cuestan Delta, esperar una capa en v1 y después atravesar el
arco a = (v1, v2) cuesta lo mismo que atravesarlo primero y esperar en v2. Eso
es lo que afirma la proposición de óptimos alternativos, y en consecuencia el
solver puede devolver una solución que acumula flujo en un tramo intermedio
aunque el acceso a la intersección siguiente esté libre.

Ese reparto no es el que se observa en la calle. Los vehículos avanzan mientras
tengan lugar y la cola se forma contra la línea de detención, no varias cuadras
antes. Este módulo toma la solución del solver y adelanta la espera todo lo
posible, hasta que cada porción de flujo queda detenida lo más cerca del
semáforo que le permiten las capacidades.

El resultado es OTRO ÓPTIMO del mismo problema: mismo valor objetivo y mismas
variables semafóricas. No se agrega ningún costo ni se modifica el modelo.

Cómo funciona
-------------
La solución del solver es, para cada producto, una circulación sobre la red
cíclicamente expandida. El primer paso es DESCOMPONERLA EN CAMINOS: cada
porción de flujo queda con su recorrido explícito, que dice por qué nodos pasa
y en qué capa está en cada uno. Los arcos de espera que atraviesa son los
intervalos en los que estuvo detenida.

Con el recorrido a la vista, adelantar es recorrerlo y correr cada espera
hacia adelante mientras se pueda. No hace falta ninguna precaución contra
ciclos: un camino tiene un orden y se recorre una sola vez, de modo que una
porción de flujo nunca puede volver a un nodo por el que ya pasó.

    from modelo import ejecutar, verificar
    from postprocesamiento import adelantar_esperas, comparar

    r = ejecutar(corredor())
    sol2 = adelantar_esperas(r["datos"], r["solucion"])
    comparar(r["datos"], r["solucion"], sol2)
    verificar(r["datos"], sol2)

Hipótesis
---------
Se supone que la solución es ÓPTIMA. Eso garantiza que la circulación de cada
producto no contiene ciclos: en la red cíclicamente expandida todo ciclo
avanza un múltiplo del período y por lo tanto cuesta al menos Gamma, de modo
que el solver lo habría eliminado. Sobre una solución obtenida por límite de
tiempo la descomposición los cancela igual, pero conviene saber que en ese
caso el objetivo puede bajar.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

Arco = Tuple[str, str]


# =============================================================================
#  Lecturas auxiliares
# =============================================================================
def objetivo(dat, sol) -> float:
    """Valor de la función objetivo (10) de una solución."""
    return sum(dat.A_k[k][e][2] * sol["x"][k, e]
               for k in dat.inst.K for e in dat.A_k[k])


def esperas_por_nodo(dat, sol) -> Dict[str, float]:
    """Tiempo de espera acumulado en cada nodo [veh-segundo por período]."""
    return {i: sum(dat.Delta * sol["x"][k, ("esp", i, h)]
                   for k in dat.inst.K for h in dat.HG)
            for i in dat.V}


def accesos_semaforizados(dat) -> List[str]:
    """Nodos de acceso a las intersecciones semaforizadas.

    Son los únicos lugares donde una cola corresponde a un semáforo en rojo.
    """
    return sorted({a[0] for p in dat.inst.P for a in dat.E_p[p]})


# =============================================================================
#  Distancia al destino
# =============================================================================
def arcos_usados(dat, sol, k: str, tol: float = 1e-9) -> set:
    """Arcos físicos por los que circula el producto k.

    El adelantamiento nunca cambia el flujo agregado de un arco: sólo lo mueve
    entre capas. Por eso este conjunto es invariante y alcanza con calcularlo
    una vez.
    """
    return {a for a in dat.A
            if sum(sol["x"][k, ("tr", a, h)] for h in dat.HG) > tol}


def distancias_al_destino(dat, destino: str,
                          arcos: Optional[set] = None) -> Dict[str, float]:
    """Tiempo de tránsito mínimo desde cada nodo hasta ``destino``.

    Se calcula recorriendo los arcos al revés, de modo que una sola pasada de
    Dijkstra desde el destino da la distancia de todos los nodos. Los pesos
    son los tiempos de tránsito tau_a, sin mirar capacidades ni semáforos.

    Si se pasa ``arcos``, la distancia se mide ÚNICAMENTE sobre ese
    subconjunto. Usarlo con los arcos que el producto efectivamente recorre es
    lo que evita ser innecesariamente restrictivo: un recorrido que se aleja
    del destino en línea recta sigue acercándose medido sobre su propia ruta,
    porque dentro de ella no hay atajo.
    """
    candidatos = dat.A if arcos is None else [a for a in dat.A if a in arcos]
    entrantes: Dict[str, List[Arco]] = {}
    for a in candidatos:
        entrantes.setdefault(a[1], []).append(a)

    dist = {destino: 0.0}
    cola = [(0.0, destino)]
    visto = set()
    while cola:
        dv, v = heapq.heappop(cola)
        if v in visto:
            continue
        visto.add(v)
        for a in entrantes.get(v, []):        # a = (w, v): w llega a v
            w = a[0]
            nueva = dv + dat.tau[a]
            if nueva < dist.get(w, float("inf")) - 1e-12:
                dist[w] = nueva
                heapq.heappush(cola, (nueva, w))
    return dist


# =============================================================================
#  Descomposición de la circulación en caminos
# =============================================================================
def descomponer(dat, sol, k: str, tol: float = 1e-7) -> List[tuple]:
    """Descompone la circulación del producto k en caminos con su flujo.

    La solución x^k conserva flujo en todos los nodos y cierra por el arco de
    retorno: es una circulación, y toda circulación se descompone en caminos
    del superorigen al superdestino más eventuales ciclos que se cancelan.

    Como los nodos de la red expandida son pares (nodo físico, capa), cada
    camino de la descomposición YA ES una trayectoria: dice en qué capa está
    el flujo en cada nodo, y los arcos de espera que atraviesa son los
    intervalos en los que estuvo detenido.

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
                indice[w] = corte
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


def adelantar_esperas(dat, sol,
                      tol: float = 1e-9,
                      verbose: bool = False) -> dict:
    """Devuelve otro óptimo en el que las colas están lo más adelante posible.

    Se descompone la circulación de cada producto en itinerarios y se recorre
    cada uno adelantando sus esperas.

    El intercambio generaliza el de la proposición de óptimos alternativos a
    un TRAMO de uno o más arcos consecutivos. Si una porción espera en v1
    durante la capa h y a continuación atraviesa los arcos a_1, ..., a_r, se
    la reasigna para que los atraviese todos una capa antes y espere al final,
    en el nodo donde termina a_r. Los dos recorridos salen de la misma copia y
    llegan a la misma, y ambos usan un arco de espera y las mismas copias
    temporales de los arcos, de modo que el costo no cambia.

    Por qué un tramo y no un solo arco
    ----------------------------------
    Los nodos de salida de una intersección tienen kappa = 0, así que el flujo
    que atraviesa un movimiento interno no puede detenerse inmediatamente
    después: tiene que seguir hasta el acceso siguiente. Saltar de a un arco
    dejaría la cola varada en el acceso del primer semáforo aunque estuviera
    en verde. El tramo se extiende, entonces, hasta el primer nodo con
    kappa > 0, que es donde la cola efectivamente puede formarse.

    Qué lo limita
    -------------
      * un movimiento interno sólo se atraviesa si su fase está en VERDE en la
        capa a la que se adelanta el cruce, restricción (24);
      * cada arco del tramo debe admitir el flujo en su nueva capa,
        restricción (14);
      * el nodo final debe tener lugar para la cola, restricción (15).

    Si un tramo no admite toda la porción, se adelanta la parte que entra y el
    resto queda donde está, lo que reproduce la propagación de la cola hacia
    los tramos anteriores. Si no entra nada, la espera no se mueve.
    """
    inst = dat.inst
    H, K = inst.H, inst.K
    movimientos = set(dat.E)

    #  esquina a la que pertenece cada movimiento, para consultar su fase
    esquina = {a: p for p in inst.P for a in dat.E_p[p]}

    def en_verde(p, a, h):
        return any(sol["y"][p, g, h] == 1
                   for g in inst.G[p] if a in inst.E_pg[p, g])

    caminos = {k: descomponer(dat, sol, k) for k in K}

    x = {clave: 0.0 for clave in sol["x"]}
    for k in K:
        for f, camino in caminos[k]:
            for e in camino:
                x[k, e] += f
        x[k, ("ret", k)] = inst.D[k]

    perdido = sum(inst.D[k] - sum(f for f, _ in caminos[k]) for k in K)
    if perdido > 1e-6:
        print("  Aviso: la descomposición no cubre %.4f veh. ¿La solución es "
              "óptima?" % perdido)

    adelantos, movido, saltos_largos, parciales = 0, 0.0, 0, 0

    for k in K:
        #  Cada elemento es (porción, pasos, posición desde la que seguir).
        #  Cuando sólo entra una parte, la porción se divide en dos.
        pila = []
        for f, camino in caminos[k]:
            pasos = [e for e in camino if e[0] in ("esp", "tr")]
            pila.append((f, pasos, len(pasos) - 2))
        pila.reverse()

        while pila:
            f, pasos, n = pila.pop()
            while n >= 0:
                if pasos[n][0] == "esp":
                    j = n
                    while True:
                        salto = _tramo_hasta_cola(dat, pasos, j)
                        if salto is None:
                            break
                        g = _cuanto_entra(dat, x, sol, salto, f, tol,
                                          movimientos, esquina, en_verde)
                        if g <= tol:
                            break
                        if g < f - tol:
                            #  lo que no entra se queda esperando acá y
                            #  sigue con las esperas anteriores
                            pila.append((f - g, list(pasos), n - 1))
                            f = g
                            parciales += 1

                        _intercambiar(dat, x, pasos, j, salto, f, k)
                        j += len(salto["arcos"])
                        adelantos += 1
                        movido += f
                        if len(salto["arcos"]) > 1:
                            saltos_largos += 1
                n -= 1

    if verbose:
        print("  %d adelantamiento(s); %.2f veh-capa de espera movidos"
              % (adelantos, movido))
        if saltos_largos:
            print("  %d de ellos atravesaron un movimiento semaforizado"
                  % saltos_largos)
        if parciales:
            print("  %d adelantamiento(s) parcial(es)" % parciales)

    nueva = dict(sol)
    nueva["x"] = x
    return nueva


# =============================================================================
#  Piezas del adelantamiento
# =============================================================================
def _tramo_hasta_cola(dat, pasos, j):
    """Arcos de tránsito que siguen a ``pasos[j]`` hasta el primer nodo con cola.

    Devuelve un diccionario con los arcos, la capa en la que cada uno se
    atravesaría tras el adelanto, el nodo final y la capa en la que el flujo
    llegaría a él. Si no hay un nodo con kappa > 0 antes de que el itinerario
    termine o aparezca otra espera, devuelve None: no hay dónde depositar la
    cola y el adelanto no se aplica.
    """
    inst = dat.inst
    H = inst.H
    h = pasos[j][2]                     # capa en la que hoy espera

    arcos, capas = [], []
    h_cruce = h                         # capa a la que se adelanta cada cruce
    t = j + 1
    while t < len(pasos) and pasos[t][0] == "tr":
        a = pasos[t][1]
        arcos.append(a)
        capas.append(h_cruce)
        h_cruce = (h_cruce + dat.l[a]) % H
        if inst.kappa[a[1]] > 0:        # acá se puede formar la cola
            return dict(arcos=arcos, capas=capas, pasos=list(range(j + 1, t + 1)),
                        nodo=a[1], h_llegada=h_cruce)
        t += 1
    return None                          # ningún nodo admite cola


def _cuanto_entra(dat, x, sol, salto, f, tol, movimientos, esquina, en_verde):
    """Mayor parte de ``f`` que admite el tramo (0 si no entra nada)."""
    inst = dat.inst
    K = inst.K
    g = f

    for a, h in zip(salto["arcos"], salto["capas"]):
        if a in movimientos:
            #  (24): un movimiento sólo admite flujo si su fase está en verde
            if not en_verde(esquina[a], a, h):
                return 0.0
        #  (14): capacidad del arco en su nueva capa
        libre = dat.u_barra[a] - sum(x[kk, ("tr", a, h)] for kk in K)
        g = min(g, libre)
        if g <= tol:
            return 0.0

    #  (15): capacidad de almacenamiento del nodo donde quedará la cola
    v, h = salto["nodo"], salto["h_llegada"]
    if inst.kappa[v] != float("inf"):
        libre = inst.kappa[v] - sum(x[kk, ("esp", v, h)] for kk in K)
        g = min(g, libre)
    return max(g, 0.0)


def _intercambiar(dat, x, pasos, j, salto, f, k):
    """Aplica el intercambio sobre el flujo y sobre la secuencia de pasos."""
    v1, h = pasos[j][1], pasos[j][2]

    #  la espera sale del nodo donde estaba
    x[k, ("esp", v1, h)] -= f

    #  cada arco del tramo se cruza una capa antes
    for a, h_nueva, t in zip(salto["arcos"], salto["capas"], salto["pasos"]):
        x[k, ("tr", a, pasos[t][2])] -= f
        x[k, ("tr", a, h_nueva)] += f

    #  y la espera reaparece al final del tramo
    x[k, ("esp", salto["nodo"], salto["h_llegada"])] += f

    #  la secuencia se reordena: primero los cruces, después la espera
    for n, (a, h_nueva) in enumerate(zip(salto["arcos"], salto["capas"])):
        pasos[j + n] = ("tr", a, h_nueva)
    pasos[j + len(salto["arcos"])] = ("esp", salto["nodo"], salto["h_llegada"])

# =============================================================================
#  Comparación entre la solución original y la reubicada
# =============================================================================
def comparar(dat, antes: dict, despues: dict, tol: float = 1e-6) -> None:
    """Muestra cómo se redistribuyó la espera y confirma que el óptimo no cambió."""
    inst = dat.inst
    accesos = set(accesos_semaforizados(dat))

    e_antes = esperas_por_nodo(dat, antes)
    e_despues = esperas_por_nodo(dat, despues)

    obj_antes, obj_despues = objetivo(dat, antes), objetivo(dat, despues)

    print()
    print("=" * 70)
    print("REUBICACIÓN DE LAS COLAS")
    print("=" * 70)
    print("  Objetivo antes   : %10.4f" % obj_antes)
    print("  Objetivo después : %10.4f   diferencia %.2e  %s"
          % (obj_despues, abs(obj_despues - obj_antes),
             "OK" if abs(obj_despues - obj_antes) < tol else "ERROR"))

    def reparto(esperas):
        en_acceso = sum(v for i, v in esperas.items() if i in accesos)
        fuera = sum(v for i, v in esperas.items() if i not in accesos)
        return en_acceso, fuera

    a_acc, a_fue = reparto(e_antes)
    d_acc, d_fue = reparto(e_despues)
    total = a_acc + a_fue

    print()
    print("  Espera total [veh-segundo por período]: %.2f" % total)
    if total > tol:
        print("    en accesos semaforizados :  antes %8.2f (%4.1f %%)"
              "   después %8.2f (%4.1f %%)"
              % (a_acc, 100 * a_acc / total, d_acc, 100 * d_acc / total))
        print("    en el resto de los nodos :  antes %8.2f (%4.1f %%)"
              "   después %8.2f (%4.1f %%)"
              % (a_fue, 100 * a_fue / total, d_fue, 100 * d_fue / total))

    print()
    print("  %-12s %12s %12s %12s" % ("nodo", "antes", "después", "cambio"))
    for i in dat.V:
        if max(e_antes[i], e_despues[i]) <= tol:
            continue
        marca = " (acceso)" if i in accesos else ""
        print("  %-12s %12.2f %12.2f %+12.2f%s"
              % (i, e_antes[i], e_despues[i], e_despues[i] - e_antes[i], marca))

    # Nodos que conservan cola fuera de un acceso: la cola no pudo adelantarse
    restantes = [i for i in dat.V
                 if i not in accesos and e_despues[i] > tol]
    if restantes:
        print()
        print("  Queda espera fuera de los accesos en: %s" % ", ".join(restantes))
        print("  Es el caso en que la cola del acceso siguiente ya está llena")
        print("  o el tramo no admite más flujo en esa capa: la cola se propaga")
        print("  hacia atrás, tal como ocurre en la realidad.")


# =============================================================================
#  Atajo
# =============================================================================
def reubicar(resumen: dict, con_comparacion: bool = True,
             con_verificacion: bool = True) -> Optional[dict]:
    """Aplica el postprocesamiento al resultado de ``modelo.ejecutar``.

    Devuelve la solución reubicada y, si se pide, la compara con la original y
    vuelve a verificar todas las restricciones sobre ella.
    """
    if "solucion" not in resumen:
        print("La instancia no tiene solución: no hay nada que reubicar.")
        return None

    dat, sol = resumen["datos"], resumen["solucion"]
    nueva = adelantar_esperas(dat, sol, verbose=True)

    if con_comparacion:
        comparar(dat, sol, nueva)
    if con_verificacion:
        from modelo import verificar
        verificar(dat, nueva)

    return nueva