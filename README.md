# Optimización de una red de semáforos: caso de estudio en Bernal

Código de la tesis *Optimización de una red de semáforos mediante técnicas de
Ciencia de Datos: Caso de estudio en Bernal*.

El modelo decide de manera conjunta la programación de los semáforos de una
red urbana y la asignación del tránsito, con el objetivo de minimizar el
tiempo total de viaje. Se formula como un programa lineal entero mixto sobre
una red cíclicamente expandida en el tiempo, a partir de la formulación de
Köhler y Strehler, con extensiones para representar una red real: selección
de fases desde un catálogo, repetición de configuraciones dentro del período,
fases peatonales obligatorias y caminos prefijados para parte de la demanda.

Incluye además un procedimiento de posprocesamiento que reubica las colas en
los accesos semaforizados sin modificar el valor objetivo, y un generador de
instancias para estudiar cómo escala el modelo.

## Requisitos

- Python 3.10 o posterior
- [Gurobi](https://www.gurobi.com) 13 con una licencia válida (existen
  licencias académicas gratuitas) y su paquete de Python, `gurobipy`
- `numpy` y `matplotlib` para las figuras y animaciones

```
pip install gurobipy numpy matplotlib
```

## Archivos

| Archivo | Contenido |
|---|---|
| `modelo.py` | Datos de una instancia, construcción de la red expandida, modelo de Gurobi, extracción y verificación de la solución |
| `main.py` | Resuelve el modelo completo sobre una instancia |
| `postprocesamiento.py` | Reubicación de las colas (adelantamiento de las esperas) |
| `instancias.py` | Instancias de prueba: corredor y red |
| `bernal_centro.py` | Instancia de Bernal Centro |
| `bernal_este.py` | Instancia de Bernal Este |
| `plan_real.py` | Planes semafóricos observados en Bernal Centro y Bernal Este |
| `modelo_real.py` | Resolución del flujo con un plan semafórico dado |
| `main_real.py` | Corre las zonas de Bernal con el plan observado y aplica la reubicación |
| `postpro_txt.py` | Fija un plan obtenido a partir de una salida guardada y aplica la reubicación |
| `generador_red.py` | Generador de redes viales para las instancias de prueba |
| `generador_demandas.py` | Generador de demandas (productos origen-destino) sobre una red generada |
| `ejemplo_red.py` | Ejemplo de construcción de una red con el generador |
| `experimentos.py` | Experimentos con instancias generadas que varían un único factor |
| `experimentos_2.py` | Experimentos que comparan la cantidad de semáforos y el tamaño de la red |
| `visual.py` | Figuras y animaciones de las soluciones |
| `regraficar.py` | Vuelve a generar las figuras a partir de resultados ya obtenidos |
| `ejemplo_completo.py` | Ejemplo de uso de punta a punta del generador |

## Licencia

MIT. Ver el archivo `LICENSE`.
