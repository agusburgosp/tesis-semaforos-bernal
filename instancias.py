
"""
Primeras zonas de estudio sobre las que se corre el modelo de ``modelo.py``.

Cada función devuelve una ``Instancia``: los datos crudos y nada más.

Para agregar una instancia nueva alcanza con escribir otra función que
devuelva una ``Instancia`` y registrarla en el diccionario ``INSTANCIAS``
del final del archivo.
"""

from modelo import Instancia, caminos_mas_cortos, nodos

# =============================================================================
#  INSTANCIA 1: CORREDOR
# =============================================================================
def corredor(caminos: bool = False) -> Instancia:
    """Una avenida con dos intersecciones semaforizadas y una calle paralela
    que permite rodear la manzana.

    El conjunto G_p es un CATÁLOGO de configuraciones compatibles, por lo que
    las variables z_pg quedan libres: el modelo decide qué fases conforman el
    plan de cada intersección.

    Geometría de la zona de estudio. Todas las calles son de un solo sentido y
    todos los arcos representan una cuadra::

                c1 ------ calle paralela ------> c2
                 ^                                |
            cuadra                            cuadra
                 |                                v
      oO --> [  P1  ] ------- avenida ------> [  P2  ] --> dE
                 ^                                |
            cuadra                            cuadra
                 |                                v
                oS                               dS

    Hay cuatro esquinas: P1 y P2 están semaforizadas, mientras que c1 y c2 no
    lo están. Las semaforizadas se representan como subgrafos, porque el
    semáforo habilita movimientos y no nodos: cada una se abre en dos nodos de
    acceso y dos de salida unidos por sus cuatro movimientos internos. Las
    esquinas sin semáforo son un único nodo: pertenecen a V pero no a ningún
    X_p, no tienen movimientos internos y ninguna variable y las alcanza. En
    ellas solo rigen la capacidad del tramo (14) y la de almacenamiento (15).

    Un vehículo que va de oO a dE puede seguir por la avenida (una cuadra entre
    P1 y P2) o rodear la manzana por el norte (tres cuadras: subir, cruzar por
    la calle paralela y bajar), entrando a P2 por su rama norte. El rodeo es
    más largo, así que solo conviene cuando la avenida se satura. Como esta
    variante no fija los caminos, la elección la hace el modelo.
    """
    Gamma, H = 60.0, 12

    # Conjunto de intersecciones semaforizadas
    P = ["P1", "P2"]

    # Nodos de acceso y salida de cada intersección semaforizada: X_p
    X = {
        "P1": ["e1O", "e1S", "s1E", "s1N"],
        "P2": ["e2O", "e2N", "s2E", "s2S"],
    }

    # Esquinas sin semáforo: un solo nodo cada una
    esq_libres = ["c1", "c2"]

    # Nodos de ingreso y egreso de la zona de estudio
    V_ext = ["oO", "oS", "dE", "dS"]

    # -------------------------------------------------------------------------
    #  Arcos que NO son movimientos de intersección: las calles (A \ E)
    #  Para cada arco se indica:
    #        t : tiempo de tránsito en segundos (de él se obtiene l_a = t / Delta)
    #        u : capacidad como tasa de flujo [vehículos / segundo]
    # -------------------------------------------------------------------------
    #  u = 1.0 veh/s equivale a 5 vehículos por intervalo de 5 s
    tramos = {
        # avenida oeste-este, cuadra por cuadra
        ("oO", "e1O"): dict(t=15.0, u=1.0),    # borde oeste -> P1
        ("s1E", "e2O"): dict(t=15.0, u=1.0),   # P1 -> P2
        ("s2E", "dE"): dict(t=15.0, u=1.0),    # P2 -> borde este
        # calle sur: entra a P1 y sale de P2
        ("oS", "e1S"): dict(t=15.0, u=1.0),    # borde sur -> P1
        ("s2S", "dS"): dict(t=15.0, u=1.0),    # P2 -> borde sur
        # rodeo por el norte: subir, cruzar la calle paralela y bajar
        ("s1N", "c1"): dict(t=15.0, u=1.0),    # P1 -> esquina noroeste
        ("c1", "c2"): dict(t=15.0, u=1.0),     # calle paralela
        ("c2", "e2N"): dict(t=15.0, u=1.0),    # esquina noreste -> P2
    }

    # -------------------------------------------------------------------------
    #  Movimientos internos de cada intersección semaforizada: E_p
    #  Cada intersección recibe flujo por dos ramas y lo entrega por otras dos,
    #  de modo que tiene cuatro movimientos: dos rectos y dos giros. Un giro
    #  tiene menor capacidad que un recto.
    # -------------------------------------------------------------------------
    movimientos = {
        "P1": {
            ("e1O", "s1E"): dict(l=1, u=1.0),    # recto oeste -> este (avenida)
            ("e1O", "s1N"): dict(l=1, u=0.5),    # giro a la izquierda oeste -> norte
            ("e1S", "s1N"): dict(l=1, u=1.0),    # recto sur -> norte
            ("e1S", "s1E"): dict(l=1, u=0.5),    # giro a la derecha sur -> este
        },
        "P2": {
            ("e2O", "s2E"): dict(l=1, u=1.0),    # recto oeste -> este (avenida)
            ("e2O", "s2S"): dict(l=1, u=0.5),    # giro a la derecha oeste -> sur
            ("e2N", "s2S"): dict(l=1, u=1.0),    # recto norte -> sur
            ("e2N", "s2E"): dict(l=1, u=0.5),    # giro a la izquierda norte -> este
        },
    }

    # -------------------------------------------------------------------------
    #  Capacidad de almacenamiento de cada nodo: kappa_i  (cola máxima)
    # -------------------------------------------------------------------------
    #  Los valores siguen la clasificación por tipo de nodo de la tesis.
    INGRESOS = ("oO", "oS")     # por acá entra la demanda a la zona de estudio
    EGRESOS = ("dE", "dS")      # por acá la abandona

    kappa = {}
    for i in nodos(V_ext, esq_libres, X):
        if i in ("e1O", "e1S", "e2O", "e2N"):
            kappa[i] = 20.0          # accesos: acá se forman las colas
        elif i in ("s1E", "s1N", "s2E", "s2S"):
            kappa[i] = 0.0           # salidas: el flujo ya cruzó y sigue de largo
        elif i in esq_libres:
            kappa[i] = 20.0          # esquinas sin semáforo
        elif i in INGRESOS:
            kappa[i] = float("inf")  # la cola aguarda fuera de la zona de estudio
        elif i in EGRESOS:
            kappa[i] = 0.0           # el flujo abandona la red sin restricciones
        else:
            raise ValueError("Nodo sin kappa asignado: %s" % i)

    # =========================================================================
    #  Fases semaforicas
    # =========================================================================
    #  G_p es un catálogo de configuraciones de movimientos compatibles entre sí.
    #  Para cada intersección se consideran tres:
    #     verde a una rama de acceso, verde a la otra, y una tercera configuración
    #     que habilita los dos movimientos que confluyen en una misma salida.
    #  Las dos primeras alcanzan para cubrir los cuatro movimientos; la tercera
    #  comparte movimientos con ambas, de modo que el modelo puede incorporarla al
    #  plan o descartarla.
    G = {
        "P1": ["g1", "g2", "g3", "g4", "g5", "g6", "g7"],
        "P2": ["h1", "h2", "h3", "h4"],
    }

    # E_pg: movimientos habilitados por la fase g de la intersección p
    E_pg = {
        # --- Intersección P1 ---
        ("P1", "g1"): [("e1O", "s1E"), ("e1O", "s1N")],   # verde al eje oeste
        ("P1", "g7"): [("e1O", "s1E"), ("e1O", "s1N")],   # verde al eje oeste
        ("P1", "g2"): [("e1S", "s1N"), ("e1S", "s1E")],   # verde al eje sur
        ("P1", "g3"): [("e1O", "s1E"), ("e1S", "s1E")],   # ambos confluyen hacia el este
        ("P1", "g4"): [("e1O", "s1N"), ("e1S", "s1N")],   # ambos confluyen hacia el norte
        ("P1", "g5"): [("e1O", "s1N"), ("e1S", "s1E"), ("e1O", "s1E")],
        ("P1", "g6"): [("e1O", "s1N"), ("e1S", "s1E"), ("e1S", "s1N")],

        # --- Intersección P2 ---
        ("P2", "h1"): [("e2O", "s2E"), ("e2O", "s2S")],   # verde al eje oeste
        ("P2", "h2"): [("e2N", "s2S"), ("e2N", "s2E")],   # verde al eje norte
        ("P2", "h3"): [("e2O", "s2E"), ("e2O", "s2S")],   # verde al eje oeste
        ("P2", "h4"): [("e2N", "s2S"), ("e2N", "s2E")],   # verde al eje norte
    }

    # Cotas de duración de cada fase, en cantidad de intervalos:
    #   L_pg = 2 intervalos = 10 s (verde mínimo)
    #   U_pg = 8 intervalos = 40 s (verde máximo)
    L = {(p, g): 2 for p in P for g in G[p]}
    U = {(p, g): 8 for p in P for g in G[p]}

    # =========================================================================
    #  Demandas
    # =========================================================================
    #  Cada producto k = (o_k, d_k, D_k) representa una demanda origen-destino.
    #  D_k está expresada en vehículos por período (Gamma = 60 s), de modo que
    #  D_k * 60 equivale a la cantidad de vehículos por hora.
    K = ["k1", "k2", "k3"]

    o = {"k1": "oO", "k2": "oS", "k3": "oO"}     # nodo de origen
    d = {"k1": "dE", "k2": "dE", "k3": "dS"}     # nodo de destino
    D = {"k1": 25.0, "k2": 10.0, "k3": 20.0}       # demanda total por período

    # =========================================================================
    #  Caminos prefijados R_k  (sólo para la segunda variante)
    # =========================================================================

    #  Cada camino se declara como la secuencia ordenada de arcos físicos que
    #  lo componen, desde o_k hasta d_k.
    #
    #  K_R es el subconjunto de productos cuyo recorrido está prefijado. No
    #  hace falta que cubra todos: los que no aparecen conservan la asignación
    #  libre. Acá k1 y k2 van por la avenida, de modo que se les descarta el
    #  rodeo por la calle paralela que en la primera variante podían elegir;
    #  k3 sigue eligiendo su recorrido.
    
    K_R = ["k1", "k2"]   # productos con recorrido prefijado

    R = {
        # k1: oO -> dE por la avenida
        "k1": [("oO", "e1O"), ("e1O", "s1E"), ("s1E", "e2O"),
               ("e2O", "s2E"), ("s2E", "dE")],
        # k2: oS -> dE, entra por la rama sur de P1 y gira al este
        "k2": [("oS", "e1S"), ("e1S", "s1E"), ("s1E", "e2O"),
               ("e2O", "s2E"), ("s2E", "dE")],
    }
    assert sorted(R) == sorted(K_R), "R y K_R no coinciden"

    return Instancia(
        nombre="corredor-caminos" if caminos else "corredor",
        descripcion="Una avenida con dos intersecciones semaforizadas y una "
                    "calle paralela que permite rodear la manzana.",
        Gamma=Gamma, H=H,
        V_ext=V_ext, esq_libres=esq_libres, X=X,
        movimientos=movimientos, P=P, tramos=tramos, kappa=kappa,
        G=G, E_pg=E_pg, L=L, U=U,
        K=K, o=o, d=d, D=D,
        R=R if caminos else None,
    )

