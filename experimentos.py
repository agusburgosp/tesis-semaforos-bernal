"""
Cuatro barridos que mueven un solo factor por vez, para ver cómo se complejiza
el problema y hasta dónde llega el solver.

    python experimentos.py                 # los cuatro
    python experimentos.py tamanio demanda # sólo esos
    python experimentos.py --tiempo 120 --gap 0.01
    python experimentos.py --csv resultados.csv

Los cuatro barridos
-------------------
``tamanio``    crece la red sin agregar semáforos
``semaforos``  crecen los semáforos sin cambiar la red
``demanda``    crece el volumen sin cambiar la red ni los productos
``periodo``    crecen Gamma y H manteniendo Delta

Sobre el aislamiento
--------------------
Aislar cada factor por completo no siempre es posible, así que las
configuraciones están elegidas para que lo sea:

* el barrido de tamaño crece sólo en columnas. Como las avenidas son
  verticales, alargar la malla hacia el este agrega calles de barrio pero no
  semáforos. Y la demanda se impone fija, de modo que el mismo tránsito
  circula por una red cada vez más grande.
* el barrido de semáforos parte de la misma grilla y va semaforizando las
  esquinas de las calles de barrio con ``semaforos_extra``. Las calles, sus
  sentidos y sus capacidades son siempre las mismas.
* el barrido de demanda fija la cobertura y mueve sólo la saturación, de modo
  que los productos son los mismos y lo único que cambia es el volumen.
* el barrido de período mantiene Delta = 5 s y compensa la saturación por H,
  porque el generador calcula la demanda proporcional a la cantidad de capas.

Ninguna de estas configuraciones es realista por separado: una malla de 3 x 20
con los mismos cinco semáforos que una de 3 x 4 no existe en ninguna ciudad.
Lo son a propósito, porque el objetivo no es representar un barrio sino medir
el efecto de un factor con los demás quietos.

Igual la tabla informa nodos, semáforos, productos y demanda en cada corrida,
así que si algo más se movió se ve.

"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from typing import Dict, List, Optional

from generador_red import generar_red
from generador_demandas import generar_demandas
from modelo import construir, ejecutar, preparar


# =============================================================================
#  Configuración base: de acá parte cada barrido
# =============================================================================
#  Reproduce la instancia ``red`` de instancias.py: una malla de 3 x 4 con una
#  avenida de doble mano (columna B) y una de mano única con semáforo cada dos
#  cuadras (columna D), más dos calles de barrio. Los sentidos se fuerzan para
#  que coincidan con los de la red escrita a mano.
#
#  Se verificó que el generador produce exactamente los mismos movimientos que
#  ``red`` en las cinco intersecciones: rectos y giros a la derecha en todas,
#  más el giro a la izquierda N->E en las dos de la avenida de mano única,
#  donde no cruza ninguna corriente.
#
#  copias_por_fase=1: con 2, cada configuración se duplica para poder recibir
#  dos bloques de verde separados, pero eso genera soluciones equivalentes por
#  permutación que el árbol de branch-and-bound tiene que descartar una por
#  una. La simetría termina dominando el tiempo y tapa el factor que cada
#  barrido quiere medir.
BASE = dict(filas=3, columnas=4,
            avenidas_v=dict(doble=1, tipo1=1), separacion_v=2, inicio_v=1,
            sentidos_v={2: "N", 3: "S"},
            copias_por_fase=1)
BASE_DEMANDA = dict(nivel="intermedia", Gamma=60.0, H=12, L=2, U=8, semilla=1)

#  Demanda fija para el barrido de tamaño.
#
#  El generador deriva los productos y su volumen de la red: una malla más
#  larga tiene más ingresos y más capacidad, de modo que al agrandarla crece
#  también la demanda y el barrido mediría dos cosas a la vez. Acá se imponen
#  los mismos seis pares origen-destino con el mismo volumen en todas las
#  redes del barrido.
#
#  Los ocho nodos de borde que usan (las puntas de las dos avenidas, de la
#  calle C y de las tres transversales) existen en todas las mallas de 3 x n,
#  y se verificó que los seis pares son alcanzables desde 3 x 4 hasta 3 x 20.
DEMANDA_FIJA = dict(
    K=["k1", "k2", "k3", "k4", "k5", "k6"],
    o={"k1": "oBN", "k2": "oBS", "k3": "oDS", "k4": "oAS",
       "k5": "o1E", "k6": "o2O"},
    d={"k1": "dBS", "k2": "dBN", "k3": "dDS", "k4": "dAS",
       "k5": "d1E", "k6": "d2O"},
    D={"k1": 8.0, "k2": 8.0, "k3": 6.0, "k4": 6.0, "k5": 4.0, "k6": 4.0},
)


# =============================================================================
#  Los cuatro barridos
# =============================================================================
def barrido_tamanio() -> List[tuple]:
    """Crece la red sin agregar semáforos ni cambiar la demanda.

    Las avenidas son verticales, de modo que alargar la malla hacia el este
    sólo agrega calles de barrio: la cantidad de semáforos no cambia. Y los
    productos se imponen con ``DEMANDA_FIJA``, de modo que el mismo tránsito
    circula por una red cada vez más grande.

    Igual que el barrido de semáforos mantiene las calles fijas para medir
    sólo el efecto de semaforizar, acá se mantiene la demanda fija para medir
    sólo el efecto del tamaño. Ninguna de las dos configuraciones es realista
    por separado: lo son a propósito, porque el objetivo es aislar un factor.
    """
    casos = []
    for columnas in (4, 6, 8, 10, 12, 16, 20):
        red = generar_red(**dict(BASE, columnas=columnas),
                          nombre="tam%02d" % columnas)
        dem = dict(BASE_DEMANDA, fija=DEMANDA_FIJA)
        casos.append(("3 x %d" % columnas, red, dem))
    return casos


def barrido_semaforos() -> List[tuple]:
    """Crecen los semáforos sin tocar las calles.

    Se parte de la red base, con sus cinco semáforos sobre las avenidas, y se
    van semaforizando también las esquinas de las calles de barrio. Las
    calles, sus sentidos y sus capacidades quedan exactamente iguales: lo
    único que cambia es cuántas esquinas tienen semáforo.
    """
    plantilla = generar_red(**BASE)
    todas = sorted(plantilla.esq_libres)

    casos = []
    for extra in (0, 2, 4, 6, 7):
        red = generar_red(**BASE, semaforos_extra=todas[:extra],
                          nombre="sem%02d" % extra)
        casos.append(("%d semáforos" % len(red.P), red, dict(BASE_DEMANDA)))
    return casos


def barrido_demanda() -> List[tuple]:
    """Crece el volumen sin cambiar la red ni los pares origen-destino.

    Con la cobertura fija y la misma semilla, los productos son siempre los
    mismos: lo único que se mueve es cuánto flujo lleva cada uno.
    """
    red = generar_red(**BASE, nombre="dem")
    casos = []
    for saturacion in (0.3, 0.6, 0.9, 1.2, 1.5, 1.8):
        dem = dict(BASE_DEMANDA, cobertura=0.7, saturacion=saturacion)
        casos.append(("saturación %.2f" % saturacion, red, dem))
    return casos


def barrido_periodo() -> List[tuple]:
    """Crece el período manteniendo Delta en 5 s.

    H = Gamma / Delta, de modo que alargar el ciclo aumenta la cantidad de
    capas y con ellas las variables semafóricas. Delta no cambia, así que los
    tiempos de tránsito siguen siendo múltiplos suyos.

    La saturación se compensa por H: el generador calcula la capacidad de un
    arco durante el período como u_barra por H, de modo que sin corregirla la
    demanda crecería con el ciclo y el barrido mediría dos cosas a la vez.
    """
    red = generar_red(**BASE, nombre="per")
    casos = []
    for Gamma in (40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 180.0):
        H = int(round(Gamma / 5.0))
        #  U también crece con el período. Las dos intersecciones de la
        #  avenida de mano única tienen una sola rama de acceso por lado y
        #  por lo tanto sólo dos fases: entre las dos tienen que cubrir las H
        #  capas, así que con U fijo en 8 cualquier H mayor que 16 vuelve
        #  infactible la restricción (16). Un verde máximo de 40 s es
        #  razonable en un ciclo de 60, pero no en uno de 180.
        dem = dict(BASE_DEMANDA, Gamma=Gamma, H=H,
                   U=max(BASE_DEMANDA["U"], (H + 1) // 2),
                   saturacion=0.5 * 12.0 / H)
        casos.append(("Gamma %3.0f s (H %2d)" % (Gamma, H), red, dem))
    return casos


BARRIDOS = {
    "tamanio": ("TAMAÑO DE LA RED (sin agregar semáforos)", barrido_tamanio),
    "semaforos": ("CANTIDAD DE SEMÁFOROS (sin cambiar las calles)", barrido_semaforos),
    "demanda": ("VOLUMEN DE DEMANDA (misma red, mismos productos)", barrido_demanda),
    "periodo": ("PERÍODO Y CAPAS (Delta constante)", barrido_periodo),
}


# =============================================================================
#  Una corrida
# =============================================================================
def promediar(filas: List[dict]) -> dict:
    """Resume varias repeticiones de un mismo caso.

    Para los tiempos y el gap informa el promedio; además guarda el mínimo y
    el máximo del tiempo total, que es lo que permite distinguir una tendencia
    de la varianza propia del solver.
    """
    validas = [f for f in filas if "nodos" in f]
    if not validas:
        return filas[0]

    base = dict(validas[0])
    base["repeticiones"] = len(validas)
    for campo in ("demanda", "productos", "objetivo", "segundos",
                  "gap", "frac_espera"):
        valores = [f.get(campo) for f in validas if f.get(campo) is not None]
        base[campo] = sum(valores) / len(valores) if valores else None
    tiempos = [f["segundos"] for f in validas]
    base["t_min"], base["t_max"] = min(tiempos), max(tiempos)
    estados = {f["estado"] for f in validas}
    base["estado"] = estados.pop() if len(estados) == 1 else "mixto"
    return base


def correr(etiqueta: str, red, demanda: dict,
           tiempo: float, gap: Optional[float], hilos: Optional[int]) -> dict:
    """Arma la instancia, la resuelve y devuelve una fila de la tabla."""
    fila = dict(caso=etiqueta)
    print("  corriendo %-24s" % etiqueta, end="", flush=True)
    demanda = dict(demanda)
    fija = demanda.pop("fija", None)
    try:
        inst = generar_demandas(red, **demanda)
        if fija is not None:
            #  Se reemplazan los productos que generó el generador por los
            #  fijos, de modo que todas las redes del barrido lleven
            #  exactamente el mismo tránsito.
            inst.K = list(fija["K"])
            inst.o, inst.d = dict(fija["o"]), dict(fija["d"])
            inst.D, inst.D_kh = dict(fija["D"]), None
            inst.R = None
    except AssertionError as e:
        fila.update(estado="no se pudo armar", detalle=str(e)[:60])
        print("  no se pudo armar")
        return fila

    dat = preparar(inst)
    fila.update(
        nodos=len(dat.V), arcos=len(dat.A), semaforos=len(inst.P),
        fases=sum(len(inst.G[p]) for p in inst.P),
        productos=len(inst.K), demanda=sum(inst.D.values()),
        H=inst.H)

    #  ``ejecutar`` imprime su propio encabezado por cada instancia, que acá
    #  sólo ensucia la tabla.
    with contextlib.redirect_stdout(io.StringIO()):
        r = ejecutar(inst, tiempo_limite=tiempo, gap=gap, hilos=hilos,
                     log=False, con_reporte=False, con_verificacion=False)
    fila.update(
        variables=r["variables"], binarias=r["binarias"],
        restricciones=r["restricciones"],
        estado=r["estado"], segundos=r["segundos"],
        frac_espera=r.get("frac_espera"),
        objetivo=r["objetivo"], gap=r["gap"])
    print("  %-18s %8.1f s" % (r["estado"], r["segundos"]))
    return fila


# =============================================================================
#  Tabla
# =============================================================================
#  "hallar" es cuánto tardó en encontrar la solución que terminó siendo la
#  mejor; "probar" es lo que llevó después demostrar que era óptima.
#  "esp %" dice cuánto del tiempo de viaje es demora: si es bajo, la
#  instancia circula a flujo libre y no está congestionada.
ENCABEZADO = ("%-20s %6s %5s %5s %8s %9s %8s %10s %7s %9s %7s"
              % ("caso", "nodos", "sem", "prod", "demanda",
                 "binarias", "restr", "objetivo", "esp %", "total", "gap %"))


def imprimir(titulo: str, filas: List[dict]) -> None:
    print()
    print("=" * len(ENCABEZADO))
    print(titulo)
    print("=" * len(ENCABEZADO))
    print(ENCABEZADO)
    print("-" * len(ENCABEZADO))
    for f in filas:
        if "nodos" not in f:
            print("%-20s  %s" % (f["caso"], f.get("detalle", f["estado"])))
            continue
        esp = f.get("frac_espera")
        print("%-20s %6d %5d %5.1f %8.1f %9d %8d %10s %7s %9.1f %7s"
              % (f["caso"], f["nodos"], f["semaforos"],
                 f["productos"], f["demanda"], f["binarias"],
                 f["restricciones"],
                 "%.1f" % f["objetivo"] if f["objetivo"] is not None else "-",
                 "%.1f" % (100 * esp) if esp is not None else "-",
                 f["segundos"],
                 "%.2f" % (100 * f["gap"]) if f["gap"] is not None else "-"))

    sin_optimo = [f for f in filas if f.get("estado") not in (None, "Optimal")
                  and "nodos" in f]
    if sin_optimo:
        print()
        print("  No llegaron al óptimo dentro del límite:")
        for f in sin_optimo:
            print("    %-20s %-20s gap %s"
                  % (f["caso"], f["estado"],
                     "%.2f %%" % (100 * f["gap"]) if f["gap"] is not None else "-"))


def guardar_csv(archivo: str, todo: Dict[str, List[dict]]) -> None:
    import csv
    columnas = ["barrido", "caso", "nodos", "arcos", "semaforos", "fases",
                "productos", "demanda", "H", "variables", "binarias",
                "restricciones", "objetivo", "frac_espera",
                "segundos", "t_min", "t_max", "repeticiones",
                "gap", "estado"]
    with open(archivo, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for barrido, filas in todo.items():
            for f in filas:
                w.writerow(dict(f, barrido=barrido))
    print()
    print("  resultados en %s" % archivo)


# =============================================================================
#  Principal
# =============================================================================
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Barridos de escalabilidad del modelo.")
    parser.add_argument("barridos", nargs="*", metavar="BARRIDO",
                        help="Cuáles correr (%s). Si se omite, todos."
                             % ", ".join(BARRIDOS))
    parser.add_argument("--tiempo", type=float, default=900.0,
                        help="Límite de tiempo por instancia, en segundos (900).")
    parser.add_argument("--gap", type=float, default=0.0,
                        help="Gap relativo de corte; 0 pide optimalidad "
                             "exacta (0).")
    parser.add_argument("--hilos", type=int, default=None,
                        help="Hilos que usa Gurobi (por defecto, todos).")
    parser.add_argument("--semillas", type=int, default=1,
                        help="Repeticiones de cada caso, con distinta semilla "
                             "en la demanda (1). Sirve para separar la "
                             "tendencia de la varianza del solver.")
    parser.add_argument("--csv", default=None,
                        help="Guarda los resultados en un archivo CSV.")
    args = parser.parse_args(argv)

    desconocidos = [b for b in args.barridos if b not in BARRIDOS]
    if desconocidos:
        parser.error("barrido desconocido: %s" % ", ".join(desconocidos))

    nombres = args.barridos or list(BARRIDOS)
    todo: Dict[str, List[dict]] = {}

    print()
    print("Límite de tiempo: %.0f s por instancia   ·   gap de corte: %.2f %%"
          "   ·   %d semilla(s) por caso"
          % (args.tiempo, 100 * args.gap, args.semillas))

    for nombre in nombres:
        titulo, armar = BARRIDOS[nombre]
        filas = []
        for etiqueta, red, dem in armar():
            repeticiones = [
                correr(etiqueta, red, dict(dem, semilla=s),
                       args.tiempo, args.gap, args.hilos)
                for s in range(1, args.semillas + 1)]
            filas.append(promediar(repeticiones))
        imprimir(titulo, filas)
        todo[nombre] = filas

    if args.csv:
        guardar_csv(args.csv, todo)
    return 0


if __name__ == "__main__":
    sys.exit(main())