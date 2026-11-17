"""
Vuelve a dibujar el gráfico de burbujas desde el CSV, sin resolver nada.

    python regraficar.py
    python regraficar.py --csv barrido_cruzado.csv --figura cruzado.png
"""

import argparse
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def leer(archivo):
    filas = []
    with open(archivo, newline="", encoding="utf-8") as fh:
        for f in csv.DictReader(fh):
            if not f.get("segundos"):
                continue
            filas.append(dict(
                caso=f["caso"], columnas=int(f["columnas"]),
                nodos=int(f["nodos"]), semaforos=int(f["semaforos"]),
                segundos=float(f["segundos"]), estado=f["estado"]))
    return filas


def figura(datos, archivo, tiempo):
    t_max = max(f["segundos"] for f in datos)
    AREA_MAX, AREA_MIN = 2200.0, 25.0

    fig, ax = plt.subplots(figsize=(9.5, 6.5))

    for f in datos:
        optima = f["estado"] == "Optimal"
        area = AREA_MIN + (AREA_MAX - AREA_MIN) * f["segundos"] / t_max
        ax.scatter(f["nodos"], f["semaforos"], s=area,
                   facecolor="#2e8b57" if optima else "#c0392b", alpha=0.45,
                   edgecolor="#2c3e50" if optima else "#c0392b",
                   linewidth=1.0 if optima else 1.6,
                   linestyle="solid" if optima else "dashed", zorder=3)

        #  la etiqueta va arriba de la burbuja, separada según su radio
        radio = (area / 3.1416) ** 0.5
        ax.annotate("%.0f s" % f["segundos"], (f["nodos"], f["semaforos"]),
                    textcoords="offset points", xytext=(0, radio + 4),
                    ha="center", fontsize=7.5,
                    color="#2c3e50" if optima else "#c0392b", zorder=6)

    ax.set_xlabel("nodos de la red expandida")
    ax.set_ylabel("intersecciones semaforizadas")
    ax.set_title("Tiempo de resolución según el tamaño de la red\n"
                 "y la cantidad de intersecciones semaforizadas", fontsize=11)
    ax.grid(alpha=0.18, zorder=0)
    ax.margins(0.18)
    fig.tight_layout()
    fig.savefig(archivo, dpi=160)
    plt.close(fig)
    print("  figura en %s" % archivo)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="barrido_cruzado.csv")
    p.add_argument("--figura", default="barrido_cruzado.png")
    p.add_argument("--tiempo", type=float, default=900.0)
    a = p.parse_args()
    figura(leer(a.csv), a.figura, a.tiempo)