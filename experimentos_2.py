"""
==================

Barrido en dos dimensiones a la vez: para cada tamaño de malla se resuelve la
instancia con distintas cantidades de esquinas semaforizadas, desde las que
traen las avenidas hasta semaforizarlas todas.

A diferencia de los barridos de ``experimentos.py``, que mueven un factor por
vez, acá interesa ver cómo interactúan los dos: si el tamaño de la red importa
poco cuando los semáforos son pocos pero empieza a pesar cuando son muchos, o
si los dos efectos son independientes entre sí.

La demanda se mantiene fija en todas las corridas, con los mismos seis pares
origen-destino y el mismo volumen, de modo que lo único que cambia entre una
celda y otra es la geometría de la red y cuántas de sus esquinas llevan
semáforo.

Salidas
-------
Una tabla por tamaño de malla, un resumen con todas las corridas, y un
gráfico de burbujas donde cada punto es una instancia: la posición da la
cantidad de nodos y de semáforos, y el área es proporcional al tiempo de
resolución. Las instancias que no cerraron dentro del límite se marcan con un
borde distinto.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from typing import Dict, List, Optional

from generador_red import generar_red
from generador_demandas import generar_demandas
from modelo import ejecutar, preparar

from experimentos import BASE, BASE_DEMANDA, DEMANDA_FIJA


# =============================================================================
#  Las instancias del barrido
# =============================================================================
#  Los mismos valores que recorren los barridos de ``experimentos.py``: de
#  3 x 4 a 3 x 20 en tamaño, y de 5 a 12 semáforos semaforizando esquinas de
#  las calles de barrio. Cruzarlos da una grilla de 7 x 5 instancias.
COLUMNAS = (4, 8, 12, 20)
EXTRAS = (0, 2, 4, 6, 7)        # semáforos: 5, 7, 9, 11 y 12


def casos(columnas: List[int], extras: List[int]) -> List[tuple]:
    """Arma la grilla de instancias: cada tamaño de malla con cada cantidad de
    semáforos.

    Se parte en cada caso de la red base, que trae sus cinco semáforos sobre
    las avenidas, y se van semaforizando esquinas de las calles de barrio.
    Como la lista de esquinas libres se recorre ordenada y las primeras
    coinciden en todas las mallas, semaforizar ``n`` esquinas significa
    semaforizar las mismas ``n`` esquinas en cualquier tamaño: lo que cambia
    entre una fila y otra de la grilla es sólo cuántas calles de barrio se
    agregaron alrededor.
    """
    salida = []
    for c in columnas:
        plantilla = generar_red(**dict(BASE, columnas=c))
        libres = sorted(plantilla.esq_libres)
        for extra in extras:
            if extra > len(libres):
                continue
            red = generar_red(**dict(BASE, columnas=c),
                              semaforos_extra=libres[:extra],
                              nombre="c%02d_s%02d" % (c, extra))
            salida.append((c, red))
    return salida


def correr(columnas: int, red, tiempo: float, gap: Optional[float],
           hilos: Optional[int]) -> dict:
    """Resuelve una instancia y devuelve su fila de la tabla."""
    etiqueta = "3 x %d, %d sem" % (columnas, len(red.P))
    print("  %-20s" % etiqueta, end="", flush=True)

    fila = dict(caso=etiqueta, columnas=columnas, semaforos=len(red.P))
    try:
        inst = generar_demandas(red, **BASE_DEMANDA)
        inst.K = list(DEMANDA_FIJA["K"])
        inst.o, inst.d = dict(DEMANDA_FIJA["o"]), dict(DEMANDA_FIJA["d"])
        inst.D, inst.D_kh = dict(DEMANDA_FIJA["D"]), None
        inst.R = None
    except AssertionError as e:
        fila.update(estado="no se pudo armar", detalle=str(e)[:60])
        print("  no se pudo armar")
        return fila

    dat = preparar(inst)
    fila.update(nodos=len(dat.V), arcos=len(dat.A),
                fases=sum(len(inst.G[p]) for p in inst.P),
                productos=len(inst.K), demanda=sum(inst.D.values()))

    with contextlib.redirect_stdout(io.StringIO()):
        r = ejecutar(inst, tiempo_limite=tiempo, gap=gap, hilos=hilos,
                     log=False, con_reporte=False, con_verificacion=False)

    fila.update(variables=r["variables"], binarias=r["binarias"],
                restricciones=r["restricciones"], estado=r["estado"],
                segundos=r["segundos"], objetivo=r["objetivo"],
                frac_espera=r.get("frac_espera"), gap=r["gap"])
    print("  %6d nodos  %5d bin  %-12s %8.1f s"
          % (fila["nodos"], fila["binarias"], r["estado"], r["segundos"]))
    return fila


# =============================================================================
#  Tabla
# =============================================================================
ENCABEZADO = ("%-18s %6s %6s %9s %8s %10s %7s %9s %7s"
              % ("caso", "nodos", "sem", "binarias", "demanda",
                 "objetivo", "esp %", "tiempo", "gap %"))


def imprimir(filas: List[dict], titulo: str) -> None:
    print()
    print("=" * len(ENCABEZADO))
    print(titulo)
    print("=" * len(ENCABEZADO))
    print(ENCABEZADO)
    print("-" * len(ENCABEZADO))
    for f in filas:
        if "nodos" not in f:
            print("%-18s  %s" % (f["caso"], f.get("detalle", f["estado"])))
            continue
        esp = f.get("frac_espera")
        print("%-18s %6d %6d %9d %8.1f %10s %7s %9.1f %7s"
              % (f["caso"], f["nodos"], f["semaforos"], f["binarias"],
                 f["demanda"],
                 "%.1f" % f["objetivo"] if f["objetivo"] is not None else "-",
                 "%.1f" % (100 * esp) if esp is not None else "-",
                 f["segundos"],
                 "%.2f" % (100 * f["gap"]) if f["gap"] is not None else "-"))


def guardar_csv(archivo: str, filas: List[dict]) -> None:
    import csv
    columnas = ["caso", "columnas", "nodos", "arcos", "semaforos", "fases",
                "productos", "demanda", "variables", "binarias",
                "restricciones", "objetivo", "frac_espera", "segundos",
                "gap", "estado"]
    with open(archivo, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for f in filas:
            w.writerow(f)
    print()
    print("  resultados en %s" % archivo)


# =============================================================================
#  Gráfico de burbujas
# =============================================================================
def figura(filas: List[dict], archivo: str, tiempo: float) -> Optional[str]:
    """Nodos en el eje horizontal, semáforos en el vertical, tiempo en el área.

    El área del círculo es proporcional al tiempo de resolución, de modo que
    la comparación visual entre dos puntos refleja el cociente entre sus
    tiempos. Las instancias que no alcanzaron el óptimo dentro del límite se
    dibujan con borde punteado.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    datos = [f for f in filas if "nodos" in f and f.get("segundos")]
    if not datos:
        print("  no hay corridas que graficar")
        return None

    t_max = max(f["segundos"] for f in datos)
    AREA_MAX = 2200.0        # área del círculo más grande, en puntos cuadrados
    AREA_MIN = 25.0

    fig, ax = plt.subplots(figsize=(9.5, 6.5))

    for f in datos:
        optima = f.get("estado") == "Optimal"
        area = AREA_MIN + (AREA_MAX - AREA_MIN) * f["segundos"] / t_max
        ax.scatter(f["nodos"], f["semaforos"], s=area,
                   facecolor="#2e8b57" if optima else "#c0392b",
                   alpha=0.45,
                   edgecolor="#2c3e50" if optima else "#c0392b",
                   linewidth=1.0 if optima else 1.6,
                   linestyle="solid" if optima else "dashed",
                   zorder=3)

    #  Se etiquetan sólo las corridas más lentas de cada tamaño de malla, para
    #  no saturar la figura.
    por_malla: Dict[int, List[dict]] = {}
    for f in datos:
        por_malla.setdefault(f["columnas"], []).append(f)
    for grupo in por_malla.values():
        peor = max(grupo, key=lambda f: f["segundos"])
        ax.annotate("%.0f s" % peor["segundos"],
                    (peor["nodos"], peor["semaforos"]),
                    textcoords="offset points", xytext=(0, 16),
                    ha="center", fontsize=7.5, color="#2c3e50", zorder=4)

    from matplotlib.lines import Line2D

    def burbuja(area, color, borde, estilo="solid"):
        return Line2D([0], [0], marker="o", linestyle="none",
                      markersize=(area / 3.1416) ** 0.5,
                      markerfacecolor=color, alpha=0.45,
                      markeredgecolor=borde, markeredgewidth=1.0)

    marcas = []
    for valor in (t_max / 8, t_max / 2, t_max):
        area = AREA_MIN + (AREA_MAX - AREA_MIN) * valor / t_max
        marcas.append((burbuja(area, "#2e8b57", "#2c3e50"), "%.0f s" % valor))
    leyenda = ax.legend([m for m, _ in marcas], [t for _, t in marcas],
                        title="tiempo de resolución", loc="upper left",
                        labelspacing=2.2, borderpad=1.2, handletextpad=2.0,
                        frameon=False, fontsize=8, title_fontsize=8.5)
    ax.add_artist(leyenda)

    sin_optimo = [f for f in datos if f.get("estado") != "Optimal"]
    if sin_optimo:
        marca = Line2D([0], [0], marker="o", linestyle="none", markersize=9,
                       markerfacecolor="#c0392b", alpha=0.45,
                       markeredgecolor="#c0392b", markeredgewidth=1.6)
        ax.legend([marca],
                  ["no alcanzó el óptimo en %.0f s" % tiempo],
                  loc="lower right", frameon=False, fontsize=8)

    ax.set_xlabel("nodos de la red expandida")
    ax.set_ylabel("intersecciones semaforizadas")
    ax.set_title("Tiempo de resolución según el tamaño de la red\n"
                 "y la cantidad de intersecciones semaforizadas",
                 fontsize=11)
    ax.grid(alpha=0.18, zorder=0)
    ax.margins(0.16)
    fig.tight_layout()
    fig.savefig(archivo, dpi=160)
    plt.close(fig)
    print("  figura en %s" % archivo)
    return archivo


