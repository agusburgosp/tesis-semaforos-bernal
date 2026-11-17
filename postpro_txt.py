import re
from modelo import preparar, construir, resolver, extraer, verificar
from postprocesamiento import adelantar_esperas, comparar
from bernal_este import bernal_este
from bernal_centro import bernal_centro

def leer_plan(archivo):
    plan, p = {}, None
    with open(archivo, encoding="utf-8") as f:
        for linea in f:
            m = re.match(r"\s*Intersección (\S+?):", linea)
            if m:
                p = m.group(1)
                continue
            m = re.match(r"\s*z=([01])\s+(\S+)\s+([V.\-]+)", linea)
            if m and p:
                plan[p, m.group(2)] = (int(m.group(1)), m.group(3))
    return plan


plan = leer_plan("este_giro_caminos.txt")
dat = preparar(bernal_este(caminos=True, giro_K1=True)) #caminos=True, giro_K1=True))
m, v = construir(dat)

for (p, g), var in v["z"].items():
    var.LB = var.UB = plan[p, g][0]

for (p, g, h), var in v["y"].items():
    z, patron = plan[p, g]
    valor = 1 if z == 1 and patron[h] == "V" else 0
    var.LB = var.UB = valor

resolver(m, tiempo_limite=300)
if m.SolCount == 0:
    raise SystemExit("Sin solución: el plan no entra en esta versión de la instancia.")
print("Objetivo con el plan fijo:", m.ObjVal)

sol = extraer(v)
print("Violaciones antes:", verificar(dat, sol))

nueva = adelantar_esperas(dat, sol, verbose=True)
comparar(dat, sol, nueva)
print("Violaciones después:", verificar(dat, nueva))

# Figuras y gif
from visual import corredor_automatico, graficar
resumen = {"datos": dat, "solucion": nueva}
graficar(resumen, corredor=corredor_automatico(dat.inst, dat),
         vehiculos=True, sufijo="_postprocesado")