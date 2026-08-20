# -*- coding: utf-8 -*-
"""
BANCO DE LÁMINAS MUNICIPALES — un indicador, los nueve municipios.
==================================================================

Es el gemelo del banco por manzana, y la unidad cambia de raíz: allá la lámina
era un municipio por dentro; acá es **un indicador** y los nueve municipios
comparados. Por eso sale una lámina por indicador y no una por par.

Y trae lo que el nivel manzana no puede tener: **el censo 2012**. Las fichas por
manzano existen sólo para 2024, así que la comparación intercensal vive
únicamente acá. Es el corazón de la lámina — la mancuerna 2012 → 2024 — y lo que
convierte un ranking en una historia.

⚠️⚠️ LAS TRES REGLAS QUE NO SE PUEDEN SALTAR
────────────────────────────────────────────
1. **El agregado regional viene DECLARADO, no se recalcula.** `armar_tableros.py`
   pondera cada indicador por SU PROPIO universo —un porcentaje de viviendas por
   viviendas, no por personas— y lo embarca en `catalogo_municipal.json` →
   `region`. El tablero ya cometió el error de recalcularlo ponderando todo por
   población: `emigrantes_x1000` salía 26,4‰ en vez de 28,5‰, un 8% de error.
2. **Ese agregado NO vale para un conteo** (`agg == "suma"`). Promediar población
   ponderando por población da Σp²/Σp, que es "el tamaño del municipio de la
   persona promedio" y no le sirve a nadie. La magnitud regional de un conteo es
   la SUMA, y el centro de la rampa es la MEDIANA de los nueve.
3. **La comparación con 2012 sólo si el catálogo la declara** (`s12`). Hay 63
   indicadores donde el dato existe pero los universos de los dos censos no son
   el mismo, y el catálogo lo dice en `w12`. Restar dos números que se llaman
   igual pero no miden lo mismo es el error de siempre: la presencia se mide, la
   comparabilidad se DECLARA. Ver [[reference_declarar-no-inferir]].

El bloque **Fiscal** (30 indicadores) queda fuera a propósito: no vive en
`municipal[]` sino en `fiscal.json`, como serie 2016-2025, y pide otra lámina.

    python scripts/banco/lamina_municipal.py [--indicador CLAVE] [--todas]
"""
import argparse, json, math, pathlib, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Polygon as MplPoly, Rectangle, Circle
from matplotlib.collections import PatchCollection
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import estilo as E
from lamina_manzana import (RAIZ, DATOS, DPI, anillos, centroide, logo_nitido,
                            ancho_de, parrafo, DEFINICION)

SALIDA = RAIZ / "docs" / "banco" / "municipal"


def cargar():
    cat = json.loads((DATOS / "catalogo_municipal.json").read_text(encoding="utf-8"))
    mun = json.loads((DATOS / "municipios_municipal.json").read_text(encoding="utf-8"))
    geo = json.loads((DATOS / "municipios.geojson").read_text(encoding="utf-8"))
    ind, grupo = {}, {}
    for g in cat["grupos"]:
        for i in g["indicadores"]:
            ind[i["key"]] = i
            grupo[i["key"]] = g["label"]
    return cat, ind, grupo, mun, geo


def indicadores_censales(ind, grupo, mun):
    """Los que tienen dato para LOS NUEVE. Se excluye el bloque fiscal, que no
    vive en `municipal[]` sino en su propia serie por año."""
    out = []
    for k, i in ind.items():
        if grupo[k].startswith("Fiscal"):
            continue
        if sum(1 for m in mun if m["municipal"].get(k) is not None) == 9:
            out.append(k)
    return sorted(out)


def valores(clave, mun, anio="municipal"):
    return {m["sigep"]: m.get(anio, {}).get(clave) for m in mun}


def agregado(clave, ind, mun, reg, anio="municipal"):
    """★ El número de la región. SUMA si es conteo, y si no el promedio
    ponderado que ya viene calculado en el catálogo. Nunca uno recalculado acá:
    ponderar todo por población es exactamente el error que ya se cometió."""
    if ind.get("agg") == "suma":
        v = [x for x in valores(clave, mun, anio).values() if x is not None]
        return sum(v) if len(v) == 9 else None
    return reg.get(anio, {}).get(clave)