# =============================================================================
#  Principal
# =============================================================================
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Barrido cruzado de tamaño de red y cantidad de semáforos.")
    parser.add_argument("--columnas", type=int, nargs="+", default=list(COLUMNAS),
                        help="Cantidades de columnas de la malla (%s)."
                             % " ".join(str(c) for c in COLUMNAS))
    parser.add_argument("--extras", type=int, nargs="+", default=list(EXTRAS),
                        help="Cuántas esquinas de barrio semaforizar en cada "
                             "malla; cinco semáforos más esa cantidad (%s)."
                             % " ".join(str(e) for e in EXTRAS))
    parser.add_argument("--tiempo", type=float, default=900.0,
                        help="Límite de tiempo por instancia, en segundos (900).")
    parser.add_argument("--gap", type=float, default=0.0,
                        help="Gap relativo de corte (0).")
    parser.add_argument("--hilos", type=int, default=None,
                        help="Hilos que usa Gurobi (por defecto, todos).")
    parser.add_argument("--csv", default="barrido_cruzado.csv",
                        help="Archivo CSV de salida.")
    parser.add_argument("--figura", default="barrido_cruzado.png",
                        help="Archivo del gráfico de burbujas.")
    args = parser.parse_args(argv)

    grilla = casos(args.columnas, args.extras)

    print()
    print("%d instancias   ·   límite %.0f s cada una   ·   gap de corte %.2f %%"
          % (len(grilla), args.tiempo, 100 * args.gap))
    print("En el peor caso el barrido tarda %.0f minutos."
          % (len(grilla) * args.tiempo / 60.0))
    print()

    filas = [correr(c, red, args.tiempo, args.gap, args.hilos)
             for c, red in grilla]

    for c in args.columnas:
        del_tamanio = [f for f in filas if f.get("columnas") == c]
        if del_tamanio:
            imprimir(del_tamanio, "MALLA DE 3 x %d" % c)

    sin_optimo = [f for f in filas
                  if "nodos" in f and f.get("estado") != "Optimal"]
    if sin_optimo:
        print()
        print("  No llegaron al óptimo dentro del límite:")
        for f in sin_optimo:
            print("    %-18s %-14s gap %s"
                  % (f["caso"], f["estado"],
                     "%.2f %%" % (100 * f["gap"]) if f["gap"] is not None else "-"))

    if args.csv:
        guardar_csv(args.csv, filas)
    if args.figura:
        figura(filas, args.figura, args.tiempo)
    return 0


if __name__ == "__main__":
    sys.exit(main())