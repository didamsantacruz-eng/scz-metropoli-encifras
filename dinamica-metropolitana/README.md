# Dinámica metropolitana — quién se mueve hacia y dentro de la RMSC + 3

Todo lo de acá sale del **microdato crudo del CPV 2024**, no de los archivos ya
publicados en `docs/datos/`. Son nueve municipios: seis de la Región
Metropolitana de Santa Cruz y tres de su área de influencia.

**Para quién es este documento:** para quien tenga que usar estos datos,
rediseñar el explorador o extender el análisis, incluido un agente que llegue al
repo sin contexto previo. Todo lo que dice está medido contra los datos que están
acá al lado.

> ### ⭐ LOS DATOS ESTÁN EN EL REPO, Y ES A PROPÓSITO
> `salida/` (13 MB) y `web/flujos_metro.json` (3,1 MB) **viajan versionados**.
> Antes estaban en `.gitignore` con el argumento de que eran «regenerables con
> los cinco scripts». Ese argumento era falso para cualquiera que no fuera la
> máquina donde se calcularon: el paso 1 lee `Persona_CPV-2024.csv`, **3,1 GB de
> microdato del INE que no está ni puede estar en el repo**. Sin esos JSON no hay
> con qué trabajar.
>
> **Se puede rediseñar el explorador entero sin volver a tocar el microdato.**
> Sólo hacen falta `web/flujos_metro.json`, `web/plantilla.html` y
> `web/secciones.js`, y los tres están acá.

---

## 1. La cadena

| paso | script | qué hace | necesita | sale |
|---|---|---|---|---|
| 1 | `01_base_metro.py` | una pasada por `Persona_CPV-2024.csv` (3,1 GB) + toda la Vivienda, filtrado a los nueve | **microdato** | `base9_metro.parquet` |
| 2 | `02_riqueza_y_privacion.py` | índice de riqueza por ACP, privaciones y capacidad de pago | parquet del 1 | `base9_metro_nivelvida.parquet` |
| 3 | `03_composicion.py` | las seis familias de descriptivos por cada relación | parquet del 2 | `salida/*.json` (7) |
| 4 | `04_paquete_web.py` | recorta por relevancia y arma el paquete | `salida/` | `web/flujos_metro.json` |
| 5 | `05_armar_pagina.py` | inyecta datos y secciones en la plantilla | paquete + plantilla | `web/quien_se_mueve.html` |

Los dos parquet y el microdato del INE viven **fuera del repo**. Los pasos 1 a 3
sólo corren en una máquina que los tenga, y esa ruta se declara con una variable
de entorno:

```bash
export CPV2024=/ruta/a/cpv2024            # Linux o macOS
$env:CPV2024 = "D:\datos\cpv2024"        # PowerShell
```

Sin la variable cae en `C:\Users\HP\cpv2024`, que es la máquina donde se
calcularon. **La ruta del repo no hay que configurarla**: los scripts la deducen
de su propia ubicación.

**Los pasos 4 y 5 corren con lo que ya está en el repo.** Ése es el bucle de
trabajo para el explorador:

```bash
# editar web/plantilla.html (estructura, estilos, la ficha)
#   o   web/secciones.js   (las siete secciones)
python dinamica-metropolitana/05_armar_pagina.py     # ~2 s
# abrir web/quien_se_mueve.html
```

**El HTML servible no se edita a mano.** `quien_se_mueve.html` son 3,1 MB de los
cuales 3,0 son los datos embebidos; se regenera del paso 5 y por eso **no está
versionado**. Editarlo directamente se pierde en la próxima corrida.

---

## 2. Los tres universos, que NO se suman entre sí

Es lo primero que hay que entender: no son tres cortes del mismo número, son tres
preguntas distintas del censo, con universos distintos.

| dimensión | variable | qué es | universo |
|---|---|---|---|
| **nacimiento** | `p35_lugnac` | stock, sin fecha: dónde nació, haya llegado cuando haya llegado | 2.282.770 |
| **residencia** | `p37_lugres5` | flujo **fechado** 2019 a 2024 | 2.109.515 |
| **trabajo** | `p52_mov` | desplazamiento **diario** | 1.043.524 |

Sumarlas, o leer una como si fuera otra, es el error más fácil de cometer acá.
Alguien nacido en Cochabamba que llegó en 2005 aparece en *nacimiento* y **no** en
*residencia*: no se mudó entre 2019 y 2024.

---

## 3. Qué hay en `salida/` — diccionario de datos

