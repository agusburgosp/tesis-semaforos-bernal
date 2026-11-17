from modelo import Instancia, caminos_mas_cortos, nodos

# =============================================================================
#  INSTANCIA: BERNAL ESTE
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

#  Recto sobre una avenida de dos carriles: el doble que en un carril.
RECTO_LARGO = 1.0

# -----------------------------------------------------------------------------
#  Calles de barrio: unos 24 km/h (6,7 m/s)
# -----------------------------------------------------------------------------
#  CUADRA:  tiempo de recorrido de una cuadra de 100 m (15 s).
#  U_CALLE: capacidad de un carril [veh/s] (2,5 veh por intervalo).
CUADRA, U_CALLE = 15.0, 0.5

#  Tramos cortos, entre esquinas a mitad de cuadra: 5 s,
#  redondeado al múltiplo de Delta más cercano.
CUADRAS_CORTAS = 5.0

#  Tramo de dos cuadras (unos 200 m) sin esquinas intermedias: 30 s.
CUADRA_LARGA_2 = 30.0

# -----------------------------------------------------------------------------
#  Avenida Caseros: unos 35 km/h (9,7 m/s), dos carriles por sentido
# -----------------------------------------------------------------------------
#  Una cuadra de 100 m se recorre en unos 10 s.
CUADRA_CASEROS = 10.0

#  Dos carriles: el doble de la capacidad de un carril (5 veh por intervalo).
U_CALLE_CASEROS = 1.0

#  Tramos cortos sobre Caseros: 5 s.
CUADRA_CASEROS_CORTAS = 5

#  Tramo de tres cuadras sin esquinas intermedias: unos 30 s
CUADRA_CASEROS_LARGA_3 = 30

def _acc(esq: str, rama: str) -> str:
    """Nodo de acceso a la esquina por la rama indicada."""
    return "%s_e%s" % (esq, rama)
 
 
def _sal(esq: str, rama: str) -> str:
    """Nodo de salida de la esquina hacia la rama indicada."""
    return "%s_s%s" % (esq, rama)
 
 
