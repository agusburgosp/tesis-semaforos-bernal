from modelo import Instancia, caminos_mas_cortos, nodos

# =============================================================================
#  INSTANCIA: BERNAL CENTRO
# =============================================================================
#  Todos los tiempos de recorrido están en segundos y son múltiplos de
#  Delta = 5 s; las capacidades, en vehículos por segundo.

# -----------------------------------------------------------------------------
#  Capacidades de los movimientos dentro de las intersecciones [veh/s]
# -----------------------------------------------------------------------------
#  Un carril admite 0,5 veh/s. El recto conserva esa capacidad y el giro la
#  reduce a la mitad, porque el vehículo que dobla pierde velocidad. Con
#  Delta = 5 s pasan 2,5 veh por intervalo en un recto y 1,25 en un giro.
RECTO, GIRO = 0.5, 0.25

#  RECTO_LARGO: recto sobre una avenida de dos carriles, el doble que en un
#               carril (5 veh por intervalo).
#  GIRO_U:      giro en U sobre la Avenida San Martín (2 veh por intervalo).
#               Tiene capacidad propia, mayor que la de un giro común, porque
#               se hace desde una avenida ancha.
RECTO_LARGO, GIRO_U = 1.0, 0.4

# -----------------------------------------------------------------------------
#  Calles de barrio: unos 24 km/h
# -----------------------------------------------------------------------------
#  CUADRA:  tiempo de recorrido de una cuadra de 100 m (15 s).
#  U_CALLE: capacidad de un carril [veh/s] (2,5 veh por intervalo).
CUADRA, U_CALLE = 15.0, 0.5

#  Tramos cortos, entre esquinas a mitad de cuadra: 5 s,
#  redondeado al múltiplo de Delta más cercano.
CUADRAS_CORTAS = 5.0

#  Tramos de dos y tres cuadras sin esquinas
CUADRA_LARGA_2 = 30.0
CUADRA_LARGA_3 = 45.0

# -----------------------------------------------------------------------------
#  Avenida San Martín: unos 35 km/h, dos carriles por sentido
# -----------------------------------------------------------------------------
#  Una cuadra de 100 m se recorre en unos 10 s.
CUADRA_SANMARTIN = 10.0

#  Dos carriles: el doble de la capacidad de un carril (5 veh por intervalo).
U_CALLE_SANMARTIN = 1.0

#  Tramos cortos sobre San Martín (unos 50 m): 5 s.
CUADRA_SANMARTIN_CORTAS = 5

#  Tramo de dos cuadras sin esquinas intermedias: unos 20 s
CUADRA_SANMARTIN_LARGA_2 = 20
 
def _acc(esq: str, rama: str) -> str:
    """Nodo de acceso a la esquina por la rama indicada."""
    return "%s_e%s" % (esq, rama)
 
 
def _sal(esq: str, rama: str) -> str:
    """Nodo de salida de la esquina hacia la rama indicada."""
    return "%s_s%s" % (esq, rama)
 
 
