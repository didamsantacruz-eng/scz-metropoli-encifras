# Sistema de generación masiva de gráficos

**Qué produce:** 375 láminas PNG de 3200×1800 —213 municipales y 162 por
manzana— más el índice navegable que las presenta, en `docs/banco/`.

**Para quién es este documento:** para quien tenga que regenerar el banco,
agregarle indicadores o cambiarle el diseño, incluido un agente que llegue al
repo sin contexto previo. Todo lo que dice está medido contra el código, no
recordado.

---

## 1. Lo que hay que entender antes de tocar nada

El banco **no tiene datos propios**. Lee el mismo catálogo que sirve al tablero
interactivo, y ésa es toda su razón de ser: la lámina y la pantalla tienen que
decir lo mismo del mismo dato. Si el banco pintara con su propia escala, un
municipio podría leerse «alto» en la lámina y «medio» en el mapa, y quien vio
las dos cosas no sabría a cuál creerle.

```
docs/datos/catalogo_municipal.json ─┐
docs/datos/municipios_municipal.json ├─→ motor/lamina_municipal.py → docs/banco/municipal/*.png
docs/datos/geo_*.json ──────────────┘

docs/datos/catalogo_manzana.json ───┐
docs/datos/dat_*.json ──────────────├─→ motor/lamina_manzana.py   → docs/banco/manzana/*.png
docs/datos/geo_*.json ──────────────┘

docs/banco/**/*.png ──────────────────→ motor/armar_sitio.py      → docs/banco/index.html + mini/
assets/paleta.json ───────────────────→ motor/estilo.py           (identidad compartida)
```

**Agregar un indicador al banco no se hace acá.** Se hace en el catálogo
(`catalogo/armar_tableros.py`) y el banco se entera solo: el motor recorre lo
que el catálogo declara y `armar_sitio.py` recorre lo que hay en el disco.

---

## 2. Regenerar todo

```bash
python sistema-graficos/generar_todo.py
```

Corre los cuatro pasos en orden y se planta en el primero que falle. Acepta
`--solo municipal`, `--solo manzana`, `--solo sitio` y `--saltear-paleta`.

Los pasos sueltos, si hace falta:

```bash
python scripts/paleta.py --verificar                      # 0 = tablero y banco alineados
python sistema-graficos/motor/lamina_municipal.py --todas
python sistema-graficos/motor/lamina_manzana.py --todas
python sistema-graficos/motor/armar_sitio.py
```

Una sola lámina, que es lo que conviene al iterar diseño:

```bash
python sistema-graficos/motor/lamina_municipal.py --indicador pct_edu_superior
python sistema-graficos/motor/lamina_manzana.py --municipio santa_cruz_de_la_sierra \
                                                --indicador pct_alcantarillado
```

**Requisitos:** `matplotlib`, `Pillow` (sólo para las miniaturas) y las fuentes
de `assets/fuentes/` (Inter en cuatro pesos + Newsreader variable). Sin las
fuentes la lámina se genera igual, con la tipografía por defecto: falla en
silencio y se ve mal, no se rompe.

**Costo:** las 375 láminas son ~233 MB en disco y la corrida completa tarda
bastante. Para probar un cambio de diseño, una sola lámina alcanza.

---

## 3. Los archivos

| archivo | qué es |
|---|---|
| `generar_todo.py` | el único comando: encadena los cuatro pasos con verificación |
| `motor/estilo.py` | la identidad: rampa, fuentes, tamaños, el gris de «sin dato». Lo importan los dos generadores |
| `motor/lamina_municipal.py` | una lámina = **un indicador**, los nueve municipios, con la mancuerna 2012→2024 |
| `motor/lamina_manzana.py` | una lámina = **un municipio por dentro**, manzana por manzana. Sólo 2024 |
| `motor/armar_sitio.py` | el índice navegable + las miniaturas de 400 px |
| `motor/plantilla_sitio.html` | el molde del índice |

Las dos unidades son distintas a propósito: arriba se comparan municipios entre
sí, abajo se mira uno por dentro. Por eso salen 213 láminas municipales (una por
indicador) y 162 por manzana (una por municipio × indicador).

---

## 4. ⚠️ Las cuatro invariantes que no se pueden romper

Están escritas en el encabezado de `motor/lamina_municipal.py`; se repiten acá
porque son las que producen errores que **no se ven** en la lámina resultante.

**1 · El agregado regional viene DECLARADO, no se recalcula.**
`catalogo/armar_tableros.py` pondera cada indicador por SU PROPIO universo —un
porcentaje de viviendas por viviendas, no por personas— y lo embarca en el
catálogo como `region`. El tablero ya cometió el error de recalcularlo
ponderando todo por población: `emigrantes_x1000` salía 26,4‰ en vez de 28,5‰,
un 8% de error, y la lámina se veía perfecta.

**2 · Ese agregado no vale para un conteo** (`agg == "suma"`). Promediar
población ponderando por población da Σp²/Σp, que es «el tamaño del municipio de
la persona promedio» y no le sirve a nadie. La magnitud regional de un conteo es
la SUMA, y el centro de la rampa es la MEDIANA de los nueve.
→ *Este error tiene un hermano un nivel más abajo, con hogares en vez de
municipios: ver la sección 5 del README de `dinamica-metropolitana/`.*

