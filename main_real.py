"""
Resuelve el flujo sobre las zonas de Bernal con el plan semafórico observado
en el terreno.

    python main_real.py                    # las dos zonas
    python main_real.py este               # sólo Bernal Este
    python main_real.py centro             # sólo Bernal Centro
    python main_real.py centro --caminos   # con los recorridos prefijados
    python main_real.py este --giro        # con el giro propuesto en K1
    python main_real.py --sin-figuras      # sin generar las visualizaciones
    python main_real.py --comparar         # además resuelve el óptimo y compara
"""

from __future__ import annotations

import argparse
import sys

from bernal_este import bernal_este
from bernal_centro import bernal_centro
from plan_real import PLAN_BERNAL_ESTE, PLAN_BERNAL_CENTRO
from modelo_real import ejecutar_real, comparar_con_optimo
from visual import graficar, corredor_automatico
from postprocesamiento import adelantar_esperas, comparar as comparar_colas
from modelo import verificar

# =============================================================================
#  Las zonas disponibles
# =============================================================================
#  Cada entrada es (nombre para mostrar, cómo construir la instancia, plan).
#  El plan de cada zona se relevó por separado y corresponde a una franja
#  horaria distinta: Bernal Este a las 8, cuando la subida a la autopista
#  concentra las mayores colas, y Bernal Centro a las 17.
ZONAS = {
    "este":   ("Bernal Este",   bernal_este,   PLAN_BERNAL_ESTE),
    "centro": ("Bernal Centro", bernal_centro, PLAN_BERNAL_CENTRO),
}


def correr(clave: str, giro: bool, caminos: bool, figuras: bool,
           comparar: bool, tiempo: float) -> dict:
    """Resuelve una zona con su plan observado y, si se pide, la grafica."""
    titulo, construir, plan = ZONAS[clave]

    print()
    print("=" * 70)
    print("%s%s%s" % (titulo.upper(),
                      "  ·  giro propuesto en K1" if (giro and clave == "este")
                      else "",
                      "  ·  caminos prefijados" if caminos else ""))
    print("=" * 70)

    #  Sólo Bernal Este admite la variante con el giro propuesto en K1.
    kw = dict(caminos=caminos)
    if giro and clave == "este":
        kw["giro_K1"] = True
    inst = construir(**kw)

    r = ejecutar_real(inst, plan)

    if comparar:
        comparar_con_optimo(inst, plan, tiempo_limite=tiempo)

    #  Sólo se grafica y posprocesa si hubo solución.
    if "solucion" in r:
        dat, sol = r["datos"], r["solucion"]
        nueva = adelantar_esperas(dat, sol, verbose=True)
        comparar_colas(dat, sol, nueva)
        print("Violaciones después:", verificar(dat, nueva))

        if figuras:
            graficar({"datos": dat, "solucion": nueva},
                     corredor=corredor_automatico(dat.inst, dat),
                     vehiculos=True, sufijo="_real_postprocesado")

    return r


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Resuelve las zonas de Bernal con su plan semafórico real.")
    parser.add_argument("zonas", nargs="*", metavar="ZONA",
                        help="Cuáles resolver (%s). Si se omite, las dos."
                             % ", ".join(ZONAS))
    parser.add_argument("--caminos", action="store_true",
                        help="Usa la variante con los recorridos prefijados.")
    parser.add_argument("--giro", action="store_true",
                        help="En Bernal Este, habilita el giro propuesto en K1.")
    parser.add_argument("--sin-figuras", action="store_true",
                        help="No genera las visualizaciones.")
    parser.add_argument("--comparar", action="store_true",
                        help="Resuelve además el óptimo y compara ambos planes.")
    parser.add_argument("--tiempo", type=float, default=900.0,
                        help="Límite de tiempo al resolver el óptimo (900 s).")
    args = parser.parse_args(argv)

    desconocidas = [z for z in args.zonas if z not in ZONAS]
    if desconocidas:
        parser.error("zona desconocida: %s" % ", ".join(desconocidas))

    claves = args.zonas or list(ZONAS)

    if args.giro and "este" not in claves:
        print("  Aviso: --giro sólo se aplica a Bernal Este, que no está "
              "entre las zonas pedidas.")

    for clave in claves:
        correr(clave, args.giro, args.caminos, not args.sin_figuras,
               args.comparar, args.tiempo)

    return 0


if __name__ == "__main__":
    sys.exit(main())