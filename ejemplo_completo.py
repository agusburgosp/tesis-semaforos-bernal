"""
Ejemplo con TODOS los parámetros escritos de forma explícita,
para tener a mano qué se puede tocar en cada etapa.

    parte 1   generar_red       -> la geometría: calles, sentidos, semáforos, fases
    parte 2   generar_demandas  -> el tiempo y las demandas
    resultado                   -> una Instancia lista para el solver

    python ejemplo_completo.py
"""

from generador_red import generar_red, describir, dibujar, dibujar_esquina
from generador_demandas import generar_demandas, describir_demandas


# #############################################################################
#  PARTE 1: LA RED
# #############################################################################
red = generar_red(

    # =========================================================================
    #  TAMAÑO DE LA MALLA
    # =========================================================================
    filas=10,             # cantidad de calles horizontales
    columnas=12,          # cantidad de calles verticales

    # =========================================================================
    #  AVENIDAS VERTICALES (columnas)
    # =========================================================================
    #  doble : doble mano, semáforo en TODAS sus esquinas
    #  tipo1 : mano única, semáforo CADA DOS cuadras
    #  tipo2 : mano única, semáforo en CADA cuadra
    #
    #  Se colocan en ese orden: primero las de doble mano, después las tipo 1 y
    #  por último las tipo 2. Acá caen en las columnas B (doble) y D (tipo1).
    avenidas_v=dict(doble=3, tipo1=0, tipo2=0),
    separacion_v=4,      # cuadras entre una avenida vertical y la siguiente
    inicio_v=1,          # columna donde va la primera (0 = la del extremo oeste)

    # =========================================================================
    #  AVENIDAS HORIZONTALES (filas)
    # =========================================================================
    #  Acá cae en la fila 2 (doble).
    avenidas_h=dict(doble=3, tipo1=0, tipo2=1),
    separacion_h=2,      # cuadras entre una avenida horizontal y la siguiente
    inicio_h=1,          # fila donde va la primera (0 = la del extremo norte)

    # =========================================================================
    #  GEOMETRÍA Y CAPACIDADES DE LOS ARCOS
    # =========================================================================
    cuadra=15.0,         # tiempo de tránsito de una cuadra [s]; 100 m a ~24 km/h
    u_calle=1.0,         # capacidad de un tramo de calle [veh/s]
    u_recto=1.0,         # capacidad de un movimiento recto [veh/s]
    u_giro=0.5,          # capacidad de un giro [veh/s]

    # =========================================================================
    #  CAPACIDAD DE ALMACENAMIENTO DE CADA TIPO DE NODO  (kappa_i)
    # =========================================================================
    kappa_acceso=20.0,           # accesos a una esquina: acá se forman las colas
    kappa_libre=20.0,            # esquinas sin semáforo (un solo nodo)
    kappa_salida=0.0,            # salidas de esquina: el flujo ya cruzó
    kappa_ingreso=float("inf"),  # ingresos: la cola aguarda fuera de la zona
    kappa_egreso=0.0,            # egresos: el flujo abandona la red

    # =========================================================================
    #  FASES
    # =========================================================================
    #  Cuántas copias de cada configuración se incluyen en G_p. Con 2, cada
    #  configuración aparece dos veces con distinto nombre y puede recibir dos
    #  bloques de verde separados; la restricción (22) impide que queden
    #  contiguos. Con 1 no hay repeticiones.
    copias_por_fase=2,

    # =========================================================================
    #  RETOQUES A MANO SOBRE LA RED
    # =========================================================================

    # --- forzar el sentido de una línea -------------------------------------
    #  Por defecto alternan: columnas pares bajan, impares suben; filas pares
    #  van al este, impares al oeste. Un valor de dos letras, como "SN" o "EO",
    #  hace la línea de doble mano.
    sentidos_v={},
    sentidos_h={},

    # --- agregar o quitar movimientos de una esquina ------------------------
    #  El criterio automático es: recto y giro a la derecha siempre; giro a la
    #  izquierda sólo si no cruza ninguna corriente. En B2 se cruzan dos
    #  avenidas de doble mano, así que no queda ninguna izquierda. Acá se
    #  habilita a mano la izquierda de la rama oeste hacia el norte.
    movimientos_extra={"B2": [("O", "N")]},
    movimientos_quitar={},

    # --- agregar o reemplazar fases -----------------------------------------
    #  Las fases automáticas son: una por rama de acceso, más una por cada par
    #  de ramas opuestas entrantes (la "avenida completa"). Toda fase debe usar
    #  movimientos que existan en esa esquina.
    fases_extra={"B2": {"Ocompleta": [("O", "E"), ("O", "S"), ("O", "N")]}},

    #  fases_reemplazo cambia TODO el catálogo de una esquina. Entre las fases
    #  que se pongan tienen que quedar cubiertos todos sus movimientos.
    fases_reemplazo={},

    # --- semaforizar o desemaforizar esquinas puntuales ---------------------
    semaforos_extra=[],
    semaforos_quitar=[],

    # =========================================================================
    #  NOMBRE
    # =========================================================================
    #  Se usa para el archivo del mapa: Visuales red/<nombre>_mapa.png
    nombre="bernal_grande",
)

