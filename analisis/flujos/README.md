# Flujos de la Región Metropolitana — medición sobre el microdato

Todo lo que hay acá se calcula desde el **CPV 2024 crudo**, no desde los archivos ya
publicados en `docs/datos/`. Es el respaldo de la auditoría del 2026-08-20 y el insumo de
la página de Dinámica metropolitana.

## Los scripts, y qué contesta cada uno

| script | pregunta | salida |
|---|---|---|
| `auditar_flujos.py` | ¿de dónde vino la gente y qué perfil trae, por origen? | `auditoria_flujos.json` |
| `perfil_socioec.py` | ¿cómo vive quien llegó? (cruce Persona × Vivienda) | `perfil_socioec.json` |
| `conmutacion2.py` | ¿quién trabaja en otro municipio, dónde y en qué? | `conmutacion_full.json` |
| `lugar_trabajo.py` | ¿trabaja en su casa o sale de ella? (`p52_mov`) | `lugar_trabajo.json` |
| `armar_auditoria.py` | junta todo para la hoja de auditoría | `auditoria_completa.json` |

Requieren el microdato en `C:\Users\HP\cpv2024\` (`Persona_CPV-2024.csv`,
`Vivienda_CPV-2024.csv`, `Emigracion_CPV-2024.csv`, `persona_full.parquet`,
`diccionario.json`). No están en el repositorio: son 3,6 GB.

## Lo que hay que saber antes de tocar esto

**El techo de granularidad.** `act_eco_2d_13` trae **23 categorías** y —pese al nombre— son
las **secciones CIIU A–U**, no divisiones a dos dígitos. `ocu_1d_13` trae **12**, el gran
grupo de ocupación. No existe el nivel que separaría «transporte terrestre» de «aéreo».
`p50_semp` **no es tamaño de empresa**: sus categorías son idénticas a `p50_catocu_13`.
La textura fina sale de **cruzar** sección × ocupación × categoría ocupacional.

**El lugar de trabajo no baja del municipio.** Son cuatro variables (`p52_mov`,
`p52_dep_mov_cod`, `p52_mun_mov_cod`, `p52_pais_mov_cod`) y ninguna llega a zona, UV,
barrio o distrito — verificado: 0 columnas de ese tipo en las 116 del archivo de personas.

**Los porcentajes de sector suman 100 y el denominador está completo**: 0 de los 49.940 que
conmutan tienen la rama sin declarar. «Descripciones incompletas» y «Sin especificar» son
categorías del INE y van DENTRO del 100%, no fuera. Al graficar: o los 22 sectores, o un
«otros» que absorba la cola — nunca un top que deje al lector sumando.

**Los parciales no se tiran.** `XX9999` y `XXYY99` son códigos válidos. Y ojo:
**9.612 de los 28.062 que figuran «trabajando fuera de la región» (34,3%) declararon una
provincia de la propia región** sin precisar municipio — 9.280 en Andrés Ibáñez, que
contiene a cinco de los nueve.

**El cruce con Vivienda va por `hogar`**, la llave que ya trae el parquet
(departamento sin cero + provincia + municipio + `i00`, como entero): 97,8% de pegue,
con `assert` para que falle ruidosamente si algún día deja de pegar.

**Leer Vivienda entera junto con las 2,28 M personas revienta por memoria.** Va por trozos.