Siete archivos. Todos comparten el mismo **perfil de 61 indicadores** descrito en
la sección 4: cada «celda» es un grupo de personas más sus 61 promedios.

| archivo | KB | contenido |
|---|---|---|
| `referencias.json` | 102 | los tres marcos contra los que se compara todo |
| `etiquetas.json` | 19 | los diccionarios: 605 lugares, 9 municipios, 61 indicadores, 6 familias |
| `mig_nacimiento.json` | 6.920 | 3.797 celdas destino × origen de nacimiento + 63 familias |
| `mig_residencia.json` | 3.853 | 2.573 celdas destino × origen 2019-2024 + 63 familias + 547 región |
| `conmutacion.json` | 931 | 1.117 celdas residencia × trabajo + 28 estados |
| `exterior.json` | 282 | 2 subgrupos + 18 por municipio + 182 por país |
| `cohortes.json` | 291 | 48 celdas de cohorte de llegada + 6 región |

### La forma de una celda

```jsonc
{
  "destino": "070101",     // municipio donde vive hoy (cod_ine)
  "origen":  "dep:03",     // de dónde viene — ver claves de lugar abajo
  "n":       28668,        // personas en la celda
  "pct_mujer": 51.0,       // …y los 61 indicadores del perfil
  "anios_estudio": 11.57
}
```

En `conmutacion.json` las claves son `residencia` y `trabajo`; en `cohortes.json`,
`cohorte`; en `exterior.json`, `pais` o `municipio`. El resto es idéntico.

### ⚠️ `n` siempre está; el perfil, no

Una celda con **menos de 40 personas** (`meta.umbral_perfil`) guarda `n` y
**ninguno de los 61 indicadores**: por debajo de eso los porcentajes son ruido. Al
recorrer, hay que probar `if "anios_estudio" in celda`, no asumir que está. De
2.573 celdas de residencia, sólo **503** tienen perfil completo.

### Claves de lugar

| forma | ejemplo | qué es |
|---|---|---|
| `mun:XXXXXX` | `mun:070104` | municipio, código INE de 6 dígitos |
| `prov:XXXXXX` | `prov:070300` | provincia (declaración parcial) |
| `dep:XX` | `dep:03` | departamento (declaración parcial) |
| `pais:XXX` | `pais:032` | país |
| `aqui` | | ya estaba en este municipio |
| `nonato` | | aún no había nacido (sólo en residencia 2019) |
| `sd` | | sin especificar |

`etiquetas.json` → `lugares` traduce las 605 claves a nombre. Las **familias de
origen** (`etiquetas.json` → `familias`) agrupan las 605 en nueve: `aqui`,
`region`, `scz`, `scz_parcial`, `dep`, `dep_parcial`, `exterior`, `nonato`, `sd`.

### Las tres referencias

| clave | qué es | para qué |
|---|---|---|
| `region` | los 2.282.770 | el marco general |
| `municipio[cod]` | todos los que viven ahí | «¿este grupo está por encima o por debajo de su municipio?» |
| `nativo_del_municipio[cod]` | los que **nacieron ahí y siguen ahí** | **el contrafactual**: comparar al que llegó contra el que no se movió |

La tercera es la que hace interesante al conjunto. Sin ella «los que llegaron de
Potosí tienen 9,8 años de estudio» no dice nada; contra el nativo del municipio
donde viven, sí.

---

## 4. Los 61 indicadores del perfil

Seis familias. Los nombres son las claves literales de los JSON.

| # | familia | indicadores |
|---|---|---|
| 1 | **Quién es** (5) | `pct_mujer` `pct_jefe` `pct_indigena` `pct_discapacidad` `tam_hogar` |
| 2 | **Qué sabe** (6) | `anios_estudio` `pct_superior` `pct_sin_nivel` `pct_analfabeto` `pct_asiste_6_17` `pct_asiste_privado` |
| 3 | **De qué vive** (4) | `pct_ocupado` `pct_desocupado` `pct_conmuta` `pct_trabaja_en_casa` |
| 4 | **Cómo vive** (13) | `pct_urbano` `pct_agua_red` `pct_agua_dentro` `pct_alcantarillado` `pct_energia_red` `pct_cocina_lena` `pct_basura_servicio` `pct_piso_tierra` `pct_pared_ladrillo` `pct_hacinamiento` `pers_por_dormitorio` `pct_propia` `pct_alquila` |
| 5 | **Con qué cuenta** (14) | `quintil_medio` `riqueza_media` `pct_auto` `pct_moto` `pct_bici` `pct_refri` `pct_lavadora` `pct_aire` `pct_compu` `pct_inet_fijo` `pct_inet_movil` `pagos_voluntarios` `pct_paga_alguno` `pct_paga_tres` |
| 6 | **Qué le falta** (19) | `privaciones` `pct_sin_seguro` `pct_sin_cedula` `pct_cedula_extranjero` `pct_sin_registro` `pct_priv_pared` `pct_priv_techo` `pct_priv_piso` `pct_priv_hacina` `pct_priv_agua` `pct_priv_saneamiento` `pct_priv_energia` `pct_priv_basura` `pct_priv_combustible` `pct_salud_publica` `pct_salud_caja` `pct_salud_privada` `pct_salud_automedica` `pct_hogar_emigro` |