describir(red)


# #############################################################################
#  PARTE 2: EL TIEMPO Y LAS DEMANDAS
# #############################################################################
inst = generar_demandas(

    red,                 # la red de la parte 1

    # =========================================================================
    #  NIVEL DE DEMANDA
    # =========================================================================
    #  Los tres niveles son atajos sobre dos perillas independientes:
    #
    #      nivel         cobertura   saturación
    #      poca             0.40        0.20
    #      intermedia       0.70        0.50
    #      completa         1.00        0.75
    #
    #  cobertura  : qué fracción de los nodos de ingreso genera demanda
    #  saturacion : qué fracción de la capacidad efectiva se carga
    #
    #  Poner cobertura o saturacion a mano PISA al nivel. Combinaciones que los
    #  presets no cubren: cobertura=1.0 con saturacion=0.2 da muchos productos
    #  con poco volumen; cobertura=0.3 con saturacion=0.9, pocos pero ahogados.
    nivel="intermedia",
    cobertura=None,              # 0..1, o None para usar la del nivel
    saturacion=0.75,             # 0..1, o None para usar la del nivel
    productos_por_origen=None,   # cuántos destinos por origen activo

    # =========================================================================
    #  TIEMPO
    # =========================================================================
    #  Delta = Gamma / H. Se comprueba que el tiempo de una cuadra sea múltiplo
    #  de Delta: con Gamma = 60 y cuadra = 15, H tiene que ser múltiplo de 4.
    Gamma=60.0,          # duración del período [s]
    H=12,                # cantidad de capas temporales
    L=2,                 # duración mínima de una fase [intervalos]
    U=8,                 # duración máxima de una fase [intervalos]

    # =========================================================================
    #  SESGO HACIA LAS AVENIDAS
    # =========================================================================
    #  El sesgo está en los EXTREMOS de cada demanda, no en su recorrido:
    #
    #      puntaje = 1 + peso_avenida * (puntas sobre avenida) / 2
    #                  + peso_semaforo * (puntas que dan a un semáforo) / 2
    #
    #  Ese puntaje decide qué ingresos se activan cuando la cobertura es
    #  parcial, qué destino se sortea para cada origen y cuánto volumen recibe.
    #  Con peso_avenida = 0 no hay sesgo y las demandas se reparten parejo.
    peso_avenida=3.0,
    peso_semaforo=1.5,

    # =========================================================================
    #  CAMINOS PREFIJADOS  (segunda variante del modelo)
    # =========================================================================
    #  Con caminos=True se fija el recorrido de una parte de las demandas. Se
    #  eligen primero las PASANTES de una avenida, es decir las que entran por
    #  una punta y salen por la otra, y después las de mayor puntaje. El resto
    #  conserva la asignación libre.
    caminos=False,
    fraccion_prefijada=0.7,

    # =========================================================================
    #  OTROS
    # =========================================================================
    semilla=1,           # fija los pares origen-destino: la instancia es reproducible
    nombre=None,         # por defecto "<nombre de la red>-<nivel>"
    descripcion=None,
)

describir_demandas(inst, red)


# #############################################################################
#  LISTO PARA EL SOLVER
# #############################################################################
#  ``inst`` es una Instancia completa. Se le puede pasar directo a ejecutar:
#
#      from modelo import ejecutar
#      r = ejecutar(inst, tiempo_limite=600, gap=0.01)
#
#  Y a las figuras:
#
#      from visual import graficar, corredor_automatico
#      graficar(r, corredor=corredor_automatico(r["datos"].inst, r["datos"]),
#               vehiculos=True)
#
#  Para correrla desde main.py, agregala al diccionario INSTANCIAS de
#  instancias.py:
#
#      from generador_red import generar_red
#      from generador_demandas import generar_demandas
#
#      def bernal(caminos: bool = False):
#          red = generar_red(filas=4, columnas=6,
#                            avenidas_v=dict(doble=1, tipo1=1),
#                            separacion_v=2, inicio_v=1,
#                            avenidas_h=dict(doble=1), inicio_h=1,
#                            nombre="bernal_centro")
#          return generar_demandas(red, nivel="intermedia", semilla=1,
#                                  caminos=caminos)
#
#      INSTANCIAS["bernal"] = bernal
#      INSTANCIAS["bernal-caminos"] = lambda: bernal(caminos=True)
#
#  y después:  python main.py bernal --figuras

print()
print("=" * 70)
print("LA INSTANCIA QUEDÓ ARMADA")
print("=" * 70)
print("  nombre      : %s" % inst.nombre)
print("  Gamma, H    : %.0f s, %d capas de %.1f s"
      % (inst.Gamma, inst.H, inst.Gamma / inst.H))
print("  semaforos   : %d" % len(inst.P))
print("  productos   : %d" % len(inst.K))
print("  con camino  : %s" % (len(inst.R) if inst.R else "ninguno"))
print()
print("  Para resolverla:")
print("      from modelo import ejecutar")
print("      ejecutar(inst)")