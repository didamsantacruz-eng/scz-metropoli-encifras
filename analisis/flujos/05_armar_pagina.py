# -*- coding: utf-8 -*-
"""PASO 5 — ARMA LA PÁGINA.

Inyecta el paquete de datos y las secciones dentro de la plantilla. Se mantiene
la plantilla y el JS separados para poder editarlos como código de verdad; el
archivo servible sale de acá y **nunca se edita a mano**.

⚠️ El JSON va dentro de un <script type="application/json">, no como literal de
   JavaScript: así ningún carácter del dato puede romper el parseo. Lo único que
   hay que escapar es `</script`, que cerraría la etiqueta antes de tiempo.
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

AQUI = pathlib.Path(__file__).resolve().parent / "web"
plantilla = (AQUI / "plantilla.html").read_text(encoding="utf-8")
datos = (AQUI / "flujos_metro.json").read_text(encoding="utf-8")
secciones = (AQUI / "secciones.js").read_text(encoding="utf-8")

datos = datos.replace("</script", "<\\/script")
html = plantilla.replace("__DATOS__", datos).replace("__SECCIONES__", secciones)

sal = AQUI / "quien_se_mueve.html"
sal.write_text(html, encoding="utf-8")
print(f"✔ {sal.name} · {len(html)/1024:.0f} KB "
      f"(datos {len(datos)/1024:.0f} KB · código {(len(html)-len(datos))/1024:.0f} KB)")
