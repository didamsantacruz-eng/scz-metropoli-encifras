# -*- coding: utf-8 -*-
"""
IDENTIDAD DEL BANCO — Santa Cruz Metrópoli en Cifras.
=====================================================

La lámina y el tablero tienen que decir lo MISMO del mismo dato. Si el banco
pintara con su propia escala, un municipio podría leerse "alto" en la lámina y
"medio" en el mapa, y quien vio las dos cosas no sabría a cuál creerle. Así que
acá se replica exactamente lo que hace `docs/index.html`:

  · la rampa divergente de la Gobernación,
  · el pivote clavado en el centro (`pos_en_rampa`),
  · la inversión por `dir`, para que el verde quede siempre del lado bueno,
  · el gris único de "sin dato",
  · y la INTERPOLACIÓN entre paradas, que desde 2026-08-20 hace también el
    tablero (antes saltaba a una de las siete y la miniatura de la tarjeta
    discrepaba del polígono que decía estar resumiendo).

★ YA NO SON DOS IMPLEMENTACIONES (2026-08-20). Acá decía «SI CAMBIA EL TABLERO,
  CAMBIA ESTO. Son dos implementaciones del mismo criterio; no hay forma de que
  una se entere sola de la otra» — y efectivamente no se enteró: la lámina y la
  pantalla llegaron a tener tres diferencias (la bisagra, los neutros y la
  saturación). La rampa se declara ahora una sola vez en `assets/paleta.json`;
  este archivo la lee y `scripts/paleta.py` la inyecta en el tablero.
  `python scripts/paleta.py --verificar` falla si alguno se desvía.

Las fuentes se cargan por ARCHIVO y por PESO, no pidiendo `weight="bold"` sobre
una familia variable: matplotlib no instancia ejes variables, así que con la
Inter variable el negrita sale igual que el redondo y nada falla — sólo se ve
mal. Cada peso se registra como su propia familia.
"""
import json
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
from matplotlib import pyplot as plt

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
FUENTES = RAIZ / "assets" / "fuentes"

# ── paleta ───────────────────────────────────────────────────────────────
# ★ NO SE ESCRIBE ACÁ (2026-08-20). Hasta ayer esta rampa estaba a mano y el
#   archivo avisaba: «SI CAMBIA EL TABLERO, CAMBIA ESTO. Son dos
#   implementaciones del mismo criterio; no hay forma de que una se entere sola
#   de la otra». No se enteró — la lámina y la pantalla terminaron con tres
#   diferencias. Ahora las dos leen `assets/paleta.json`, que `scripts/paleta.py`
#   deriva y sincroniza. La bisagra, la bajada de saturación y el realce del tema
#   oscuro están ahí, cada una con su motivo escrito.
_PALETA = json.loads((RAIZ / "assets" / "paleta.json").read_text(encoding="utf-8"))["pinta"]
DIV = list(_PALETA["divergente"])
SIN_DATO = _PALETA["sin_dato"]
VERDE     = _PALETA["senal"]           # el del logotipo — color de SEÑAL, nunca de dato
VERDE_INS = _PALETA["institucional"]   # verde institucional
TOPBAR    = "#043520"
FONDO     = "#eeebe1"
PAPEL     = "#fffefb"
TINTA     = "#1d2321"
SUAVE     = "#5f6a63"
TENUE     = "#949c96"
LINEA     = "#d7d2c4"
# ★ LA FRANJA DEL PIE (pedido de Carlos, 2026-08-19). La ficha técnica —qué
#   universo, qué fuente, quién elabora— se leía como si fuera una explicación
#   más del gráfico. Sobre un tono propio deja de competir: el ojo la reconoce
#   como aparato crítico y la salta o la busca según necesite.
#   Es un crema apenas más profundo que el papel, no un gris: un gris ahí abre
#   un segundo plano y ensucia toda la lámina.
PIE_BANDA = "#e4e0d2"