# =============================================================================
#  INSTANCIA 2: RED
# =============================================================================
# Capacidades de los movimientos [veh/s]: un recto tiene mayor capacidad que un giro.
# Con Delta = 5 s quedan 5 veh por intervalo el recto y 2.5 el giro.
RECTO, GIRO = 1, 0.5
 
# Las cuadras son todas iguales: 100 m recorridos a unos 24 km/h dan 15 s
CUADRA, U_CALLE = 15.0, 1
 
 
def _acc(esq: str, rama: str) -> str:
    """Nodo de acceso a la esquina por la rama indicada."""
    return "%s_e%s" % (esq, rama)
 
 
def _sal(esq: str, rama: str) -> str:
    """Nodo de salida de la esquina hacia la rama indicada."""
    return "%s_s%s" % (esq, rama)
 
 
def red(caminos: bool = False) -> Instancia:
    """Dos avenidas paralelas unidas por tres calles transversales, con una
    calle de barrio entre ambas.
 
    Cuatro corredores verticales paralelos, unidos por tres calles transversales::
 
                 oF       oAN dAN        dC             oB
                 |         |  ^          ^              |
                 v         v  |          |              v
      oT1 -----> F1 -----> A1 --------> C1 ---------> B1 -----> dT1   transversal norte
                 |         |  ^          ^              |
                 v         v  |          |              v
      dT2 <----- F2 <----- A2 <-------- C2 <---------- B2 <----- oT2  transversal medio
                 |         |  ^          ^              |
                 v         v  |          |              v
      oT3 -----> F3 -----> A3 --------> C3 ---------> B3 -----> dT3   transversal sur
                 |         |  ^          ^              |
                 v         v  |          |              v
                dF        dAS oAS        oC             dB
 
            calle de      avenida A     calle de        avenida B
            barrio        doble mano    barrio          mano única
            mano única                  mano única      (norte -> sur)
            (norte -> sur)              (sur -> norte)
 
    Las cinco esquinas de las avenidas están semaforizadas: A1, A2 y A3 sobre la
    avenida de doble mano, y B1 y B3 en las dos puntas de la avenida de mano
    única. Las restantes (F1, F2, F3, C1, C2, C3 y B2) no lo están.
 
    Las esquinas semaforizadas se representan como subgrafos con nodos de acceso
    y de salida unidos por sus movimientos. Eso es lo que impide el giro en U y
    los giros que no se declararon, ya que un nodo único con dos ramas entrantes
    y dos salientes habilitaría implícitamente todas las combinaciones.
 
    En las tres esquinas de la avenida de doble mano no se permite girar a la
    izquierda desde la calle transversal.
    """
    Gamma, H = 60.0, 12
 
    # -------------------------------------------------------------------------
    #  Esquinas: sus movimientos, con la capacidad de cada uno [veh/s]
    #  Cada movimiento se declara como (rama de acceso, rama de salida) según
    #  el punto cardinal por el que el flujo llega y por el que se va.
    # -------------------------------------------------------------------------
    esquinas = {
        # --- avenida A (doble mano), semaforizadas ---
        "A1": {("N", "S"): RECTO,                        # baja
               ("S", "N"): RECTO, ("S", "E"): GIRO,      # sube y gira a la derecha
               ("O", "E"): RECTO, ("O", "S"): GIRO},     # transversal y giro a la derecha
        "A2": {("N", "S"): RECTO, ("N", "O"): GIRO,
               ("S", "N"): RECTO,
               ("E", "O"): RECTO, ("E", "N"): GIRO},
        "A3": {("N", "S"): RECTO,
               ("S", "N"): RECTO, ("S", "E"): GIRO,
               ("O", "E"): RECTO, ("O", "S"): GIRO},
        # --- avenida B (mano única), semaforizadas sólo las puntas ---
        "B1": {("N", "S"): RECTO, ("N", "E"): GIRO,
               ("O", "E"): RECTO, ("O", "S"): GIRO},
        "B3": {("N", "S"): RECTO, ("N", "E"): GIRO,
               ("O", "E"): RECTO, ("O", "S"): GIRO},
    }
 
    # Conjunto de intersecciones semaforizadas
    P = ["A1", "A2", "A3", "B1", "B3"]
 
    # Esquinas sin semáforo: un solo nodo cada una
    esq_libres = ["C1", "C2", "C3", "B2", "F1", "F2", "F3"]
 
    # X_p: nodos de acceso y salida de cada esquina
    X = {}
    for esq, movs in esquinas.items():
        ramas_acc = sorted({r for r, _ in movs})
        ramas_sal = sorted({r for _, r in movs})
        X[esq] = [_acc(esq, r) for r in ramas_acc] + [_sal(esq, r) for r in ramas_sal]
 
    # Movimientos internos, expresados ya como arcos entre nodos
    movimientos = {esq: {(_acc(esq, ra), _sal(esq, rb)): dict(l=1, u=cap)
                         for (ra, rb), cap in movs.items()}
                   for esq, movs in esquinas.items()}
 
    # Nodos de ingreso y egreso de la zona de estudio
    V_ext = ["oAN", "dAN", "oAS", "dAS",     # puntas de la avenida A (doble mano)
             "oC", "dC",                     # puntas de la calle C
             "oB", "dB",                     # puntas de la avenida B
             "oT1", "dT1",                   # puntas de la transversal norte
             "oT2", "dT2",                   # puntas de la transversal medio
             "oT3", "dT3",                   # puntas de la transversal sur
             "oF", "dF"]                     # puntas de la calle F
 
    # -------------------------------------------------------------------------
    #  Las calles (A \ E): cada arco es una cuadra
    # -------------------------------------------------------------------------
    conexiones = [
        # avenida A, sentido sur
        ("oAN", _acc("A1", "N")), (_sal("A1", "S"), _acc("A2", "N")),
        (_sal("A2", "S"), _acc("A3", "N")), (_sal("A3", "S"), "dAS"),
        # avenida A, sentido norte
        ("oAS", _acc("A3", "S")), (_sal("A3", "N"), _acc("A2", "S")),
        (_sal("A2", "N"), _acc("A1", "S")), (_sal("A1", "N"), "dAN"),
        # calle C, sentido norte
        ("oC", "C3"), ("C3", "C2"), ("C2", "C1"), ("C1", "dC"),
        # calle F, sentido sur
        ("oF", "F1"), ("F1", "F2"), ("F2", "F3"), ("F3", "dF"),
        # avenida B, sentido sur
        ("oB", _acc("B1", "N")), (_sal("B1", "S"), "B2"),
        ("B2", _acc("B3", "N")), (_sal("B3", "S"), "dB"),
        # transversal norte, sentido este
        ("oT1", "F1"), ("F1", _acc("A1", "O")), (_sal("A1", "E"), "C1"),
        ("C1", _acc("B1", "O")), (_sal("B1", "E"), "dT1"),
        # transversal medio, sentido oeste
        ("oT2", "B2"), ("B2", "C2"), ("C2", _acc("A2", "E")),
        (_sal("A2", "O"), "F2"), ("F2", "dT2"),
        # transversal sur, sentido este
        ("oT3", "F3"), ("F3", _acc("A3", "O")), (_sal("A3", "E"), "C3"),
        ("C3", _acc("B3", "O")), (_sal("B3", "E"), "dT3"),
    ]
 
    tramos = {a: dict(t=CUADRA, u=U_CALLE) for a in conexiones}
 
    # -------------------------------------------------------------------------
    #  Capacidad de almacenamiento de cada nodo: kappa_i  (cola máxima)
    # -------------------------------------------------------------------------
    #  Los valores siguen la clasificación por tipo de nodo de la tesis.
    INGRESOS = [i for i in V_ext if i.startswith("o")]   # por acá entra la demanda
    EGRESOS = [i for i in V_ext if i.startswith("d")]    # por acá la abandona
 
    kappa = {}
    for i in nodos(V_ext, esq_libres, X):
        if "_e" in i:
            kappa[i] = 20.0          # accesos: acá se forman las colas
        elif "_s" in i:
            kappa[i] = 0.0           # salidas: el flujo ya cruzó y sigue de largo
        elif i in esq_libres:
            kappa[i] = 20.0          # esquinas sin semáforo: una sola cola
        elif i in INGRESOS:
            kappa[i] = float("inf")  # la cola aguarda fuera de la zona de estudio
        elif i in EGRESOS:
            kappa[i] = 0.0           # el flujo abandona la red sin restricciones
        else:
            raise ValueError("Nodo sin kappa asignado: %s" % i)
 
    # =========================================================================
    #  Fases semaforicas
    # =========================================================================
    #  G_p es un catálogo de configuraciones compatibles.
    fases = {
        # --- A1 y A3: avenida de doble mano con la transversal que sale al este ---
        "A1": {
            # avenida completa: las dos corrientes opuestas siguen derecho
            "f1": [("N", "S"), ("S", "N"), ("S", "E")],
            # rama sur con su giro a la izquierda protegido
            "f2": [("S", "N"), ("S", "E")],
            # rama transversal completa
            "f3": [("O", "E"), ("O", "S")],
            # f4 habilita exactamente los mismos movimientos que f1, con otro
            # nombre. Como son fases distintas, cada una puede recibir su propio
            # bloque de verde, de modo que la avenida puede pasar dos veces en
            # el período. El modelo decide si le conviene usar las dos.
            "f4": [("N", "S"), ("S", "N"), ("S", "E")],
        },
        # Digamos que tiene semaforo de giro a la derecha desde el sur
        "A3": {
            "f1": [("N", "S"), ("S", "N"), ("S", "E")],
            "f2": [("S", "N"), ("S", "E")],
            "f3": [("O", "E"), ("O", "S")],
            "f4": [("O", "E"), ("O", "S"), ("S", "E")],
            "f5": [("N", "S"), ("S", "E")],
            "f6": [("N", "S"), ("S", "N")],
        },
        # --- A2: avenida de doble mano con la transversal que llega del este ---
        "A2": {
            "f1": [("N", "S"), ("N", "O")],
            "f2": [("E", "O"), ("E", "N")],
            "f3": [("N", "S"), ("N", "O"), ("S", "N")],
        },
        # --- B1 y B3: avenida de mano única con la transversal ---
        "B1": {
            "f1": [("N", "S"), ("N", "E")],               # rama norte completa
            "f2": [("O", "E"), ("O", "S")],               # rama transversal completa
            "f3": [("N", "S"), ("N", "E")],               # repetida de f1
        },
        # B3 tiene la misma geometría que B1 pero SIN la fase repetida, de modo
        # que comparar las dos muestra qué efecto tiene permitir dos bloques de
        # verde para un mismo conjunto de movimientos.
        "B3": {
            "f1": [("N", "S"), ("N", "E")],
            "f2": [("O", "E"), ("O", "S")],
        },
    }
 
    G = {p: sorted(fases[p]) for p in P}
 
    # E_pg: movimientos habilitados por la fase g de la intersección p
    E_pg = {(p, g): [(_acc(p, ra), _sal(p, rb)) for ra, rb in movs]
            for p in P for g, movs in fases[p].items()}
 
    # Cotas de duración de cada fase, en cantidad de intervalos:
    #   L_pg = 2 intervalos = 10 s (verde mínimo)
    #   U_pg = 8 intervalos = 40 s (verde máximo)
    L = {(p, g): 2 for p in P for g in G[p]}
    U = {(p, g): 8 for p in P for g in G[p]}
 
    # =========================================================================
    #  Demandas
    # =========================================================================
    #  Cada producto k = (o_k, d_k, D_k) representa una demanda origen-destino.
    #  D_k está expresada en vehículos por período (Gamma = 60 s), de modo que
    #  D_k * 60 equivale a la cantidad de vehículos por hora. Ingresa flujo por
    #  todas las puntas del borde en las que hay una calle entrante.
    K = ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9", "k10"]
 
    o = {"k1": "oAN", "k2": "oAS", "k3": "oAN", "k4": "oAS", "k5": "oC",
         "k6": "oF", "k7": "oT2", "k8": "oT1", "k9": "oT3", "k10": "oB"}
    d = {"k1": "dAS", "k2": "dAN", "k3": "dB", "k4": "dB", "k5": "dAN",
         "k6": "dT1", "k7": "dT2", "k8": "dB", "k9": "dC", "k10": "dF"}
    D = {"k1": 10.0, "k2": 8.0, "k3": 6.0, "k4": 6.0, "k5": 5.0,
         "k6": 4.0, "k7": 3.0, "k8": 4.0, "k9": 3.0, "k10": 2.0}
 
    #  Con estas capacidades la red queda holgada y el modelo circula por los
    #  caminos más cortos sin tener que decidir nada. Escalando la demanda un
    #  50 % el giro de B3 se satura: pide 9.6 intervalos de verde y U_pg = 8 no
    #  los da, de modo que parte del flujo hacia dB tiene que buscar otra ruta.
    D = {k: 1.5 * v for k, v in D.items()}
    #     k1: 600 veh/h  (avenida A, sentido sur)
    #     k2: 480 veh/h  (avenida A, sentido norte)
    #     k3: 360 veh/h  (transversal norte, de punta a punta)
    #     k4: 360 veh/h  (transversal medio, de punta a punta)
    #     k5: 300 veh/h  (baja por la avenida B y sale al este por la transversal sur)
    #     k6: 240 veh/h  (calle de barrio, sentido norte)
 
    inst = Instancia(
        nombre="red-caminos" if caminos else "red",
        descripcion="Dos avenidas paralelas unidas por tres calles "
                    "transversales, con una calle de barrio entre ambas.",
        Gamma=Gamma, H=H,
        V_ext=V_ext, esq_libres=esq_libres, X=X,
        movimientos=movimientos, P=P, tramos=tramos, kappa=kappa,
        G=G, E_pg=E_pg, L=L, U=U,
        K=K, o=o, d=d, D=D,
    )
 
    # =========================================================================
    #  Caminos prefijados R_k  (sólo para la segunda variante)
    # =========================================================================
    #  R no cubre todos los productos. Los que aparecen acá representan las
    #  demandas cuyo recorrido se conoce: el itinerario que efectivamente
    #  siguen hoy. Los que no aparecen conservan la asignación libre.
    #
    #  Así, la comparación entre las dos variantes mide exactamente cuánto se
    #  gana si esas demandas pudieran redistribuirse. En la variante libre el
    #  modelo elige por dónde va cada una; en la de caminos prefijados, las
    #  conocidas quedan atadas a su itinerario y sólo el resto puede moverse.
    #
    #  El recorrido de cada una es el de mínimo tiempo de tránsito a flujo
    #  libre, que es una aproximación razonable a la ruta observada.
    K_R = ["k1", "k2", "k7", "k8"]   # productos con recorrido prefijado

    if caminos:
        todos = caminos_mas_cortos(inst)
        inst.R = {k: todos[k] for k in K_R}
 
    return inst
 
 
# =============================================================================
#  Catálogo de instancias disponibles
# =============================================================================
#  Cada zona de estudio aparece dos veces: con asignación de tráfico (el
#  modelo elige los recorridos) y con caminos prefijados (restricciones
#  (30) y (31)).
INSTANCIAS = {
    "corredor": corredor,
    "corredor-caminos": lambda: corredor(caminos=True),
    "red": red,
    "red-caminos": lambda: red(caminos=True),
}