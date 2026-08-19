# -*- coding: utf-8 -*-
"""
BANCO DE LÁMINAS — un municipio, un indicador, a nivel manzana.
================================================================

Cada lámina responde tres preguntas sobre el mismo dato, que es lo que una
imagen suelta necesita para poder viajar sin el tablero al lado:

  1. **Dónde** — el mapa de las manzanas de ese municipio.
  2. **Cómo se reparte adentro** — la caja p25-p75 con su mediana, contra las
     de los otros ocho. Es la lectura que el promedio municipal esconde: en 57
     de los 91 indicadores la desigualdad DENTRO de un municipio supera todo el
     rango ENTRE los nueve.
  3. **Contra qué se compara** — la cifra del municipio y la de la región.

⚠️ LA COBERTURA VA ESCRITA EN LA LÁMINA. El INE suprime la ficha de las
   manzanas más chicas por privacidad, así que en la mayoría de los indicadores
   un tercio del territorio va en gris. En pantalla el lector puede pasar el
   mouse y enterarse; en una imagen que viaja sola, si no está escrito, el gris
   se lee como "acá no vive nadie".

    python scripts/banco/lamina_manzana.py [--municipio SLUG] [--indicador CLAVE]
"""
import argparse, json, pathlib, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Rectangle
from matplotlib.collections import PatchCollection
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import estilo as E

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
DATOS = RAIZ / "docs" / "datos"
SALIDA = RAIZ / "docs" / "banco" / "manzana"

# ★ RESOLUCIÓN. La figura se compone en 16×9 pulgadas y se GUARDA al doble de
#   densidad: 3200×1800. El mapa amanzanado tiene miles de polígonos de 2-3 px
#   de lado a tamaño de pantalla, así que al ampliar se veía el píxel. Todo lo
#   demás escala solo —las medidas están en pulgadas y puntos, no en píxeles—
#   salvo el logotipo, que es un bitmap y hay que pedirlo al doble.
DPI = 200

# ── los 12 que RINDEN a nivel manzana ────────────────────────────────────
# Elegidos midiendo, no por tema: un indicador sólo merece una lámina por
# manzana si VARÍA dentro del municipio. Los que quedaron fuera —agua de
# vertiente, cocina solar, basura a la calle, agua mejorada— tienen brecha
# interna 0,0 y no varían en NINGÚN municipio: su lámina saldría de un color.
INDICADORES = [
    "densidad", "pob_total", "pct_menor20",
    "pct_agua_caneria",
    "pct_alcantarillado", "pct_pozo_ciego", "pct_camara_septica",
    "pct_gas_red", "pct_gas_garrafa",
    "pct_basura_formal", "pct_basura_carro", "pct_basura_quema",
    # ── educación y salud ────────────────────────────────
    # El dato YA venía en las fichas del geoportal —las 91 columnas están en
    # cada dat_*.json— y son de los que más varían dentro de un mismo
    # municipio: la mediana de la brecha p10-p90 da 42,7 pp en afiliación al
    # SUS y 39,1 pp en educación superior, por encima de casi todo servicio.
    "pct_edu_superior", "pct_edu_secundaria", "pct_edu_primaria",
    "pct_sin_educacion",
    "pct_sin_seguro", "pct_sus",
]

# ★ QUÉ MIDE CADA UNO, DECLARADO Y NO DEDUCIDO. Ni la etiqueta ni la unidad
#   alcanzan: "Recojo formal de basura" no dice qué cuenta como formal, y el
#   lector no tiene por qué adivinarlo. Cada línea se escribe desde el `e24`
#   del catálogo —la expresión que de verdad se calcula sobre el microdato— y
#   nombra el universo, que es donde se cometen los errores de lectura.
#   ⚠️ El censo mide VIVIENDAS particulares ocupadas, no hogares: son unidades
#   distintas y la lámina dice viviendas porque es lo que se contó.
DEFINICION = {
    "densidad":           "Habitantes por hectárea de superficie",
    "pob_total":          "Personas empadronadas",
    "pct_menor20":        "Porcentaje de la población con menos de 20 años",
    "pct_agua_caneria":   "Porcentaje de viviendas cuya agua llega por cañería de red",
    "pct_alcantarillado": "Porcentaje de viviendas con desagüe conectado al alcantarillado",
    "pct_pozo_ciego":     "Porcentaje de viviendas cuyo desagüe termina en pozo ciego",
    "pct_camara_septica": "Porcentaje de viviendas cuyo desagüe termina en cámara séptica",
    "pct_gas_red":        "Porcentaje de viviendas que cocinan con gas por cañería a domicilio",
    "pct_gas_garrafa":    "Porcentaje de viviendas que cocinan con gas en garrafa",
    "pct_basura_formal":  "Porcentaje de viviendas cuya basura sale por el sistema público, "
                          "sea al carro basurero o a un contenedor",
    "pct_basura_carro":   "Porcentaje de viviendas que entregan su basura al carro basurero",
    "pct_basura_quema":   "Porcentaje de viviendas que queman su basura",
    "pct_edu_superior":   "Porcentaje de personas de 19 años o más que alcanzaron "
                          "educación superior",
    "pct_edu_secundaria": "Porcentaje de personas de 19 años o más cuyo nivel más "
                          "alto es secundaria",
    "pct_edu_primaria":   "Porcentaje de personas de 19 años o más cuyo nivel más "
                          "alto es primaria",
    "pct_sin_educacion":  "Porcentaje de personas de 19 años o más sin ningún nivel "
                          "educativo aprobado",
    "pct_sin_seguro":     "Porcentaje de la población sin afiliación a ningún seguro "
                          "de salud",
    "pct_sus":            "Porcentaje de la población afiliada al Sistema Único de "
                          "Salud (SUS)",
}


def definicion(clave, ind):
    """La definición cerrada con ', por manzana': sin eso la lámina se lee como
    si la cifra fuera del municipio, que es el error de lectura más caro de
    todo el tablero."""
    d = DEFINICION.get(clave)
    if not d:                       # nunca deducir de la etiqueta: mejor decir menos
        d = (ind.get("desc") or ind.get("label", "")).split(".")[0]
    return d + ", por manzana"