def registrar_fuentes():
    """Registra cada peso como familia PROPIA y devuelve sus nombres.

    ⚠️⚠️ EL BUG QUE ESTO ARREGLA — y que estuvo vivo en las 375 láminas.
    Los cuatro archivos de Inter declaran el MISMO nombre de familia interno:
    `FontProperties(fname=…).get_name()` devuelve "Inter" para el Regular, el
    Medium, el SemiBold y el Bold por igual. Así que F_TXT, F_MED, F_SEMI y
    F_BOLD valían los cuatro "Inter", matplotlib resolvía siempre al peso normal
    y NINGUNA negrita del banco existía: la jerarquía tipográfica era plana y
    nada fallaba — sólo se veía mal. Es la misma trampa anotada en
    [[reference_matplotlib-negrita-real]], pero por otra puerta: allá el
    problema era el eje variable, acá que los cuatro archivos comparten nombre.

    La cura es renombrar la ENTRADA que matplotlib acaba de registrar, para que
    cada archivo tenga su propia familia y `family="Inter Bold"` caiga en el
    archivo del Bold y no en el del Regular.
    """
    fam = {}
    for archivo, alias in (("Inter-Regular.ttf", "Inter"),
                           ("Inter-Medium.ttf", "Inter Medium"),
                           ("Inter-SemiBold.ttf", "Inter SemiBold"),
                           ("Inter-Bold.ttf", "Inter Bold"),
                           ("Newsreader-var.ttf", "Newsreader")):
        f = FUENTES / archivo
        if not f.exists():
            continue
        fm.fontManager.addfont(str(f))
        for e in fm.fontManager.ttflist:
            try:
                if pathlib.Path(e.fname).resolve() == f.resolve():
                    # FontEntry es un dataclass CONGELADO: la asignación directa
                    # levanta FrozenInstanceError
                    object.__setattr__(e, "name", alias)
            except OSError:
                pass
        fam[alias] = alias
    # el cacheo de búsquedas se limpia: si algo se resolvió antes del renombre,
    # quedaría clavado al archivo viejo y el arreglo no se notaría
    for c in ("_findfont_cached", "findfont"):
        obj = getattr(fm, c, None)
        if obj is not None and hasattr(obj, "cache_clear"):
            obj.cache_clear()
    plt.rcParams["font.family"] = fam.get("Inter", "DejaVu Sans")
    plt.rcParams["axes.unicode_minus"] = False
    return fam


FAM = registrar_fuentes()
# nombres reales que matplotlib registró (pueden diferir del alias)
F_TXT  = FAM.get("Inter", "DejaVu Sans")
F_MED  = FAM.get("Inter Medium", F_TXT)
F_SEMI = FAM.get("Inter SemiBold", F_TXT)
F_BOLD = FAM.get("Inter Bold", F_TXT)
F_TIT  = FAM.get("Newsreader", F_TXT)


# ★ CURSIVA SINTÉTICA. La familia de marca no trae itálica: en `assets/fuentes`
#   sólo están los cuatro pesos redondos de Inter y la Newsreader variable, cuyo
#   único eje aparte del peso es el tamaño óptico. Pedirle `style="italic"` a
#   matplotlib con esas familias devuelve el REDONDO sin avisar — el mismo modo
#   de fallar silencioso que ya costó caro con la negrita.
#   Antes que meter una segunda tipografía en la lámina se inclina la propia:
#   se aplica un sesgo en el espacio de pantalla, anclado en el punto del texto
#   para que no se corra de sitio. Es lo que hace cualquier procesador de texto
#   cuando le pedís cursiva de una fuente que no la tiene.
GRADOS_CURSIVA = 11


def cursiva(fig, t, x, y, grados=GRADOS_CURSIVA):
    """Inclina un `Text` ya colocado. `x`,`y` en fracción de figura."""
    import matplotlib.transforms as mtr
    base = fig.transFigure
    x0, y0 = base.transform((x, y))
    t.set_transform(base + mtr.Affine2D().translate(-x0, -y0)
                    .skew_deg(grados, 0).translate(x0, y0))
    return t