def bernal_este(caminos: bool = False, giro_K1: bool = False) -> Instancia:
    Gamma, H = 80.0, 16
 
    # -------------------------------------------------------------------------
    #  Esquinas: sus movimientos, con la capacidad de cada uno [veh/s]
    #  Cada movimiento se declara como (rama de acceso, rama de salida) según
    #  el punto cardinal por el que el flujo llega y por el que se va.
    # -------------------------------------------------------------------------
    esquinas = {
        # A1 - A8 : Lomas de Zamora
        # A1: dos semaforos
        "A1": {("S", "E"): GIRO,     # a autopista
               ("S", "O"): GIRO,
               ("O", "E"): RECTO_LARGO,    # a autopista
               ("E", "O"): RECTO_LARGO,    # a nodo de salida oeste (dA1) ---> va en todas las fases, viene de Z1
               ("E", "S"): GIRO,     # a uriburu
               ("O", "S"): GIRO},    # a uriburu

        "A2": {("N", "S"): RECTO,    # a uriburu
               ("S", "E"): GIRO,     # a carabelas
               ("N", "E"): GIRO,     # a carabelas
               ("S", "N"): RECTO},   # a caseros

        "A3": {("N", "S"): RECTO,    # a uriburu
               ("N", "O"): GIRO,     # a nodo de salida oeste (dA3)
               ("S", "N"): RECTO,    # a caseros
               ("S", "O"): GIRO,     # a nodo de salida oeste (dA3)
               ("E", "N"): GIRO,     # a caseros
               ("E", "O"): RECTO,    # a nodo de salida oeste (dA3)
               ("E", "S"): GIRO,     # a uriburu
               ("O", "N"): GIRO,     # a caseros
               ("O", "S"): GIRO},    # a uriburu

        "A4": {("S", "N"): RECTO,    # a caseros
               ("N", "S"): RECTO,    # a uriburu
               ("O", "N"): GIRO,     # a caseros
               ("O", "S"): GIRO},    # a uriburu

        "A5": {("S", "N"): RECTO,    # a caseros
               ("N", "S"): RECTO,    # a uriburu
               ("O", "E"): RECTO,    # a roca
               ("O", "N"): GIRO,     # a caseros
               ("O", "S"): GIRO,     # a uriburu
               ("N", "E"): GIRO,     # a roca
               ("S", "E"): GIRO},    # a roca

        "A6": {("S", "N"): RECTO,    # a caseros
               ("N", "S"): RECTO,    # a uriburu
               ("E", "O"): RECTO,    # a nodo de salida oeste (dA6)
               ("E", "N"): GIRO,     # a caseros
               ("E", "S"): GIRO,     # a uriburu
               ("N", "O"): GIRO,     # a nodo de salida oeste (dA6)
               ("S", "O"): GIRO},    # a nodo de salida oeste (dA6)

        "A7": {("S", "N"): RECTO,    # a caseros
               ("N", "S"): RECTO,    # a uriburu
               ("E", "O"): RECTO,    # a nodo de salida oeste (dA7)
               ("O", "E"): RECTO,    # a cramer
               ("E", "S"): GIRO,     # a uriburu
               ("E", "N"): GIRO,     # a caseros
               ("O", "N"): GIRO,     # a caseros
               ("O", "S"): GIRO,     # a uriburu
               ("S", "E"): GIRO,     # a cramer
               ("S", "O"): GIRO,     # a nodo de salida oeste (dA7)
               ("N", "O"): GIRO,     # a nodo de salida oeste (dA7)
               ("N", "E"): GIRO},    # a cramer

        "A8": {("N", "O"): GIRO,     # a nodo de salida oeste (dA8)
               ("E", "N"): GIRO,      # a caseros
               ("E", "O"): RECTO},    # a nodo de salida oeste (dA8)

        # Caseros entre lomas y la paz (menos capacidad porque esta a mitad de cuadra)
        "Z1": {("E", "N"): GIRO,     # a nodo de salida norte (dZ1)
               ("E", "O"): RECTO_LARGO,    # a nodo de salida oeste (dA1)
               ("O", "E"): RECTO_LARGO,    # a autopista
               ("N", "E"): GIRO,           # a autopista
               ("N", "O"): GIRO,           # a lomas
               ("O", "N"): GIRO},    # a nodo de salida norte (dZ1)

        # B1 - B7 : La Paz
        # B1: tres semaforos
        "B1": {("O", "E"): RECTO_LARGO,    # a autopista
               ("S", "O"): GIRO,     # a Z1
               ("S", "E"): GIRO,     # a autopista
               ("E", "O"): RECTO_LARGO},   # a Z1  

        "B6": {("S", "N"): RECTO,    # a caseros
               ("S", "E"): GIRO,     # a cramer
               ("S", "O"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO,    # a nodo de salida (dA7)
               ("E", "N"): GIRO,     # a caseros
               ("O", "N"): GIRO,     # a caseros
               ("O", "E"): RECTO},   # a cramer 

        # C1 - C4 : Juncal
        "C3": {("N", "S"): RECTO,    # a uriburu
               ("N", "E"): GIRO,     # a cramer
               ("N", "O"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO,    # a nodo de salida (dA7)
               ("E", "S"): GIRO,     # a uriburu
               ("O", "S"): GIRO,     # a uriburu
               ("O", "E"): RECTO},   # a cramer   

        # D1 - D7 : Victoria  
        "D1": {("O", "E"): RECTO_LARGO,    # a autopista
               ("O", "S"): GIRO,     # a victoria
               ("E", "S"): GIRO,     # a victoria
               ("N", "S"): RECTO,    # a uriburu
               ("N", "O"): GIRO,     # a nodo de salida (dA7)
               ("N", "E"): GIRO,     # a autopista
               ("E", "O"): RECTO_LARGO},   # a lomas

        "D6": {("N", "S"): RECTO,    # a uriburu
               ("N", "E"): GIRO,     # a cramer
               ("N", "O"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO,    # a nodo de salida (dA7)
               ("E", "S"): GIRO,     # a uriburu
               ("O", "S"): GIRO,     # a uriburu
               ("O", "E"): RECTO},   # a cramer 

        # E1 - E7 : Tacuari
        "E1": {("O", "E"): RECTO_LARGO,    # a autopista
               ("E", "N"): GIRO,     # a nodo salida (dE1)
               ("O", "N"): GIRO,     # a nodo salida (dE1)
               ("S", "N"): RECTO,    # a nodo salida (dE1)
               ("S", "O"): GIRO,     # a autopista
               ("S", "E"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO_LARGO},   # a lomas 

        "E6": {("S", "N"): RECTO,    # a caseros
               ("S", "E"): GIRO,     # a cramer
               ("S", "O"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO,    # a nodo de salida (dA7)
               ("E", "N"): GIRO,     # a caseros
               ("O", "N"): GIRO,     # a caseros
               ("O", "E"): RECTO},   # a cramer 

        # F1 - F7 : Ramella  
        "F1": {("O", "E"): RECTO_LARGO,    # a autopista
               ("O", "S"): GIRO,     # a victoria
               ("E", "S"): GIRO,     # a victoria
               ("N", "S"): RECTO,    # a uriburu
               ("N", "O"): GIRO,     # a nodo de salida (dA7)
               ("N", "E"): GIRO,     # a autopista
               ("E", "O"): RECTO_LARGO},   # a lomas

        # F6: tres semaforos
        "F6": {("N", "S"): RECTO,    # a uriburu
               ("N", "E"): GIRO,     # a cramer
               ("N", "O"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO,    # a nodo de salida (dA7)
               ("O", "S"): GIRO,     # a uriburu
               ("O", "E"): RECTO},   # a cramer 

        # G1 - G8 : Constitucion
        # G1: tres semaforos
        "G1": {("O", "E"): RECTO_LARGO,    # a autopista
               ("O", "N"): GIRO,     # a nodo salida (dG1)
               ("S", "N"): RECTO,    # a nodo salida (dG1)
               ("S", "O"): GIRO,     # a autopista
               ("S", "E"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO_LARGO},   # a lomas 

        "G2": {("S", "N"): RECTO,    # a caseros
               ("S", "E"): GIRO,     # a almafuerte
               ("E", "N"): GIRO,     # a caseros
               },

        "G7": {("S", "N"): RECTO,    # a caseros
               ("S", "E"): GIRO,     # a cramer
               ("S", "O"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO,    # a nodo de salida (dA7)
               ("E", "N"): GIRO,     # a caseros
               ("O", "N"): GIRO,     # a caseros
               ("O", "E"): RECTO},   # a cramer

        # Caseros entre constitucion y almafuerte (mas capcidad)
        "Z2": {("E", "N"): GIRO,     # a autopista
               ("O", "N"): GIRO,     # a nodo de salida oeste (dA1)
               ("O", "E"): RECTO_LARGO,    # a autopista
               ("E", "O"): RECTO_LARGO},   # a nodo de salida norte (dA1)

        # H1 - H7 : Almafuerte  
        "H1": {("O", "E"): RECTO_LARGO,    # a autopista
               ("O", "S"): GIRO,     # a almafuerte
               ("E", "S"): GIRO,     # a almafuerte
               ("E", "O"): RECTO_LARGO},   # a lomas

        "H2": {("N", "S"): RECTO,    # a cramer
               ("N", "O"): GIRO,     # a constitucion
               ("O", "S"): GIRO,     # a cramer
               },

        "H7": {("N", "S"): RECTO,    # a uriburu
               ("N", "E"): GIRO,     # a cramer
               ("N", "O"): GIRO,     # a nodo de salida (dA7)
               ("E", "O"): RECTO,    # a nodo de salida (dA7)
               ("E", "S"): GIRO,     # a uriburu
               ("O", "S"): GIRO,     # a uriburu
               ("O", "E"): RECTO},   # a cramer

        # I1 - I2 : Guemes
        "I1": {("O", "E"): RECTO,    # a cramer
               ("S", "O"): GIRO,     # a nodo de salida (dA7)
               ("S", "E"): GIRO,     # a cramer
               ("E", "O"): RECTO},   # a nodo de salida (dA7) 

        # J1 - J2 : Estrada
        # J1: tres semaforos
        "J1": {("O", "E"): RECTO,    # a cramer
               ("O", "S"): GIRO,      # a uriburu
               ("S", "O"): GIRO,     # a nodo de salida (dA7)
               ("S", "E"): GIRO,     # a cramer
               ("E", "S"): GIRO,      # a uriburu
               ("E", "O"): RECTO},   # a nodo de salida (dA7) 

        "J2": {("E", "N"): GIRO,     # a cramer
               ("N", "O"): GIRO,     # a nodo de salida (dA8)
               ("N", "E"): GIRO,     # a estacion
               ("E", "O"): RECTO},   # a nodo de salida (dA8) 

        # K1 - K5 : Espora
        # K1: cuatro semaforos. Autopista
        "K1": {("S", "N"): RECTO,    # a autopista
               ("S", "E"): GIRO,     # a quilmes
               ("S", "O"): GIRO,     # a nq
               ("E", "O"): RECTO_LARGO,    # a nq
               ("E", "N"): GIRO,     # a autopista
               ("O", "E"): RECTO_LARGO,    # a quilmes
               ("O", "N"): GIRO,     # a autopista (movimiento agregado)
               ("O", "S"): GIRO,     # a bernal
               ("N", "S"): RECTO,    # a bernal
               ("N", "O"): GIRO,     # a nq
               ("N", "E"): GIRO},    # a quilmes

        "K2": {("N", "S"): RECTO,    # a uriburu
               ("S", "E"): GIRO,     # a andrade
               ("N", "E"): GIRO,     # a andrade
               ("E", "S"): GIRO,     # a uriburu
               ("E", "N"): GIRO,     # a caseros
               ("S", "N"): RECTO},   # a caseros

        "K3": {("N", "S"): RECTO,    # a uriburu
               ("E", "N"): GIRO,     # a caseros
               ("E", "S"): GIRO,     # a uriburu
               ("S", "N"): RECTO},   # a caseros

        "K4": {("S", "N"): RECTO,    # a caseros
               ("N", "S"): RECTO,    # a paso bajo nivel (dZ3)
               ("N", "O"): GIRO,     # a lomas
               ("S", "E"): GIRO,     # a estacion
               ("O", "S"): GIRO},    # paso bajo nivel a centro (dZ3)

        "K5": {("O", "E"): RECTO,    # a estacion
               ("E", "O"): RECTO},   # a lomas

        # Z4 - Z5 : vueltita de uriburu
        "Z4": {("E", "N"): GIRO,     # a dar la vuelta
               ("O", "E"): RECTO,    # a estacion
               ("E", "O"): RECTO},   # a lomas

        # L1 - L8 : Roque Saenz Peña  
        "L1": {("O", "E"): RECTO_LARGO,    # a quilmes
               ("O", "S"): GIRO,     # a roque
               ("E", "S"): GIRO,     # a roque
               ("E", "O"): RECTO_LARGO},   # a autopista

        "L2": {("O", "E"): RECTO,    # a quilmes
               ("O", "S"): GIRO,     # a uriburu
               ("E", "S"): GIRO,     # a uriburu
               ("N", "E"): GIRO,     # a quilmes
               ("N", "O"): GIRO,     # a autopista
               ("N", "S"): RECTO,     # a uriburu
               ("E", "O"): RECTO},   # a autopista

        # L7: dos semaforos
        "L7": {("N", "S"): RECTO,    # a uriburu
               ("O", "S"): GIRO},    # a uriburu

        # L8: dos semaforos
        "L8": {("N", "E"): GIRO,     # a bernal
               ("N", "O"): GIRO,     # a quilmes
               ("O", "E"): RECTO},   # a quilmes

        # M1 - M7 : Dean Funes  
        "M1": {("S", "E"): GIRO,     # a quilmes
               ("S", "O"): GIRO,     # a autopista
               ("O", "E"): RECTO_LARGO,    # a quilmes
               ("E", "O"): RECTO_LARGO},   # a autopista

        "M2": {("O", "E"): RECTO,    # a quilmes
               ("O", "N"): GIRO,     # a caseros
               ("E", "N"): GIRO,     # a caseros
               ("S", "E"): GIRO,     # a quilmes
               ("S", "O"): GIRO,     # a autopista
               ("S", "N"): RECTO,     # a caseros
               ("E", "O"): RECTO},   # a autopista

        "M4": {("E", "O"): RECTO,    # a quilmes
               ("E", "N"): GIRO,     # a caseros
               ("S", "E"): GIRO,     # a quilmes
               ("S", "O"): GIRO,     # a autopista
               ("S", "N"): RECTO},   # a caseros

        "M7": {("O", "N"): RECTO,    # a caseros
               ("E", "N"): RECTO},   # a caseros

        # N1 - N8 : Independencia  
        "N1": {("O", "S"): GIRO,     # a uriburu
               ("E", "S"): GIRO,     # a uriburu
               ("O", "E"): RECTO_LARGO,    # a quilmes
               ("E", "O"): RECTO_LARGO},   # a autopista

        "N2": {("O", "E"): RECTO,    # a quilmes
               ("O", "S"): GIRO,     # a uriburu
               ("E", "S"): GIRO,     # a uriburu
               ("N", "E"): GIRO,     # a quilmes
               ("N", "O"): GIRO,     # a autopista
               ("N", "S"): RECTO,     # a uriburu
               ("E", "O"): RECTO},   # a autopista

        "N4": {("O", "E"): RECTO,    # a quilmes
               ("O", "S"): GIRO,     # a uriburu
               ("E", "S"): GIRO,     # a uriburu
               ("N", "E"): GIRO,     # a quilmes
               ("N", "O"): GIRO,     # a autopista
               ("N", "S"): RECTO,     # a uriburu
               ("E", "O"): RECTO},   # a autopista
        
        # Chaparral
        "Z12": {("N", "S"): RECTO,
                ("S", "N"): RECTO}
    }

    # -------------------------------------------------------------------------
    #  Giro propuesto en K1: del oeste hacia el norte
    # -------------------------------------------------------------------------
    #  Hoy ese giro no existe en la calle. Se incluye en el catálogo para poder
    #  evaluar si conviene habilitarlo, pero la red con giro_K1=False es la
    #  situación actual.
    GIRO_PROPUESTO = ("O", "N")
    if not giro_K1:
        del esquinas["K1"][GIRO_PROPUESTO]

    # Conjunto de intersecciones semaforizadas
    P = ["A1", "B1", "F6", "G1", "J1", "K1", "L7", "L8", "Z12"]
 
    # Esquinas sin semáforo: un solo nodo cada una
    esq_libres = [
        # La Paz a norte (a caseros)
        "B2", "B3", "B4", "B5", "B7",

        # Juncal a sur (a uriburu)
        "C1", "C2", "C4",

        # Victoria a sur (a uriburu)
        "D2", "D3", "D4", "D5", "D7",

        # Tacuari a norte (a caseros)
        "E2", "E3", "E4", "E5", "E7",

        # Ramella a sur (a uriburu)
        "F2", "F3", "F4", "F5", "F7",

        # Constitucion a norte (a caseros)
        "G3", "G4", "G5", "G6", "G8",

        # Almafuerte a sur (a uriburu)
        "H3", "H4", "H5", "H6", "H8",

        # Guemes a norte (a cramer)
        "I2",

        # Vueltita de uriburu
        "Z5",

        # Roque Saenz Peña a sur (a uriburu)
        "L3", "L4", "L5", "L6",

        # Dean Funes a norte (a caseros)
        "M3", "M5", "M6",

        # Independencia a sur (a uriburu)
        "N3", "N5", "N6", "N7", "N8"
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
            "oA1", "dA1", "oA3", "dA3", "oA4", "oA5", "dA6", "oA7", "dA7", "dA8",          # Lomas de Zamora: Caseros - Uriburu
            "oZ1", "dZ1", "oD1", "dE1", "oF1", "dG1", "dZ2", "oK1", "dK1",                 # Caseros : Lomas de Zamora - Labarden
            "oZ3", "dZ3",                                                                  # Paso nivel
            "oN1", "dN1", "oN2", "dN2", "oN3", "oN4", "dN4", "dN5", "dN6", "oN7", "oN8"     # Labarden: Caseros - Uriburu
        ]                    
 
    # -------------------------------------------------------------------------
    #  Las calles (A \ E): cada arco es una cuadra
    # -------------------------------------------------------------------------
    conexiones = [
        # -------------------------------------------------------------
        # VERTICALES
        # -------------------------------------------------------------
        # Lomas de Zamora
        (_sal("A1", "S"), _acc("A2", "N")), (_sal("A2", "N"), _acc("A1", "S")),
        (_sal("A2", "S"), _acc("A3", "N")), (_sal("A3", "N"), _acc("A2", "S")),
        (_sal("A4", "S"), _acc("A5", "N")), (_sal("A5", "N"), _acc("A4", "S")),
        (_sal("A5", "S"), _acc("A6", "N")), (_sal("A6", "N"), _acc("A5", "S")),
        (_sal("A6", "S"), _acc("A7", "N")), (_sal("A7", "N"), _acc("A6", "S")),
        (_sal("A7", "S"), _acc("A8", "N")), (_sal("A8", "N"), _acc("A7", "S")),

        # Juncal
        ("C1", "C2"), ("C2", _acc("C3", "N")), (_sal("C3", "S"), "C4"),

        # Z1
        ("oZ1", _acc("Z1", "N")), (_sal("Z1", "N"), "dZ1"),

        # La Paz
        ("B7", _acc("B6", "S")), (_sal("B6", "N"), "B5"), ("B5", "B4"),
        ("B4", "B3"), ("B3", "B2"), ("B2", _acc("B1", "S")),

        # Victoria
        ("oD1", _acc("D1", "N")), (_sal("D1", "S"), "D2"), ("D2", "D3"), ("D3", "D4"), 
        ("D4", "D5"), ("D5", _acc("D6", "N")), (_sal("D6", "S"), "D7"),

        # Tacuari
        ("E7", _acc("E6", "S")), (_sal("E6", "N"), "E5"), ("E5", "E4"),
        ("E4", "E3"), ("E3", "E2"), ("E2", _acc("E1", "S")), (_sal("E1", "N"), "dE1"),

        # Ramella
        ("oF1", _acc("F1", "N")), (_sal("F1", "S"), "F2"), ("F2", "F3"), ("F3", "F4"), 
        ("F4", "F5"), ("F5", _acc("F6", "N")), (_sal("F6", "S"), "F7"),

        # Constitucion
        ("G8", _acc("G7", "S")), (_sal("G7", "N"), "G6"), ("G6", "G5"), 
        ("G5", "G4"), ("G4", "G3"), (_sal("G1", "N"), "dG1"),

        # Z2
        (_sal("Z2", "N"), "dZ2"),

        # Almafuerte
        ("H3", "H4"), ("H4", "H5"), ("H5", "H6"), ("H6", _acc("H7", "N")), (_sal("H7", "S"), "H8"),

        # Guemes
        ("I2", _acc("I1", "S")),

        # Estrada
        (_sal("J1", "S"), _acc("J2", "N")), (_sal("J2", "N"), _acc("J1", "S")),

        # Espora
        ("oK1", _acc("K1", "N")), (_sal("K1", "N"), "dK1"),
        (_sal("K1", "S"), _acc("K2", "N")), (_sal("K2", "N"), _acc("K1", "S")),
        (_sal("K2", "S"), _acc("K3", "N")), (_sal("K3", "N"), _acc("K2", "S")),

        # Z4 - Z5 : vueltita de uriburu
        (_sal("Z4", "N"), "Z5"),

        # Roque Saenz Peña
        (_sal("L1", "S"), _acc("L2", "N")), (_sal("L2", "S"), "L3"),
        ("L3", "L4"), ("L4", "L5"), ("L5", "L6"),

        # Dean Funes
        (_sal("M7", "N"), "M6"), ("M6", "M5"), ("M5", _acc("M4", "S")),
        (_sal("M4", "N"), "M3"), ("M3", _acc("M2", "S")), (_sal("M2", "N"), _acc("M1", "S")),

        # Independencia
        (_sal("N1", "S"), _acc("N2", "N")), (_sal("N2", "S"), "N3"), 
        ("N3", _acc("N4", "N")), ("N6", "N7"), ("N7", "N8"),

        # -------------------------------------------------------------
        # HORIZONTALES
        # -------------------------------------------------------------

        # San Luis
        (_sal("H2", "O"), _acc("G2", "E")), (_sal("G2", "E"), _acc("H2", "O")),

        # Carabelas
        (_sal("A2", "E"), "B2"), ("B2","D2"), ("D2", "E2"),
        ("E2","F2"), ("F2", "G3"), ("G3", "H3"),

        # Ciudadela
        ("H4", "G4"), ("G4", "F3"), ("F3", "E3"), ("E3", "D3"), ("D3", "B3"), 
        ("B3", _acc("A3", "E")), (_sal("A3", "O"), "dA3"), ("oA3", _acc("A3", "O")),

        # Roca
        ("oA4", _acc("A4", "O")),

        # Roca
        ("oA5", _acc("A5", "O")), (_sal("A5", "E"), "C1"), ("C1", "B4"),
        ("B4", "D4"), ("D4", "E4"), ("E4","F4"), ("F4", "G5"), ("G5", "H5"),

        # Chiclana
        ("H6", "G6"), ("G6", "F5"), ("F5", "E5"), ("E5", "D5"), ("D5", "B5"), 
        ("B5", "C2"), ("C2", _acc("A6", "E")), (_sal("A6", "O"), "dA6"),

        # Cramer
        ("oA7", _acc("A7", "O")), (_sal("A7", "O"), "dA7"),
        (_sal("A7", "E"), _acc("C3", "O")), (_sal("C3", "O"), _acc("A7", "E")),
        (_sal("C3", "E"), _acc("B6", "O")), (_sal("B6", "O"), _acc("C3", "E")),
        (_sal("B6", "E"), _acc("D6", "O")), (_sal("D6", "O"), _acc("B6", "E")),
        (_sal("D6", "E"), _acc("E6", "O")), (_sal("E6", "O"), _acc("D6", "E")),
        (_sal("E6", "E"), _acc("F6", "O")), (_sal("F6", "O"), _acc("E6", "E")),
        (_sal("F6", "E"), _acc("G7", "O")), (_sal("G7", "O"), _acc("F6", "E")),
        (_sal("G7", "E"), _acc("H7", "O")), (_sal("H7", "O"), _acc("G7", "E")),
        (_sal("H7", "E"), _acc("I1", "O")), (_sal("I1", "O"), _acc("H7", "E")),
        (_sal("I1", "E"), _acc("J1", "O")), (_sal("J1", "O"), _acc("I1", "E")),
        (_sal("J1", "E"), _acc("K4", "O")), (_sal("K4", "O"), _acc("J1", "E")),
        (_sal("K4", "E"), "Z5"),

        # Uriburu
        ("oN8", "N8"), ("N8", _acc("M7", "E")), (_sal("L8", "E"), _acc("M7", "O")), 
        (_sal("Z4", "O"), _acc("K5", "E")), (_sal("K5", "E"), _acc("Z4", "O")),
        (_sal("K5", "O"), _acc("J2", "E")), (_sal("J2", "E"), _acc("K5", "O")),
        (_sal("J2", "O"), "I2"), ("I2", "H8"), ("H8", "G8"), ("G8", "F7"), ("F7", "E7"), 
        ("E7", "D7"), ("D7", "B7"), ("B7", "C4"), ("C4", _acc("A8", "E")), (_sal("A8", "O"), "dA8"),

        # Cramer 2
        ("oN7", "N7"), ("N7", "M6"), ("M6", "L6"),

        # Chiclana 2
        ("L5", "M5"), ("M5", "N6"), ("N6", "dN6"),

        # Rafael Obligado
        ("N5", "dN5"),

        # Lebenshon
        (_sal("M4", "O"), "L4"), 
        (_sal("M4", "E"), _acc("N4", "O")), (_sal("N4", "O"), _acc("M4", "E")), 
        (_sal("N4", "E"), "dN4"), ("oN4", _acc("N4", "E")), 

        # Carabelas
        ("oN3", "N3"), ("N3", "M3"), ("M3", "L3"), ("L3", _acc("K3", "E")),

        # Andrade
        (_sal("K2", "E"), _acc("L2", "O")), (_sal("L2", "O"), _acc("K2", "E")),
        (_sal("L2", "E"), _acc("M2", "O")), (_sal("M2", "O"), _acc("L2", "E")),
        (_sal("M2", "E"), _acc("N2", "O")), (_sal("N2", "O"), _acc("M2", "E")), 
        (_sal("N2", "E"), "dN2"), ("oN2", _acc("N2", "E")), 
    ]

    conexiones_cortas = [
       # Lomas de Zamora
       (_sal("A3", "S"), _acc("A4", "N")), (_sal("A4", "N"), _acc("A3", "S")),

       # Constitucion
       ("G3", _acc("G2", "S")), (_sal("G2", "N"), _acc("G1", "S")),

       # Almafuerte
       (_sal("H1", "S"), _acc("H2", "N")), (_sal("H2", "S"), "H3"),

       # Roque Senz Peña
       ("L6", _acc("L7", "N")), (_sal("L7", "S"), _acc("L8", "N")),

       # Independencia
       (_sal("N4", "S"), "N5"), ("N5", "N6"),

       # Espora
       (_sal("K3", "S"), _acc("Z12", "N")), (_sal("Z12", "N"), _acc("K3", "S")),
    ]

    conexiones_largas_2 = [
       # Espora (Paso bajo nivel)
       (_sal("K4", "S"), "dZ3"), ("oZ3", _acc("K4", "S")),

       # Uriburu
       (_sal("L8", "O"), _acc("Z4", "E")), (_sal("Z4", "E"), _acc("L8", "O")),

       # Cramer 
       ("Z5", _acc("L7", "O")),

       # Espora
       (_sal("Z12", "S"), _acc("K4", "N")), (_sal("K4", "N"), _acc("Z12", "S")),
    ]

    conexiones_caseros = [
       ("oA1", _acc("A1", "O")), (_sal("A1", "O"), "dA1"),
       (_sal("B1", "E"), _acc("D1", "O")), (_sal("D1", "O"), _acc("B1", "E")),
       (_sal("D1", "E"), _acc("E1", "O")), (_sal("E1", "O"), _acc("D1", "E")),
       (_sal("E1", "E"), _acc("F1", "O")), (_sal("F1", "O"), _acc("E1", "E")),
       (_sal("F1", "E"), _acc("G1", "O")), (_sal("G1", "O"), _acc("F1", "E")),
       (_sal("G1", "E"), _acc("Z2", "O")), (_sal("Z2", "O"), _acc("G1", "E")),
       (_sal("K1", "E"), _acc("L1", "O")), (_sal("L1", "O"), _acc("K1", "E")),
       (_sal("L1", "E"), _acc("M1", "O")), (_sal("M1", "O"), _acc("L1", "E")),
       (_sal("M1", "E"), _acc("N1", "O")), (_sal("N1", "O"), _acc("M1", "E")),
       (_sal("N1", "E"), "dN1"), ("oN1", _acc("N1", "E")), 
    ]

    conexiones_caseros_cortas = [
       (_sal("A1", "E"), _acc("Z1", "O")), (_sal("Z1", "O"), _acc("A1", "E")),
       (_sal("Z1", "E"), _acc("B1", "O")), (_sal("B1", "O"), _acc("Z1", "E")),
       (_sal("Z2", "E"), _acc("H1", "O")), (_sal("H1", "O"), _acc("Z2", "E")),   
    ]

    conexiones_caseros_largas_3 = [
       (_sal("H1", "E"), _acc("K1", "O")), (_sal("K1", "O"), _acc("H1", "E")),
    ]

    #  m = largo del tramo en metros. No lo usa el modelo: sirve para calcular
    #  la cola, que depende de la geometría y no del tiempo de recorrido.
    tramos = {}
    tramos.update({a: dict(t=CUADRA,          u=U_CALLE,         m=100.0) for a in conexiones})
    tramos.update({a: dict(t=CUADRAS_CORTAS,  u=U_CALLE,         m=50.0)  for a in conexiones_cortas})
    tramos.update({a: dict(t=CUADRA_LARGA_2,  u=U_CALLE,         m=200.0) for a in conexiones_largas_2})

    tramos.update({a: dict(t=CUADRA_CASEROS,          u=U_CALLE_CASEROS, m=100.0) for a in conexiones_caseros})
    tramos.update({a: dict(t=CUADRA_CASEROS_CORTAS,   u=U_CALLE_CASEROS, m=50.0)  for a in conexiones_caseros_cortas})
    tramos.update({a: dict(t=CUADRA_CASEROS_LARGA_3,  u=U_CALLE_CASEROS, m=300.0) for a in conexiones_caseros_largas_3})

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
        "A1": {
            "f1": [("O", "E"), ("O", "S")],
            "f2": [("E", "O"), ("E", "S")],
            "f3": [("S", "E"), ("S", "O")],
            # repite
            "f4": [("O", "E"), ("O", "S")],
            "f5": [("E", "O"), ("E", "S")],
            "f6": [("S", "E"), ("S", "O")],
        },

        "B1": {
            "f1": [("O", "E"), ("E", "O")],
            "f2": [("E", "O")],
            "f3": [("S", "E"), ("S", "O")],
            "f4": [("O", "E")],
            "peatonal":[], 
            # repite
            "f5": [("O", "E"), ("E", "O")],
            "f6": [("E", "O")],
            "f7": [("S", "E"), ("S", "O")],
            "f8": [("O", "E")],
        },

        "F6": {
            "f1": [("N", "S"), ("N", "E"), ("N", "O")],
            "f2": [("E", "O"), ("O", "E"), ("O", "S")],
            "f3": [("E", "O")],
            "f4": [("O", "E"), ("O", "S")],
            # repite
            "f5": [("N", "S"), ("N", "E"), ("N", "O")],
            "f6": [("E", "O"), ("O", "E"), ("O", "S")],
            "f7": [("E", "O")],
            "f8": [("O", "E"), ("O", "S")],
        },

        "G1": {
            "f1": [("S", "N"), ("S", "E"), ("S", "O")],
            "f2": [("E", "O"), ("O", "E"), ("O", "N")],
            "f3": [("E", "O")],
            "f4": [("O", "E"), ("O", "N")],
            # repito
            "f5": [("S", "N"), ("S", "E"), ("S", "O")],
            "f6": [("E", "O"), ("O", "E"), ("O", "N")],
            "f7": [("E", "O")],
            "f8": [("O", "E"), ("O", "N")],
        },

        "J1": {
            "f1": [("S", "E"), ("S", "O")],
            "f2": [("O", "S"), ("O", "E")],
            "f3": [("E", "O"), ("E", "S")],
            "f4": [("E", "O")],
            "f5": [("E", "S")],
            "f6": [("E", "O"), ("O", "S"), ("O", "E")], 
            "peatonal":[],
            # repito
            "f7": [("S", "E"), ("S", "O")],
            "f8": [("O", "S"), ("O", "E")],
            "f9": [("E", "O"), ("E", "S")],
            "f10": [("E", "O")],
            "f11": [("E", "S")],
            "f12": [("E", "O"), ("O", "S"), ("O", "E")], 
        },

        "K1": {
            "f1": [("S", "N"), ("S", "E"), ("S", "O")],
            "f2": [("O", "E"), ("O", "S"), ("O", "N")],
            "f3": [("O", "N")],
            "f4": [("O", "E"), ("O", "S")],
            "f5": [("E", "N"), ("E", "O")],
            "f6": [("N", "S"), ("N", "O"), ("N", "E")], 
            "f7": [("O", "E"), ("O", "S"), ("E", "N"), ("E", "O")],
            "f8": [("N", "S"), ("N", "O"), ("N", "E"), ("E", "N")], 
            # repito
            "f9": [("S", "N"), ("S", "E"), ("S", "O")],
            "f10": [("O", "E"), ("O", "S"), ("O", "N")],
            "f11": [("O", "N")],
            "f12": [("O", "E"), ("O", "S")],
            "f13": [("E", "N"), ("E", "O")],
            "f14": [("N", "S"), ("N", "O"), ("N", "E")], 
            "f15": [("O", "E"), ("O", "S"), ("E", "N"), ("E", "O")],
            "f16": [("N", "S"), ("N", "O"), ("N", "E"), ("E", "N")], 
        },

        "L7": {
            "f1": [("O", "S")],
            "f2": [("N", "S")],
            # repito
            "f3": [("O", "S")],
            "f4": [("N", "S")],
        },

        "L8": {
            "f1": [("N", "E"), ("N", "O")],
            "f2": [("O", "E")],
            "peatonal": [],
            # repito
            "f3": [("N", "E"), ("N", "O")],
            "f4": [("O", "E")],
        },

        "Z12": {
            "f1": [("N", "S"), ("S", "N")],
            "peatonal": [],
            # repito: el ciclo real es de 40 s, dos veces por período
            "f2": [("N", "S"), ("S", "N")],
            "peatonal2": [],
        }
    }

    #  Las fases que lo habilitan también pierden el movimiento. Las que eran
    #  sólo ese giro desaparecen del catálogo.
    if not giro_K1:
        for g in list(fases["K1"]):
            fases["K1"][g] = [m for m in fases["K1"][g] if m != GIRO_PROPUESTO]
            if not fases["K1"][g]:
                del fases["K1"][g]
 
    G = {p: sorted(fases[p]) for p in P}
 
    # E_pg: movimientos habilitados por la fase g de la intersección p
    E_pg = {(p, g): [(_acc(p, ra), _sal(p, rb)) for ra, rb in movs]
            for p in P for g, movs in fases[p].items()}

    # Intersecciones con fase peatonal exclusiva: durante esos intervalos
    # ningún movimiento vehicular está habilitado. La duración de cada una
    # depende del ancho de la calzada que se cruza, de modo que no es una
    # decisión del modelo sino un dato de la intersección.
    PEATONAL = {"B1": 2, "J1": 2, "L8": 3, "Z12": 2}    # en capas

    L = {(p, g): 4 for p in P for g in G[p]}
    U = {(p, g): 12 for p in P for g in G[p]}
    for p, capas in PEATONAL.items():
        L[p, "peatonal"] = capas
        U[p, "peatonal"] = capas
    L["Z12", "peatonal2"] = U["Z12", "peatonal2"] = PEATONAL["Z12"]

    #  Con el giro, K1 necesita más fases: O-N, E-N y S-N no entran en 16 capas
    #  con un mínimo de 4.
    if giro_K1:
        for g in G["K1"]:
            L["K1", g] = 3

    # =========================================================================
    #  Demandas
    # =========================================================================
    #  Los conteos se tomaron entre las 7:40 y las 9:00, dos ciclos por
    #  intersección, promediando y llevando el resultado al ciclo normalizado
    #  de 80 s.
    #  Productos comunes a todas las variantes: (origen, destino, demanda,
    #  recorrido). Con None conserva la asignación libre.
    PRODUCTOS = [
        # oN1
        ("oN1", "dK1", 11.00, "oN1_dK1_prin"),
        ("oN1", "dZ3",  6.00, "oN1_dZ3_prin"),
        ("oN1", "dA7",  3.00, "oN1_dA7_estrada"),
        ("oN1", "dA8",  2.00, "oN1_dA8_estrada"),
        ("oN1", "dA1",  1.00, "oN1_dA1_prin"),
        ("oN1", "dA8",  1.00, "oN1_dA8_prin"),
        # oK1
        ("oK1", "dN1",  6.00, "oK1_dN1_prin"),
        ("oK1", "dZ3",  5.00, "oK1_dZ3_prin"),
        ("oK1", "dA1",  2.00, "oK1_dA1_prin"),
        ("oK1", "dA3",  2.00, "oK1_dA3_prin"),
        # oZ3
        ("oZ3", "dK1",  7.00, "oZ3_dK1_prin"),
        ("oZ3", "dN1",  7.00, "oZ3_dN1_L8este"),
        ("oZ3", "dN1",  4.00, "oZ3_dN1_Andrade"),
        ("oZ3", "dA1",  2.00, "oZ3_dA1_prin"),
        ("oZ3", "dA3",  2.00, None),
        ("oZ3", "dN1",  1.00, "oZ3_dN1_prin"),
        ("oZ3", "dA1",  1.00, None),
        ("oZ3", "dG1",  0.75, None),
        ("oZ3", "dZ1",  0.25, None),
        # oA1
        ("oA1", "dK1",  3.25, "oA1_dK1_rodeo"),
        ("oA1", "dN1",  1.00, "oA1_dN1_prin"),
        ("oA1", "dZ3",  0.75, None),
        ("oA1", "dZ1",  0.75, None),
        ("oA1", "dN1",  0.25, None),
        # oA7
        ("oA7", "dZ3",  8.00, "oA7_dZ3_prin"),
        ("oA7", "dN4",  0.50, None),
        # oA3
        ("oA3", "dK1",  1.00, None),
        ("oA3", "dZ3",  1.25, None),
        ("oA3", "dE1",  0.50, None),
        ("oA3", "dN2",  0.25, None),
        # oN2
        ("oN2", "dZ2",  1.00, None),
        ("oN2", "dA1",  1.00, None),
        ("oN2", "dG1",  0.75, None),
        ("oN2", "dE1",  0.25, None),
        # oN4
        ("oN4", "dN1",  2.75, None),
        ("oN4", "dA8",  0.50, None),
        # oN8
        ("oN8", "dA8",  0.50, None),
        # oA4
        ("oA4", "dN1",  0.50, None),
        ("oA4", "dE1",  0.25, None),
        ("oA4", "dN6",  0.25, None),
        # oA5
        ("oA5", "dZ3",  1.00, "oA5_dZ3_prin"),
        # oZ1
        ("oZ1", "dZ3",  0.25, None),
        # oD1
        ("oD1", "dN2",  0.75, None),
        # oF1
        ("oF1", "dK1",  0.75, "oF1_dK1_rodeo"),
        ("oF1", "dN5",  0.25, None),
        # oN3
        ("oN3", "dA6",  0.25, None),
        # oN7
        ("oN7", "dA6",  0.25, None),
    ]

    #  Con caminos prefijados, parte de la demanda da la vuelta por Estrada y
    #  sale por donde entró. Con asignación libre esos viajes no tienen sentido,
    #  así que se cruzan los destinos: cada origen y cada destino conservan su
    #  volumen, y los dos juegos de productos mueven los mismos vehículos.
    if caminos:
        PRODUCTOS += [
            ("oN1", "dN1", 2.00, "oN1_dN1_vuelta"),
            ("oA7", "dA7", 2.00, "oA7_dA7_vuelta"),
            ("oA1", "dA1", 1.00, "oA1_dA1_vuelta"),
            ("oN2", "dN2", 1.00, "oN2_dN2_vuelta"),
            ("oZ3", "dZ3", 1.00, "oZ3_dZ3_vuelta"),
        ]
    else:
        PRODUCTOS += [
            ("oN1", "dA7", 2.00, None),
            ("oA7", "dN1", 2.00, None),
            ("oA1", "dN2", 1.00, None),
            ("oN2", "dZ3", 1.00, None),
            ("oZ3", "dA1", 1.00, None),
        ]

    K = ["k%d" % (n + 1) for n in range(len(PRODUCTOS))]
    o = {k: p[0] for k, p in zip(K, PRODUCTOS)}
    d = {k: p[1] for k, p in zip(K, PRODUCTOS)}
    D = {k: p[2] for k, p in zip(K, PRODUCTOS)}
    recorrido = {k: p[3] for k, p in zip(K, PRODUCTOS)}

    inst = Instancia(
        nombre=("bernal-este-giro" if giro_K1 else "bernal-este")
               + ("-caminos" if caminos else ""),
        descripcion="Bernal Este",
        Gamma=Gamma, H=H,
        V_ext=V_ext, esq_libres=esq_libres, X=X,
        movimientos=movimientos, P=P, tramos=tramos, kappa=kappa,
        G=G, E_pg=E_pg, L=L, U=U,
        K=K, o=o, d=d, D=D,
        fases_obligatorias={**{p: ["peatonal"] for p in PEATONAL},
                            "Z12": ["peatonal", "peatonal2"]},
    )

    # =========================================================================
    #  Caminos prefijados R_k  (sólo para la segunda variante)
    # =========================================================================
    def _por(*secuencia):
        return [(secuencia[i], secuencia[i + 1])
                for i in range(len(secuencia) - 1)]

    #  Quien viene del oeste y va a la autopista: sin el giro sigue hasta Roque
    #  Sáenz Peña, baja a Andrade y sube por Espora; con el giro dobla en K1.
    _A_DK1 = (["K1_sN", "dK1"] if giro_K1 else ["K1_sE", "L1_eO", "L1_sS", "L2_eN", "L2_sO", "K2_eE", "K2_sN", "K1_eS", "K1_sN", "dK1"])

    CAMINOS = {
        "oN1_dK1_prin": _por(
            "oN1", "N1_eE", "N1_sO", "M1_eE", "M1_sO", "L1_eE", "L1_sO",
            "K1_eE", "K1_sN", "dK1"),
        "oN1_dZ3_prin": _por(
            "oN1", "N1_eE", "N1_sO", "M1_eE", "M1_sO", "L1_eE", "L1_sS",
            "L2_eN", "L2_sO", "K2_eE", "K2_sS", "K3_eN", "K3_sS", "Z12_eN",
            "Z12_sS", "K4_eN", "K4_sS", "dZ3"),
        "oN1_dN1_vuelta": _por(
            "oN1", "N1_eE", "N1_sO", "M1_eE", "M1_sO", "L1_eE", "L1_sS",
            "L2_eN", "L2_sS", "L3", "L4", "L5", "L6", "L7_eN", "L7_sS",
            "L8_eN", "L8_sO", "Z4_eE", "Z4_sO", "K5_eE", "K5_sO", "J2_eE",
            "J2_sO", "I2", "I1_eS", "I1_sE", "J1_eO", "J1_sS", "J2_eN",
            "J2_sE", "K5_eO", "K5_sE", "Z4_eO", "Z4_sE", "L8_eO", "L8_sE",
            "M7_eO", "M7_sN", "M6", "M5", "M4_eS", "M4_sN", "M3", "M2_eS",
            "M2_sN", "M1_eS", "M1_sE", "N1_eO", "N1_sE", "dN1"),
        "oN1_dA8_estrada": _por(
            "oN1", "N1_eE", "N1_sO", "M1_eE", "M1_sO", "L1_eE", "L1_sS",
            "L2_eN", "L2_sO", "K2_eE", "K2_sS", "K3_eN", "K3_sS", "Z12_eN",
            "Z12_sS", "K4_eN", "K4_sO", "J1_eE", "J1_sS", "J2_eN", "J2_sO",
            "I2", "I1_eS", "I1_sO", "H7_eE", "H7_sO", "G7_eE", "G7_sO",
            "F6_eE", "F6_sO", "E6_eE", "E6_sO", "D6_eE", "D6_sO", "B6_eE",
            "B6_sO", "C3_eE", "C3_sO", "A7_eE", "A7_sS", "A8_eN", "A8_sO",
            "dA8"),
        "oN1_dA1_prin": _por(
            "oN1", "N1_eE", "N1_sO", "M1_eE", "M1_sO", "L1_eE", "L1_sO",
            "K1_eE", "K1_sO", "H1_eE", "H1_sO", "Z2_eE", "Z2_sO", "G1_eE",
            "G1_sO", "F1_eE", "F1_sO", "E1_eE", "E1_sO", "D1_eE", "D1_sO",
            "B1_eE", "B1_sO", "Z1_eE", "Z1_sO", "A1_eE", "A1_sO", "dA1"),
        "oN1_dA8_prin": _por(
            "oN1", "N1_eE", "N1_sO", "M1_eE", "M1_sO", "L1_eE", "L1_sS",
            "L2_eN", "L2_sO", "K2_eE", "K2_sS", "K3_eN", "K3_sS", "Z12_eN",
            "Z12_sS", "K4_eN", "K4_sO", "J1_eE", "J1_sO", "I1_eE", "I1_sO",
            "H7_eE", "H7_sO", "G7_eE", "G7_sO", "F6_eE", "F6_sO", "E6_eE",
            "E6_sO", "D6_eE", "D6_sO", "B6_eE", "B6_sO", "C3_eE", "C3_sO",
            "A7_eE", "A7_sS", "A8_eN", "A8_sO", "dA8"),
        "oK1_dN1_prin": _por(
            "oK1", "K1_eN", "K1_sE", "L1_eO", "L1_sE", "M1_eO", "M1_sE",
            "N1_eO", "N1_sE", "dN1"),
        "oK1_dZ3_prin": _por(
            "oK1", "K1_eN", "K1_sS", "K2_eN", "K2_sS", "K3_eN", "K3_sS",
            "Z12_eN", "Z12_sS", "K4_eN", "K4_sS", "dZ3"),
        "oK1_dA1_prin": _por(
            "oK1", "K1_eN", "K1_sO", "H1_eE", "H1_sO", "Z2_eE", "Z2_sO",
            "G1_eE", "G1_sO", "F1_eE", "F1_sO", "E1_eE", "E1_sO", "D1_eE",
            "D1_sO", "B1_eE", "B1_sO", "Z1_eE", "Z1_sO", "A1_eE", "A1_sO",
            "dA1"),
        "oK1_dA3_prin": _por(
            "oK1", "K1_eN", "K1_sO", "H1_eE", "H1_sO", "Z2_eE", "Z2_sO",
            "G1_eE", "G1_sO", "F1_eE", "F1_sO", "E1_eE", "E1_sO", "D1_eE",
            "D1_sO", "B1_eE", "B1_sO", "Z1_eE", "Z1_sO", "A1_eE", "A1_sS",
            "A2_eN", "A2_sS", "A3_eN", "A3_sO", "dA3"),
        "oZ3_dK1_prin": _por(
            "oZ3", "K4_eS", "K4_sN", "Z12_eS", "Z12_sN", "K3_eS", "K3_sN",
            "K2_eS", "K2_sN", "K1_eS", "K1_sN", "dK1"),
        "oZ3_dN1_L8este": _por(
            "oZ3", "K4_eS", "K4_sE", "Z5", "L7_eO", "L7_sS", "L8_eN",
            "L8_sE", "M7_eO", "M7_sN", "M6", "M5", "M4_eS", "M4_sN", "M3",
            "M2_eS", "M2_sN", "M1_eS", "M1_sE", "N1_eO", "N1_sE", "dN1"),
        "oZ3_dN1_Andrade": _por(
            "oZ3", "K4_eS", "K4_sN", "Z12_eS", "Z12_sN", "K3_eS", "K3_sN",
            "K2_eS", "K2_sE", "L2_eO", "L2_sE", "M2_eO", "M2_sN", "M1_eS",
            "M1_sE", "N1_eO", "N1_sE", "dN1"),
        "oZ3_dA1_prin": _por(
            "oZ3", "K4_eS", "K4_sN", "Z12_eS", "Z12_sN", "K3_eS", "K3_sN",
            "K2_eS", "K2_sN", "K1_eS", "K1_sO", "H1_eE", "H1_sO", "Z2_eE",
            "Z2_sO", "G1_eE", "G1_sO", "F1_eE", "F1_sO", "E1_eE", "E1_sO",
            "D1_eE", "D1_sO", "B1_eE", "B1_sO", "Z1_eE", "Z1_sO", "A1_eE",
            "A1_sO", "dA1"),
        "oZ3_dN1_prin": _por(
            "oZ3", "K4_eS", "K4_sN", "Z12_eS", "Z12_sN", "K3_eS", "K3_sN",
            "K2_eS", "K2_sN", "K1_eS", "K1_sE", "L1_eO", "L1_sE", "M1_eO",
            "M1_sE", "N1_eO", "N1_sE", "dN1"),
        "oZ3_dZ3_vuelta": _por(
            "oZ3", "K4_eS", "K4_sE", "Z5", "L7_eO", "L7_sS", "L8_eN",
            "L8_sO", "Z4_eE", "Z4_sO", "K5_eE", "K5_sO", "J2_eE", "J2_sO",
            "I2", "I1_eS", "I1_sE", "J1_eO", "J1_sE", "K4_eO", "K4_sS",
            "dZ3"),
        "oA1_dK1_rodeo": _por(
            "oA1", "A1_eO", "A1_sE", "Z1_eO", "Z1_sE", "B1_eO", "B1_sE",
            "D1_eO", "D1_sE", "E1_eO", "E1_sE", "F1_eO", "F1_sE", "G1_eO",
            "G1_sE", "Z2_eO", "Z2_sE", "H1_eO", "H1_sE", "K1_eO",
            *_A_DK1),
        "oA1_dN1_prin": _por(
            "oA1", "A1_eO", "A1_sE", "Z1_eO", "Z1_sE", "B1_eO", "B1_sE",
            "D1_eO", "D1_sE", "E1_eO", "E1_sE", "F1_eO", "F1_sE", "G1_eO",
            "G1_sE", "Z2_eO", "Z2_sE", "H1_eO", "H1_sE", "K1_eO", "K1_sE",
            "L1_eO", "L1_sE", "M1_eO", "M1_sE", "N1_eO", "N1_sE", "dN1"),
        "oA1_dA1_vuelta": _por(
            "oA1", "A1_eO", "A1_sS", "A2_eN", "A2_sS", "A3_eN", "A3_sS",
            "A4_eN", "A4_sS", "A5_eN", "A5_sS", "A6_eN", "A6_sS", "A7_eN",
            "A7_sE", "C3_eO", "C3_sE", "B6_eO", "B6_sE", "D6_eO", "D6_sE",
            "E6_eO", "E6_sE", "F6_eO", "F6_sE", "G7_eO", "G7_sE", "H7_eO",
            "H7_sE", "I1_eO", "I1_sE", "J1_eO", "J1_sS", "J2_eN", "J2_sO",
            "I2", "I1_eS", "I1_sO", "H7_eE", "H7_sO", "G7_eE", "G7_sO",
            "F6_eE", "F6_sO", "E6_eE", "E6_sO", "D6_eE", "D6_sO", "B6_eE",
            "B6_sO", "C3_eE", "C3_sO", "A7_eE", "A7_sN", "A6_eS", "A6_sN",
            "A5_eS", "A5_sN", "A4_eS", "A4_sN", "A3_eS", "A3_sN", "A2_eS",
            "A2_sN", "A1_eS", "A1_sO", "dA1"),
        "oA7_dZ3_prin": _por(
            "oA7", "A7_eO", "A7_sE", "C3_eO", "C3_sE", "B6_eO", "B6_sE",
            "D6_eO", "D6_sE", "E6_eO", "E6_sE", "F6_eO", "F6_sE", "G7_eO",
            "G7_sE", "H7_eO", "H7_sE", "I1_eO", "I1_sE", "J1_eO", "J1_sE",
            "K4_eO", "K4_sS", "dZ3"),
        "oA7_dA7_vuelta": _por(
            "oA7", "A7_eO", "A7_sE", "C3_eO", "C3_sE", "B6_eO", "B6_sE",
            "D6_eO", "D6_sE", "E6_eO", "E6_sE", "F6_eO", "F6_sE", "G7_eO",
            "G7_sE", "H7_eO", "H7_sE", "I1_eO", "I1_sE", "J1_eO", "J1_sS",
            "J2_eN", "J2_sO", "I2", "I1_eS", "I1_sO", "H7_eE", "H7_sO",
            "G7_eE", "G7_sO", "F6_eE", "F6_sO", "E6_eE", "E6_sO", "D6_eE",
            "D6_sO", "B6_eE", "B6_sO", "C3_eE", "C3_sO", "A7_eE", "A7_sO",
            "dA7"),
        "oN2_dN2_vuelta": _por(
            "oN2", "N2_eE", "N2_sO", "M2_eE", "M2_sO", "L2_eE", "L2_sS",
            "L3", "L4", "L5", "L6", "L7_eN", "L7_sS", "L8_eN", "L8_sO",
            "Z4_eE", "Z4_sO", "K5_eE", "K5_sO", "J2_eE", "J2_sO", "I2",
            "I1_eS", "I1_sE", "J1_eO", "J1_sS", "J2_eN", "J2_sE", "K5_eO",
            "K5_sE", "Z4_eO", "Z4_sE", "L8_eO", "L8_sE", "M7_eO", "M7_sN",
            "M6", "M5", "M4_eS", "M4_sN", "M3", "M2_eS", "M2_sE", "N2_eO",
            "N2_sE", "dN2"),
        "oA5_dZ3_prin": _por(
            "oA5", "A5_eO", "A5_sS", "A6_eN", "A6_sS", "A7_eN", "A7_sE",
            "C3_eO", "C3_sE", "B6_eO", "B6_sE", "D6_eO", "D6_sE", "E6_eO",
            "E6_sE", "F6_eO", "F6_sE", "G7_eO", "G7_sE", "H7_eO", "H7_sE",
            "I1_eO", "I1_sE", "J1_eO", "J1_sE", "K4_eO", "K4_sS", "dZ3"),
        "oF1_dK1_rodeo": _por(
            "oF1", "F1_eN", "F1_sE", "G1_eO", "G1_sE", "Z2_eO", "Z2_sE",
            "H1_eO", "H1_sE", "K1_eO",
            *_A_DK1),
        "oN1_dA7_estrada": _por(
            "oN1", "N1_eE", "N1_sO", "M1_eE", "M1_sO", "L1_eE", "L1_sS",
            "L2_eN", "L2_sO", "K2_eE", "K2_sS", "K3_eN", "K3_sS", "Z12_eN",
            "Z12_sS", "K4_eN", "K4_sO", "J1_eE", "J1_sS", "J2_eN", "J2_sO",
            "I2", "I1_eS", "I1_sO", "H7_eE", "H7_sO", "G7_eE", "G7_sO",
            "F6_eE", "F6_sO", "E6_eE", "E6_sO", "D6_eE", "D6_sO", "B6_eE",
            "B6_sO", "C3_eE", "C3_sO", "A7_eE", "A7_sO", "dA7"),
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
BERNAL_ESTE = {
    "bernal-este": bernal_este,
    "bernal-este-caminos": lambda: bernal_este(caminos=True),
    "bernal-este-giro": lambda: bernal_este(giro_K1=True),
    "bernal-este-giro-caminos": lambda: bernal_este(caminos=True, giro_K1=True),
}