**Siete NO son porcentajes** y hay que formatearlos distinto: `tam_hogar`,
`anios_estudio`, `pers_por_dormitorio`, `quintil_medio`, `riqueza_media`,
`pagos_voluntarios`, `privaciones`. El campo `es_porcentaje` de `etiquetas.json` →
`indicadores` lo dice para cada uno; no hay que adivinarlo por el prefijo `pct_`.

**La «huella»** (`etiquetas.json` → `huella`) son los 10 que el explorador usa
para el radar comparativo: `anios_estudio`, `pct_superior`, `quintil_medio`,
`privaciones`, `pct_sin_seguro`, `pct_hacinamiento`, `pct_alcantarillado`,
`pct_propia`, `pct_ocupado`, `pct_conmuta`.

### ⚠️ Todo se lee como PERSONAS, incluida la vivienda

«38% con alcantarillado» significa que el **38% de esas personas vive en un hogar
que lo tiene**, no que el 38% de las viviendas lo tenga. Son números distintos y
el segundo es el que publica el INE. Está declarado en
`meta.advertencia_vivienda`.

---

## 5. ⛔ Las trampas. Leer antes de tocar nada

**Dos códigos que parecen geografía y no lo son.** `999995` (lugar de trabajo) y
`999999` (nacimiento y residencia-5) son **«Sin especificar»**. Con `zfill(6)` el
segundo pasa el patrón `XX9999` y sale clasificado como **departamento 99**: son
27.720 personas que aparecerían «trabajando en otro municipio» sin trabajar en
ninguno declarado. Ojo que `099999` **sí** es geografía —Pando sin precisar—, así
que el filtro va sobre el código crudo, no sobre los dos primeros dígitos.

**Los parciales no se tiran.** `XX9999` y `XXYY99` son códigos válidos del INE:
43.970 a nivel departamento y 35.341 a nivel provincia, **79.311 personas**. Cada
dimensión guarda su `*_nivel` para que la precisión sea un dato explícito.

**La no respuesta no es aleatoria.** Los 43.574 que no declararon origen en
residencia 2019 tienen **17,5%** con educación superior contra **35,7%** de la
región. Cualquier total que los meta adentro sesga hacia abajo. Está declarado en
`meta.advertencia_no_respuesta`.

**`p28_cn` pregunta por el registro civil BOLIVIANO.** Que alguien nacido en otro
país conteste «no» es la respuesta correcta y esperable, **no una carencia**.
Publicarlo como privación convierte el enunciado de una pregunta en un problema
social inexistente. El indicador que sí dice algo es `p29_ci`, la cédula.

**`p32_pueblos` no es un sí/no de indígena.** Su categoría 1 es *Afroboliviano* y
la 98 «no se autoidentifica». Medirlo como `== "1"` da 0,2% y es basura.

**El mismo universo arriba y abajo.** Cada indicador restringido se construye como
una columna con `NaN` fuera de su universo, para que el promedio use el mismo
denominador que su numerador. Ése fue el error que dio porcentajes de ocupados de
100,8% y 102,1%.

**⛔ `tam_hogar` es «el tamaño del hogar de la persona promedio», no el tamaño
medio del hogar** (corregido el 2026-08-26). Da **4,72**; el tamaño medio del
hogar es **3,58** —2.282.770 personas entre 637.667 hogares—. Son dos estadísticos
distintos, y el de acá está ponderado por personas como todo el resto de la ficha.

