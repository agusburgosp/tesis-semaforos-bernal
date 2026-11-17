"""
=======

Ejemplos::

    python main.py                              # corre las cuatro
    python main.py corredor                     # asignación de tráfico
    python main.py corredor-caminos             # caminos prefijados
    python main.py corredor corredor-caminos    # compara las dos variantes
    python main.py red --tiempo 1800            # con otro límite de tiempo
    python main.py red --gap 0.01           # se conforma con un 1 % de gap
    python main.py red --silencioso         # sin el log del solver
    python main.py corredor --lp            # además escribe corredor.lp
"""

import argparse
import sys

from instancias import INSTANCIAS
from bernal_este import BERNAL_ESTE
from bernal_centro import BERNAL_CENTRO
from modelo import ejecutar

# Catálogo completo: las instancias escritas a mano más las generadas.
CATALOGO = dict(INSTANCIAS)
CATALOGO.update(BERNAL_ESTE)
CATALOGO.update(BERNAL_CENTRO)

# --- la instancia definida en ejemplo_completo.py ---------------------------
#  Se importa de forma perezosa: el módulo sólo se carga si se pide esta
#  instancia. Importarlo ejecuta todo su código, así que va a dibujar el mapa
#  y a imprimir sus reportes antes de resolver.
def _ejemplo_completo():
    from ejemplo_completo import inst
    return inst

CATALOGO["ejemplo"] = _ejemplo_completo

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Coordinación semafórica con asignación de tráfico (Gurobi).")
    parser.add_argument("instancias", nargs="*", metavar="INSTANCIA",
                        help="Instancias a correr (%s, o cualquiera de las "
                             "generadas). Si se omite, se corren las escritas "
                             "a mano." % ", ".join(INSTANCIAS))
    parser.add_argument("--familia", action="store_true",
                        help="Corre la familia de instancias generadas.")
    parser.add_argument("--listar", action="store_true",
                        help="Lista las instancias disponibles y termina.")
    parser.add_argument("--tiempo", type=float, default=600.0,
                        help="Límite de tiempo por instancia, en segundos (600).")
    parser.add_argument("--gap", type=float, default=None,
                        help="Gap relativo de corte, por ejemplo 0.01 para 1 %%.")
    parser.add_argument("--hilos", type=int, default=None,
                        help="Cantidad de hilos que usa Gurobi (por defecto, todos).")
    parser.add_argument("--silencioso", action="store_true",
                        help="No muestra el log del solver.")
    parser.add_argument("--sin-reporte", action="store_true",
                        help="Omite el reporte de la solución.")
    parser.add_argument("--sin-verificacion", action="store_true",
                        help="Omite la verificación de las restricciones.")
    parser.add_argument("--postprocesado", action="store_true",
                        help="Reubica las colas: las adelanta hasta el acceso "
                             "semaforizado, sin cambiar el valor óptimo.")
    parser.add_argument("--figuras", action="store_true",
                        help="Genera las figuras de cada instancia resuelta.")
    parser.add_argument("--vehiculos", action="store_true",
                        help="Agrega la descomposición en caminos y la "
                             "animación con vehículos (implica --figuras).")
    parser.add_argument("--lp", action="store_true",
                        help="Escribe el modelo en <instancia>.lp antes de resolver.")
    args = parser.parse_args(argv)

    if args.listar:
        print("A mano:   " + ", ".join(INSTANCIAS))
        print("Generadas: " + ", ".join(n for n in CATALOGO if n not in INSTANCIAS))
        return 0

    desconocidas = [n for n in args.instancias if n not in CATALOGO]
    if desconocidas:
        parser.error("instancia desconocida: %s (probá --listar)"
                     % ", ".join(desconocidas))

    if args.instancias:
        nombres = args.instancias
    elif args.familia:
        nombres = [n for n in CATALOGO if n not in INSTANCIAS]
    else:
        nombres = list(INSTANCIAS)
    resumenes = []

    for nombre in nombres:
        resumen = ejecutar(
            CATALOGO[nombre](),
            tiempo_limite=args.tiempo,
            gap=args.gap,
            hilos=args.hilos,
            log=not args.silencioso,
            con_reporte=not args.sin_reporte,
            con_verificacion=not args.sin_verificacion,
            archivo_lp=("%s.lp" % nombre) if args.lp else None,
        )
        # --- reubicación de las colas ---------------------------------------
        #  El modelo es indiferente al lugar de la demora, así que el reparto
        #  que devuelve el solver es arbitrario entre los óptimos. Se elige el
        #  que corresponde al comportamiento observado: la cola contra el
        #  semáforo. El objetivo no cambia.
        if args.postprocesado and "solucion" in resumen:
            from postprocesamiento import adelantar_esperas, comparar
            original = resumen["solucion"]
            reubicada = adelantar_esperas(resumen["datos"], original,
                                          verbose=True)
            comparar(resumen["datos"], original, reubicada)
            resumen["solucion_original"] = original
            resumen["solucion"] = reubicada

        if args.figuras or args.vehiculos:
            from visual import corredor_automatico, graficar
            if "datos" in resumen:
                eje = corredor_automatico(resumen["datos"].inst, resumen["datos"])
                graficar(resumen, corredor=eje, vehiculos=args.vehiculos,
                         sufijo="_postprocesado" if args.postprocesado else "")

        resumenes.append(resumen)

    # --- Comparación final ---------------------------------------------------
    if len(resumenes) > 1:
        print()
        print("=" * 94)
        print("RESUMEN DE LAS INSTANCIAS")
        print("=" * 94)
        print("  %-18s %-18s %10s %10s %8s %9s %8s"
              % ("instancia", "estado", "objetivo", "cota", "gap %", "segundos", "viol."))
        for r in resumenes:
            print("  %-18s %-18s %10s %10s %8s %9.2f %8s"
                  % (r["instancia"], r["estado"],
                     "%.2f" % r["objetivo"] if r["objetivo"] is not None else "-",
                     "%.2f" % r["cota"] if r["cota"] is not None else "-",
                     "%.3f" % (100 * r["gap"]) if r["gap"] is not None else "-",
                     r["segundos"],
                     r["incumplimientos"] if r["incumplimientos"] is not None else "-"))

    # Devuelve 1 si alguna instancia no llegó a una solución o violó restricciones
    problemas = any(r["objetivo"] is None or (r["incumplimientos"] or 0) > 0
                    for r in resumenes)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())