def definicion(clave, i):
    """Qué mide, en una línea. Para los 18 que ya tienen definición escrita a
    mano en el banco por manzana se usa esa —es mejor que cualquier automática—
    y para el resto el universo que declara el catálogo, que es el dato donde de
    verdad se cometen los errores de lectura.
    Nunca se inventa: si el catálogo no dice nada, la lámina dice menos."""
    if clave in DEFINICION:
        return DEFINICION[clave] + ", por municipio"
    d = (i.get("desc") or "").strip()
    if not d:
        return "Por municipio"
    # `desc` suele ser "<etiqueta>. <universo>." y la etiqueta ya es el título
    partes = [p.strip() for p in d.split(".") if p.strip()]
    if partes and partes[0].lower().rstrip(" (0-9+)") == i["label"].lower().rstrip(" (0-9+)"):
        partes = partes[1:]
    if not partes:
        partes = [d.rstrip(".")]
    return ". ".join(partes).rstrip(".") + ", por municipio"


def cambio(v24, v12, es_conteo):
    """La variación intercensal. Un conteo cambia en PORCENTAJE —"creció 38%"—
    y una tasa en PUNTOS —"subió 8,7 pp". Mezclarlos es el error que ya costó
    caro en `comparar_niveles.py`, que reportaba 3.420 pp de brecha en población
    porque trataba personas como si fueran porcentaje."""
    if v24 is None or v12 is None:
        return None, None
    if es_conteo:
        return (100 * (v24 - v12) / v12 if v12 else None), "%"
    return v24 - v12, "pp"


def signo(v, u):
    if v is None:
        return "s/d"
    s = E.fmt(abs(v), u)
    return ("+" if v > 0 else ("−" if v < 0 else "")) + s


# ★ DÓNDE VA EL RÓTULO DE CADA MUNICIPIO. La geometría de los nueve NO CAMBIA
#   nunca —cambian los colores y las cifras, no el mapa—, así que las posiciones
#   se resuelven una vez y quedan bien en las 213 láminas.
#   Van RELATIVAS al rectángulo que encierra la región (0 a 1), así que no
#   dependen de la proyección ni del encuadre.
#
#   ⚠️⚠️ EL BUG QUE ESTO ARREGLA: antes la guía salía del PROMEDIO DE LOS
#   VÉRTICES del polígono, y ese punto no tiene por qué caer adentro — depende
#   de dónde el borde tenga más vértices. En Santa Cruz de la Sierra caía en
#   (.253, .403), que está prácticamente encima de Cotoca: la lámina publicaba
#   una flecha que decía «Santa Cruz de la Sierra» apuntando al municipio
#   vecino. `ANCLA` guarda el POLO DE INACCESIBILIDAD —el punto más adentro que
#   existe, el que maximiza la distancia al borde— calculado por barrido de
#   grilla sobre el anillo de mayor área.
POLO = {
    "1714": (.794, .419),   # Pailón
    "1706": (.223, .644),   # Warnes
    "1703": (.108, .425),   # Porongo
    "1705": (.075, .177),   # El Torno
    "1704": (.159, .265),   # La Guardia
    "1702": (.298, .421),   # Cotoca
    "1734": (.148, .760),   # Montero
    "1756": (.141, .596),   # Colpa Bélgica
    "1701": (.290, .275),   # Santa Cruz de la Sierra
}
#   Tres no entran en su propio polígono y salen con guía: Santa Cruz de la
#   Sierra —cuyo nombre es tres veces más ancho que el municipio—, Colpa Bélgica
#   y Montero, que se pisaba con Warnes. Los otros seis van sobre su polo.
FUERA = {
    "1701": (.430, .075),
    "1756": (-.050, .640),
    "1734": (.098, .885),
}
# El encuadre deja aire a la izquierda y arriba para los rótulos con guía
VISTA = (-.09, 1.03, -.05, 1.02)
ASPECTO_MAPA = 2.11          # ancho/alto de la VISTA, medido sobre la geometría