Antes daba **40,54**, y de ahí salió la corrección. Dos cosas se sumaban: es un
atributo del hogar promediado sobre personas (Σn²/Σn, sesgado por tamaño por
construcción) y además entraban las **viviendas colectivas**. `v01_tipoviv` 12 es
«recinto penitenciario» y promedia 7.318 personas —ese único registro de 8.645 es
Palmasola—; la 8 es hospital con internación y la 9, cuartel. Eran 279 viviendas
sobre 20 personas, el 0,04% de los hogares, y solas levantaban la media de 3,58 a
40,54. Hoy el campo se restringe a **vivienda particular** (`v01_tipoviv` 1 a 6).
*Es el mismo error que la invariante 2 de `sistema-graficos/`, un nivel más abajo:
hogares en vez de municipios.*

La restricción **no** se aplica a los otros 60: quien vive en un cuartel o en un
penal sigue siendo una persona, y su edad, su educación y su origen son datos
válidos. Medido: ninguno de los otros indicadores de vivienda se mueve más de 1,2
puntos al restringir, y `pers_por_dormitorio` no se mueve nada.

**Leer Vivienda entera junto con las 2,28 M personas revienta por memoria.** Va
por trozos, y así está escrito.

---

## 6. El nivel de vida: qué método y por qué

**El censo no pregunta ingreso.** Ninguna de las 114 variables de persona ni de
las 44 de vivienda. Decisión de Carlos (2026-08-26): se hacen los niveles 1 y 2 y
se **declara** el 3 sin hacerlo.

**Nivel 1 · índice de riqueza por ACP** — Filmer & Pritchett (2001), *Demography*
38(1), con la corrección urbano/rural de Rutstein (2008), DHS WP 60. 33 variables,
20 comunes, 19,6% de varianza explicada por el primer componente. Las cargas están
en `ficha_metodo_nivelvida.json` y ordenan como se espera: lavadora, refrigerador
y computadora arriba; piso de tierra y cocina de leña abajo.

**Es ordinal y hay que decirlo:** «quintil 5» es «entre el 20% con más activos de
la región», **no** un monto en bolivianos. Validación externa: los años de estudio
van de 9,2 a 14,3 y la educación superior de 9,6% a 47,1% entre el quintil 1 y el
5.

**Nivel 2 · privaciones declaradas** una por una, en las dimensiones del NBI.
**No se rotula «NBI»** a propósito: los umbrales y normas exactas del NBI del INE
no están en el diccionario del censo, y llamar NBI a un cálculo con umbrales
propios sería presentar como oficial algo que no lo es. Los umbrales usados están
todos en `ficha_metodo_nivelvida.json`.

**Nivel 3 · ingreso en bolivianos — DECLARADO, SIN HACER.** Estimación por áreas
pequeñas (Elbers, Lanjouw & Lanjouw 2003) cruzando el censo con el microdato de la
Encuesta de Hogares de ANDA.

**Cohortes de llegada:** separan asimilación (Chiswick 1978) de composición
(Borjas 1985). Un migrante que llegó hace 20 años tiene mejores indicadores que
uno que llegó hace 2 por dos razones que se confunden: porque lleva más tiempo, o
porque los que llegaban hace 20 años eran otra gente. `cohortes.json` da el corte
por año de llegada para poder separarlas; **el análisis que las separa no está
hecho**.

---

## 7. El hallazgo que no hay que perder

**El exterior son dos migraciones opuestas que se promedian en una.** De los
24.672 nacidos fuera del país, **11.931 son retornados bolivianos (48,4%)** y
**12.741 extranjeros (51,6%)**, y tienen perfiles distintos. Promediarlos produce
un «migrante internacional» que no existe. `exterior.json` → `subgrupo` los trae
separados.

De ahí salió también la trampa de `p28_cn`: se estuvo a punto de publicar «31,5%
sin registro civil» sobre este grupo. La cifra que sí dice algo es **24,1% de los
nacidos en el exterior mayores de edad sin documento boliviano**.

---

## 8. El explorador

`web/quien_se_mueve.html` es el producto: matriz de pares + ficha de par, que fue
la navegación elegida. **No está publicado** —`docs/flujos/index.html` es una
página anterior, con la identidad vieja y tres errores de cálculo ya medidos— y
rediseñarlo es la tarea pendiente.

| archivo | versionado | qué es |
|---|---|---|
| `web/plantilla.html` | sí | estructura, estilos y la ficha de par. **Acá se edita el diseño** |
| `web/secciones.js` | sí | las siete secciones del explorador |
| `web/flujos_metro.json` | sí | el paquete de datos, 3,1 MB |
| `web/quien_se_mueve.html` | no | producto de los tres anteriores; se regenera con el paso 5 |

### Qué trae `flujos_metro.json`

