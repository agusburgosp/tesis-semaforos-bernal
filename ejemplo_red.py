"""
===============

Reproduce con ``generar_red`` la instancia ``red`` de ``instancias.py``: dos
avenidas paralelas unidas por tres calles transversales, con una calle de
barrio entre ambas.

Correspondencia de nombres
--------------------------
El generador nombra las columnas A, B, C, D de oeste a este, así que los
nombres cambian respecto de la instancia escrita a mano:

    instancia a mano            generador
    ----------------            ---------
    calle F   (baja)            columna A
    avenida A (doble mano)      columna B
    calle C   (sube)            columna C
    avenida B (mano única)      columna D
    transversales 1, 2, 3       filas 1, 2, 3

    esquinas:   F1..F3 -> A1..A3      A1..A3 -> B1..B3
                C1..C3 -> C1..C3      B1, B2, B3 -> D1, D2, D3

    externos:   oAN -> oBS   dAS -> dBS   oAS -> oBN   dAN -> dBN
                oC  -> oCN   dC  -> dCN   oB  -> oDS   dB  -> dDS
                oF  -> oAS   dF  -> dAS
                oT1 -> o1E   dT1 -> d1E   oT2 -> o2O   dT2 -> d2O
                oT3 -> o3E   dT3 -> d3E
"""

from generador_red import generar_red, describir
from modelo import Instancia, caminos_mas_cortos

# Capacidades [veh/s] y tiempo de una cuadra [s], iguales a la instancia a mano
RECTO, GIRO = 1.0, 0.5
CUADRA, U_CALLE = 15.0, 1.0

# -----------------------------------------------------------------------------
#  Catálogos de fases
# -----------------------------------------------------------------------------
#  Los de la instancia a mano no coinciden con los automáticos (A1 no tiene la
#  fase de la rama norte sola, A2 no tiene la de la rama sur sola y B1 repite
#  sólo una fase), así que se reemplazan por completo. Con copias_por_fase=1
#  el generador agrega el sufijo "1" a cada nombre: "NS" -> "NS1".
FASES = {
    # A1 de la instancia a mano
    "B1": {
        "NS":    [("N", "S"), ("S", "N"), ("S", "E")],   # f1: avenida completa
        "S":     [("S", "N"), ("S", "E")],               # f2: rama sur
        "O":     [("O", "E"), ("O", "S")],               # f3: transversal
        "NSbis": [("N", "S"), ("S", "N"), ("S", "E")],   # f4: repetida de f1
    },
    # A2
    "B2": {
        "N":  [("N", "S"), ("N", "O")],                  # f1: rama norte
        "E":  [("E", "O"), ("E", "N")],                  # f2: transversal
        "NS": [("N", "S"), ("N", "O"), ("S", "N")],      # f3: avenida completa
    },
    # A3 (con semáforo de giro a la derecha desde el sur)
    "B3": {
        "NS":     [("N", "S"), ("S", "N"), ("S", "E")],  # f1
        "S":      [("S", "N"), ("S", "E")],              # f2
        "O":      [("O", "E"), ("O", "S")],              # f3
        "OSder":  [("O", "E"), ("O", "S"), ("S", "E")],  # f4
        "Nder":   [("N", "S"), ("S", "E")],              # f5
        "rectos": [("N", "S"), ("S", "N")],              # f6
    },
    # B1: la rama norte puede recibir dos bloques de verde
    "D1": {
        "N":    [("N", "S"), ("N", "E")],                # f1
        "O":    [("O", "E"), ("O", "S")],                # f2
        "Nbis": [("N", "S"), ("N", "E")],                # f3: repetida de f1
    },
    # B3: misma geometría que B1 pero sin la fase repetida
    "D3": {
        "N": [("N", "S"), ("N", "E")],
        "O": [("O", "E"), ("O", "S")],
    },
}


def armar_red():
    """Parte geométrica: la malla de 3 x 4 con sus dos avenidas."""
    return generar_red(
        filas=3,
        columnas=4,

        # Avenida doble mano en la columna B (índice 1) y avenida tipo 1 en
        # la columna D (índice 3). Tipo 1 pone semáforo en las filas de
        # índice par, o sea en D1 y D3: las dos puntas, como en la original.
        avenidas_v=dict(doble=1, tipo1=1),
        separacion_v=2,
        inicio_v=1,
        avenidas_h={},                      # las tres transversales son calles

        # Por defecto la columna C (par) bajaría y la D (impar) subiría: en
        # la instancia original es al revés. Las filas ya alternan bien.
        sentidos_v={2: "N", 3: "S"},

        cuadra=CUADRA,
        u_calle=U_CALLE,
        u_recto=RECTO,
        u_giro=GIRO,

        kappa_acceso=20.0,
        kappa_libre=20.0,
        kappa_salida=0.0,
        kappa_ingreso=float("inf"),
        kappa_egreso=0.0,

        copias_por_fase=1,                  # las repeticiones van en FASES
        fases_reemplazo=FASES,
        nombre="red",
    )


def generar(caminos: bool = False) -> Instancia:
    """Instancia completa: la red generada más las demandas de la original."""
    red = armar_red()
    Gamma, H = 60.0, 12

    # -------------------------------------------------------------------------
    #  Demandas: las mismas diez de la instancia a mano, con los nombres nuevos
    # -------------------------------------------------------------------------
    K = ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9", "k10"]
    o = {"k1": "oBS", "k2": "oBN", "k3": "oBS", "k4": "oBN", "k5": "oCN",
         "k6": "oAS", "k7": "o2O", "k8": "o1E", "k9": "o3E", "k10": "oDS"}
    d = {"k1": "dBS", "k2": "dBN", "k3": "dDS", "k4": "dDS", "k5": "dBN",
         "k6": "d1E", "k7": "d2O", "k8": "dDS", "k9": "dCN", "k10": "dAS"}
    D = {"k1": 10.0, "k2": 8.0, "k3": 6.0, "k4": 6.0, "k5": 5.0,
         "k6": 4.0, "k7": 3.0, "k8": 4.0, "k9": 3.0, "k10": 2.0}
    D = {k: 1.5 * v for k, v in D.items()}   # escalada un 50 %

    inst = Instancia(
        nombre="red-gen-caminos" if caminos else "red-gen",
        descripcion="Instancia 'red' reconstruida con generar_red: dos "
                    "avenidas paralelas unidas por tres calles transversales, "
                    "con una calle de barrio entre ambas.",
        Gamma=Gamma, H=H,
        V_ext=red.V_ext, esq_libres=red.esq_libres, X=red.X,
        movimientos=red.movimientos, P=red.P, tramos=red.tramos,
        kappa=red.kappa, G=red.G, E_pg=red.E_pg,
        L={(p, g): 2 for p in red.P for g in red.G[p]},
        U={(p, g): 8 for p in red.P for g in red.G[p]},
        K=K, o=o, d=d, D=D,
    )

    # Caminos prefijados: los mismos productos que en la original
    if caminos:
        K_R = ["k1", "k2", "k7", "k8"]
        todos = caminos_mas_cortos(inst)
        inst.R = {k: todos[k] for k in K_R}

    return inst


if __name__ == "__main__":
    describir(armar_red())