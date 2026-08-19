# Atlas Metropolitano de Santa Cruz

Tablero territorial de la **Región Metropolitana de Santa Cruz** — 9 municipios,
**2.282.770 habitantes**, sobre el Censo de Población y Vivienda 2024 del INE.

**Gobierno Autónomo Departamental de Santa Cruz**

| | |
|---|---|
| **Municipal** | `docs/municipal/` — 243 indicadores en 25 categorías, con serie intercensal 2012 ↔ 2024 |
| **Municipio ↔ manzana** | `docs/manzana/` — 91 indicadores, **38.892 manzanas**; el nivel cambia con el zoom |
| **Flujos** | `docs/flujos/` — quién llega y quién se mueve: nacimiento, residencia 5 años y conmutación laboral |

---

## Cómo se ve

No hace falta compilar nada: es HTML estático.

```bash
python scripts/servir.py 8099     # http://127.0.0.1:8099/manzana/
```

> ⚠️ Usar **este** servidor y no `python -m http.server`. El nivel manzana se
> sirve como teselas vectoriales (`docs/datos/manzanas.pmtiles`) y el navegador
> las pide por **rango de bytes**; `http.server` no implementa `Range` y responde
> con el archivo entero, así que la prueba local no se parece a producción.
> GitHub Pages sí lo implementa.

---

## Cómo se regenera

Desde `catalogo/`, en este orden:

```bash
python armar_tableros.py            # catálogos y fichas de los dos tableros
cd ..
python scripts/estadisticas_manzana.py   # escala y distribución del nivel manzana
python scripts/generar_pmtiles.py        # teselas vectoriales (~70 s)
python scripts/generar_sitios.py         # deriva los dos index.html de la plantilla
```

⚠️ **`docs/index.html` es la plantilla.** No editar `docs/municipal/index.html` ni
`docs/manzana/index.html` a mano: son derivados y se pisan al regenerar.

### Antes de publicar

```bash
python scripts/servir.py 8099
# y en otra terminal, o en el navegador:
#   http://127.0.0.1:8099/_prueba_humo.html?t=manzana
#   http://127.0.0.1:8099/_prueba_humo.html?t=municipal
```

Comprueba que las capas del mapa **existen de verdad**. Un `import` roto o una
constante borrada no rompen la sintaxis: dejan el tablero en blanco sin ningún
error a la vista. Ya pasó una vez.

---

## Qué contiene y qué no

**Sí:** el producto publicable, los motores que lo calculan, el catálogo
declarativo de indicadores, y los datos **recortados a los 9 municipios** de la
región.

**No:** la base de los 343 municipios del país, el microdato del censo (91 MB) y
los GeoJSON intermedios (78,9 MB). Son insumos, no producto.

> ⚠️ **Consecuencia, dicha de frente:** con los datos recortados el tablero se
> **regenera** completo, pero **no se re-verifica**. El contraste de cada
> indicador contra los tabulados del INE necesita los 343 municipios para que la
> comparación signifique algo (`comparar_niveles.py` exige al menos 100), así
> que la auditoría estadística vive del lado de quien tiene la base nacional.
> Los indicadores que se publican acá **ya pasaron** esa verificación: 74 de los
> 91 del nivel manzana reproducen la cifra urbana del microdato, 8 entran con
> aviso por efecto de borde urbano y 5 quedaron excluidos por definición
> distinta (`catalogo_manzana.json` → `excluidos`).

### Dependencias externas

`motor_geo.py` y `motor_manzana.py` leen el mapa municipal maestro y la espina de
municipios desde una ruta local (`bo-geo-maestro`), y los motores del censo leen
el microdato del INE. **Nada de eso hace falta para regenerar el tablero** desde
los CSV incluidos; sí para recalcular los indicadores desde el censo.

---

## Cómo está hecho

- **MapLibre GL 4.7.1** sobre teselas CARTO, sin framework ni build.
- El nivel manzana son **teselas vectoriales PMTiles** con los 91 indicadores
  como atributos: cambiar de indicador es cambiar la expresión de color, no
  recargar datos. El navegador baja sólo las teselas que mira.
- El nivel lo decide el **zoom**, no un botón: las manzanas asoman en z10, el
  nivel cambia en z10,4 y el relleno municipal termina de irse en z10,9.
- El catálogo es **declarativo** (`catalogo/catalogo.py`): agregar un indicador
  es agregar una fila, no editar un script.

## Cobertura del nivel manzana

38.892 manzanas, de las cuales **25.698 tienen ficha del INE (66%)** — el INE
suprime las más chicas por privacidad — y concentran el **93,8% de la población**.
Las manzanas sin ficha se dibujan en gris a propósito: borrarlas dejaría agujeros
que se leen como «acá no vive nadie». **Población y densidad sí existen para las
38.892**, porque salen de otra fuente.

---

**Fuente:** INE · Censo de Población y Vivienda 2024. Fichas por manzano del
geoportal del INE. Ejecución presupuestaria del MEFP para el bloque fiscal.