def cargar():
    cat = json.loads((DATOS / "catalogo_manzana.json").read_text(encoding="utf-8"))
    ind = {i["key"]: i for g in cat["grupos"] for i in g["indicadores"]}
    mun = json.loads((DATOS / "municipios_manzana.json").read_text(encoding="utf-8"))
    st = json.loads((DATOS / "mz_stats.json").read_text(encoding="utf-8"))
    return ind, mun, st


def slug(nombre):
    import unicodedata
    s = unicodedata.normalize("NFD", nombre.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "_")


def geometria(sl):
    geo = json.loads((DATOS / f"geo_{sl}.geojson").read_text(encoding="utf-8"))
    dat = json.loads((DATOS / f"dat_{sl}.json").read_text(encoding="utf-8"))
    return geo, dat


def anillos(g):
    """Lista de anillos exteriores, sin suponer el tipo de geometría."""
    if not g:
        return []
    t = g.get("type")
    if t == "Polygon":
        return [g["coordinates"][0]] if g["coordinates"] else []
    if t == "MultiPolygon":
        return [p[0] for p in g["coordinates"] if p]
    if t == "GeometryCollection":
        out = []
        for x in g.get("geometries", []):
            out += anillos(x)
        return out
    return []


def logo_nitido(ruta, alto_px):
    """★ EL LOGO PIXELADO. `OffsetImage(zoom=…)` reescala en el momento de
    dibujar y matplotlib no interpola bien al achicar: el logotipo de 688×168
    llegaba dentado. Se reduce ANTES con LANCZOS, al tamaño exacto en píxeles
    que va a ocupar, y se dibuja a escala 1:1."""
    from PIL import Image
    import numpy as np
    im = Image.open(ruta).convert("RGBA")
    w = max(1, round(im.width * alto_px / im.height))
    return np.asarray(im.resize((w, alto_px), Image.LANCZOS))


def minimapa(ax, geo9, sigep, esc_color):
    """Dónde queda este municipio dentro de la región. Sin esto, quien no
    conozca la geografía ve una mancha y no sabe de dónde es."""
    ax.set_xticks([]); ax.set_yticks([])
    for lado in ("top", "right", "bottom", "left"):
        ax.spines[lado].set_visible(False)
    xs, ys = [], []
    for f in geo9["features"]:
        propio = str(f["properties"].get("sigep")) == str(sigep)
        for anillo in anillos(f.get("geometry")):
            ax.add_patch(MplPoly(anillo, closed=True,
                                 facecolor=esc_color if propio else "#d5d9d4",
                                 edgecolor="#ffffff", linewidth=.5, zorder=2 if propio else 1))
            for x, y in anillo:
                xs.append(x); ys.append(y)
    if xs:
        mx = (max(xs)-min(xs))*.02; my = (max(ys)-min(ys))*.02
        ax.set_xlim(min(xs)-mx, max(xs)+mx); ax.set_ylim(min(ys)-my, max(ys)+my)
    ax.set_aspect("equal", adjustable="datalim")


# Los nombres de localidad vienen del INE en MAYÚSCULAS. Las partículas van en
# minúscula salvo al principio: "SAN MIGUEL DE LOS JUNOS" -> "San Miguel de los
# Junos", no "San Miguel De Los Junos". Misma regla que el tablero.
PARTICULAS = {"de", "del", "la", "las", "los", "el", "y", "en"}


def tituloCaso(s):
    if not s:
        return ""
    ps = str(s).lower().split()
    return " ".join(p if k > 0 and p in PARTICULAS else p.capitalize()
                    for k, p in enumerate(ps))


def centroide(g):
    """Centro aproximado de una geometría, sin dependencias."""
    pts = [p for anillo in anillos(g) for p in anillo]
    if not pts:
        return None
    return sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts)


