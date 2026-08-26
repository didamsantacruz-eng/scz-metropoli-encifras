# -*- coding: utf-8 -*-
"""
BAJA Y FUSIONA EL MAPA BASE VECTORIAL DE CARTO.
================================================

⛔ POR QUÉ EXISTE ESTE PASO — el 2026-08-26 el sitio publicado apareció con
   «API KEY REQUIRED» estampado sobre los dos mapas. CARTO empezó a exigir clave
   para sus mapas base **ráster** (`light_all`, `dark_all` y también
   `light_nolabels` / `dark_nolabels`, verificado uno por uno renderizando).
   No falla ni da error: responde 200 y devuelve la tesela con la marca encima,
   así que el tablero «funciona» y se ve roto.

   Lo que **sigue siendo gratuito y sin clave** son los estilos **vectoriales
   GL** y la capa ráster de **sólo rótulos**. Es exactamente la combinación que
   usa `desarrollo-infantil.pages.dev`, el tablero que inspiró este zoom, y de
   ahí salió el arreglo.

★ POR QUÉ SE HORNEA EN LA PLANTILLA EN VEZ DE PEDIRLO EN CALIENTE
  El mapa se construye de forma SÍNCRONA dentro de un `try` y todo lo que sigue
  depende de que `map` exista. Meter un `fetch` antes obligaría a envolver el
  resto en la promesa, que es justo la clase de cambio que ya dejó una vez el
  tablero en blanco en producción. Horneado: sin ida y vuelta extra, sin una
  falla nueva posible, y el estilo queda fijado y versionado como cualquier
  dependencia clavada.

★ POR QUÉ LOS DOS ESTILOS Y NO UNO
  El tablero alterna tema **sin `setStyle()`**: las dos bases viven en el mismo
  objeto de estilo y se conmuta su visibilidad, porque reemplazar el estilo
  entero se lleva puestas las capas de municipios y manzanas. Así que hacen
  falta los dos juegos de capas, con prefijo para que no choquen los
  identificadores. Comparten la MISMA fuente vectorial, que va una sola vez.

    python scripts/bajar_mapa_base.py
"""
import json
import pathlib
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "plantilla" / "mapa_base.json"

ESTILOS = {
    "claro": {
        "url": "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
        "rotulos": "https://basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
        "prefijo": "bc_",
    },
    "oscuro": {
        "url": "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json",
        "rotulos": "https://basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
        "prefijo": "bo_",
    },
}
ATRIB = ('© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
         ' · © <a href="https://carto.com/attributions">CARTO</a>')


def bajar(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": "scz-metropoli/1.0"})
    with urllib.request.urlopen(pedido, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


fuentes, capas, glyphs, sprite = {}, {}, None, None
for tema, cfg in ESTILOS.items():
    st = bajar(cfg["url"])
    glyphs = glyphs or st.get("glyphs")
    sprite = sprite or st.get("sprite")

    # La fuente vectorial es la MISMA en los dos estilos: se guarda una sola vez
    # y las capas de los dos temas la comparten.
    for sid, sdef in st["sources"].items():
        if sid not in fuentes:
            sdef = dict(sdef)
            sdef["attribution"] = ATRIB
            fuentes[sid] = sdef

    propias = []
    for capa in st["layers"]:
        c = dict(capa)
        if c.get("type") == "background":
            # el fondo lo pone el tablero, que lo repinta al cambiar de tema
            continue
        c["id"] = cfg["prefijo"] + c["id"]
        lay = dict(c.get("layout") or {})
        lay["visibility"] = "visible" if tema == "claro" else "none"
        c["layout"] = lay
        c.pop("metadata", None)
        propias.append(c)

    # los rótulos van ARRIBA de todo el juego vectorial de su tema
    rid = cfg["prefijo"] + "rotulos"
    fuentes[rid] = {"type": "raster", "tiles": [cfg["rotulos"]],
                    "tileSize": 256, "attribution": ATRIB}
    propias.append({
        "id": rid, "type": "raster", "source": rid,
        "layout": {"visibility": "visible" if tema == "claro" else "none"},
        # los rótulos NO llevan desaturación: son texto, y bajarles el color
        # los vuelve ilegibles sobre la coropleta
        "paint": {"raster-opacity": .95},
    })
    capas[tema] = propias
    print(f"{tema:7} · {len(propias):>3} capas · {cfg['url'].rsplit('/', 2)[-2]}")

paquete = {
    "glyphs": glyphs,
    "sprite": sprite,
    "sources": fuentes,
    "capas": capas,          # separadas por tema: el tablero las conmuta
    "atribucion": ATRIB,
    "origen": {t: c["url"] for t, c in ESTILOS.items()},
}
SALIDA.write_text(json.dumps(paquete, ensure_ascii=False, separators=(",", ":")),
                  encoding="utf-8")
print(f"\n✔ {SALIDA.relative_to(RAIZ)} · {SALIDA.stat().st_size/1024:.0f} KB "
      f"· {len(fuentes)} fuentes · {sum(len(v) for v in capas.values())} capas")
print("  ahora: python scripts/generar_sitios.py")