# El pie va en un gris propio: ni la tinta del dato ni el tenue de un rótulo
# perdido. Baja el contraste lo justo para que se lea como aparato crítico.
GRIS_PIE = "#7d857f"


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def _rgb_hex(t):
    return "#" + "".join(f"{max(0,min(255,round(c*255))):02x}" for c in t)


def rampa(direccion):
    """`dir == 1` significa que MÁS ES PEOR ⇒ se da vuelta, y el verde queda
    siempre del lado bueno. Es la misma regla del tablero."""
    return list(reversed(DIV)) if direccion == 1 else list(DIV)


def escala_util(esc):
    """★ EL PIVOTE RECORTADO. Es el paso que el tablero hace y la lámina se
    había saltado, con la consecuencia exacta que el proyecto ya tenía escrita:
    *pegado a un extremo la rampa se degenera y media paleta no se usa nunca*.

    En `pct_basura_formal` la mediana regional es 100,0 y el máximo también:
    con el pivote crudo, la mitad verde de la rampa quedaba para valores
    mayores a 100 —que no existen— y NINGUNA manzana podía salir verde. Santa
    Cruz se salvaba de casualidad porque casi todas sus manzanas están en 100 y
    caían justo en el centro; el resto de los municipios salía todo naranja.

    Devuelve la escala con `piv` recortado y `piv_real` aparte: el número que se
    ROTULA es el real, porque publicar el recortado sería rebautizar un borde
    con el nombre de una estadística.
    """
    lo, hi = esc["lo"], esc["hi"]
    if hi <= lo:
        hi = lo + 1
    real = esc["piv"]
    pad = (hi - lo) * .08
    piv = min(max(real, lo + pad), hi - pad) if pad > 0 else real
    return {**esc, "lo": lo, "hi": hi, "piv": piv, "piv_real": real,
            "recortado": abs(piv - real) > 1e-9}


def cuantil(ordenados, q):
    """Idéntico al del tablero: interpolación lineal entre vecinos."""
    if not ordenados:
        return None
    h = (len(ordenados) - 1) * q
    b = int(h)
    r = h - b
    return ordenados[b] + r * (ordenados[b+1] - ordenados[b]) if b + 1 < len(ordenados) else ordenados[b]


def escala_local(valores, tipo="mediana"):
    """★ ESCALA PROPIA DEL MUNICIPIO (decisión de Carlos, 2026-08-19).

    La regional hace que un municipio entero por debajo de la mediana de la
    región salga casi de un color y su variación interna se aplane: en
    `pct_basura_formal` la mediana regional es 100%, así que Cotoca —que está
    realmente por debajo— quedaba todo naranja y no se veía nada de lo que pasa
    adentro, que es lo que la lámina viene a mostrar.

    ⚠️⚠️ EL PRECIO, Y HAY QUE ROTULARLO: el mismo verde significa cosas
    distintas en cada lámina, así que DOS LÁMINAS NO SE PUEDEN COMPARAR entre
    sí. Es la trampa clásica del mapa por cuantiles. Por eso la lámina dice
    "escala propia de <municipio>" al lado de la rampa, y la comparación entre
    municipios se deja donde sí es honesta: el gráfico de distribución, que
    tiene un eje numérico común para los nueve.

    ★ LLEGA A LOS EXTREMOS, SALVO QUE UNA MANZANA SUELTA ROMPA LA RAMPA
    (decisión de Carlos, 2026-08-19). Antes cortaba fijo en el percentil 2 y el
    98, y eso dejaba dos defectos: la rampa decía "0,0% a 49,8%" mientras el
    rango real de Porongo era 0,0% a 78,0% —dos pares de números distintos en la
    misma lámina, los dos llamados "el rango"— y las manzanas que pasaban el
    corte salían todas del mismo color sin que nada lo dijera.

    Ahora la rampa llega al mínimo y al máximo REALES. El corte sólo aparece
    cuando la cola se aleja más de 1,2 veces el ancho del 80% central, que es el
    caso de `densidad`: en Warnes hay una manzana de 245 hab/ha contra un p90 de
    79, y con el máximo crudo la mediana caía al 7% de la rampa y el municipio
    entero salía de un color. Cuando pasa se corta Y SE AVISA: `recorte_hi`
    enciende el ángulo › y el máximo verdadero va escrito al lado.

    Es la MISMA regla que el eje del gráfico de distribución, a propósito: dos
    criterios distintos en la misma lámina es justamente lo que había que
    arreglar.
    """
    v = sorted(x for x in valores if x is not None)
    if not v:
        return None
    q10, q90 = cuantil(v, .10), cuantil(v, .90)
    span = (q90 - q10) or (abs(q90) * .1 or 1)
    vmin, vmax = v[0], v[-1]
    lo = vmin if (q10 - vmin) <= span*1.2 else q10 - span*.25
    hi = vmax if (vmax - q90) <= span*1.2 else q90 + span*.25
    if hi <= lo:
        lo, hi = vmin, (vmax if vmax > vmin else vmin + 1)
    real = cuantil(v, .5)
    pad = (hi - lo) * .08
    piv = min(max(real, lo + pad), hi - pad) if pad > 0 else real
    return {"lo": lo, "hi": hi, "piv": piv, "piv_real": real, "tipo": tipo,
            "n": len(v), "min": vmin, "max": vmax,
            "recorte_lo": lo > vmin + 1e-9, "recorte_hi": hi < vmax - 1e-9,
            "recortado": abs(piv - real) > 1e-9}