def encuadre_ajustado(centros, q=.012):
    """★ RECORTA LOS ISLOTES LEJANOS. Cotoca tiene núcleos a decenas de km de su
    mancha principal, y encuadrar por el mínimo y el máximo absolutos dejaba el
    grueso de las manzanas diminuto en un rincón con el resto vacío. Se recorta
    por PERCENTIL de los centroides —cada manzana cuenta una— así que un puñado
    de manzanas alejadas no manda sobre el encuadre de miles.
    ⚠️ Las manzanas que quedan fuera se siguen dibujando: no se borra nada, sólo
    se elige dónde mirar. Por eso el pie dice cuántas quedaron fuera del cuadro."""
    if not centros:
        return None
    xs = sorted(c[0] for c in centros); ys = sorted(c[1] for c in centros)
    def cor(v, qq):
        k = min(len(v)-1, max(0, int(round(qq*(len(v)-1)))))
        return v[k]
    x0, x1 = cor(xs, q), cor(xs, 1-q)
    y0, y1 = cor(ys, q), cor(ys, 1-q)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def perfil_localidades(dat, col, minimo=12):
    """★ NÚCLEO + LAS DOS PUNTAS ENTRE LOS SATÉLITES.

    Los nueve municipios tienen la misma estructura: una localidad homónima que
    concentra el grueso de las manzanas —el núcleo urbano— y un rosario de
    satelites chicos. Sacar "la mejor" y "la peor" de todas juntas devuelve casi
    siempre el núcleo como mejor, y eso no es una punta: es el promedio del
    municipio con otro nombre. En Santa Cruz de la Sierra el núcleo se lleva
    20.775 de 21.406 manzanas y su mediana coincide con la municipal.

    Por eso se separan los papeles: el núcleo va como REFERENCIA —la ciudad— y
    las dos puntas se buscan entre los SATÉLITES, que es donde la brecha vive.

    Devuelve (núcleo, alto, bajo); cada uno (nombre, mediana, n_manzanas) o None.
    ⚠️ Son ALTO y BAJO, no "mejor" y "peor": cuál de los dos es el bueno depende
    de la DIRECCIÓN del indicador, y eso lo declara el catálogo — no lo puede
    deducir esta función mirando números. En `pct_sin_seguro` el valor bajo es
    el bueno, y rotular por tamaño publicaba al mejor como el peor. En los
    neutros —población, densidad, gas en garrafa— no hay bueno ni malo.
    Se descartan las localidades con menos de `minimo` manzanas con dato: una
    mediana de tres manzanas no es una punta, es una an\u00e9cdota.
    """
    from collections import defaultdict
    g = defaultdict(list)
    for k, v in enumerate(col):
        if v is None:
            continue
        n = dat["nombre"][k] if k < len(dat["nombre"]) else None
        if n:
            g[n].append(v)
    if not g:
        return None, None, None
    # el núcleo es el de más manzanas: no se busca por nombre, porque el nombre
    # de la localidad y el del municipio no siempre coinciden (Porongo → Urubó)
    nom_nucleo = max(g, key=lambda n: len(g[n]))

    def resumen(n):
        v = sorted(g[n])
        return (n, v[len(v)//2], len(v))

    nucleo = resumen(nom_nucleo)
    sat = [n for n in g if n != nom_nucleo and len(g[n]) >= minimo]
    if not sat:
        return nucleo, None, None
    med = {n: sorted(g[n])[len(g[n])//2] for n in sat}
    orden = sorted(sat, key=lambda n: med[n])
    if len(orden) == 1:
        return nucleo, resumen(orden[0]), None
    return nucleo, resumen(orden[-1]), resumen(orden[0])   # (núcleo, alto, bajo)


def puesto_regional(dist, sigep, nom):
    """En qué puesto de los nueve queda, por mediana de sus manzanas."""
    orden = sorted(dist.items(), key=lambda kv: -kv[1]["p50"])
    for n, (sg, d) in enumerate(orden, 1):
        if sg == sigep:
            mejor, peor = orden[0], orden[-1]
            return n, len(orden), (nom.get(mejor[0]), mejor[1]["p50"]), (nom.get(peor[0]), peor[1]["p50"])
    return None, len(orden), None, None


def ancho_de(fig, txt, fs, fam):
    """Ancho de un texto en fracción de figura. matplotlib no lo dice sin
    dibujar, así que se escribe un artista de prueba, se mide y se descarta."""
    t = fig.text(0, 0, txt, fontsize=fs, family=fam)
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    t.remove()
    return bb.width / (fig.get_figwidth() * fig.dpi)


def parrafo(fig, x, y, tramos, fs, salto, ancho_max, dibujar=True):
    """★ TEXTO QUE FLUYE, CON TRAMOS DE DISTINTO COLOR Y TIPOGRAFÍA.

    matplotlib no sabe cortar líneas ni mezclar estilos dentro de un texto, y el
    titular tiene que hacer las dos cosas: "Santa Cruz de la Sierra:" en verde y
    el indicador en negro, cortando donde haga falta. Se mide palabra por
    palabra y se coloca a mano.

    `tramos` es una lista de (texto, color, familia) y, opcionalmente, un cuarto
    valor True para CORTAR LÍNEA después de ese tramo. Devuelve (y_final, líneas)
    y con dibujar=False sólo mide, que es como se elige el cuerpo de letra.
    """
    palabras = []
    for tr in tramos:
        txt, c, f = tr[0], tr[1], tr[2]
        ws = [w for w in txt.split(" ") if w]
        for k, w in enumerate(ws):
            # el corte se marca en la ÚLTIMA palabra del tramo, no en el tramo:
            # así el flujo sigue siendo palabra a palabra y no hay caso especial
            palabras.append((w, c, f, len(tr) > 3 and tr[3] and k == len(ws)-1))
    if not palabras:
        return y, 0
    esp = ancho_de(fig, " ", fs, tramos[0][2])
    lineas, act, w_act = [], [], 0.0
    for w, c, f, cortar in palabras:
        ww = ancho_de(fig, w, fs, f)
        suma = ww if not act else esp + ww
        if act and w_act + suma > ancho_max:
            lineas.append(act)
            act, w_act = [(w, c, f, ww)], ww
        else:
            act.append((w, c, f, ww))
            w_act += suma
        if cortar and act:
            lineas.append(act)
            act, w_act = [], 0.0
    if act:
        lineas.append(act)
    if dibujar:
        yy = y
        for ln in lineas:
            xx = x
            for w, c, f, ww in ln:
                fig.text(xx, yy, w, color=c, fontsize=fs, family=f, va="top")
                xx += ww + esp
            yy -= salto
    return y - salto*len(lineas), len(lineas)


def lamina(sl, clave, ind, mun, st, salida):
    """Lámina HORIZONTAL 1600×900.

    GRILLA. Un solo margen (M) para los cuatro lados y para el pie, y dos
    columnas con un canal fijo entre ellas. Antes cada bloque tenía su propio
    margen improvisado y el pie quedaba pegado al borde mientras el resto
    respiraba: la lámina se leía desalineada sin que se supiera por qué.

    SIN CAJAS. Las cifras no van dentro de un recuadro blanco —que sobre un
    fondo crema abre un segundo plano y ensucia— sino sueltas, separadas por
    un filete. El peso lo dan la tipografía y el aire, no un contorno.
    """
    i = ind[clave]
    s_ = st[clave]
    reg = E.escala_util(s_["esc"])
    m = next(x for x in mun if slug(x["nombre"]) == sl)
    geo, dat = geometria(sl)
    col = dat["cols"].get(clave, [])
    esc = E.escala_local(col) or reg
    d = s_["dist"].get(m["sigep"])
    u = i["unit"]
    D = i.get("dir", 0)

    # ── grilla ───────────────────────────────────────────────────────────
    M = .030                     # margen único
    BARRA = .072                 # alto de la barra superior
    PIE = .098                   # banda del pie
    COL_IZQ = .505               # ancho del mapa
    CANAL = .035
    X = M + COL_IZQ + CANAL      # arranque de la columna derecha
    W = 1 - X - M

    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor(E.FONDO)

    # ── barra superior ───────────────────────────────────────────────────
    fig.add_artist(Rectangle((0, 1-BARRA), 1, BARRA, transform=fig.transFigure,
                             facecolor=E.TOPBAR, edgecolor="none", zorder=5))
    yb = 1 - BARRA/2
    logo = RAIZ / "docs" / "img" / "scz-oscuro.png"
    if logo.exists():
        ab = AnnotationBbox(OffsetImage(logo_nitido(logo, int(30*DPI/100)),
                                        zoom=100/DPI),
                            (M, yb), xycoords="figure fraction",
                            frameon=False, box_alignment=(0, .5), zorder=6)
        fig.add_artist(ab)
    # \u2605 EL NOMBRE, EN DOS PESOS. \u00abSanta Cruz Metr\u00f3poli\u00bb en el verde de la marca
    #   y \u00abEn Cifras\u00bb en blanco: es el nombre que ya lleva la URL del sitio
    #   (scz-metropoli-encifras) y el que corresponde. La x del segundo tramo se
    #   MIDE en vez de estimarse \u2014 con la coordenada fija, cambiar una palabra
    #   dejaba los dos tramos pisados o separados por un hueco.
    x_marca = .148
    fig.text(x_marca, yb, "Santa Cruz Metr\u00f3poli", color=E.VERDE, fontsize=14.5,
             family=E.F_BOLD, va="center", zorder=6)
    fig.text(x_marca + ancho_de(fig, "Santa Cruz Metr\u00f3poli\u00a0\u00a0", 14.5, E.F_BOLD),
             yb, "En Cifras", color="#ffffff", fontsize=14.5,
             family=E.F_SEMI, va="center", zorder=6)
    fig.text(1-M, yb, "Censo 2024 \u00b7 INE", color="#dfe9df", fontsize=10.5,
             family=E.F_MED, va="center", ha="right", zorder=6)

    # ══ IZQUIERDA: el mapa, con todo el aire ═════════════════════════════
    ALTO_PUNTAS = .062           # la banda del pie de foto, bajo el mapa
    ax = fig.add_axes([M, PIE + .015 + ALTO_PUNTAS, COL_IZQ,
                       1 - BARRA - PIE - .045 - ALTO_PUNTAS])
    ax.set_facecolor(E.FONDO)
    for lado in ("top", "right", "bottom", "left"):
        ax.spines[lado].set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    parches, colores, xs, ys = [], [], [], []
    for f in geo["features"]:
        idx = f["properties"]["i"]
        v = col[idx] if idx < len(col) else None
        c = E.tono(v, esc, D)
        for anillo in anillos(f.get("geometry")):
            parches.append(MplPoly(anillo, closed=True)); colores.append(c)
            for x, y in anillo:
                xs.append(x); ys.append(y)
    centros = [c for c in (centroide(f.get("geometry")) for f in geo["features"]) if c]
    caja = encuadre_ajustado(centros)
    if caja:
        x0, y0, x1, y1 = caja
        mx = (x1-x0)*.05; my = (y1-y0)*.05
        ax.set_xlim(x0-mx, x1+mx); ax.set_ylim(y0-my, y1+my)
        fuera = sum(1 for c in centros if not (x0 <= c[0] <= x1 and y0 <= c[1] <= y1))
    elif xs:
        mx = (max(xs)-min(xs))*.04; my = (max(ys)-min(ys))*.04
        ax.set_xlim(min(xs)-mx, max(xs)+mx); ax.set_ylim(min(ys)-my, max(ys)+my)
        fuera = 0
    else:
        fuera = 0
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale(False)          # el encuadre no se mueve con lo que se agregue

    # ★ LÍMITES DE TODOS LOS MUNICIPIOS, debajo de las manzanas. Con el
    #   encuadre ya fijo, los que caen fuera se recortan solos: se ve el tramo
    #   de frontera que rodea la mancha y nada más. Da referencia territorial
    #   —dónde termina este municipio y empieza el vecino— sin robarle espacio
    #   al mapa, que es lo que pasaba dibujando el contorno completo.
    g9 = json.loads((DATOS / "municipios.geojson").read_text(encoding="utf-8"))
    for f in g9["features"]:
        propio = str(f["properties"].get("sigep")) == str(m["sigep"])
        for anillo in anillos(f.get("geometry")):
            ax.add_patch(MplPoly(anillo, closed=True, facecolor="none",
                                 edgecolor="#a9b3ab" if propio else "#c6cec7",
                                 linewidth=1.3 if propio else .8,
                                 linestyle="-" if propio else (0, (4, 3)), zorder=0))
    ax.add_collection(PatchCollection(parches, facecolor=colores,
                                      edgecolor="#ffffff", linewidths=.10, zorder=2))

    # Las dos puntas NO van encima del mapa: la cajita tapaba justo las
    # manzanas que se estaban señalando. Van al pie, como pie de foto.
    nucleo, sat_alto, sat_bajo = perfil_localidades(dat, col)

    # ══ PIE DE FOTO DEL MAPA: quién es quién dentro del municipio ═════
    # El mapa muestra la desigualdad pero no dice DÓNDE: sin esto el lector ve
    # una mancha y no puede ir a buscar el lugar. Va acá abajo, alineado con el
    # mapa y con la muestra del color que le toca en la rampa, así el ojo cierra
    # el circuito color → lugar → cifra sin leer un renglón de prosa.
    # \u2605 EL ROL DE CADA PUNTA LO DECIDE `dir`, NO EL N\u00daMERO. Con dir = \u22121
    #   \u2014"sin afiliaci\u00f3n a salud", "pozo ciego", "quema la basura"\u2014 el valor
    #   bajo es el bueno, y rotular por tama\u00f1o publicaba al mejor como el peor:
    #   Porongo sal\u00eda de "peor sat\u00e9lite" con 5,0% sin seguro siendo el mejor de
    #   todos. Con dir = 0 no hay juicio que hacer y se dice alto y bajo.
    if D == 0:
        roles = [(sat_alto, "el sat\u00e9lite m\u00e1s alto"), (sat_bajo, "el m\u00e1s bajo")]
    elif D < 0:
        roles = [(sat_bajo, "el mejor sat\u00e9lite"), (sat_alto, "el peor sat\u00e9lite")]
    else:
        roles = [(sat_alto, "el mejor sat\u00e9lite"), (sat_bajo, "el peor sat\u00e9lite")]
    piezas = [(p, r) for p, r in [(nucleo, "el n\u00facleo urbano")] + roles if p]
    if len(piezas) > 1:
        yp = PIE + .015 + ALTO_PUNTAS - .018
        fig.text(M, yp, "POR LOCALIDAD, DENTRO DE " + m["nombre"].upper(),
                 color=E.TINTA, fontsize=8, family=E.F_BOLD, va="center")
        paso = COL_IZQ / max(len(piezas), 3)
        SANGRIA = .019               # del borde de la muestra al texto
        CANAL_SLOT = .012            # aire garantizado entre una columna y la de al lado
        util = paso - SANGRIA - CANAL_SLOT
        for k, (p, rol) in enumerate(piezas):
            nl, val, nmz = p
            xx = M + paso*k
            nombre_loc = tituloCaso(nl)
            # \u2605 CADA COLUMNA SE MIDE ANTES DE ESCRIBIRSE. Los nombres del INE
            #   van de "Cotoca" a "Comunidad Platanillo Brecha 7" y el rol suma
            #   otro rengl\u00f3n: a cuerpo fijo, los largos se met\u00edan en la columna
            #   vecina. Se baja el cuerpo hasta que entre y, si ni al m\u00ednimo
            #   entra, se suelta primero el recuento de manzanas \u2014que es el dato
            #   menos importante de la l\u00ednea\u2014 antes que recortar un nombre.
            fs_n = 9.5
            while fs_n > 7.0 and ancho_de(fig, nombre_loc, fs_n, E.F_SEMI) > util:
                fs_n -= .5
            largo = (E.fmt(val, u) + "  \u00b7  " + rol + ", "
                     + f"{nmz:,}".replace(",", ".")
                     + (" manzana" if nmz == 1 else " manzanas"))
            corto = E.fmt(val, u) + "  \u00b7  " + rol
            fs_d = 7.5
            while fs_d > 6.5 and ancho_de(fig, largo, fs_d, E.F_TXT) > util:
                fs_d -= .5
            detalle = largo if ancho_de(fig, largo, fs_d, E.F_TXT) <= util else corto
            # el borde va en tinta y no en gris: el centro de la rampa es del
            # color del papel, y con borde suave la muestra desaparec\u00eda
            fig.add_artist(Rectangle((xx, yp - .049), .013, .022,
                                     transform=fig.transFigure, edgecolor=E.TINTA,
                                     lw=.7, facecolor=E.tono(val, esc, D), zorder=3))
            fig.text(xx + SANGRIA, yp - .029, nombre_loc, color=E.TINTA,
                     fontsize=fs_n, family=E.F_SEMI, va="center")
            fig.text(xx + SANGRIA, yp - .050, detalle,
                     color=E.TINTA, fontsize=fs_d, family=E.F_TXT, va="center")

    # ★ EL RECUADRO DE UBICACIÓN, DENTRO DEL MAPA. Estaba arriba a la derecha,
    #   mordiendo el ancho del titular y obligando a bajar el cuerpo de letra.
    #   Aquí abajo cumple mejor su oficio —está al lado del mapa que ubica, no
    #   en la otra punta de la lámina— y el título se queda con toda la columna.
    axm = fig.add_axes([M + .006, PIE + .021 + ALTO_PUNTAS, .078, .078])
    axm.set_facecolor(E.FONDO)
    # Va sin rótulo: un mapa de la región con un municipio pintado se explica
    # solo, y el renglón que lo nombraba sólo agregaba ruido en la esquina.
    minimapa(axm, g9, m["sigep"], E.VERDE_INS)

    # ══ DERECHA: la lectura, en una columna ═══════════════════
    # EL TITULAR: municipio primero, indicador después. La lámina viaja sola y
    # sin el lugar adelante el lector no sabe de dónde le están hablando.
    y = 1 - BARRA - .048
    W_TIT = W                    # el ancho entero: ya nada le disputa la esquina
    # El paréntesis del universo —"(19+)"— sale del titular: el subtítulo ya dice
    # "personas de 19 años o más", y arrastrado al final del título quedaba
    # huérfano en el segundo renglón. Sólo se quita si hay definición escrita:
    # sin ella el paréntesis es el único lugar donde el universo está dicho.
    etiqueta = i["label"]
    if clave in DEFINICION:
        etiqueta = re.sub(r"\s*\([^)]*\)\s*$", "", etiqueta)
    # EN UN SOLO RENGLÓN. Con el recuadro de ubicación adentro del mapa, la
    # columna quedó entera para el título, y el lugar y el tema se leen de un
    # tirón. El cuerpo baja hasta que entre —midiendo de verdad, no estimando—
    # y sólo se parte en dos si ni al mínimo alcanza.
    tramos = [(m["nombre"] + ":", E.VERDE_INS, E.F_TIT),
              (etiqueta, E.TINTA, E.F_TIT)]
    fs_tit = 26.0
    while fs_tit > 15 and parrafo(fig, X, y, tramos, fs_tit, .044,
                                  W_TIT, dibujar=False)[1] > 1:
        fs_tit -= 1.0
    y, _ = parrafo(fig, X, y, tramos, fs_tit, fs_tit*.00175, W_TIT)

    # EL SUBTÍTULO: qué mide, con letra chica. La jerarquía la da el CUERPO y no
    # el gris: en tinta plena y pequeño se lee sin competir con el titular.
    y -= .006
    y, _ = parrafo(fig, X, y, [(definicion(clave, i), E.TINTA, E.F_TXT)],
                   9.5, .0225, W)

    # filete: cierra el bloque del título sin encajonarlo
    y -= .014
    fig.add_artist(plt.Line2D([X, X + W*.42], [y, y],
                              transform=fig.transFigure, color=E.VERDE, lw=2))

    # ✂ SE FUE EL TITULAR "Entre sus manzanas va de X a Y". Decía en prosa lo
    #   que el gráfico de abajo dibuja mejor, y encima decía otra cosa: hablaba
    #   del p10 y el p90 llamándolos el desde y el hasta, cuando entre ellos
    #   queda el 80% central y no el rango. Ahora el rango se DIBUJA completo y
    #   el espacio que ocupaba el párrafo se lo lleva el gráfico.

    # dónde queda entre los nueve: escala inmediata sin leer el gráfico
    pos, tot, mej, peo = puesto_regional(s_["dist"], m["sigep"],
                                         {x["sigep"]: x["nombre"] for x in mun})
    if pos:
        y -= .050
        fig.text(X, y, str(pos) + ".\u00ba de " + str(tot) + " municipios",
                 color=E.VERDE_INS, fontsize=10.5, family=E.F_BOLD, va="top")
        if mej and peo:
            fig.text(X + .105, y, "\u00b7  del " + E.fmt(peo[1], u) + " de " + peo[0]
                     + " al " + E.fmt(mej[1], u) + " de " + mej[0],
                     color=E.TINTA, fontsize=9.5, family=E.F_TXT, va="top")

    # LAS DOS CIFRAS, comprimidas. Bajaron de 34 a 27 pt y los dos renglones de
    # abajo se juntaron: siguen siendo lo primero que se lee \u2014nada m\u00e1s en la
    # l\u00e1mina compite con ellas\u2014 y el alto que sueltan se lo lleva el gr\u00e1fico,
    # que es donde estaba la lectura apretada.
    y -= .042
    fig.text(X, y, E.fmt(d["p50"] if d else None, u), color=E.TINTA,
             fontsize=27, family=E.F_TIT, va="top")
    fig.text(X, y - .050, "MEDIANA DE SUS MANZANAS", color=E.VERDE_INS,
             fontsize=8.5, family=E.F_BOLD, va="top")
    fig.text(X, y - .069, "es lo que pinta el mapa", color=E.TINTA,
             fontsize=8.5, family=E.F_TXT, va="top")
    xd = X + W*.52
    fig.add_artist(plt.Line2D([xd - .028, xd - .028], [y - .078, y + .006],
                              transform=fig.transFigure, color=E.LINEA, lw=1))
    fig.text(xd, y, E.fmt(m["municipal"].get(clave), u), color=E.TINTA,
             fontsize=27, family=E.F_TIT, va="top")
    fig.text(xd, y - .050, "TODO EL MUNICIPIO", color=E.TINTA,
             fontsize=8.5, family=E.F_BOLD, va="top")
    fig.text(xd, y - .069, "incluye el \u00e1rea rural", color=E.TINTA,
             fontsize=8.5, family=E.F_TXT, va="top")

    # la rampa
    y -= .112
    fig.text(X, y, "COLOR DE CADA MANZANA", color=E.TINTA, fontsize=8.5,
             family=E.F_BOLD, va="top")
    fig.text(X + .152, y, "\u00b7  escala propia de " + m["nombre"],
             color=E.VERDE_INS, fontsize=8.5, family=E.F_MED, va="top")
    axl = fig.add_axes([X, y - .040, W, .017])
    axl.set_xticks([]); axl.set_yticks([])
    for lado in ("top", "right", "bottom", "left"):
        axl.spines[lado].set_visible(False)
    for t in range(260):
        f = t / 259
        axl.add_patch(Rectangle((f, 0), 1/260 + .002, 1, edgecolor="none",
                                facecolor=E.tono(esc["lo"] + (esc["hi"]-esc["lo"])*f, esc, D)))
    axl.set_xlim(0, 1); axl.set_ylim(0, 1)
    pp = E.pos_visual(esc["piv"], esc, D)
    axl.plot([pp, pp], [-.45, 1.45], color=E.TINTA, lw=1.2, clip_on=False, zorder=4)
    fig.text(X, y - .048,
             ("‹ " if esc.get("recorte_lo") else "") + E.fmt(esc["lo"], u),
             color=E.TINTA, fontsize=8.5, family=E.F_TXT, va="top")
    fig.text(X + W, y - .048,
             E.fmt(esc["hi"], u) + (" ›" if esc.get("recorte_hi") else ""),
             color=E.TINTA, fontsize=8.5, family=E.F_TXT, va="top", ha="right")
    # ★ EL RÓTULO DEL PIVOTE SE CORRE CUANDO CHOCA. En la rampa divergente el
    #   pivote cae siempre en la mitad y no molesta a nadie; en la secuencial
    #   cae donde el dato mande —la mediana de densidad de Warnes está al 18%
    #   de la barra— y se montaba encima del rótulo del extremo. Se mide, y si
    #   no entra abajo se escribe arriba, al lado de la nota de la escala.
    t_piv = esc.get("tipo", "mediana") + " " + E.fmt(esc["piv_real"], u)
    w_piv = ancho_de(fig, t_piv, 8.5, E.F_MED)
    w_lo = ancho_de(fig, E.fmt(esc["lo"], u), 8.5, E.F_TXT)
    w_hi = ancho_de(fig, E.fmt(esc["hi"], u), 8.5, E.F_TXT)
    x_piv = X + W*pp
    if (x_piv - w_piv/2) > (X + w_lo + .010) and (x_piv + w_piv/2) < (X + W - w_hi - .010):
        fig.text(x_piv, y - .048, t_piv, color=E.TINTA, fontsize=8.5,
                 family=E.F_MED, va="top", ha="center")
    else:
        fig.text(X + W, y, t_piv, color=E.TINTA, fontsize=8.5,
                 family=E.F_MED, va="top", ha="right")
    # ★ EL RECORTE SE DICE, NO SE CALLA. La rampa llega al mínimo y al máximo
    #   reales salvo que una manzana suelta la rompa —en `densidad` hay una de
    #   245 hab/ha contra un p90 de 79—; ahí el ángulo marca el corte y el valor
    #   verdadero va escrito. Sin esto la leyenda daría un rango más corto que
    #   el del gráfico de abajo, llamándose los dos "el rango".
    if esc.get("recorte_hi") or esc.get("recorte_lo"):
        fig.text(X + W, y - .068, "la rampa corta la cola — el rango real va de "
                 + E.fmt(esc["min"], u) + " a " + E.fmt(esc["max"], u),
                 color=E.TINTA, fontsize=7.5, family=E.F_TXT, va="top", ha="right")

    # la distribución de los nueve
    y -= .082
    fig.text(X, y, "C\u00d3MO SE REPARTE DENTRO DE CADA MUNICIPIO", color=E.TINTA,
             fontsize=8.5, family=E.F_BOLD, va="top")
    # El rengl\u00f3n "X va de A a B entre sus manzanas" se fue: los dos n\u00fameros
    # ahora van escritos en las puntas del hilo, dentro del gr\u00e1fico, que es
    # donde se leen sin tener que buscarlos.
    alto = y - .018 - (PIE + .026)
    axd = fig.add_axes([X + .120, PIE + .026, W - .120, alto])
    axd.set_facecolor(E.FONDO)
    for lado in ("top", "right", "left"):
        axd.spines[lado].set_visible(False)
    axd.spines["bottom"].set_color(E.LINEA)
    filas = sorted(s_["dist"].items(), key=lambda kv: -kv[1]["p50"])
    nom = {x["sigep"]: x["nombre"] for x in mun}

    # ★ EL EJE: rango completo, pero acotado cuando una sola manzana lo estira.
    #   El bigote p10-p90 cubre el 80% CENTRAL, no el rango, y llamarlo "de X a
    #   Y" era falso: quedaba fuera una manzana de cada diez en cada punta. Ahora
    #   se dibuja el mínimo y el máximo de verdad.
    #   ⚠️ Con el mínimo y el máximo crudos el eje se rompe: en `densidad` hay
    #   una manzana de 4.447 hab/ha contra un p90 de 220, y las nueve cajas
    #   quedarían apretadas en el 5% izquierdo. Cuando la cola se aleja más de
    #   1,2 veces el ancho del 80% central, el eje se corta ahí y las filas que
    #   siguen más allá se marcan con un ángulo — nunca en silencio.
    lo_p = min(x["p10"] for _, x in filas); hi_p = max(x["p90"] for _, x in filas)
    lo_t = min(x.get("min", x["p10"]) for _, x in filas)
    hi_t = max(x.get("max", x["p90"]) for _, x in filas)
    span = (hi_p - lo_p) or (abs(hi_p) * .1 or 1)
    lo = lo_t if (lo_p - lo_t) <= span*1.2 else lo_p - span*.25
    hi = hi_t if (hi_t - hi_p) <= span*1.2 else hi_p + span*.25
    if hi <= lo:
        hi = lo + 1
    cortado = False
    # ★ LOS DOS EXTREMOS, ESCRITOS SOBRE CADA HILO. Sin número, el hilo dice
    #   que hay cola pero no cuánta, y había que ir a buscar el eje. Van arriba
    #   de la línea y no en la punta: en la punta se salían del cuadro.
    #   Se mide cuánto ocupa cada rótulo EN UNIDADES DEL DATO para saber si los
    #   dos entran; cuando el rango es angosto se cae el mínimo y queda el
    #   máximo, que es el que casi siempre sorprende.
    ancho_eje = (W - .105) * 16.0                      # pulgadas reales del eje
    dato_x_pulgada = ((hi + (hi-lo)*.03) - lo) / max(ancho_eje, .01)

    def ancho_dato(txt, fs):
        return ancho_de(fig, txt, fs, E.F_TXT) * 16.0 * dato_x_pulgada

    for n, (sg, dd) in enumerate(filas):
        yy = len(filas) - n
        propio = sg == m["sigep"]
        vmin = dd.get("min", dd["p10"]); vmax = dd.get("max", dd["p90"])
        x_ini, x_fin = max(vmin, lo), min(vmax, hi)
        # 1 · el rango entero, en hilo fino
        axd.plot([x_ini, x_fin], [yy, yy], color="#b9c0ba", lw=.7, zorder=1)
        # el ángulo avisa que la fila sigue más allá del eje
        recorte_izq = vmin < lo - 1e-9
        recorte_der = vmax > hi + 1e-9
        for hay, lim, mk in ((recorte_izq, lo, "<"), (recorte_der, hi, ">")):
            if hay:
                axd.plot([lim], [yy], marker=mk, ms=3.4, color="#8a938c",
                         zorder=4, clip_on=False)
                cortado = True
        # los dos números del hilo
        fs_r = 7.0 if propio else 6.5
        fam_r = E.F_SEMI if propio else E.F_TXT
        t_min = ("‹ " if recorte_izq else "") + E.fmt(vmin, u)
        t_max = E.fmt(vmax, u) + (" ›" if recorte_der else "")
        # El mínimo se escribe siempre en la fila de la lámina; en las otras,
        # sólo si se despega del arranque del eje. Casi todos los mínimos son 0
        # y nueve "0 hab/ha" repetidos son ruido, no información.
        entran = (ancho_dato(t_min, fs_r) + ancho_dato(t_max, fs_r)) * .60 <= (x_fin - x_ini)
        vale = propio or recorte_izq or (vmin - lo) > (hi - lo) * .02
        if entran and vale:
            axd.text(x_ini, yy + .36, t_min, ha="left", va="bottom",
                     fontsize=fs_r, color=E.TINTA, family=fam_r, zorder=5)
        # El máximo sigue la misma regla que el mínimo: se escribe en la fila
        # de la lámina, cuando la fila se sale del eje, o cuando se despega del
        # tope. Casi todos los municipios llegan a 100% y nueve «100,0%»
        # apilados en columna son ruido, no información.
        if propio or recorte_der or (hi - vmax) > (hi - lo) * .02:
            axd.text(x_fin, yy + .36, t_max, ha="right", va="bottom",
                     fontsize=fs_r, color=E.TINTA, family=fam_r, zorder=5)
        # 2 · el 80% central, en trazo grueso
        axd.plot([dd["p10"], dd["p90"]], [yy, yy], color="#7f8a82", lw=1.8, zorder=2)
        # 3 · la mitad más común
        axd.add_patch(Rectangle((dd["p25"], yy - .21),
                                max(dd["p75"]-dd["p25"], (hi-lo)*.004), .42,
                                facecolor=E.VERDE_INS if propio else "#c4cdc6",
                                edgecolor="none", zorder=3))
        # 4 · la mediana
        axd.plot([dd["p50"]]*2, [yy-.29, yy+.29],
                 color=E.TINTA, lw=1.7 if propio else 1.3, zorder=4)
        axd.text(-.025, yy, nom.get(sg, ""), ha="right", va="center",
                 transform=axd.get_yaxis_transform(), fontsize=10, color=E.TINTA,
                 family=E.F_BOLD if propio else E.F_TXT)
    axd.set_xlim(lo, hi + (hi-lo)*.03); axd.set_ylim(.35, len(filas)+.75)
    axd.set_yticks([])
    axd.tick_params(axis="x", colors=E.TINTA, labelsize=8, length=0, pad=3)
    for lbl in axd.get_xticklabels():
        lbl.set_family(E.F_TXT)
    # la leyenda del gráfico, en una línea al pie del propio gráfico
    # La leyenda entra en un rengl\u00f3n midi\u00e9ndola, no a ojo: con el cuerpo fijo se
    # pasaba del margen y el \u00faltimo tramo \u2014justo el que explica el \u00e1ngulo\u2014 se
    # cortaba fuera del lienzo sin que nada lo delatara.
    ley = ("hilo: rango entero, con sus extremos   \u00b7   trazo: 80% central   \u00b7   "
           "caja: mitad m\u00e1s com\u00fan   \u00b7   marca: mediana")
    if cortado:
        ley += "   \u00b7   \u203a  sigue m\u00e1s all\u00e1"
    fs_l = 8.0
    while fs_l > 6.5 and ancho_de(fig, ley, fs_l, E.F_TXT) > W:
        fs_l -= .25
    fig.text(X, PIE + .004, ley, color=E.TINTA, fontsize=fs_l, family=E.F_TXT, va="top")

    # ══ PIE ══════════════════════════════════════════════════════════════
    # A ras del papel, la ficha técnica se leía como un renglón más de la
    # explicación del gráfico. Sobre su propia franja se reconoce de un vistazo
    # como lo que es —universo, fuente, autoría— y deja de disputarle atención
    # al dato. Es un crema apenas más profundo, no un gris: un gris ahí abre un
    # segundo plano y ensucia la lámina entera.
    fig.add_artist(Rectangle((0, 0), 1, PIE - .006, transform=fig.transFigure,
                             facecolor=E.PIE_BANDA, edgecolor="none", zorder=0))
    cob = ("Poblaci\u00f3n y densidad tienen dato en las 38.892 manzanas del \u00e1rea urbana censada."
           if clave in ("densidad", "pob_total") else
           "En gris, las manzanas sin ficha: el INE las suprime por privacidad. Son 25.698 "
           "con ficha de 38.892, y concentran el 93,8% de la poblaci\u00f3n de la regi\u00f3n.")
    if fuera:
        cob += "  El cuadro se ajusta a la mancha principal: " + str(fuera) + \
               (" manzana queda" if fuera == 1 else " manzanas quedan") + " fuera."
    fs_c = 8.5
    while fs_c > 6.0 and ancho_de(fig, cob, fs_c, E.F_TXT) > 1 - 2*M:
        fs_c -= .25
    y1 = PIE - .040
    E.cursiva(fig, fig.text(M, y1, cob, color=E.GRIS_PIE, fontsize=fs_c,
                            family=E.F_TXT, va="center", zorder=2), M, y1)
    # La autor\u00eda, tal como la pidi\u00f3 Carlos: el Didam elabora, y las dos fuentes
    # quedan nombradas. La sigla se abre una vez ac\u00e1 porque la l\u00e1mina viaja sola
    # y afuera de la Gobernaci\u00f3n nadie tiene por qu\u00e9 saber qu\u00e9 es el Didam.
    y2 = PIE - .068
    E.cursiva(fig, fig.text(
        M, y2, "Elaboración Didam (Dirección de la Instancia Departamental de "
        "Asuntos Metropolitanos) en base a CPV 2024 — INE y POPULI",
        color=E.GRIS_PIE, fontsize=8.5, family=E.F_TXT, va="center", zorder=2),
        M, y2)
    E.cursiva(fig, fig.text(
        1-M, y2, "didamsantacruz-eng.github.io/scz-metropoli-encifras",
        color=E.GRIS_PIE, fontsize=8, family=E.F_TXT, va="center",
        ha="right", zorder=2), 1-M, y2)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, facecolor=E.FONDO, dpi=DPI)
    plt.close(fig)
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--municipio", default="santa_cruz_de_la_sierra")
    ap.add_argument("--indicador", default="pct_alcantarillado")
    ap.add_argument("--todas", action="store_true")
    a = ap.parse_args()
    ind, mun, st = cargar()
    if a.todas:
        n = 0
        for m in mun:
            sl = slug(m["nombre"])
            for k in INDICADORES:
                if k not in ind or k not in st:
                    continue
                lamina(sl, k, ind, mun, st, SALIDA / f"{sl}__{k}.png")
                n += 1
                print(f"  {n:>3}  {sl} · {k}")
        print(f"\n{n} láminas -> {SALIDA}")
    else:
        p = lamina(a.municipio, a.indicador, ind, mun, st,
                   SALIDA / f"{a.municipio}__{a.indicador}.png")
        print(f"-> {p}")


if __name__ == "__main__":
    main()
