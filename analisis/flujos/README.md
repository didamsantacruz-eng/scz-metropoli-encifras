# Flujos de la Región Metropolitana — composición de cada relación

Todo lo de acá se calcula desde el **CPV 2024 crudo**, no desde los archivos ya
publicados en `docs/datos/`.

## La cadena (correr en orden)

| paso | script | qué hace | salida |
|---|---|---|---|
| 1 | `01_base_metro.py` | una pasada por `Persona_CPV-2024.csv` (3,1 GB) + toda la Vivienda, para los nueve municipios | `base9_metro.parquet` |
| 2 | `02_riqueza_y_privacion.py` | índice de riqueza por ACP, privaciones y capacidad de pago | `base9_metro_nivelvida.parquet` |
| 3 | `03_composicion.py` | las seis familias de descriptivos por cada relación | `salida/*.json` (7 archivos) |
| 4 | `04_paquete_web.py` | recorta y arma el paquete para la página | `web/flujos_metro.json` |
| 5 | `05_armar_pagina.py` | inyecta datos y secciones en la plantilla | `web/quien_se_mueve.html` |

Los parquet viven en `C:\Users\HP\cpv2024\` (fuera del repo: son microdato).
`salida/`, `web/flujos_metro.json` y `web/quien_se_mueve.html` están en `.gitignore`:
son 19 MB regenerables y `.git` ya pesa 611 MB.

**El HTML servible NO se edita a mano.** Se edita `web/plantilla.html` (estructura,
estilos, la ficha) o `web/secciones.js` (las siete secciones) y se corre el paso 5.

## Los tres universos, que NO se suman entre sí

| dimensión | variable | qué es | universo |
|---|---|---|---|
| nacimiento | `p35_lugnac` | stock sin fecha | 2.282.770 |
| residencia | `p37_lugres5` | flujo fechado 2019→2024 | 2.109.515 |
| trabajo | `p52_mov` | desplazamiento diario | 1.043.524 |

## Lo que hay que saber antes de tocar esto

**⛔ Dos códigos que parecen geografía y no lo son.** `999995` (lugar de trabajo) y
`999999` (nacimiento y residencia-5) son **«Sin especificar»**. Con `zfill(6)` el
segundo pasa el patrón `XX9999` y sale clasificado como **departamento 99**: son
27.720 personas que aparecerían «trabajando en otro municipio» sin trabajar en
ninguno declarado. Ojo que `099999` **sí** es geografía —Pando sin precisar—, así que
el filtro va sobre el código crudo, no sobre los dos primeros dígitos.

**⛔ Los parciales no se tiran.** `XX9999` y `XXYY99` son códigos válidos del INE.
Son **43.970** a nivel departamento y **35.341** a nivel provincia: 79.311 personas.
Cada dimensión guarda su `*_nivel` para que la precisión sea un dato explícito.

**⛔ `p28_cn` pregunta por el registro civil BOLIVIANO.** Que alguien nacido en otro
país conteste «no» es la respuesta correcta y esperable, **no una carencia**.
Publicarlo como privación convierte el enunciado de una pregunta en un problema
social inexistente. El indicador que sí dice algo es `p29_ci`, la cédula.

**⛔ `p32_pueblos` no es un sí/no de indígena.** Su categoría 1 es *Afroboliviano* y
la 98 «no se autoidentifica». Medirlo como `== "1"` da 0,2% y es basura.

**⛔ El mismo universo arriba y abajo.** Cada indicador restringido se construye como
una columna con `NaN` fuera de su universo, para que el promedio use el mismo
denominador que su numerador. Ése fue el error que dio porcentajes de ocupados de
100,8% y 102,1%.

**El techo de granularidad.** `act_eco_2d_13` trae 23 categorías y —pese al nombre—
son las **secciones CIIU A–U**, no divisiones a dos dígitos. `ocu_1d_13` trae 12.
`p50_semp` **no** es tamaño de empresa: sus categorías son idénticas a `p50_catocu_13`.
La textura fina sale de **cruzar**, no de bajar de nivel.

**El lugar de trabajo no baja del municipio**, ni la residencia anterior. No hay zona,
UV, barrio ni distrito. Y no hay ninguna pregunta de modo de transporte, tiempo de
viaje ni hora de salida.

**El censo no pregunta ingreso.** Ninguna de las 114 variables de persona ni de las 44
de vivienda. El nivel de vida se mide con el índice de riqueza del paso 2, que es
**ordinal**: ordena hogares, no expresa bolivianos.

**Leer Vivienda entera junto con las 2,28 M personas revienta por memoria.** Va por
trozos, y así está escrito.

## Lo que falta

- **Media conmutación.** Sólo se ve a quien *vive* en los nueve. Quien vive fuera de
  la región y viene a trabajar adentro (~16.700 personas) requiere otra pasada por el
  CSV nacional filtrando `mun_lab_cod ∈ los nueve` con residencia afuera.
- **Ingreso en bolivianos.** Estimación por áreas pequeñas (Elbers, Lanjouw & Lanjouw
  2003) con el microdato de la Encuesta de Hogares de ANDA. Declarado, sin hacer.

## Los scripts viejos

`auditar_flujos.py`, `perfil_socioec.py`, `conmutacion2.py`, `lugar_trabajo.py` y
`armar_auditoria.py` son de la auditoría del 2026-08-20 y quedan como respaldo de
esa hoja. **La cadena 01→05 los reemplaza** y corrige dos de sus resultados.
