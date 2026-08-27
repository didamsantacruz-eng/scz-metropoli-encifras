# -*- coding: utf-8 -*-
"""
BANCO DE LÁMINAS — un municipio, un indicador, a nivel manzana.
================================================================

Cada lámina responde tres preguntas sobre el mismo dato, que es lo que una
imagen suelta necesita para poder viajar sin el tablero al lado:

  1. **Dónde** — el mapa de las manzanas de ese municipio.
  2. **Cómo se reparte adentro** — el CUADRO de los nueve municipios: cuántas
     manzanas tiene cada uno con ficha y en qué valores caen su mínimo, su
     primer cuarto, su mediana, su tercer cuarto y su máximo. Es la lectura
     que el promedio municipal esconde: en 57 de los 91 indicadores la
     desigualdad DENTRO de un municipio supera todo el rango ENTRE los nueve.
     Hasta 2026-08-27 esto era una tira de cajas y bigotes; se cambió por un
     cuadro porque obligaba a traducir una leyenda de cuatro trazos antes de
     poder leer un número, y los valores sólo salían impresos en las puntas.
  3. **Contra qué se compara** — la cifra del municipio y la de la región.

⚠️ LA COBERTURA VA ESCRITA EN LA LÁMINA. El INE suprime la ficha de las
   manzanas más chicas por privacidad, así que en la mayoría de los indicadores
   un tercio del territorio va en gris. En pantalla el lector puede pasar el
   mouse y enterarse; en una imagen que viaja sola, si no está escrito, el gris
   se lee como "acá no vive nadie".

    python sistema-graficos/motor/lamina_manzana.py [--municipio SLUG] [--indicador CLAVE]
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


# ✂ SE FUERON `tituloCaso`, `perfil_localidades` y `puesto_regional`
#   (2026-08-20). Servían a las dos piezas que Carlos sacó de la lámina: la
#   banda «POR LOCALIDAD, DENTRO DE …» bajo el mapa y el renglón «N.º de 9
#   municipios · del X al Y» sobre las cifras. Sin ellas no quedaba ningún
#   consumidor, y código muerto con explicación larga se lee como código vivo.
#   El perfil por localidad seguía estando bien calculado: si alguna vez vuelve,
#   está en el historial de este archivo.

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

    # ══ IZQUIERDA: el mapa, con todo el aire ═════════════════════════════
    # ✂ SE FUE LA BANDA «POR LOCALIDAD, DENTRO DE …» (pedido de Carlos,
    #   2026-08-20). Ocupaba .062 de alto bajo el mapa para nombrar el núcleo y
    #   los dos satélites. El mapa se queda con ese espacio: es la pieza que
    #   justifica la lámina y ahora llega hasta la banda del pie.
    ax = fig.add_axes([M, PIE + .015, COL_IZQ,
                       1 - BARRA - PIE - .045])
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

    # ★ EL RECUADRO DE UBICACIÓN, DENTRO DEL MAPA. Estaba arriba a la derecha,
    #   mordiendo el ancho del titular y obligando a bajar el cuerpo de letra.
    #   Aquí abajo cumple mejor su oficio —está al lado del mapa que ubica, no
    #   en la otra punta de la lámina— y el título se queda con toda la columna.
    axm = fig.add_axes([M + .006, PIE + .021, .078, .078])
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

    # ✂ SE FUE «N.º de 9 municipios · del X de A al Y de B» (pedido de Carlos,
    #   2026-08-20). Era un renglón de ranking encima de las dos cifras; el
    #   gráfico de distribución de abajo ya ordena los nueve y muestra dónde
    #   cae éste, sin pedirle al lector que cruce dos lecturas. El alto que
    #   suelta se lo lleva ese gráfico, que es donde estaba apretado.

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
        # la barra va por POSICIÓN DE RAMPA, igual que el degradé del
        # tablero: así el pivote ES la mitad y la marca de abajo
        # señala su propio color
        axl.add_patch(Rectangle((f, 0), 1/260 + .002, 1, edgecolor="none",
                                facecolor=E.tono_en(f, D)))
    axl.set_xlim(0, 1); axl.set_ylim(0, 1)
    pp = E.pos_visual(esc["piv"], esc, D)
    axl.plot([pp, pp], [-.45, 1.45], color=E.TINTA, lw=1.2, clip_on=False, zorder=4)
    fig.text(X, y - .048,
             ("‹ " if esc.get("recorte_lo") else "") + E.fmt(esc["lo"], u),
             color=E.TINTA, fontsize=8.5, family=E.F_TXT, va="top")
    fig.text(X + W, y - .048,
             E.fmt(esc["hi"], u) + (" ›" if esc.get("recorte_hi") else ""),
             color=E.TINTA, fontsize=8.5, family=E.F_TXT, va="top", ha="right")
    # ★ EL RÓTULO DEL PIVOTE SE CORRE CUANDO CHOCA con el del mínimo o el del
    #   máximo. Desde que la barra va por posición de rampa (2026-08-20) la MARCA
    #   cae siempre en la mitad —que es lo que los comentarios de antes ya daban
    #   por sentado, y no era cierto—; lo que se sale de sitio es el TEXTO.
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
    hay_nota_recorte = bool(esc.get("recorte_hi") or esc.get("recorte_lo"))
    if hay_nota_recorte:
        fig.text(X + W, y - .068, "la rampa corta la cola — el rango real va de "
                 + E.fmt(esc["min"], u) + " a " + E.fmt(esc["max"], u),
                 color=E.TINTA, fontsize=7.5, family=E.F_TXT, va="top", ha="right")

    # la distribución de los nueve
    # ⚠️ EL SALTO DEPENDE DE SI HUBO NOTA DE RECORTE. Con .082 fijo, cuando la
    #   nota estaba el rótulo de acá abajo le quedaba a 2 px —medido: la nota
    #   ocupa .0116 de figura y arrancaba en −.068, o sea que terminaba en
    #   −.0796—, y los dos renglones se leían pegados. Sin nota, .082 es el aire
    #   correcto y agrandarlo sería regalarle alto al gráfico de abajo.
    y -= .096 if hay_nota_recorte else .082
    fig.text(X, y, "DISTRIBUCI\u00d3N DENTRO DE CADA MUNICIPIO", color=E.TINTA,
             fontsize=8.5, family=E.F_BOLD, va="top")
    # ★ EL RÓTULO DE LA DERECHA DICE LAS DOS COSAS QUE NINGUNA COLUMNA PUEDE
    #   DECIR: en qué orden vienen las filas y en qué unidad están las cifras.
    #   Sin lo primero el orden se lee como arbitrario; sin lo segundo habría
    #   que repetir «%» —o peor, «hab/ha»— cincuenta y cuatro veces.
    u_txt = {"%": "%", "hab": "personas",
             "hab/ha": "habitantes por hectárea"}.get(u, u)
    fig.text(X + W, y, "ordenados por su mediana  ·  cifras en " + u_txt,
             color=E.SUAVE, fontsize=8, family=E.F_MED, va="top", ha="right")

    # ══ EL CUADRO ════════════════════════════════════════════════════════
    # ✂ SE FUE LA TIRA DE CAJAS Y BIGOTES (pedido de Carlos, 2026-08-27).
    #   Un solo renglón codificaba cuatro cosas a la vez —hilo fino, trazo
    #   grueso, caja y marca— y había que traducir una leyenda antes de poder
    #   leer un número. Los valores, además, sólo salían impresos en las
    #   puntas, y ni siquiera en todas las filas: la regla los escondía cuando
    #   no entraban. El cuadro dice exactamente lo mismo con los números
    #   puestos, uno por celda, y no deja nada que decodificar.
    #
    # ★ LAS COLUMNAS SE NOMBRAN EN CASTELLANO, NO EN PERCENTILES. «p25» hay
    #   que saberlo de antes; «1 de cada 4» se entiende leyéndolo. Y «25%»
    #   —la abreviatura obvia— acá es la peor opción de las tres: casi todos
    #   estos indicadores YA se miden en por ciento y el encabezado se
    #   confundiría con la unidad del dato.
    filas = sorted(s_["dist"].items(), key=lambda kv: -kv[1]["p50"])
    nom = {x["sigep"]: x["nombre"] for x in mun}

    # forma corta de la unidad, la que entra en una frase corrida
    u_frase = {"%": "%", "hab": " personas"}.get(u, (" " + u) if u else "")

    def num(v):
        """El valor SIN su unidad y con los MISMOS decimales en toda la columna.

        Dos reglas, y las dos son de cuadro y no de cifra suelta:

        · LA UNIDAD SE ESCRIBE UNA VEZ, en el rótulo. Repetida en las 54
          celdas —«4.447 hab/ha»— la columna deja de ser una columna.

        · LOS DECIMALES SE DECLARAN POR UNIDAD, no se deducen del tamaño de
          cada número. `E.fmt` los elige por magnitud —cero decimales de 100
          para arriba, uno para abajo—, que es lo correcto para una cifra
          suelta y veneno para una columna: dejaba «118» pegado a «77,5» y
          las dos cifras parecían medidas con distinta precisión. Acá los
          conteos van enteros y todo lo demás con un decimal, de arriba abajo.
        """
        if v is None:
            return "s/d"
        dec = 0 if u in ("hab", "viv") else 1
        return f"{v:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")

    def val(v, unidad=True):
        """La misma cifra del cuadro, para citarla en la frase de lectura: si
        el cuadro dice 77,1 la frase no puede decir 77."""
        return num(v) + (u_frase if unidad else "")

    # ── el renglón que enseña a leer el cuadro ───────────────────────────
    # ★ SE ARMA CON LOS DATOS DE ESTA LÁMINA, no es una nota genérica. Lee en
    #   voz alta la fila propia —la única que el lector ya tiene ubicada— y
    #   con eso quedan aprendidas las otras ocho. Una leyenda que nombra
    #   trazos enseña a mirar; una frase con los números adentro enseña a leer.
    ALTO_TXT = 8.5 / 72 / 9          # alto de un renglón a cuerpo 8,5, en figura
    SALTO = ALTO_TXT * 1.42
    p50s = [x["p50"] for _, x in filas]
    # sin ninguna fila no hay cuadro que armar: se dice y se sale, en vez de
    # dejar el hueco mudo o reventar en un max() de lista vacía
    if not p50s:
        fig.text(X, y - .040, "Sin manzanas suficientes para repartir este "
                 "indicador.", color=E.SUAVE, fontsize=9, family=E.F_TXT,
                 va="top")
        p50s = [0]
    rango_med = max(p50s) - min(p50s)

    def dif(v):
        """Una diferencia entre porcentajes se mide en PUNTOS, no en por
        ciento: decir «21,3%» de brecha sería otra cifra y otra cosa."""
        return num(v) + (" pp" if u == "%" else u_frase)

    if d:
        brecha = d["p75"] - d["p25"]
        # `E.fmt(n, "hab")` es el formateo de conteo —miles con punto y sin
        # sufijo—, que es justo lo que necesita un recuento de manzanas.
        tramos = [
            ("Cómo se lee:", E.TINTA, E.F_BOLD),
            ("en " + m["nombre"] + ", la mitad de sus " + E.fmt(d["n"], "hab") +
             " manzanas con ficha no pasa de " + val(d["p50"]) +
             "; la más baja marca " + val(d["min"], False) +
             " y la más alta, " + val(d["max"], False) + ".",
             E.TINTA, E.F_TXT, True),
            ("La mitad del medio", E.TINTA, E.F_SEMI),
            ("de sus manzanas abarca " + dif(brecha) +
             ", y entre las medianas de los nueve municipios hay " +
             dif(rango_med) + ": " +
             ("adentro de un solo municipio el dato se reparte más desigual "
              "que entre los nueve."
              if brecha > rango_med else
              "acá la distancia entre municipios pesa más que la de adentro."),
             E.TINTA, E.F_TXT),
        ]
    else:
        # sin ficha suficiente para deciles no se inventa una lectura: se dice
        tramos = [
            ("Cómo se lee:", E.TINTA, E.F_BOLD),
            ("cada fila reparte las manzanas de un municipio de menor a mayor. "
             "La mediana parte el grupo en dos mitades; entre «1 de cada 4» y "
             "«3 de cada 4» cae la mitad del medio.", E.TINTA, E.F_TXT),
        ]
    _, n_ln = parrafo(fig, X, 0, tramos, 8.5, SALTO, W, dibujar=False)
    # La última línea tiene que APOYAR sobre la franja del pie, no meterse
    # adentro: el párrafo baja desde su techo, así que el techo se calcula
    # hacia arriba desde el suelo y no al revés.
    Y_LECTURA = PIE + .014 + ALTO_TXT + SALTO * (n_ln - 1)
    parrafo(fig, X, Y_LECTURA, tramos, 8.5, SALTO, W)

    # ── la grilla del cuadro ─────────────────────────────────────────────
    BASE = Y_LECTURA + .018          # suelo del cuadro
    TOP = y - .030                   # techo, bajo el rótulo de la sección
    H_BANDA = .019                   # franja del rótulo «aquí cae la mitad…»
    H_ENC = .021                     # renglón de los rótulos de columna
    h_fila = (TOP - BASE - H_BANDA - H_ENC) / max(len(filas), 1)

    # ★ EL ANCHO DEL CANAL DEL NOMBRE SE MIDE, NO SE TANTEA: «Santa Cruz de
    #   la Sierra» a cuerpo 9,5 en negrita es el más largo de los nueve.
    w_nom = ancho_de(fig, "Santa Cruz de la Sierra", 9.5, E.F_BOLD) + .012
    w_n = .052                       # la columna del recuento, más angosta
    w_val = (W - w_nom - w_n) / 5    # las cinco cifras, todas iguales
    xr = [X + w_nom + w_n]           # borde derecho de cada columna
    xr += [xr[0] + w_val * (k + 1) for k in range(5)]
    PAD = .007                       # aire a la derecha de cada cifra

    # ★ LA MITAD DEL MEDIO, PINTADA. Es el único recurso gráfico que queda, y
    #   hace el trabajo que hacía la caja gris: agrupa las tres columnas del
    #   centro para que se lean como un tramo y no como tres cifras sueltas.
    #   Es el crema del pie —no un gris—: un gris acá abriría un segundo plano
    #   sobre el fondo y ensuciaría la lámina entera.
    fig.add_artist(Rectangle((xr[1], BASE), xr[4] - xr[1], TOP - BASE,
                             transform=fig.transFigure, facecolor=E.PIE_BANDA,
                             edgecolor="none", zorder=0))
    fig.text((xr[1] + xr[4]) / 2, TOP - H_BANDA * .55,
             "AQUÍ CAE LA MITAD DE SUS MANZANAS", color=E.SUAVE,
             fontsize=7.5, family=E.F_BOLD, ha="center", va="center", zorder=3)

    # ── los rótulos de columna ───────────────────────────────────────────
    y_enc = TOP - H_BANDA - H_ENC * .52
    fig.text(X, y_enc, "MUNICIPIO", color=E.SUAVE, fontsize=7.5,
             family=E.F_BOLD, ha="left", va="center", zorder=3)
    ENC = ["MANZANAS", "MÍNIMO", "1 DE CADA 4", "MEDIANA", "3 DE CADA 4",
           "MÁXIMO"]
    # ★ EL CUERPO DE LOS RÓTULOS SE MIDE CONTRA LA COLUMNA, no se elige. A 7,5
    #   «3 DE CADA 4» ocupa .66" en una columna de .78" y con el aire de la
    #   derecha quedaba a dos décimas de milímetro de la cifra de al lado.
    fs_enc = 7.5
    while fs_enc > 6.0 and max(ancho_de(fig, e, fs_enc, E.F_BOLD)
                               for e in ENC) > w_val - PAD * 1.6:
        fs_enc -= .25
    for k, t in enumerate(ENC):
        # la mediana es la columna que manda —ordena las filas y es la cifra
        # grande de arriba—, así que su rótulo va en tinta y no en gris
        fig.text(xr[k] - PAD, y_enc, t, color=E.TINTA if k == 3 else E.SUAVE,
                 fontsize=fs_enc, family=E.F_BOLD, ha="right", va="center",
                 zorder=3)
    y_filas = TOP - H_BANDA - H_ENC
    fig.add_artist(plt.Line2D([X, X + W], [y_filas, y_filas],
                              transform=fig.transFigure, color=E.LINEA, lw=.9,
                              zorder=2))

    # ── las nueve filas ──────────────────────────────────────────────────
    for n_, (sg, dd) in enumerate(filas):
        yc = y_filas - h_fila * (n_ + .5)
        propio = sg == m["sigep"]
        if propio:
            # ★ LA FILA PROPIA SE MARCA POR COLOR, no por peso: los nueve
            #   nombres van en negrita (pedido del 2026-08-20) y el verde
            #   institucional ya es el de su caja en el resto de la lámina.
            fig.add_artist(Rectangle((X - .009, yc - h_fila * .5), W + .011,
                                     h_fila, transform=fig.transFigure,
                                     facecolor=E.VERDE_INS, alpha=.12,
                                     edgecolor="none", zorder=1))
        elif n_:
            fig.add_artist(plt.Line2D([X, X + W], [yc + h_fila * .5] * 2,
                                      transform=fig.transFigure, color=E.LINEA,
                                      lw=.5, alpha=.8, zorder=2))
        tinta = E.VERDE_INS if propio else E.TINTA
        fig.text(X, yc, nom.get(sg, ""), color=tinta, fontsize=9.5,
                 family=E.F_BOLD, ha="left", va="center", zorder=3)
        celdas = [E.fmt(dd["n"], "hab"), num(dd["min"]), num(dd["p25"]),
                  num(dd["p50"]), num(dd["p75"]), num(dd["max"])]
        for k, t in enumerate(celdas):
            # el recuento es contexto, no dato: va en gris para que las cinco
            # cifras de la derecha queden solas en el primer plano
            if k == 0:
                c, f = E.SUAVE, E.F_TXT
            else:
                c = tinta if (propio or k == 3) else E.TINTA
                f = E.F_SEMI if (propio or k == 3) else E.F_TXT
            fig.text(xr[k] - PAD, yc, t, color=c, fontsize=9.5, family=f,
                     ha="right", va="center", zorder=3)
    fig.add_artist(plt.Line2D([X, X + W], [BASE, BASE], transform=fig.transFigure,
                              color=E.LINEA, lw=.9, zorder=2))

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
    # La autor\u00eda, tal como la pidi\u00f3 Carlos: el DIDAM elabora, y las dos fuentes
    # quedan nombradas. La sigla va en MAY\u00daSCULAS y con dos puntos despu\u00e9s de
    # "Elaboraci\u00f3n" (pedido del 2026-08-20), igual que en la l\u00e1mina municipal;
    # se abre una vez ac\u00e1 porque la l\u00e1mina viaja sola y afuera de la Gobernaci\u00f3n
    # nadie tiene por qu\u00e9 saber qu\u00e9 es el DIDAM.
    y2 = PIE - .068
    E.cursiva(fig, fig.text(
        M, y2, "Elaboración: DIDAM (Dirección de la Instancia Departamental de "
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