def pos_en_rampa(v, lo, piv, hi):
    """Posición 0..1 con el PIVOTE clavado en 0,5. Sin esto, el color diría
    'cuánto' y no 'de qué lado de la región'."""
    if v is None:
        return None
    if hi <= lo:
        return .5
    piv = min(max(piv, lo), hi)
    if v <= piv:
        d = piv - lo
        return 0 if d <= 0 else .5 * (v - lo) / d
    d = hi - piv
    return 1 if d <= 0 else .5 + .5 * (v - piv) / d


# ★ LA RAMPA SECUENCIAL SE BAJÓ (decisión de Carlos, 2026-08-20).
#   Entre el 19 y el 20 los indicadores neutros (`dir == 0`) se pintaban acá con
#   una rampa de un solo tono, para no afirmar un lado bueno donde el dato no lo
#   trae —en `pob_total` la divergente pinta a Santa Cruz de la Sierra de rojo
#   por ser la más poblada y a Colpa Bélgica de verde por ser la más chica—.
#   El tablero nunca la tuvo, así que la lámina y la pantalla decían cosas
#   distintas del mismo indicador. Se resolvió al revés de como estaba propuesto:
#   la divergente vale para TODO. Costó regenerar 184 de las 375 láminas.
#   El argumento queda escrito en `assets/paleta.json`, en `ajustes.sin_secuencial`.
#
# ★ Y LA BAJADA DE SATURACIÓN TAMPOCO SE HACE ACÁ. Era un `SUAVE_FACTOR = .80`
#   que sólo aplicaba el banco, así que la lámina y la pantalla mostraban colores
#   distintos para el mismo valor. Ahora la aplica `scripts/paleta.py` sobre la
#   rampa declarada y la reciben los dos: lo que se lee de `paleta.json` YA viene
#   suavizado.


def pos_visual(v, esc, direccion):
    """Dónde cae un valor A LO LARGO DE LA RAMPA DIBUJADA, 0 a 1.

    Tiene que decidir igual que `tono`, porque las dos responden la misma
    pregunta: dónde cae este valor sobre la rampa que el lector está viendo.
    Con el pivote clavado en la mitad, la respuesta es una sola para todos los
    indicadores."""
    if v is None:
        return None
    # ⚠️ EL PIVOTE SE CLAVA EN LA MITAD, no se reparte por proporción cruda entre
    #   mínimo y máximo. Se probó así y el mapa de `densidad` por manzana quedó
    #   ilegible: la mediana de Warnes es 17,8 de un rango 0-99, así que el
    #   grueso de las manzanas se apilaba en el primer quinto de la rampa y salía
    #   todo del mismo tono claro. Es el mismo reparto que hace el tablero.
    return pos_en_rampa(v, esc["lo"], esc["piv"], esc["hi"])