| clave | contenido |
|---|---|
| `meta` | fuente, universo, los 9 municipios, `umbral_perfil`, y **dos advertencias que conviene mostrar en la página** |
| `indicadores` | los 61, con `familia` y `es_porcentaje` |
| `familias_de_indicadores` | los 6 nombres |
| `huella` | los 10 del radar |
| `familias_de_origen` | las 9 agrupaciones de lugar |
| `referencias` | `region`, `municipio`, `nativo_del_municipio` |
| `matrices` | `res`, `nac`, `con` — 72 + 72 + 69 pares |
| `fichas` | 154 fichas de par; la clave es tipo, destino y origen unidos por barra vertical |
| `familias_por_municipio` | `res` y `nac` agregados por familia de origen |
| `externos` | 129 orígenes externos listados (11.509 personas fuera del corte) |
| `corredores` | 166 corredores de conmutación (5.407 fuera) |
| `estados_de_trabajo` | 28 |
| `exterior` | `subgrupo`, `por_municipio`, `por_pais` |
| `cohortes` | `celdas`, `region` |
| `etiquetas_lugar` | las 605 traducciones |

**El recorte se declara.** Cada lista recortada trae `no_listadas` con cuánta
gente quedó fuera. No hay truncamiento silencioso, y no hay que introducir uno.

---

## 9. Qué más se puede sacar: los cruces disponibles

El microdato da mucho más de lo que el paquete web recorta. Lo que **ya está
calculado en `salida/`** y no se usa en la página:

- **`mig_nacimiento.json` → `familias` y `mig_residencia.json` → `familias`** (63
  cada uno): el perfil por familia de origen, no por origen exacto. Es el corte
  que sirve para el mapa general.
- **`mig_residencia.json` → `region`** (547 celdas): el flujo agregado a la región
  entera, sin abrir por municipio de destino.
- **`exterior.json` → `por_pais`** (182 países), del que la página lista 129.
- **`cohortes.json`** entero: el corte por año de llegada casi no se explota.

Y lo que **se puede calcular** con la base ya construida, sin volver al CSV de
3,1 GB (`base9_metro_nivelvida.parquet`, 125 columnas × 2,28 M filas):

- Cruzar **origen × cualquier variable de persona**: rama de actividad (23
  secciones CIIU), ocupación (12 grupos), categoría ocupacional, estado civil,
  idioma materno, pueblo de pertenencia, tipo de establecimiento educativo.
- Cruzar **origen × cohorte × indicador**, que es lo que hace falta para separar
  asimilación de composición.
- **Origen × destino × conmutación**: quién llegó de fuera *y además* trabaja en
  otro municipio.

### El techo de granularidad — lo que NO se puede

- **`act_eco_2d_13` no son divisiones a dos dígitos** pese al nombre: son las 23
  **secciones CIIU A a U**. `ocu_1d_13` trae 12 grupos.
- **`p50_semp` no es tamaño de empresa**: sus categorías son idénticas a
  `p50_catocu_13`.
- **El lugar de trabajo no baja del municipio**, ni la residencia anterior. No hay
  zona, UV, barrio ni distrito. **No hay mapa de conmutación dentro de la ciudad.**
- **No hay modo de transporte, ni tiempo de viaje, ni hora de salida.** El bloque
  `MOVI` son cuatro preguntas y ninguna es ésas.
- La textura fina sale de **cruzar**, no de bajar de nivel.

---

## 10. Lo que falta

- **Media conmutación.** Sólo se ve a quien *vive* en los nueve. Quien vive fuera
  de la región y viene a trabajar adentro (~16.700 personas) requiere otra pasada
  por el CSV nacional filtrando `mun_lab_cod` en los nueve con residencia afuera.
- **Ingreso en bolivianos.** Nivel 3, declarado y sin hacer (sección 6).
- **Separar asimilación de composición.** Los datos de cohorte están; el análisis
  no.
- **Rediseñar el explorador** y decidir si se publica reemplazando
  `docs/flujos/index.html`.

---

## 11. Los scripts viejos

`auditar_flujos.py`, `perfil_socioec.py`, `conmutacion2.py`, `lugar_trabajo.py` y
`armar_auditoria.py` son de la auditoría del 2026-08-20 y quedan como respaldo de
esa hoja, con sus JSON al lado. **La cadena 01 a 05 los reemplaza** y corrige dos
de sus resultados: los «11.163 parciales» de la hoja publicada eran en realidad
«Sin especificar», y los parciales reales son 79.311.