**3 · La comparación con 2012 sólo si el catálogo la declara** (`s12`). Hay 63
indicadores donde el dato de los dos censos existe pero los universos no son el
mismo, y el catálogo lo dice en `w12`. Restar dos números que se llaman igual
pero no miden lo mismo es el error de siempre: **la presencia se mide, la
comparabilidad se declara.**

**4 · La rampa se declara una sola vez, en `assets/paleta.json`.** Acá vivió una
segunda implementación del mismo criterio y llegaron a tener tres diferencias
—la bisagra, los neutros y la saturación—. Hoy `motor/estilo.py` lee el JSON y
`scripts/paleta.py` lo inyecta en el tablero. **`python scripts/paleta.py
--verificar` falla si alguno se desvía**, y ése es el chequeo que hay que correr
antes de publicar.

---

## 5. El contrato con el catálogo

Cada indicador del catálogo trae estos campos, y son los que el motor lee:

| campo | qué es | si falta |
|---|---|---|
| `key` | la clave; **es también el nombre del PNG** (`docs/banco/municipal/<key>.png`) | no hay lámina |
| `label` | el título de la lámina | — |
| `unit` | `%`, `‰`, `años`, `Bs`… decide el formato de la cifra | se imprime crudo |
| `desc` | la definición: qué busca medir. Ver `catalogo/definiciones_*.py` | se cae al título |
| `dir` | hacia qué lado está «lo bueno»; invierte la rampa para que el verde quede siempre del lado bueno | asume mayor = mejor |
| `agg` | `media` o `suma`; decide cómo se resume la región (ver invariante 2) | asume media |
| `s12` | si la serie 2012 es comparable (ver invariante 3) | sin mancuerna |
| `w12` | el motivo declarado de por qué no lo es; se imprime en la lámina | — |

La correspondencia lámina ↔ indicador es **1 a 1 por la clave**, verificado: los
213 indicadores censales municipales tienen su PNG y no sobra ninguno. Por eso
el tablero puede armar el enlace «Descargar este mapa» sin un índice aparte.

**El bloque fiscal (30 indicadores) queda fuera del banco a propósito:** no vive
en `municipal[]` sino en `fiscal.json`, como serie 2016–2025, y pide otra lámina
que todavía no existe.

---

## 6. ⚠️ Estado conocido: el índice tiene la rampa oscura vieja

**Correr `armar_sitio.py` sobre el repo tal como está produce un diff en
`docs/banco/index.html`, y ese diff es correcto.** No es ruido ni un bug: es una
diferencia real que todavía no se propagó.

El 2026-08-26 se cambió la rampa del **modo oscuro** por pedido de Carlos —«que
sea el color tal cual, pero más intenso, no tan transparente»—, y quedó idéntica
a la clara (`realce_oscuro = 0`). El tablero se regeneró; **el banco no**, porque
en esa misma sesión Carlos pidió expresamente no tocarlo. Así que hoy:

| | `divergente_oscuro` |
|---|---|
| `assets/paleta.json` (el contrato) | `#0c683b #499044 #89b84c #f0e9cd #ca9829 #c46b20 #9a412c` |
| `docs/banco/index.html` (publicado) | `#16c46f #6dbb67 #a8cc78 #f5f0d9 #e2b657 #e69048 #d06147` |

**En modo oscuro el índice del banco pinta con una rampa que el tablero ya no
usa.** Se arregla con `python sistema-graficos/motor/armar_sitio.py` y nada más
—las 375 láminas no se tocan, sólo el índice—, pero **es una decisión de Carlos**,
porque cambia cómo se ve el banco. Preguntarle antes.

⚠️ **`paleta.py --verificar` no lo detecta**, y decir «OK: paleta sincronizada»
mientras esto pasa es exactamente el punto ciego que hay que conocer: verifica
las FUENTES (`plantilla/tablero.html`, `motor/estilo.py`, las dos plantillas), no
los HTML ya generados en `docs/`. Un producto generado antes de un cambio de
paleta queda desactualizado y el verificador dice que todo está bien.

---

## 7. Trampas conocidas

**`weight="bold"` no hace negrita.** matplotlib no instancia ejes variables, así
que sobre la Inter variable el negrita sale idéntico al redondo: no falla, sólo
se ve mal. Por eso `estilo.py` registra **cada archivo de fuente como su propia
familia** (`Inter`, `Inter Medium`, `Inter SemiBold`, `Inter Bold`) y hay que
pedir `family="Inter Bold"`, nunca `weight="bold"`.

**Las miniaturas no son un lujo, son el requisito.** Las láminas pesan entre 400
KB y 1 MB: una grilla de 375 con los PNG completos serían ~230 MB por visita.
`armar_sitio.py` genera una miniatura de 400 px (~15 KB) y el PNG entero sólo
viaja cuando alguien lo abre. Las regenera sólo si faltan o si la lámina es más
nueva, así que volver a correrlo es barato.

**El nombre del recorte se dice entero.** Son nueve municipios: seis de la
Región Metropolitana y tres de su área de influencia. Ni la lámina ni el índice
dicen «la región» a secas, porque dejaría fuera del nombre a un tercio de lo que
están mostrando. En el tablero el rótulo corto es **RMSC + 3**.

**Cambiar el diseño de una lámina cambia 375 archivos.** Iterar con `--indicador`
sobre una sola, mirar el PNG, y recién entonces correr `--todas`.