def mapa_nueve(ax, geo, vals, esc, D, tr=lambda v: v, unidad=""):
    """Coropleta de los nueve, con el nombre y la cifra encima de cada uno.

    Con nueve polígonos el etiquetado directo le gana a cualquier leyenda: el
    ojo no tiene que ir y volver a una escala de colores para saber quién es
    quién ni cuánto tiene."""
    ax.set_xticks([]); ax.set_yticks([])
    for lado in ("top", "right", "bottom", "left"):
        ax.spines[lado].set_visible(False)
    parches, colores, xs, ys = [], [], [], []
    for f in geo["features"]:
        v = vals.get(f["properties"].get("sigep"))
        c = E.tono(tr(v) if v is not None else None, esc, D)
        for anillo in anillos(f.get("geometry")):
            parches.append(MplPoly(anillo, closed=True)); colores.append(c)
            for x, y in anillo:
                xs.append(x); ys.append(y)
    # ⚠️ El contorno NO va en blanco. El centro de la rampa es exactamente el
    #   color del papel, así que un municipio parado en el pivote —Cotoca en
    #   población— desaparecía: se leía como un agujero en el mapa.
    # ⚠️ El contorno NO va en blanco ni en un gris suave: el centro de la rampa
    #   es un tono muy claro y un municipio parado ahí se leía como un agujero.
    #   En negro, la división municipal se lee siempre, sea cual sea el dato.
    ax.add_collection(PatchCollection(parches, facecolor=colores,
                                      edgecolor=E.TINTA, linewidths=1.0, zorder=2))
    # ★ EL NÚCLEO METROPOLITANO, PERFILADO. Los nueve no son lo mismo: seis
    #   forman la Región Metropolitana propiamente dicha y tres son su área de
    #   influencia. El mapa los pintaba a todos igual y esa distinción —que es
    #   la razón de ser del recorte— no se veía por ningún lado. Se traza el
    #   contorno EXTERIOR de la unión de los seis, no el borde de cada uno: lo
    #   que hay que ver es dónde termina el núcleo, no sus divisiones internas.
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
        nucleo = unary_union([shape(f["geometry"]) for f in geo["features"]
                              if f["properties"].get("ambito") == "núcleo"])
        for g in getattr(nucleo, "geoms", [nucleo]):
            ax.plot(*g.exterior.xy, color=E.TINTA, lw=2.4, zorder=4,
                    solid_joinstyle="round", solid_capstyle="round")
    except Exception:
        pass                     # sin shapely el mapa sigue saliendo, sin perfil

    X0, X1, Y0, Y1 = min(xs), max(xs), min(ys), max(ys)
    ax.set_xlim(X0 + VISTA[0]*(X1-X0), X0 + VISTA[1]*(X1-X0))
    ax.set_ylim(Y0 + VISTA[2]*(Y1-Y0), Y0 + VISTA[3]*(Y1-Y0))
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale(False)

    def punto(rel):
        return X0 + rel[0]*(X1-X0), Y0 + rel[1]*(Y1-Y0)

    # el contorno del color del fondo: sobre una coropleta el texto plano se
    # pierde justo en los municipios de color más saturado
    borde = [pe.withStroke(linewidth=2.2, foreground=E.FONDO)]
    dy = (Y1-Y0) * .012
    for f in geo["features"]:
        sg = f["properties"].get("sigep")
        if sg not in POLO:
            continue
        px, py = punto(POLO[sg])
        lx, ly = punto(FUERA[sg]) if sg in FUERA else (px, py)
        if sg in FUERA:
            ax.plot([px, lx], [py, ly], color="#6d7871", lw=.6, zorder=5,
                    solid_capstyle="round")
            ax.plot([px], [py], marker="o", ms=1.8, color="#6d7871", zorder=6)
        # Sólo el NOMBRE. La cifra de cada municipio ya está escrita —dos veces,
        # con su año— en el gráfico de la derecha; repetirla acá recargaba el
        # mapa sin agregar nada. El mapa ubica y muestra el patrón del color.
        ax.text(lx, ly, f["properties"].get("nombre", ""), ha="center",
                va="center", fontsize=9, family=E.F_SEMI, color=E.TINTA,
                zorder=7, path_effects=borde)

def puntas(v24, nom, D):
    """El mejor y el peor de los nueve. Igual que en el banco por manzana, el
    ROL lo decide la dirección declarada del indicador y no el tamaño del
    número: en «sin afiliación a salud» el valor bajo es el bueno."""
    vv = sorted(((v, sg) for sg, v in v24.items() if v is not None), reverse=True)
    if len(vv) < 2:
        return []
    alto, bajo = vv[0], vv[-1]
    if D == 0:
        return [(alto, "el más alto"), (bajo, "el más bajo")]
    if D < 0:
        return [(bajo, "el mejor"), (alto, "el peor")]
    return [(alto, "el mejor"), (bajo, "el peor")]