def tono(v, esc, direccion):
    """Color de un valor, interpolando linealmente entre las paradas.

    Una sola paleta para las tres direcciones: `dir` sólo decide si la rampa se
    da vuelta, nunca cuál se usa. Es la misma cuenta que `tonoDe()` en el
    tablero."""
    if v is None:
        return SIN_DATO
    p = pos_en_rampa(v, esc["lo"], esc["piv"], esc["hi"])
    if p is None:
        return SIN_DATO
    r = rampa(direccion)
    x = max(0.0, min(1.0, p)) * (len(r) - 1)
    i = int(x)
    if i >= len(r) - 1:
        return r[-1]
    f = x - i
    a, b = _hex_rgb(r[i]), _hex_rgb(r[i + 1])
    return _rgb_hex(tuple(a[k] + (b[k] - a[k]) * f for k in range(3)))


def tono_en(pos, direccion):
    """El color en una POSICIÓN de la rampa (0..1), sin pasar por un valor.

    ★ ES LO QUE NECESITA LA BARRA DE LA LEYENDA (2026-08-20), y es el bug que
      esto arregla. La barra se dibujaba muestreando `tono(lo + (hi-lo)*f)`, o
      sea LINEAL EN VALOR, mientras la marca del pivote se ponía en
      `pos_visual(piv)`, que vale 0,5 SIEMPRE. Los dos comentarios del código
      decían «en la rampa divergente el pivote cae siempre en la mitad y no
      molesta a nadie» — daban por hecho que la barra era lineal en posición de
      rampa. No lo era.

      Medido sobre `pct_alcantarillado.png` tal como estaba publicada: la barra
      va de 7,8% a 70,4% con la región en 56,7%. La bisagra —el color del
      pivote— aparecía al 78% del ancho, y la marca rotulada «la región 56,7%»
      estaba clavada al 50%. La marca señalaba un color que no era el suyo, en
      las 375 láminas.

      Se resuelve del lado de la barra y no de la marca, para que la leyenda de
      la lámina quede IDÉNTICA a la del tablero, que dibuja
      `linear-gradient(to right, …7 paradas…)` — o sea, lineal en posición de
      rampa. Con eso los extremos siguen siendo `lo` y `hi`, el pivote sigue
      siendo el centro, y el eje es lo que una divergente es: dos tramos
      lineales unidos en el pivote.
    """
    r = rampa(direccion)
    x = max(0.0, min(1.0, pos)) * (len(r) - 1)
    i = int(x)
    if i >= len(r) - 1:
        return r[-1]
    f = x - i
    a, b = _hex_rgb(r[i]), _hex_rgb(r[i + 1])
    return _rgb_hex(tuple(a[k] + (b[k] - a[k]) * f for k in range(3)))


def fmt(v, unidad):
    """Mismo formateo que el tablero: los conteos sin decimales, y el resto con
    los decimales que pide su MAGNITUD — un valor no nulo nunca se imprime 0."""
    if v is None:
        return "s/d"
    if unidad in ("hab", "viv"):
        return f"{round(v):,.0f}".replace(",", ".")
    if unidad in ("%", "pp"):
        s = f"{v:,.1f}".replace(",", "@").replace(".", ",").replace("@", ".")
        return s + ("%" if unidad == "%" else " pp")
    a = abs(v)
    d = 0 if a == 0 or a >= 100 else (1 if a >= 1 else min(6, 1 - int(__import__("math").floor(__import__("math").log10(a)))))
    s = f"{v:,.{d}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"{s} {unidad}" if unidad else s