def bernal_centro(caminos: bool = False) -> Instancia:
    Gamma, H = 80.0, 16
 
    # -------------------------------------------------------------------------
    #  Esquinas: sus movimientos, con la capacidad de cada uno [veh/s]
    #  Cada movimiento se declara como (rama de acceso, rama de salida) según
    #  el punto cardinal por el que el flujo llega y por el que se va.
    # -------------------------------------------------------------------------
    esquinas = {
        # X1 - X3 : Cerrito
        # X1: tres semaforos
        "X1": {("S", "E"): GIRO,     # a bernal
               ("S", "O"): GIRO,     # a wilde
               ("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("E", "S"): GIRO,     # a cerrito
               ("O", "S"): GIRO},    # a cerrito

        "X2": {("N", "E"): GIRO,     # a bernal
               ("N", "S"): RECTO,    # a belgrano
               ("S", "N"): RECTO,    # a san martin
               ("S", "E"): GIRO,     # a bernal
               ("O", "E"): RECTO,    # a bernal
               ("O", "S"): GIRO,     # a belgrano
               ("O", "N"): GIRO},    # a san martin

        "X3": {("N", "O"): GIRO,     # a wilde
               ("N", "S"): RECTO,    # a belgrano
               ("S", "N"): RECTO,    # a san martin
               ("S", "O"): GIRO,     # a wilde
               ("E", "O"): RECTO,    # a wilde
               ("E", "S"): GIRO,     # a belgrano
               ("E", "N"): GIRO},    # a san martin


        # O1 - O3 : Zeballos
        "O1": {("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("E", "S"): GIRO,     # a cerrito
               ("O", "S"): GIRO},    # a cerrito

        # Z7 - Z8 : Blandegues
        "Z7": {("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("E", "S"): GIRO,     # a cerrito
               ("O", "S"): GIRO},    # a cerrito

        # P1 - P3 : Leandro N. Alem
        # P1: cuatro semaforos
        "P1": {("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("E", "E"): GIRO_U,   # a bernal (giro en U)
               ("S", "O"): GIRO,     # a wilde
               ("S", "E"): GIRO},    # a bernal

        # Q1 - Q3 : Ameghino
        "Q1": {("O", "E"): RECTO_LARGO,    # a bernal
               ("N", "O"): GIRO,     # de paso bajo nivel
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("O", "S"): GIRO},    # a cerrito

        # R1 - R3 : Avellaneda
        # R1: tres semaforos
        "R1": {("S", "E"): GIRO,     # a bernal
               ("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("O", "S"): GIRO},    # a cerrito

        "R2": {("N", "E"): GIRO,     # a bernal
               ("N", "S"): RECTO,    # a belgrano
               ("S", "N"): RECTO,    # a san martin
               ("S", "E"): GIRO,     # a bernal
               ("O", "E"): RECTO,    # a bernal
               ("O", "N"): GIRO,     # a san martin
               ("O", "S"): GIRO},    # a belgrano

        # R3: dos semaforos
        "R3": {("N", "O"): GIRO,     # a wilde
               ("N", "S"): RECTO,    # a belgrano
               ("S", "N"): RECTO,    # a san martin
               ("E", "O"): RECTO,    # a wilde
               ("E", "S"): GIRO,     # a belgrano
               ("E", "N"): GIRO},    # a san martin

        # S1 - S3 : 25 de Mayo
        # S1: dos semaforos
        "S1": {("E", "S"): GIRO,     # a 25 de mayo
               ("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("O", "S"): GIRO},    # a 25 de mayo

        # S3: dos semaforos
        "S3": {("N", "O"): GIRO,     # a wilde
               ("E", "S"): GIRO,     # a belgrano
               ("E", "O"): RECTO,    # a wilde
               ("N", "S"): RECTO},   # a belgrano

        # Z9: entre 9 de julio y 25 de mayo
        # Z9: dos semaforos
        "Z9": {("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde/paso bajo nivel
               ("E", "N"): GIRO,     # a paso bajo nivel
               ("O", "N"): GIRO},    # a paso bajo nivel

        # T1 - T2 : 9 de Julio
        # T1: tres semaforos
        "T1": {("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("S", "O"): GIRO,     # a wilde
               ("S", "E"): GIRO},    # a bernal
        
        # T2: dos semaforos
        "T2": {("S", "N"): RECTO,    # a san martin
               ("E", "O"): RECTO,    # a wilde
               ("S", "O"): GIRO,     # a wilde
               ("E", "N"): GIRO},    # a san martin

        # U1 - U2 : Castro Barros
        "U1": {("E", "S"): GIRO,     # a castro barros
               ("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "E"): GIRO_U,
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("O", "S"): GIRO},    # a castro barros

        # V1 - V2 : Don Bosco
        # V1: tres semaforos
        "V1": {("O", "E"): RECTO_LARGO,    # a bernal
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("S", "O"): GIRO,     # a wilde
               ("S", "E"): GIRO},    # a bernal

        # W1 - W4 : Zapiola
        # W1: tres semaforos
        "W1": {("O", "E"): RECTO_LARGO,    # a bernal
               ("O", "S"): GIRO,     # a zapiola
               ("E", "O"): RECTO_LARGO,    # a wilde
               ("E", "S"): GIRO,     # a zapiola
               ("S", "O"): GIRO,     # a wilde
               ("S", "E"): GIRO},    # a bernal

        "W2": {("N", "S"): RECTO,    # a belgrano
               ("S", "N"): RECTO,    # a san martin
               ("E", "N"): GIRO,     # a san martin
               ("E", "S"): GIRO},    # a belgrano

        "W3": {("N", "S"): RECTO,    # a belgrano
               ("S", "N"): RECTO,    # a san martin
               ("N", "E"): GIRO,     # a quilmes
               ("S", "E"): GIRO},    # a quilmes

        # W4: tres semaforos
        "W4": {("N", "S"): RECTO,    # a belgrano
               ("N", "E"): GIRO,     # a quilmes
               ("N", "O"): GIRO,     # a bernal
               ("E", "O"): RECTO,    # a bernal
               ("E", "S"): GIRO,     # a belgrano
               ("E", "N"): GIRO,     # a san martin
               ("S", "N"): RECTO,    # a san martin
               ("S", "O"): GIRO,     # a bernal
               ("S", "E"): GIRO}     # a quilmes
    }
 
    # Conjunto de intersecciones semaforizadas
    P = ["X1", "P1", "R1", "R3", "S1", "S3", "Z9", "T1", "T2", "V1", "W1", "W4"]
 
    # Esquinas sin semáforo: un solo nodo cada una
    esq_libres = [
        # Zeballos a sur
        "O2", "O3",

        # Blandengues a sur
        "Z8",

        # Leando N. Alem
        "P2", "P3",

        # Ameghino
        "Q2", "Q3",

        # 25 de Mayo
        "S2",

        # Castro Barros
        "U2",

        # Don Bosco
        "V2"
        ]
 
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
    V_ext = [
            "oX1", "dX1", "oX2", "dX3",  "oZ6", "dZ6",                  # Cerrito
            "dO3",                                                      # Zeballos
            "oP3",                                                      # Leando N. Alem
            "oQ1", "dQ3",                                               # entrada paso bajo nivel / Ameghino
            "oR3", "dR3",                                               # Avellaneda
            "dS3",                                                      # 25 de Mayo
            "dZ9",                                                      # a paso bajo nivel
            "oT2",                                                      # 9 de Julio
            "dU2",                                                      # Castro Barros
            "oV2",                                                      # Don Bosco
            "oW1", "dW1","oW2", "dW3", "oW4", "dW4", "oZ10", "dZ10"     # Zapiola
        ]                    
 
    # -------------------------------------------------------------------------
    #  Las calles (A \ E): cada arco es una cuadra
    # -------------------------------------------------------------------------
    conexiones = [
        # -------------------------------------------------------------
        # VERTICALES
        # -------------------------------------------------------------
        # Cerrito
        (_sal("X1", "S"), _acc("X2", "N")), (_sal("X2", "N"), _acc("X1", "S")),
        (_sal("X2", "S"), _acc("X3", "N")), (_sal("X3", "N"), _acc("X2", "S")),
        (_sal("X3", "S"), "dZ6"), ("oZ6", _acc("X3", "S")),

        # Zeballos
        (_sal("O1", "S"), "O2"), ("O2", "O3"), ("O3", "dO3"),

        # Blandengues
        (_sal("Z7", "S"), "Z8"), 

        # Leando N. Alem
        ("oP3", "P3"), ("P3", "P2"), ("P2", _acc("P1", "S")),

        # Ameghino
        ("oQ1", _acc("Q1", "N")), (_sal("Q1", "S"), "Q2"), ("Q3", "dQ3"),

        # Avellaneda
        (_sal("R1", "S"), _acc("R2", "N")), (_sal("R2", "N"), _acc("R1", "S")),
        (_sal("R2", "S"), _acc("R3", "N")), (_sal("R3", "N"), _acc("R2", "S")),
        (_sal("R3", "S"), "dR3"), ("oR3", _acc("R3", "S")),

        # 25 de Mayo
        (_sal("S1", "S"), "S2"), ("S2", _acc("S3", "N")), (_sal("S3", "S"), "dS3"),

        # Salida paso bajo nivel
        (_sal("Z9", "N"), "dZ9"),

        # 9 de Julio
        ("oT2", _acc("T2", "S")), 

        # Castro Barros
        ("U2", "dU2"),

        # Don Bosco
        ("oV2", "V2"), 

        # Zapiola
        (_sal("W1", "S"), _acc("W2", "N")), (_sal("W2", "N"), _acc("W1", "S")),
        (_sal("W2", "S"), _acc("W3", "N")), (_sal("W3", "N"), _acc("W2", "S")),
        (_sal("W3", "S"), _acc("W4", "N")), (_sal("W4", "N"), _acc("W3", "S")),
        (_sal("W4", "S"), "dW4"), ("oW4", _acc("W4", "S")),

        # -------------------------------------------------------------
        # HORIZONTALES
        # -------------------------------------------------------------

        # Coronel Pringles
        ("oX2", _acc("X2", "O")), (_sal("X2", "E"), "O2"),
        ("P2", "Q2"), ("Q2", _acc("R2", "O")), (_sal("R2", "E"), "S2"),

        # Rawson
        ("oW2", _acc("W2", "E")),

        # Coronel Pringles 2
        (_sal("W3", "E"), "dW3"),

        # Belgrano
        ("oZ10", _acc("W4", "E")), (_sal("W4", "E"), "dZ10"),
        ("V2", "U2"), ("U2", _acc("T2", "E")), (_sal("T2", "O"), _acc("S3", "E")), 
        (_sal("S3", "O"), _acc("R3", "E")), (_sal("R3", "O"), "Q3"), ("Q3", "P3"), 
        ("P3", "O3"), ("O3", _acc("X3", "E")), (_sal("X3", "O"), "dX3")
    ]

    conexiones_cortas = [
        # Coronel Pringles
        ("O2", "Z8"), ("Z8", "P2"), 
    ]

    conexiones_largas_3 = [
        # Don Bosco
        ("V2", _acc("V1", "S")), 
    ]

    conexiones_largas_2 = [
        # Castro Barros
        (_sal("U1", "S"), "U2"),

        # 9 de Julio
        (_sal("T2", "N"), _acc("T1", "S")),

        # Belgrano
        (_sal("W4", "O"), "V2"), 
    ]

    conexiones_san_martin = [
        ("oX1", _acc("X1", "O")), (_sal("X1", "O"), "dX1"),
        (_sal("X1", "E"), _acc("O1", "O")), (_sal("O1", "O"), _acc("X1", "E")),
        (_sal("P1", "E"), _acc("Q1", "O")), (_sal("Q1", "O"), _acc("P1", "E")),
        (_sal("Q1", "E"), _acc("R1", "O")), (_sal("R1", "O"), _acc("Q1", "E")),
        (_sal("R1", "E"), _acc("S1", "O")), (_sal("S1", "O"), _acc("R1", "E")),
        (_sal("T1", "E"), _acc("U1", "O")), (_sal("U1", "O"), _acc("T1", "E")),
        (_sal("U1", "E"), _acc("V1", "O")), (_sal("V1", "O"), _acc("U1", "E")),
        (_sal("W1", "E"), "dW1"), ("oW1", _acc("W1", "E")),
    ]

    conexiones_san_martin_cortas = [
        (_sal("O1", "E"), _acc("Z7", "O")), (_sal("Z7", "O"), _acc("O1", "E")),
        (_sal("Z7", "E"), _acc("P1", "O")), (_sal("P1", "O"), _acc("Z7", "E")),  
        (_sal("S1", "E"), _acc("Z9", "O")), (_sal("Z9", "O"), _acc("S1", "E")),
        (_sal("Z9", "E"), _acc("T1", "O")), (_sal("T1", "O"), _acc("Z9", "E")),
    ]

    conexiones_san_martin_largas_2 = [
        (_sal("V1", "E"), _acc("W1", "O")), (_sal("W1", "O"), _acc("V1", "E")),
    ]

    #  m = largo del tramo en metros. No lo usa el modelo: sirve para calcular
    #  la cola, que depende de la geometría y no del tiempo de recorrido.
    tramos = {}
    tramos.update({a: dict(t=CUADRA,          u=U_CALLE,         m=100.0) for a in conexiones})
    tramos.update({a: dict(t=CUADRAS_CORTAS,  u=U_CALLE,         m=50.0)  for a in conexiones_cortas})
    tramos.update({a: dict(t=CUADRA_LARGA_2,  u=U_CALLE,         m=200.0) for a in conexiones_largas_2})
    tramos.update({a: dict(t=CUADRA_LARGA_3,  u=U_CALLE,         m=300.0) for a in conexiones_largas_3})

    tramos.update({a: dict(t=CUADRA_SANMARTIN,          u=U_CALLE_SANMARTIN, m=100.0) for a in conexiones_san_martin})
    tramos.update({a: dict(t=CUADRA_SANMARTIN_CORTAS,   u=U_CALLE_SANMARTIN, m=50.0)  for a in conexiones_san_martin_cortas})
    tramos.update({a: dict(t=CUADRA_SANMARTIN_LARGA_2,  u=U_CALLE_SANMARTIN, m=200.0) for a in conexiones_san_martin_largas_2})

    # -------------------------------------------------------------------------
    #  Capacidad de almacenamiento de cada nodo: kappa_i  (cola máxima)
    # -------------------------------------------------------------------------
    #  Los valores siguen la clasificación por tipo de nodo de la tesis.
    INGRESOS = [i for i in V_ext if i.startswith("o")]   # por acá entra la demanda
    EGRESOS = [i for i in V_ext if i.startswith("d")]    # por acá la abandona

    ESPACIAMIENTO = 7.0     # metros que ocupa un vehículo detenido
    U_CARRIL = 0.5          # capacidad de un carril [veh/s]

    #  Cada nodo hereda la cola del tramo que desemboca en él. Si llegan
    #  varios, como en una esquina libre donde confluyen dos calles, se toma
    #  el más largo.
    llega = {}
    for (i, j), dat in tramos.items():
        if j not in llega or dat["m"] > llega[j]["m"]:
            llega[j] = dat

    kappa = {}
    for i in nodos(V_ext, esq_libres, X):
        if i in INGRESOS:
            kappa[i] = float("inf")
        elif i in EGRESOS or "_s" in i:
            kappa[i] = 0.0
        else:
            dat = llega[i]
            carriles = round(dat["u"] / U_CARRIL)
            kappa[i] = round(dat["m"] / ESPACIAMIENTO) * carriles
 
    # =========================================================================
    #  Fases semaforicas
    # =========================================================================
    #  G_p es un catálogo de configuraciones compatibles.

    fases = {
        "X1": {
            "f1": [("O", "E"), ("O", "S")],
            "f2": [("S", "E"), ("S", "O")],
            "f3": [("E", "O")],
            "f4": [("E", "S")],
            "f5": [("E", "O"), ("E", "S")],
            "f6": [("E", "O"), ("O", "E"), ("O", "S")],
            # repite
            "f7": [("O", "E"), ("O", "S")],
            "f8": [("S", "E"), ("S", "O")],
            "f9": [("E", "O")],
            "f10": [("E", "S")],
            "f11": [("E", "O"), ("E", "S")],
            "f12": [("E", "O"), ("O", "E"), ("O", "S")]
        },

        "P1": {
            "f1": [("E", "O")],
            "f2": [("O", "E")],
            "f3": [("E", "O"), ("O", "E")],
            "f4": [("E", "E")], # giro en U
            "f5": [("S", "E"), ("S", "O")],
            # repite
            "f6": [("E", "O")],
            "f7": [("O", "E")],
            "f8": [("E", "O"), ("O", "E")],
            "f9": [("E", "E")], # giro en U
            "f10": [("S", "E"), ("S", "O")]
        },

        "R1": {
            "f1": [("O", "E"), ("O", "S")],
            "f2": [("S", "E")],
            "f3": [("E", "O")],
            "f4": [("O", "E"), ("O", "S"), ("E", "O")],
            "f5": [("S", "E"), ("E", "O")],
            "peatonal":[],
            # repite
            "f6": [("O", "E"), ("O", "S")],
            "f7": [("S", "E")],
            "f8": [("E", "O")],
            "f9": [("O", "E"), ("O", "S"), ("E", "O")],
            "f10": [("S", "E"), ("E", "O")],
        },

        "R3": {
            "f1": [("N", "S"), ("N", "O")],
            "f2": [("E", "O"), ("E", "N"), ("E", "S")],
            "f3": [("S", "N")],
            "f4": [("S", "N"), ("N", "S"), ("N", "O")],
            # repite
            "f5": [("N", "S"), ("N", "O")],
            "f6": [("E", "O"), ("E", "N"), ("E", "S")],
            "f7": [("S", "N")],
            "f8": [("S", "N"), ("N", "S"), ("N", "O")]
        },

        "S1": {
            "f1": [("O", "E"), ("O", "S"), ("E", "O")],
            "f2": [("E", "S"), ("E", "O")],
            # repite
            "f3": [("O", "E"), ("O", "S"), ("E", "O")],
            "f4": [("E", "S"), ("E", "O")]
        },

        "S3": {
            "f1": [("N", "S"), ("N", "O")],
            "f2": [("E", "O"), ("E", "S")],
            # repite
            "f3": [("N", "S"), ("N", "O")],
            "f4": [("E", "O"), ("E", "S")]
        },

        "Z9": {
            "f1": [("O", "N"), ("O", "E")],
            "f2": [("E", "O"), ("E", "N"), ("O", "E")],
            # repite
            "f3": [("O", "N"), ("O", "E")],
            "f4": [("E", "O"), ("E", "N"), ("O", "E")]
        },

        "T1": {
            "f1": [("S", "E"), ("S", "O")],
            "f2": [("O", "E")],
            "f3": [("E", "O")],
            "f4": [("O", "E"), ("E", "O")],
            "peatonal":[],
            # repite
            "f5": [("S", "E"), ("S", "O")],
            "f6": [("O", "E")],
            "f7": [("E", "O")],
            "f8": [("O", "E"), ("E", "O")]
        },

        "T2": {
            "f1": [("S", "N"), ("S", "O")],
            "f2": [("E", "N"), ("E", "O")],
            # repite
            "f3": [("S", "N"), ("S", "O")],
            "f4": [("E", "N"), ("E", "O")]
        },

        "V1": {
            "f1": [("O", "E")],
            "f2": [("S", "E"), ("S", "O")],
            "f3": [("E", "O")],
            "f4": [("E", "O"), ("O", "E")],
            # repite
            "f5": [("O", "E")],
            "f6": [("S", "E"), ("S", "O")],
            "f7": [("E", "O")],
            "f8": [("E", "O"), ("O", "E")],
        },

        "W1": {
            "f1": [("O", "E"), ("O", "S")],
            "f2": [("E", "O")],
            "f3": [("E", "S")],
            "f4": [("S", "E"), ("S", "O")],
            "f5": [("O", "E"), ("O", "S"), ("E", "O")],
            "f6": [("E", "O"), ("E", "S")],
            # repite
            "f7": [("O", "E"), ("O", "S")],
            "f8": [("E", "O")],
            "f9": [("E", "S")],
            "f10": [("S", "E"), ("S", "O")],
            "f11": [("O", "E"), ("O", "S"), ("E", "O")],
            "f12": [("E", "O"), ("E", "S")]
        },

        "W4": {
            "f1": [("N", "O"), ("N", "S")],
            "f2": [("N", "E")],
            "f3": [("N", "O"), ("N", "S"), ("N", "E")],
            "f4": [("S", "N"), ("S", "E")],
            "f5": [("S", "O")],
            "f6": [("S", "N"), ("S", "E"), ("S", "O")],
            "f7": [("E", "O"), ("E", "N"), ("E", "S")],
            "f8": [("N", "O"), ("N", "S"), ("S", "N"), ("S", "E")],
            # repite
            "f9": [("N", "O"), ("N", "S")],
            "f10": [("N", "E")],
            "f11": [("N", "O"), ("N", "S"), ("N", "E")],
            "f12": [("S", "N"), ("S", "E")],
            "f13": [("S", "O")],
            "f14": [("S", "N"), ("S", "E"), ("S", "O")],
            "f15": [("E", "O"), ("E", "N"), ("E", "S")],
            "f16": [("N", "O"), ("N", "S"), ("S", "N"), ("S", "E")]
        }
    }

    G = {p: sorted(fases[p]) for p in P}
 
    # E_pg: movimientos habilitados por la fase g de la intersección p
    E_pg = {(p, g): [(_acc(p, ra), _sal(p, rb)) for ra, rb in movs]
            for p in P for g, movs in fases[p].items()}
 
    # Intersecciones con fase peatonal exclusiva: durante esos intervalos
    # ningún movimiento vehicular está habilitado.
    CON_PEATONAL = ["R1", "T1"]

    # Cotas de duración de cada fase, en cantidad de intervalos:
    #   L_pg = 4 intervalos = 20 s (verde mínimo)
    #   U_pg = 12 intervalos = 60 s (verde máximo)
    L = {(p, g): 4 for p in P for g in G[p]}
    U = {(p, g): 12 for p in P for g in G[p]}
    for p in CON_PEATONAL:
        U[p, "peatonal"] = 3        # queda fija en 3 capas para el cruce peatonal = 15 s
        L[p, "peatonal"] = 3

# =========================================================================
    #  Demandas
    # =========================================================================
    #  Los conteos se tomaron en las intersecciones de mayor demanda, durante
    #  dos ciclos consecutivos, promediando y llevando el resultado al ciclo
    #  normalizado de 80 s. R3 y T2 se relevaron en ciclos de 40 s, de modo que
    #  sus conteos se duplican.
    #
    #  Cada producto es (origen, destino, demanda, recorrido). Con None conserva
    #  la asignación libre.
    PRODUCTOS = [
        # oX1 = 10.00
        ("oX1", "dZ9",  3.50, "oX1_dZ9"),
        ("oX1", "dW1",  3.50, "oX1_dW1"),
        ("oX1", "dO3",  1.00, None),
        ("oX1", "dR3",  1.00, "oX1_dR3"),
        ("oX1", "dZ10",  1.00, "oX1_dZ10"),
        # oQ1 = 14.00
        ("oQ1", "dR3",  7.00, "oQ1_dR3"),
        ("oQ1", "dS3",  2.00, "oQ1_dS3"),
        ("oQ1", "dW1",  2.00, "oQ1_dW1"),
        ("oQ1", "dZ10",  2.00, "oQ1_dZ10"),
        ("oQ1", "dX1",  1.00, "oQ1_dX1"),
        # oW1 = 14.00
        ("oW1", "dX1",  7.00, "oW1_dX1"),
        ("oW1", "dZ9",  5.00, "oW1_dZ9"),
        ("oW1", "dZ6",  1.00, None),
        ("oW1", "dX3",  0.50, None),
        ("oW1", "dW4",  0.50, "oW1_dW4"),
        # oZ10 = 9.00
        ("oZ10", "dR3",  6.00, "oZ10_dR3"),
        ("oZ10", "dX3",  2.00, "oZ10_dX3"),
        ("oZ10", "dX1",  1.00, "oZ10_dX1"),
        # oR3 = 4.00
        ("oR3", "dW1",  4.00, "oR3_dW1"),
        # oW4 = 7.00
        ("oW4", "dW1",  3.00, "oW4_dW1"),
        ("oW4", "dX3",  1.75, None),
        ("oW4", "dX1",  1.00, "oW4_dX1"),
        ("oW4", "dZ9",  1.00, "oW4_dZ9"),
        ("oW4", "dQ3",  0.25, None),
        # oT2 = 8.00
        ("oT2", "dX3",  3.25, "oT2_dX3"),
        ("oT2", "dZ9",  2.00, "oT2_dZ9"),
        ("oT2", "dX1",  1.00, "oT2_dX1"),
        ("oT2", "dZ10",  1.00, None),
        ("oT2", "dZ6",  0.75, None),
        # oZ6 = 3.75
        ("oZ6", "dW4",  2.25, None),
        ("oZ6", "dS3",  1.00, None),
        ("oZ6", "dW1",  0.50, None),
        # oW2 = 1.00
        ("oW2", "dX3",  0.50, "oW2_dX3"),
        ("oW2", "dZ9",  0.50, None),
        # oX2 = 0.25
        ("oX2", "dU2",  0.25, None),
        # oP3 = 0.25
        ("oP3", "dZ6",  0.25, None),
        # oV2 = 1.00
        ("oV2", "dW3",  0.50, None),
        ("oV2", "dW4",  0.25, None),
        ("oV2", "dW1",  0.25, None),
    ]

    K = ["k%d" % (n + 1) for n in range(len(PRODUCTOS))]
    o = {k: p[0] for k, p in zip(K, PRODUCTOS)}
    d = {k: p[1] for k, p in zip(K, PRODUCTOS)}
    D = {k: p[2] for k, p in zip(K, PRODUCTOS)}
    recorrido = {k: p[3] for k, p in zip(K, PRODUCTOS)}

    inst = Instancia(
        nombre="bernal-centro-caminos" if caminos else "bernal-centro",
        descripcion="Bernal Centro",
        Gamma=Gamma, H=H,
        V_ext=V_ext, esq_libres=esq_libres, X=X,
        movimientos=movimientos, P=P, tramos=tramos, kappa=kappa,
        G=G, E_pg=E_pg, L=L, U=U,
        K=K, o=o, d=d, D=D,
        fases_obligatorias={p: ["peatonal"] for p in CON_PEATONAL},
    )

    # =========================================================================
    #  Caminos prefijados R_k
    # =========================================================================
    def _por(*secuencia):
        return [(secuencia[i], secuencia[i + 1])
                for i in range(len(secuencia) - 1)]

    CAMINOS = {
        "oX1_dZ9": _por(
            "oX1", "X1_eO", "X1_sE", "O1_eO", "O1_sE", "Z7_eO", "Z7_sE",
            "P1_eO", "P1_sE", "Q1_eO", "Q1_sE", "R1_eO", "R1_sE", "S1_eO",
            "S1_sE", "Z9_eO", "Z9_sN", "dZ9"),
        "oX1_dW1": _por(
            "oX1", "X1_eO", "X1_sE", "O1_eO", "O1_sE", "Z7_eO", "Z7_sE",
            "P1_eO", "P1_sE", "Q1_eO", "Q1_sE", "R1_eO", "R1_sE", "S1_eO",
            "S1_sE", "Z9_eO", "Z9_sE", "T1_eO", "T1_sE", "U1_eO", "U1_sE",
            "V1_eO", "V1_sE", "W1_eO", "W1_sE", "dW1"),
        "oX1_dR3": _por(
            "oX1", "X1_eO", "X1_sE", "O1_eO", "O1_sE", "Z7_eO", "Z7_sE",
            "P1_eO", "P1_sE", "Q1_eO", "Q1_sE", "R1_eO", "R1_sS", "R2_eN",
            "R2_sS", "R3_eN", "R3_sS", "dR3"),
        "oX1_dZ10": _por(
            "oX1", "X1_eO", "X1_sE", "O1_eO", "O1_sE", "Z7_eO", "Z7_sE",
            "P1_eO", "P1_sE", "Q1_eO", "Q1_sE", "R1_eO", "R1_sE", "S1_eO",
            "S1_sE", "Z9_eO", "Z9_sE", "T1_eO", "T1_sE", "U1_eO", "U1_sE",
            "V1_eO", "V1_sE", "W1_eO", "W1_sS", "W2_eN", "W2_sS", "W3_eN",
            "W3_sS", "W4_eN", "W4_sE", "dZ10"),
        "oQ1_dR3": _por(
            "oQ1", "Q1_eN", "Q1_sO", "P1_eE", "P1_sO", "Z7_eE", "Z7_sS",
            "Z8", "P2", "Q2", "R2_eO", "R2_sS", "R3_eN", "R3_sS", "dR3"),
        "oQ1_dS3": _por(
            "oQ1", "Q1_eN", "Q1_sO", "P1_eE", "P1_sE", "Q1_eO", "Q1_sE",
            "R1_eO", "R1_sE", "S1_eO", "S1_sS", "S2", "S3_eN", "S3_sS",
            "dS3"),
        "oQ1_dW1": _por(
            "oQ1", "Q1_eN", "Q1_sO", "P1_eE", "P1_sE", "Q1_eO", "Q1_sE",
            "R1_eO", "R1_sE", "S1_eO", "S1_sE", "Z9_eO", "Z9_sE", "T1_eO",
            "T1_sE", "U1_eO", "U1_sE", "V1_eO", "V1_sE", "W1_eO", "W1_sE",
            "dW1"),
        "oQ1_dZ10": _por(
            "oQ1", "Q1_eN", "Q1_sO", "P1_eE", "P1_sE", "Q1_eO", "Q1_sE",
            "R1_eO", "R1_sE", "S1_eO", "S1_sE", "Z9_eO", "Z9_sE", "T1_eO",
            "T1_sE", "U1_eO", "U1_sE", "V1_eO", "V1_sE", "W1_eO", "W1_sS",
            "W2_eN", "W2_sS", "W3_eN", "W3_sS", "W4_eN", "W4_sE", "dZ10"),
        "oQ1_dX1": _por(
            "oQ1", "Q1_eN", "Q1_sO", "P1_eE", "P1_sO", "Z7_eE", "Z7_sO",
            "O1_eE", "O1_sO", "X1_eE", "X1_sO", "dX1"),
        "oW1_dX1": _por(
            "oW1", "W1_eE", "W1_sO", "V1_eE", "V1_sO", "U1_eE", "U1_sO",
            "T1_eE", "T1_sO", "Z9_eE", "Z9_sO", "S1_eE", "S1_sO", "R1_eE",
            "R1_sO", "Q1_eE", "Q1_sO", "P1_eE", "P1_sO", "Z7_eE", "Z7_sO",
            "O1_eE", "O1_sO", "X1_eE", "X1_sO", "dX1"),
        "oW1_dZ9": _por(
            "oW1", "W1_eE", "W1_sO", "V1_eE", "V1_sO", "U1_eE", "U1_sO",
            "T1_eE", "T1_sO", "Z9_eE", "Z9_sN", "dZ9"),
        "oW1_dW4": _por(
            "oW1", "W1_eE", "W1_sS", "W2_eN", "W2_sS", "W3_eN", "W3_sS",
            "W4_eN", "W4_sS", "dW4"),
        "oZ10_dR3": _por(
            "oZ10", "W4_eE", "W4_sO", "V2", "U2", "T2_eE", "T2_sO", "S3_eE",
            "S3_sO", "R3_eE", "R3_sS", "dR3"),
        "oZ10_dX3": _por(
            "oZ10", "W4_eE", "W4_sO", "V2", "U2", "T2_eE", "T2_sO", "S3_eE",
            "S3_sO", "R3_eE", "R3_sO", "Q3", "P3", "O3", "X3_eE", "X3_sO",
            "dX3"),
        "oZ10_dX1": _por(
            "oZ10", "W4_eE", "W4_sN", "W3_eS", "W3_sN", "W2_eS", "W2_sN",
            "W1_eS", "W1_sO", "V1_eE", "V1_sO", "U1_eE", "U1_sO", "T1_eE",
            "T1_sO", "Z9_eE", "Z9_sO", "S1_eE", "S1_sO", "R1_eE", "R1_sO",
            "Q1_eE", "Q1_sO", "P1_eE", "P1_sO", "Z7_eE", "Z7_sO", "O1_eE",
            "O1_sO", "X1_eE", "X1_sO", "dX1"),
        "oR3_dW1": _por(
            "oR3", "R3_eS", "R3_sN", "R2_eS", "R2_sN", "R1_eS", "R1_sE",
            "S1_eO", "S1_sE", "Z9_eO", "Z9_sE", "T1_eO", "T1_sE", "U1_eO",
            "U1_sE", "V1_eO", "V1_sE", "W1_eO", "W1_sE", "dW1"),
        "oW4_dW1": _por(
            "oW4", "W4_eS", "W4_sN", "W3_eS", "W3_sN", "W2_eS", "W2_sN",
            "W1_eS", "W1_sE", "dW1"),
        "oW4_dX1": _por(
            "oW4", "W4_eS", "W4_sN", "W3_eS", "W3_sN", "W2_eS", "W2_sN",
            "W1_eS", "W1_sO", "V1_eE", "V1_sO", "U1_eE", "U1_sO", "T1_eE",
            "T1_sO", "Z9_eE", "Z9_sO", "S1_eE", "S1_sO", "R1_eE", "R1_sO",
            "Q1_eE", "Q1_sO", "P1_eE", "P1_sO", "Z7_eE", "Z7_sO", "O1_eE",
            "O1_sO", "X1_eE", "X1_sO", "dX1"),
        "oW4_dZ9": _por(
            "oW4", "W4_eS", "W4_sN", "W3_eS", "W3_sN", "W2_eS", "W2_sN",
            "W1_eS", "W1_sO", "V1_eE", "V1_sO", "U1_eE", "U1_sO", "T1_eE",
            "T1_sO", "Z9_eE", "Z9_sN", "dZ9"),
        "oT2_dX3": _por(
            "oT2", "T2_eS", "T2_sO", "S3_eE", "S3_sO", "R3_eE", "R3_sO",
            "Q3", "P3", "O3", "X3_eE", "X3_sO", "dX3"),
        "oT2_dZ9": _por(
            "oT2", "T2_eS", "T2_sN", "T1_eS", "T1_sO", "Z9_eE", "Z9_sN",
            "dZ9"),
        "oT2_dX1": _por(
            "oT2", "T2_eS", "T2_sN", "T1_eS", "T1_sO", "Z9_eE", "Z9_sO",
            "S1_eE", "S1_sO", "R1_eE", "R1_sO", "Q1_eE", "Q1_sO", "P1_eE",
            "P1_sO", "Z7_eE", "Z7_sO", "O1_eE", "O1_sO", "X1_eE", "X1_sO",
            "dX1"),
        "oW2_dX3": _por(
            "oW2", "W2_eE", "W2_sS", "W3_eN", "W3_sS", "W4_eN", "W4_sO",
            "V2", "U2", "T2_eE", "T2_sO", "S3_eE", "S3_sO", "R3_eE", "R3_sO",
            "Q3", "P3", "O3", "X3_eE", "X3_sO", "dX3"),
    }

    if caminos:
        inst.R = {k: CAMINOS[recorrido[k]] for k in K if recorrido[k]}

    return inst
 
# =============================================================================
#  Catálogo de instancias disponibles
# =============================================================================
#  Cada zona de estudio aparece dos veces: con asignación de tráfico (el
#  modelo elige los recorridos) y con caminos prefijados (restricciones
#  (30) y (31)).
BERNAL_CENTRO = {
    "bernal-centro": bernal_centro,
    "bernal-centro-caminos": lambda: bernal_centro(caminos=True),
}