def lamina(clave, ind, grupo, mun, reg, geo, salida):
    """Lámina municipal 16:9 — el mapa de los nueve a la izquierda y la
    mancuerna 2012 → 2024 a la derecha."""
    i = ind[clave]
    u = i["unit"]
    D = i.get("dir", 0)
    es_conteo = i.get("agg") == "suma"
    v24 = valores(clave, mun, "municipal")
    hay12 = bool(i.get("s12"))
    v12 = valores(clave, mun, "municipal_2012") if hay12 else {}
    nom = {m["sigep"]: m["nombre"] for m in mun}
    serie = [x for x in v24.values() if x is not None]

    # ★ EL CENTRO DE LA RAMPA. Para una tasa, el agregado regional declarado;
    #   para un conteo, la MEDIANA de los nueve: la suma cae por construcción
    #   fuera del rango municipal y centrar la rampa ahí la degeneraría.
    orden_v = sorted(serie)
    piv = (orden_v[len(orden_v)//2] if es_conteo
           else (agregado(clave, i, mun, reg) or orden_v[len(orden_v)//2]))
    # ★ EL CONTEO VA EN LOGARITMO. Santa Cruz de la Sierra tiene 1.610.982
    #   habitantes y Colpa Bélgica 6.007: en escala lineal, ocho de los nueve
    #   municipios se apilan contra el borde izquierdo y el mapa pinta a Warnes
    #   —151.248— casi del mismo tono que Colpa. Con el logaritmo cada paso
    #   multiplica por diez y los nueve se distinguen. Se aplica sólo cuando hay
    #   órdenes de magnitud de por medio y ningún valor es cero o negativo:
    #   `saldo_migratorio` tiene municipios en negativo y ahí no existe.
    LOG = (es_conteo and min(serie) > 0
           and max(serie) / min(serie) >= 25)
    tr = (lambda v: math.log10(v)) if LOG else (lambda v: v)
    esc = E.escala_util({"lo": tr(orden_v[0]), "hi": tr(orden_v[-1]),
                         "piv": tr(piv),
                         "tipo": "mediana" if es_conteo else "la región"})
    # lo que se ROTULA es siempre el número de verdad, nunca su logaritmo
    def rot(v):
        return E.fmt(10**v if LOG else v, u)

    # el nombre visible del indicador se resuelve UNA vez: lo usan el titular y
    # el rótulo de la rampa, y calcularlo dos veces invita a que se separen
    etiqueta = i["label"]
    defi = definicion(clave, i)
    if len(defi) > 28:
        etiqueta = re.sub(r"\s*\([^)]*\)\s*$", "", etiqueta)

    M, BARRA, PIE = .030, .072, .098
    # El mapa crece hasta comerse el hueco que quedaba bajo la rampa: está
    # trabado por su aspecto (2,04 a 1), así que la única forma de darle alto es
    # darle ancho. La columna derecha cede lo que le sobraba de margen.
    COL_IZQ, CANAL = .560, .026
    X = M + COL_IZQ + CANAL
    W = 1 - X - M

    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor(E.FONDO)

    # ── barra superior ───────────────────────────────────────────────────
    fig.add_artist(Rectangle((0, 1-BARRA), 1, BARRA, transform=fig.transFigure,
                             facecolor=E.TOPBAR, edgecolor="none", zorder=5))
    yb = 1 - BARRA/2
    logo = RAIZ / "docs" / "img" / "scz-oscuro.png"
    if logo.exists():
        fig.add_artist(AnnotationBbox(
            OffsetImage(logo_nitido(logo, int(30*DPI/100)), zoom=100/DPI),
            (M, yb), xycoords="figure fraction", frameon=False,
            box_alignment=(0, .5), zorder=6))
    # ★ EL NOMBRE, EN DOS PESOS. «Santa Cruz Metrópoli» en el verde de la marca
    #   y «En Cifras» en blanco: es el nombre que ya lleva la URL del sitio
    #   (scz-metropoli-encifras). La x del segundo tramo se MIDE en vez de
    #   estimarse — con la coordenada fija, cambiar una palabra dejaba los dos
    #   tramos pisados o separados por un hueco.
    x_marca = .148
    fig.text(x_marca, yb, "Santa Cruz Metrópoli", color=E.VERDE, fontsize=14.5,
             family=E.F_BOLD, va="center", zorder=6)
    fig.text(x_marca + ancho_de(fig, "Santa Cruz Metrópoli", 14.5, E.F_BOLD) + .011,
             yb, "En Cifras", color="#ffffff", fontsize=14.5,
             family=E.F_SEMI, va="center", zorder=6)
    # La barra queda sólo con la marca: el censo y su año ya están dichos en el
    # subtítulo y en el pie, y repetirlos arriba a la derecha no agregaba nada.

    # ══ IZQUIERDA: el mapa, su rampa y las dos puntas ════════════════════
    # El alto del mapa sale del ASPECTO de la región (2,3 a 1), no de lo que
    # sobre en la columna: forzarle una caja alta dejaba una franja vacía
    # debajo que se leía como un error de armado.
    alto_mapa = (COL_IZQ * 16.0 / ASPECTO_MAPA) / 9.0
    # ★ SIN LA BANDA DE PUNTAS, la columna izquierda queda con dos bloques —el
    #   mapa y su rampa— y bastante aire. Se centra el conjunto en la altura
    #   disponible: repartido arriba y abajo, el vacío se lee como margen; todo
    #   junto arriba, se leería como que falta algo abajo.
    techo, piso = 1 - BARRA - .028, PIE + .022
    alto_bloque = alto_mapa + .086 + .020
    margen = max((techo - piso - alto_bloque) / 2, .010)
    y_mapa = techo - margen - alto_mapa
    ax = fig.add_axes([M, y_mapa, COL_IZQ, alto_mapa])
    ax.set_facecolor(E.FONDO)
    mapa_nueve(ax, geo, v24, esc, D, tr, u)

    # ★ LA COLUMNA IZQUIERDA SE REPARTE, NO SE APILA. El mapa está trabado por
    #   su aspecto, así que siempre sobra alto debajo; colgando la rampa del
    #   mapa y clavando las puntas arriba de la franja, todo ese aire se juntaba
    #   en un solo hueco al fondo que se leía como un error de armado. Se mide
    #   lo que sobra y se reparte en los dos huecos por igual.
    BLOQUE_RAMPA = .086
    fondo_col = PIE + .022
    hueco = max((y_mapa - fondo_col - BLOQUE_RAMPA), .020) / 2
    yr = y_mapa - hueco
    # El rótulo de la rampa nombra el INDICADOR, no el recurso: «color de cada
    # municipio» describía el dibujo; el nombre del indicador dice qué se mide.
    rot_r = etiqueta.upper()
    fs_r = 8.5
    while fs_r > 6.5 and ancho_de(fig, rot_r, fs_r, E.F_BOLD) > COL_IZQ:
        fs_r -= .25
    fig.text(M, yr, rot_r, color=E.TINTA, fontsize=fs_r,
             family=E.F_BOLD, va="top")
    axl = fig.add_axes([M, yr - .042, COL_IZQ, .016])
    axl.set_xticks([]); axl.set_yticks([])
    for lado in ("top", "right", "bottom", "left"):
        axl.spines[lado].set_visible(False)
    for t in range(280):
        f = t / 279
        # la barra va por POSICIÓN DE RAMPA, igual que el degradé del
        # tablero: así el pivote ES la mitad y la marca de abajo
        # señala su propio color
        axl.add_patch(Rectangle((f, 0), 1/280 + .002, 1, edgecolor="none",
                                facecolor=E.tono_en(f, D)))
    axl.set_xlim(0, 1); axl.set_ylim(0, 1)
    pp = E.pos_visual(esc["piv"], esc, D)
    axl.plot([pp, pp], [-.45, 1.45], color=E.TINTA, lw=1.2, clip_on=False, zorder=4)
    fig.text(M, yr - .050, rot(esc["lo"]), color=E.TINTA, fontsize=8.5,
             family=E.F_TXT, va="top")
    fig.text(M + COL_IZQ, yr - .050, rot(esc["hi"]), color=E.TINTA,
             fontsize=8.5, family=E.F_TXT, va="top", ha="right")
    # ★ EL RÓTULO DEL PIVOTE SE CORRE CUANDO CHOCA con el del mínimo o el del
    #   máximo. Desde que la barra va por posición de rampa, la MARCA cae siempre
    #   en la mitad; lo que se sale de sitio es el TEXTO, que con cifras largas
    #   («1.610.982») se monta sobre los extremos.
    t_piv = (esc.get("tipo", "mediana") + " " + rot(esc["piv_real"])
             + ("   ·   escala logarítmica" if LOG else ""))
    w_piv = ancho_de(fig, t_piv, 8.5, E.F_MED)
    w_lo = ancho_de(fig, rot(esc["lo"]), 8.5, E.F_TXT)
    w_hi = ancho_de(fig, rot(esc["hi"]), 8.5, E.F_TXT)
    x_piv = M + COL_IZQ*pp
    if (x_piv - w_piv/2) > (M + w_lo + .010) and (x_piv + w_piv/2) < (M + COL_IZQ - w_hi - .010):
        fig.text(x_piv, yr - .050, t_piv, color=E.TINTA, fontsize=8.5,
                 family=E.F_MED, va="top", ha="center")
    else:
        fig.text(M + COL_IZQ, yr, t_piv, color=E.TINTA, fontsize=8.5,
                 family=E.F_MED, va="top", ha="right")

    # ★ AVISO CUANDO EL COLOR EXAGERA. La rampa se estira al rango de los nueve,
    #   así que en `pct_agua_mejorada` —donde todos están entre 96,6% y 99,8%—
    #   Pailón sale rojo intenso por estar 3 puntos abajo y el mapa se lee como
    #   una crisis que no existe. Estirar la escala es correcto para ver el
    #   patrón; callarlo, no. Se avisa cuando los nueve caben en pocos puntos.
    ancho_r = max(serie) - min(serie)
    if u == "%" and ancho_r < 8:
        fig.text(M, yr - .072,
                 "Ojo: los nueve caben en " + E.fmt(ancho_r, "pp")
                 + " — el color estira una diferencia chica para que se vea el patrón.",
                 color=E.TINTA, fontsize=7.5, family=E.F_TXT, va="top")

    # ✂ SE FUE «LAS DOS PUNTAS DE LA REGIÓN». Rotulaba a un municipio como «el
    #   mejor» y a otro como «el peor», y un calificativo colgado del nombre de
    #   un municipio en una lámina oficial dice más de lo que el dato aguanta:
    #   el orden ya está a la derecha, y quien lo lea que saque su conclusión.

    # ══ DERECHA ══════════════════════════════════════════════════════════
    y = 1 - BARRA - .048
    # el paréntesis del universo sale del titular: el subtítulo lo dice entero
    # ★ ANTETÍTULO EN VEZ DE PREFIJO. «Región Metropolitana:» va delante en las
    #   213 láminas y no distingue a ninguna, así que ocupando el renglón del
    #   titular sólo lograba partirlo en dos. Arriba y en chico ubica igual, y
    #   de paso se lleva el bloque temático, que antes gastaba otro renglón.
    # El ámbito, dicho entero: son los seis municipios del núcleo metropolitano
    # MÁS los tres del área de influencia (Montero, Pailón y Colpa Bélgica).
    # Decir sólo «Región Metropolitana» dejaba fuera del nombre a tres de los
    # nueve que la lámina sí está midiendo.
    fig.text(X, y, "REGIÓN METROPOLITANA Y ÁREA DE INFLUENCIA   ·   "
             + grupo[clave].upper(),
             color=E.VERDE_INS, fontsize=8.5, family=E.F_BOLD, va="top")
    y -= .028
    tramos = [(etiqueta, E.TINTA, E.F_TIT)]
    fs_tit = 27.0
    while fs_tit > 15 and parrafo(fig, X, y, tramos, fs_tit, .044,
                                  W, dibujar=False)[1] > 1:
        fs_tit -= 1.0
    y, _ = parrafo(fig, X, y, tramos, fs_tit, fs_tit*.00175, W)

    y -= .006
    y, _ = parrafo(fig, X, y, [(defi, E.TINTA, E.F_TXT)], 9.5, .0225, W)
    y -= .014
    fig.add_artist(plt.Line2D([X, X + W*.38], [y, y], transform=fig.transFigure,
                              color=E.VERDE, lw=2))

    # ── las dos cifras de la región ──────────────────────────────────────
    y -= .052
    r24 = agregado(clave, i, mun, reg, "municipal")
    r12 = agregado(clave, i, mun, reg, "municipal_2012") if hay12 else None
    fig.text(X, y, E.fmt(r24, u), color=E.TINTA, fontsize=27, family=E.F_TIT, va="top")
    fig.text(X, y - .050, "RMSC + 3", color=E.VERDE_INS,
             fontsize=8.5, family=E.F_BOLD, va="top")
    fig.text(X, y - .069,
             "suma de los nueve" if es_conteo else "ponderado por su propio universo",
             color=E.TINTA, fontsize=8.5, family=E.F_TXT, va="top")
    xd = X + W*.46
    fig.add_artist(plt.Line2D([xd - .026, xd - .026], [y - .078, y + .006],
                              transform=fig.transFigure, color=E.LINEA, lw=1))
    if r12 is not None:
        dv, du = cambio(r24, r12, es_conteo)
        fig.text(xd, y, signo(dv, du), color=E.TINTA, fontsize=27,
                 family=E.F_TIT, va="top")
        fig.text(xd, y - .050, "DESDE 2012", color=E.TINTA, fontsize=8.5,
                 family=E.F_BOLD, va="top")
        fig.text(xd, y - .069, "era " + E.fmt(r12, u), color=E.TINTA,
                 fontsize=8.5, family=E.F_TXT, va="top")
    else:
        fig.text(xd, y, E.fmt(max(serie) - min(serie), "pp" if u == "%" else u),
                 color=E.TINTA, fontsize=27, family=E.F_TIT, va="top")
        fig.text(xd, y - .050, "DE PUNTA A PUNTA", color=E.TINTA, fontsize=8.5,
                 family=E.F_BOLD, va="top")
        fig.text(xd, y - .069, "sin dato 2012 comparable", color=E.TINTA,
                 fontsize=8.5, family=E.F_TXT, va="top")

    # ── la mancuerna 2012 → 2024 ─────────────────────────────────────────
    y -= .112
    # Sin comparativa no hay rótulo: «Los nueve, ordenados» describía el eje
    # que el lector ya está viendo y no agregaba nada.
    if r12 is not None:
        fig.text(X, y, "Comparativa Intercensal: 2012 vs 2024", color=E.TINTA,
                 fontsize=10.5, family=E.F_BOLD, va="top")
    COL_CAMBIO = .050 if r12 is not None else .0
    if COL_CAMBIO:
        fig.text(X + W, y, "CAMBIO", ha="right", va="top", fontsize=7.5,
                 family=E.F_BOLD, color=E.TINTA)


    # El gráfico se queda con todo lo que va del rótulo al pie: es el bloque que
    # tiene que respirar, porque son nueve filas con dos cifras cada una.
    COL_NOM = .096
    x0 = X + COL_NOM
    ancho_ax = W - COL_NOM - COL_CAMBIO
    y_base = PIE + .052
    alto = y - .030 - y_base
    axd = fig.add_axes([x0, y_base, ancho_ax, alto])
    axd.set_facecolor(E.FONDO)
    for lado in ("top", "right", "left"):
        axd.spines[lado].set_visible(False)
    axd.spines["bottom"].set_color(E.LINEA)

    filas = sorted((sg for sg in v24 if v24[sg] is not None), key=lambda sg: -v24[sg])
    todos = serie + [x for x in v12.values() if x is not None]
    lo_e, hi_e = min(todos), max(todos)
    if hi_e <= lo_e:
        hi_e = lo_e + 1
    # ⚠️ El margen crece porque ahora hay un número en CADA punta de la
    #   mancuerna: con el margen viejo, el 2012 del municipio más chico y el
    #   2024 del más grande se salían del cuadro.
    if LOG:
        axd.set_xscale("log")
        axd.set_xlim(lo_e / 3.0, hi_e * 3.0)
        from matplotlib.ticker import LogLocator, FuncFormatter
        axd.xaxis.set_major_locator(LogLocator(base=10))
        axd.xaxis.set_minor_locator(LogLocator(base=10, subs=(2., 5.)))
        axd.xaxis.set_major_formatter(FuncFormatter(lambda v, _: E.fmt(v, u)))
        axd.xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    else:
        m_e = (hi_e - lo_e) * .22
        axd.set_xlim(lo_e - m_e, hi_e + m_e)
    # filas repartidas parejo: mismo aire arriba de la primera que abajo de la
    # última, para que el bloque quede centrado en su caja
    axd.set_ylim(.5, len(filas) + .5)
    axd.set_yticks([])
    axd.tick_params(axis="x", colors="#8a938c", labelsize=8, length=0, pad=4)
    for lbl in axd.get_xticklabels():
        lbl.set_family(E.F_TXT)
    # ★ GUÍAS EN VEZ DE MARCAS. Con sólo los números al pie, para saber dónde
    #   cae un punto había que bajar la vista y estimar. Las verticales lo
    #   resuelven, pero tienen que ser un susurro: si compiten con la mancuerna
    #   —que es el dato— arruinan justamente lo que vienen a ayudar a leer.
    axd.grid(axis="x", color="#cdd2cb", lw=.4, zorder=0)
    axd.set_axisbelow(True)
    axd.spines["bottom"].set_color("#cdd2cb")
    axd.spines["bottom"].set_linewidth(.6)
    borde_f = [pe.withStroke(linewidth=2.6, foreground=E.FONDO)]

    # ✂ SE FUE LA LÍNEA DE LA REGIÓN. Cruzaba el gráfico entero para marcar un
    #   promedio que ya está escrito arriba en grande, y sumaba una vertical más
    #   a un cuadro que ya tiene las guías del eje.

    for n, sg in enumerate(filas):
        yy = len(filas) - n
        a, b = v12.get(sg), v24[sg]
        if a is not None:
            # el trazo une los dos censos: su LARGO es la magnitud del cambio
            axd.plot([a, b], [yy, yy], color="#a7b0a8", lw=2.0,
                     solid_capstyle="round", zorder=2)
            axd.plot([a], [yy], marker="o", ms=7.0, markerfacecolor=E.FONDO,
                     markeredgecolor="#6d7871", markeredgewidth=1.1, zorder=3)
        else:
            # el tallo va MÁS marcado que las guías del eje: es dato, no retícula
            axd.plot([axd.get_xlim()[0], b], [yy, yy], color="#9aa39c", lw=1.6,
                     zorder=2)
        axd.plot([b], [yy], marker="o", ms=9.5, markerfacecolor=E.tono(tr(b), esc, D),
                 markeredgecolor=E.TINTA, markeredgewidth=.8, zorder=4)
        # ★ EL NOMBRE, ALINEADO A LA IZQUIERDA. En columna derecha quedaba un
        #   borde dentado —«Colpa Bélgica» contra «El Torno»— que llamaba más la
        #   atención que el dato. Alineado a la izquierda arma un riel limpio y
        #   se corre del camino.
        axd.text(-COL_NOM/ancho_ax, yy, nom.get(sg, ""), ha="left", va="center",
                 transform=axd.get_yaxis_transform(), fontsize=10,
                 color=E.TINTA, family=E.F_BOLD)

        # ★ LAS DOS CIFRAS, UNA EN CADA PUNTA. El 2024 sin el 2012 al lado
        #   obliga a leer la posición del aro contra el eje para saber de dónde
        #   venía. Cada número va del lado de AFUERA de su punto, así el trazo
        #   —que es el cambio— queda limpio en el medio.
        if a is not None:
            creció = b >= a
            axd.annotate(E.fmt(b, u), (b, yy), textcoords="offset points",
                         xytext=(9 if creció else -9, 0),
                         ha="left" if creció else "right", va="center",
                         fontsize=8, family=E.F_SEMI, color=E.TINTA,
                         zorder=5, path_effects=borde_f)
            axd.annotate(E.fmt(a, u), (a, yy), textcoords="offset points",
                         xytext=(-8 if creció else 8, 0),
                         ha="right" if creció else "left", va="center",
                         fontsize=7.5, family=E.F_TXT, color="#5c6660",
                         zorder=5, path_effects=borde_f)
        else:
            axd.annotate(E.fmt(b, u), (b, yy), textcoords="offset points",
                         xytext=(10, 0), ha="left", va="center",
                         fontsize=8, family=E.F_SEMI, color=E.TINTA,
                         zorder=5, path_effects=borde_f)

        if a is not None and COL_CAMBIO:
            dv, du = cambio(b, a, es_conteo)
            fr = (yy - .5) / len(filas)
            fig.text(X + W, y_base + alto*fr, signo(dv, du), ha="right",
                     va="center", fontsize=8.5, family=E.F_SEMI, color=E.TINTA)

    # La leyenda va DEBAJO del gráfico: es una nota de lectura, no un titular.
    # Se mide y se achica hasta entrar, porque si se pasa del margen el último
    # tramo se corta fuera del lienzo sin que nada lo delate.
    ley = ("Aro hueco: 2012   ·   Punto lleno: 2024   ·   El trazo es la magnitud "
           "del cambio" if r12 is not None
           else "El color del punto es el mismo del mapa")
    if LOG:
        ley += "   ·   Eje logarítmico: cada paso multiplica por diez"
    fs_l = 7.5
    while fs_l > 6.0 and ancho_de(fig, ley, fs_l, E.F_TXT) > W:
        fs_l -= .25
    fig.text(X, y_base - .028, ley, color=E.GRIS_PIE, fontsize=fs_l,
             family=E.F_TXT, va="top")

    # ══ PIE, EN SU PROPIA FRANJA ═════════════════════════════════════════
    # A ras del papel, la ficha técnica se leía como un renglón más de la
    # explicación del gráfico. Sobre su franja se reconoce de un vistazo como lo
    # que es —universo, fuente, autoría— y deja de disputarle atención al dato.
    fig.add_artist(Rectangle((0, 0), 1, PIE - .006, transform=fig.transFigure,
                             facecolor=E.PIE_BANDA, edgecolor="none", zorder=0))
    cob = ("RMSC + 3 es la Región Metropolitana de Santa Cruz —seis municipios— "
           "más su área de influencia: Montero, Pailón y Colpa Bélgica. "
           "El dato es del municipio entero: incluye el área rural.")
    if not hay12:
        cob += ("  Sin comparación intercensal: el catálogo no la declara para "
                "este indicador.")
        if i.get("w12"):
            cob += "  " + str(i["w12"]).rstrip(".") + "."
    fs_c = 8.5
    while fs_c > 6.0 and ancho_de(fig, cob, fs_c, E.F_TXT) > 1 - 2*M:
        fs_c -= .25
    # Los dos renglones van JUNTOS, en cursiva y en gris: apretados ocupan la
    # mitad de alto y todo lo de arriba respira, y el cambio de estilo dice
    # «esto es la ficha, no la explicación» sin necesidad de más recursos.
    y1, y2 = PIE - .040, PIE - .068
    E.cursiva(fig, fig.text(M, y1, cob, color=E.GRIS_PIE, fontsize=fs_c,
                            family=E.F_TXT, va="center", zorder=2), M, y1)
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
    ap.add_argument("--indicador", default="pct_edu_superior")
    ap.add_argument("--todas", action="store_true")
    a = ap.parse_args()
    cat, ind, grupo, mun, geo = cargar()
    reg = cat["region"]
    if a.todas:
        claves = indicadores_censales(ind, grupo, mun)
        for n, k in enumerate(claves, 1):
            lamina(k, ind, grupo, mun, reg, geo, SALIDA / f"{k}.png")
            print(f"  {n:>3}/{len(claves)}  {k}")
        print(f"\n{len(claves)} láminas municipales -> {SALIDA}")
    else:
        print("->", lamina(a.indicador, ind, grupo, mun, reg, geo,
                           SALIDA / f"{a.indicador}.png"))


if __name__ == "__main__":
    main()
