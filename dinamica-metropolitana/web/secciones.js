/* ═══════════════════════════════════════════════════════════════════════════
   LAS SECCIONES. Cada una devuelve un <section>; el nav las alterna.
   ═══════════════════════════════════════════════════════════════════════════ */
const SECS = [];
const sec = (id, rotulo, construir) => SECS.push({id, rotulo, construir});

const CORTO_MUN={"070101":"Santa Cruz","070102":"Cotoca","070103":"Porongo",
  "070104":"La Guardia","070105":"El Torno","070201":"Warnes","071001":"Montero",
  "070502":"Pailón","070603":"Colpa Bélgica"};

const cab = (eyebrow, titulo, bajada) => h("div", {class:"sec-head"},
  h("p",{class:"eyebrow"},eyebrow), h("h2",{},titulo),
  bajada ? h("p",{class:"serif narrow",style:"color:var(--ink-2)"},bajada) : null);

const tabla = (cols, filas, nota) => {
  const t = h("table",{class:"dat"});
  t.append(h("thead",{},h("tr",{},cols.map(c=>
    h("th",{class:c.n?"n":null},c.t)))));
  t.append(h("tbody",{},filas.map(f=>
    h("tr",{class:f._c||null},cols.map((c,i)=>
      h("td",{class:(c.n?"n ":"")+(i===0?"k":"")},f[c.k]))))));
  return h("div",{class:"stack-sm"},h("div",{class:"tw"},t),
    nota?h("p",{class:"tcap",html:nota}):null);
};

/* ─────────────── 1 · LA REGIÓN ─────────────── */
sec("region","La región",()=>{
  const r=REF.region;
  const fam=D.familias_por_municipio.res;
  const porFam={}; fam.forEach(c=>porFam[c.familia]=(porFam[c.familia]||0)+c.n);
  const c=h("div",{class:"stack"});
  c.append(cab("El punto de partida",
    "Cuatro de cada diez personas que viven acá nacieron en otro municipio",
    "La Región Metropolitana de Santa Cruz es, antes que nada, un lugar al que se llega. "
    +"Lo que sigue mide quién llega, de dónde, y en qué se diferencia del que ya estaba."));
  c.append(h("div",{class:"card"},
    h("div",{class:"hero-n"},
      h("div",{class:"hn"},h("span",{class:"v"},fmt(r.n)),h("span",{class:"l"},"personas censadas en los nueve municipios")),
      h("div",{class:"hn"},h("span",{class:"v acc"},"982.469"),h("span",{class:"l"},"nacieron fuera de su municipio · el 43%")),
      h("div",{class:"hn"},h("span",{class:"v acc"},"239.884"),h("span",{class:"l"},"llegaron de fuera de su municipio entre 2019 y 2024")),
      h("div",{class:"hn"},h("span",{class:"v"},"106.151"),h("span",{class:"l"},"trabajan en un municipio distinto del que viven")))));

  c.append(h("div",{class:"card"},
    h("h3",{},"Tres dimensiones que nunca se suman entre sí"),
    tabla([{t:"Dimensión",k:"d"},{t:"Qué mide",k:"q"},{t:"Universo",k:"u",n:1},{t:"La pregunta",k:"p"}],
      [{d:"Nacimiento",q:"stock, sin fecha",u:"2.282.770",p:"¿dónde nació?"},
       {d:"Residencia 2019",q:"flujo fechado 2019→2024",u:"2.109.515",p:"¿dónde vivía hace cinco años?"},
       {d:"Trabajo",q:"desplazamiento diario",u:"1.043.524",p:"¿dónde está su trabajo?"}],
      "El universo de residencia excluye a las <b>173.255 personas que aún no habían nacido</b> en 2019; "
      +"el de trabajo, a quien no declaró lugar. Quien se mueve a trabajar <b>no se mudó</b>: se desplaza todos los días.")));

  const orden=["dep","scz_parcial","region","dep_parcial","scz","exterior","sd"];
  c.append(h("div",{class:"card"},
    h("h3",{},"De dónde vino quien llegó entre 2019 y 2024"),
    figuraBarras(orden.filter(k=>porFam[k]).map(k=>({
      k:D.familias_de_origen[k]||k, v:porFam[k],
      destacar:k==="region"||k==="exterior"})),"personas"),
    h("p",{class:"tcap",html:"Los dos grupos «sin precisar» son declaraciones parciales: "
      +"la persona dijo el departamento o la provincia pero no el municipio. <b>No se descartan</b>: "
      +"son códigos válidos del INE, no datos faltantes."})));
  return c;
});

/* barras horizontales simples, un solo color */
function figuraBarras(datos,unidad){
  const max=Math.max(...datos.map(d=>d.v));
  return h("div",{class:"stack-sm"},datos.map(d=>{
    const b=h("div",{class:"b",style:"height:15px;background:var(--panel-2);position:relative"});
    b.append(h("i",{style:`position:absolute;left:0;top:0;height:100%;width:${100*d.v/max}%;`
      +`background:var(${d.destacar?"--acc":"--r3"})`}));
    const fila=h("div",{style:"display:flex;flex-direction:column;gap:3px"},
      h("div",{style:"display:flex;justify-content:space-between;font-size:.79rem"},
        h("span",{style:d.destacar?"font-weight:600":""},d.k),
        h("span",{style:"font-variant-numeric:tabular-nums;color:var(--ink-2)"},fmt(d.v))),b);
    conTip(fila,`<b>${d.k}</b><br>${fmt(d.v)} ${unidad}`);
    return fila;
  }));
}

/* ─────────────── 2 · QUIÉN LLEGA ─────────────── */
sec("llegan","Quién llega",()=>{
  const c=h("div",{class:"stack"});
  c.append(cab("Dimensión · residencia 2019 → 2024",
    "No es una migración: son seis, y no se parecen en nada",
    "La página anterior publicaba un solo perfil del recién llegado. Separados por origen, "
    +"el promedio se rompe: el que viene de más lejos llega con más escuela, y el que se mudó "
    +"acá al lado vive peor que todos."));

  const fam=D.familias_por_municipio.res, agg={};
  fam.forEach(x=>{
    const a=agg[x.familia]||(agg[x.familia]={n:0,s:{}});
    a.n+=x.n;
    ["anios_estudio","pct_superior","quintil_medio","privaciones","pct_sin_seguro",
     "pct_alcantarillado","pct_hacinamiento","pct_alquila","pct_conmuta","pct_paga_tres"]
      .forEach(k=>{if(x[k]!=null){a.s[k]=(a.s[k]||0)+x[k]*x.n}});
  });
  const K=["anios_estudio","pct_superior","quintil_medio","privaciones","pct_sin_seguro",
           "pct_alcantarillado","pct_hacinamiento","pct_alquila","pct_conmuta"];
  const filas=Object.entries(agg).filter(([k])=>k!=="sd")
    .sort((a,b)=>b[1].n-a[1].n).map(([k,a])=>{
      const f={o:D.familias_de_origen[k]||k,n:fmt(a.n),
        _c:(k==="region"||k==="exterior")?"hi":null};
      K.forEach(x=>f[x]=a.s[x]!=null?val(a.s[x]/a.n,x):"—");
      return f;
    });
  const r=REF.region, fr={o:"· toda la región ·",n:fmt(r.n),_c:"ref"};
  K.forEach(x=>fr[x]=val(r[x],x)); filas.push(fr);

  c.append(h("div",{class:"card"},
    h("h3",{},"Los llegados 2019→2024, por origen, contra el total regional"),
    tabla([{t:"De dónde venía",k:"o"},{t:"Personas",k:"n",n:1},
      ...K.map(k=>({t:nom(k),k,n:1}))],filas,
      "Las dos filas marcadas son las que rompen el promedio. El que se mudó <b>dentro de la "
      +"región</b> tiene menos de la mitad del alcantarillado de la media y conmuta cuatro veces "
      +"más que nadie, con educación y riqueza de clase media: no es pobreza, es haberse ido a "
      +"vivir donde no llegó la red. El que llegó del <b>exterior</b> es el opuesto en todo, salvo "
      +"en el seguro de salud.")));

  c.append(h("figure",{class:"card"},
    h("div",{},h("h3",{},"Educación y servicios no van juntos"),
      h("p",{class:"tag"},"años de estudio contra porcentaje que vive en un hogar con alcantarillado")),
    h("div",{class:"chartbox"},dispersion(Object.entries(agg).filter(([k])=>k!=="sd").map(([k,a])=>({
      k:D.familias_de_origen[k]||k, x:a.s.anios_estudio/a.n, y:a.s.pct_alcantarillado/a.n,
      n:a.n, destacar:k==="region"})),r)),
    h("figcaption",{html:"El punto de referencia (cruz punteada) es el total de la región. "
      +"<b>El que se mudó dentro de la región queda solo abajo</b>: escuela de clase media y "
      +"el peor saneamiento de los seis grupos."})));

  c.append(h("div",{class:"nota ojo",html:"<span class='lede'>La no respuesta no es aleatoria</span>"
    +"Las <b>43.574</b> personas que no declararon de dónde venían tienen <b>17,5%</b> con "
    +"educación superior contra 35,7% de la región. Sesgan hacia abajo cualquier total que las "
    +"incluya, y por eso van en su propia fila y no repartidas entre las demás."}));

  c.append(h("div",{class:"card"},
    h("h3",{},"Los orígenes de fuera de la región, uno por uno"),
    h("p",{class:"tag"},"los "+D.externos.celdas.length+" con al menos 150 personas, de los cientos que hay"),
    tabla([{t:"Origen",k:"o"},{t:"Personas",k:"n",n:1},{t:"Años de estudio",k:"e",n:1},
      {t:"% superior",k:"s",n:1},{t:"Quintil",k:"q",n:1},{t:"Privaciones",k:"p",n:1},
      {t:"% alcantarillado",k:"a",n:1}],
      D.externos.celdas.filter(x=>x.origen!=="sd").slice(0,26).map(x=>({
        o:x.nombre,n:fmt(x.n),e:dec(x.anios_estudio,2),s:dec(x.pct_superior,1)+"%",
        q:dec(x.quintil_medio,2),p:dec(x.privaciones,2),a:dec(x.pct_alcantarillado,1)+"%"})),
      "Ordenados por tamaño. Los que dicen sólo el departamento o la provincia son "
      +"<b>declaraciones parciales</b>, y entran con esa etiqueta en vez de descartarse.")));
  return c;
});

function dispersion(pts,ref){
  const W=720,H=340,L=52,R=20,T=20,B=44;
  const sv=s("svg",{viewBox:`0 0 ${W} ${H}`,width:W,height:H,role:"img",
    "aria-label":"Dispersión de los orígenes migratorios entre años de estudio y acceso a alcantarillado"});
  const xs=pts.map(p=>p.x).concat(ref.anios_estudio), ys=pts.map(p=>p.y).concat(ref.pct_alcantarillado);
  const x0=Math.min(...xs)-.5,x1=Math.max(...xs)+.5,y0=Math.max(0,Math.min(...ys)-8),y1=Math.max(...ys)+8;
  const X=v=>L+(v-x0)/(x1-x0)*(W-L-R), Y=v=>H-B-(v-y0)/(y1-y0)*(H-T-B);
  const i3=cssv("--ink-3"),ru=cssv("--rule-2"),ac=cssv("--acc"),pa=cssv("--panel"),ik=cssv("--ink");
  for(let v=Math.ceil(y0/10)*10;v<=y1;v+=10){
    sv.append(s("line",{x1:L,x2:W-R,y1:Y(v),y2:Y(v),stroke:ru,"stroke-width":1}));
    sv.append(s("text",{x:L-8,y:Y(v)+4,"text-anchor":"end","font-size":11,fill:i3},v+"%"));
  }
  for(let v=Math.ceil(x0*2)/2;v<=x1;v+=.5){
    if(Math.round(v*2)%2)continue;
    sv.append(s("text",{x:X(v),y:H-B+18,"text-anchor":"middle","font-size":11,fill:i3},dec(v,0)));
  }
  sv.append(s("line",{x1:L,x2:W-R,y1:H-B,y2:H-B,stroke:cssv("--rule"),"stroke-width":1}));
  sv.append(s("text",{x:L,y:H-8,"font-size":10.5,fill:i3},"años promedio de estudio →"));
  sv.append(s("text",{x:-T-4,y:13,"font-size":10.5,fill:i3,transform:"rotate(-90)","text-anchor":"end"},
    "↑ % que vive en un hogar con alcantarillado"));
  sv.append(s("line",{x1:L,x2:W-R,y1:Y(ref.pct_alcantarillado),y2:Y(ref.pct_alcantarillado),
    stroke:i3,"stroke-width":1,"stroke-dasharray":"3 4",opacity:.6}));
  sv.append(s("line",{x1:X(ref.anios_estudio),x2:X(ref.anios_estudio),y1:T,y2:H-B,
    stroke:i3,"stroke-width":1,"stroke-dasharray":"3 4",opacity:.6}));
  pts.forEach((p,i)=>{
    const g=s("g",{}), cx=X(p.x), cy=Y(p.y);
    g.append(s("circle",{cx,cy,r:9,fill:pa}));
    g.append(s("circle",{cx,cy,r:7,fill:ac,opacity:p.destacar?1:.72}));
    const arriba=cy>T+34, an=cx>W-140?"end":(cx<L+90?"start":"middle");
    g.append(s("text",{x:cx+(an==="end"?-11:an==="start"?11:0),y:cy+(arriba?-13:22),
      "text-anchor":an,"font-size":11.5,"font-weight":p.destacar?700:600,fill:ik},p.k));
    conTip(g,`<b>${p.k}</b><br>${fmt(p.n)} personas<br>${dec(p.x,2)} años de estudio<br>${dec(p.y,1)}% con alcantarillado`);
    sv.append(g);
  });
  return sv;
}

/* ─────────────── 3 · EL EXTERIOR ─────────────── */
sec("exterior","El exterior",()=>{
  const c=h("div",{class:"stack"});
  const sub={}; D.exterior.subgrupo.forEach(x=>sub[x.subgrupo]=x);
  c.append(cab("Dimensión · residencia 2019 → 2024",
    "«El exterior» son dos migraciones opuestas, y casi la mitad son bolivianos que volvieron",
    "De los 24.672 que en 2019 vivían en otro país, la mitad nació en Bolivia. Promediarlos "
    +"borra el único indicador que aquí dice algo."));
  c.append(h("div",{class:"card"},h("div",{class:"hero-n"},
    h("div",{class:"hn"},h("span",{class:"v"},fmt(sub.retornado.n)),
      h("span",{class:"l"},"nacieron en Bolivia y volvieron · 48,4%")),
    h("div",{class:"hn"},h("span",{class:"v acc"},fmt(sub.extranjero.n)),
      h("span",{class:"l"},"nacieron en el exterior · 51,6%")),
    h("div",{class:"hn"},h("span",{class:"v al"},"24,1%"),
      h("span",{class:"l"},"de los nacidos afuera y mayores de 18 no tiene ningún documento de identidad boliviano")),
    h("div",{class:"hn"},h("span",{class:"v"},"0,1%"),
      h("span",{class:"l"},"entre los retornados")))));

  const K=["anios_estudio","pct_superior","quintil_medio","privaciones","pct_sin_seguro",
           "pct_sin_cedula","pct_cedula_extranjero","pct_alcantarillado","pct_alquila","pct_paga_tres"];
  const filas=["retornado","extranjero"].map(k=>{
    const x=sub[k],f={o:k==="retornado"?"Retornados (nacidos en Bolivia)":"Extranjeros (nacidos afuera)",
      n:fmt(x.n),_c:k==="extranjero"?"hi":null};
    K.forEach(y=>f[y]=val(x[y],y));return f});
  const r=REF.region,fr={o:"· toda la región ·",n:fmt(r.n),_c:"ref"};
  K.forEach(y=>fr[y]=val(r[y],y));filas.push(fr);
  c.append(h("div",{class:"card"},
    h("h3",{},"Los dos grupos, lado a lado"),
    tabla([{t:"Quién",k:"o"},{t:"Personas",k:"n",n:1},...K.map(k=>({t:nom(k),k,n:1}))],filas)));

  c.append(h("div",{class:"nota alerta",html:"<span class='lede'>Una trampa de redacción que casi publicamos</span>"
    +"La variable <code>p28_cn</code> pregunta si el nacimiento está inscrito en el registro civil "
    +"<b>boliviano</b>. Que alguien nacido en Perú conteste «no» es la respuesta correcta y esperable, "
    +"<b>no una carencia</b>. Publicar «31,5% del exterior sin registro civil» habría convertido el "
    +"enunciado de una pregunta en un problema social inexistente. El indicador que sí dice algo es "
    +"la cédula: entre los nacidos afuera y mayores de edad, <b>el 24,1% no tiene ningún documento "
    +"de identidad boliviano</b> — ni cédula nacional ni cédula de extranjero."}));

  const pais=D.exterior.por_pais.filter(x=>x.subgrupo==="extranjero").slice(0,14);
  c.append(h("div",{class:"card"},
    h("h3",{},"De qué países vinieron los nacidos en el exterior"),
    tabla([{t:"País donde vivía en 2019",k:"o"},{t:"Personas",k:"n",n:1},
      {t:"Años de estudio",k:"e",n:1},{t:"% superior",k:"s",n:1},
      {t:"Quintil",k:"q",n:1},{t:"% sin cédula boliviana",k:"c",n:1}],
      pais.map(x=>({o:x.nombre,n:fmt(x.n),e:dec(x.anios_estudio,2),
        s:dec(x.pct_superior,1)+"%",q:dec(x.quintil_medio,2),
        c:x.pct_sin_cedula!=null?dec(x.pct_sin_cedula,1)+"%":"—"})),
      "Sólo los países con al menos 60 personas. El porcentaje sin cédula se calcula sobre "
      +"los mayores de 18 años de cada grupo.")));
  return c;
});

/* ─────────────── 4 · LA TRAYECTORIA ─────────────── */
sec("trayectoria","La trayectoria",()=>{
  const c=h("div",{class:"stack"});
  c.append(cab("Dimensión · año de llegada",
    "Con los años se acumula vivienda, pero la escuela no mejora: llega ya puesta",
    "1.638.883 personas declararon desde qué año residen. Cortando por cohorte de llegada, "
    +"una foto se vuelve una película — con la condición de saber qué parte es trayectoria "
    +"y qué parte es que las cohortes son gente distinta."));

  const ORD=["antes de 2000","2000-2009","2010-2014","2015-2019","2020-2022","2023-2024"];
  const cel=D.cohortes.celdas;
  const grupos=[["extranjero","Nacidos en el exterior"],["retornado","Retornados"],
    ["dep","Nacidos en otro departamento"],["scz","Nacidos en el resto de Santa Cruz"],
    ["region","Nacidos en otro municipio de la región"]];

  c.append(h("figure",{class:"card"},
    h("div",{},h("h3",{},"Propietarios según cuándo llegaron"),
      h("p",{class:"tag"},"porcentaje que vive en una vivienda propia, por cohorte de llegada")),
    h("div",{class:"chartbox"},lineasCohorte(grupos,cel,ORD,"pct_propia")),
    h("figcaption",{html:"Esto <b>sí</b> es trayectoria: el hogar acumula patrimonio con los años "
      +"de residencia. Entre los nacidos en el exterior, la propiedad pasa de <b>25,1%</b> en los "
      +"que llegaron en 2023-24 a <b>77,4%</b> en los que llegaron antes de 2000, y el alquiler "
      +"recorre el camino inverso, de 60,4% a 13,6%."})));

  c.append(h("figure",{class:"card"},
    h("div",{},h("h3",{},"Años de estudio según cuándo llegaron"),
      h("p",{class:"tag"},"promedio de años de estudio, por cohorte de llegada")),
    h("div",{class:"chartbox"},lineasCohorte(grupos,cel,ORD,"anios_estudio")),
    h("figcaption",{html:"Esto <b>no</b> es trayectoria: va al revés. Los que llegaron hace poco "
      +"tienen <b>más</b> escuela que los que llegaron hace veinticinco años. La educación de un "
      +"adulto es un stock fijado <b>antes</b> de migrar y no puede mejorar por asimilación, así que "
      +"su variación entre cohortes es <b>composición</b>: la migración reciente es distinta de la "
      +"vieja."})));

  c.append(h("div",{class:"nota ojo",html:"<span class='lede'>Cómo leer estas curvas sin equivocarse</span>"
    +"Un corte transversal por cohorte mezcla dos cosas: cuánto mejora una persona con los años "
    +"de residencia (asimilación, Chiswick 1978) y cuánto difieren entre sí las cohortes que "
    +"llegaron en épocas distintas (composición, Borjas 1985). <b>El criterio para separarlas</b>: "
    +"si el atributo se fija antes de migrar —la educación de un adulto— su variación es "
    +"composición; si cambia después de llegar —la vivienda, los servicios, los bienes— hay "
    +"trayectoria. Por eso publicamos las dos curvas juntas y no una sola."}));
  return c;
});

function lineasCohorte(grupos,cel,ORD,ind){
  const W=740,H=330,L=54,R=150,T=20,B=44;
  const sv=s("svg",{viewBox:`0 0 ${W} ${H}`,width:W,height:H,role:"img",
    "aria-label":"Curvas por cohorte de llegada de "+nom(ind)});
  const series=grupos.map(([k,et])=>({k,et,
    p:ORD.map(o=>{const x=cel.find(z=>z.origen===k&&z.cohorte===o);return x?x[ind]:null})}))
    .filter(z=>z.p.some(v=>v!=null));
  const vals=series.flatMap(z=>z.p).filter(v=>v!=null);
  const y0=Math.min(...vals),y1=Math.max(...vals),pad=(y1-y0)*.16;
  const Y=v=>H-B-(v-(y0-pad))/((y1+pad)-(y0-pad))*(H-T-B);
  const X=i=>L+i*(W-L-R)/(ORD.length-1);
  const i3=cssv("--ink-3"),ru=cssv("--rule-2"),pa=cssv("--panel");
  const COL=[cssv("--acc"),cssv("--acc-2"),cssv("--amber"),cssv("--r3"),cssv("--rust")];
  const paso=(y1-y0)>60?20:((y1-y0)>12?5:1);
  for(let v=Math.ceil((y0-pad)/paso)*paso;v<=y1+pad;v+=paso){
    sv.append(s("line",{x1:L,x2:W-R,y1:Y(v),y2:Y(v),stroke:ru,"stroke-width":1}));
    sv.append(s("text",{x:L-8,y:Y(v)+4,"text-anchor":"end","font-size":11,fill:i3},
      esPct(ind)?v+"%":dec(v,0)));
  }
  ORD.forEach((o,i)=>sv.append(s("text",{x:X(i),y:H-B+18,"text-anchor":"middle",
    "font-size":10,fill:i3},o.replace("antes de ","<"))));
  sv.append(s("text",{x:L,y:H-8,"font-size":10.5,fill:i3},"← llegaron hace más tiempo   ·   llegaron hace menos →"));
  series.forEach((z,si)=>{
    const col=COL[si%COL.length];
    let d="",prev=false;
    z.p.forEach((v,i)=>{if(v==null){prev=false;return}
      d+=(prev?"L":"M")+X(i)+","+Y(v)+" ";prev=true});
    sv.append(s("path",{d,fill:"none",stroke:col,"stroke-width":2,
      "stroke-linejoin":"round","stroke-linecap":"round"}));
    z.p.forEach((v,i)=>{if(v==null)return;
      const g=s("g",{});
      g.append(s("circle",{cx:X(i),cy:Y(v),r:6.5,fill:pa}));
      g.append(s("circle",{cx:X(i),cy:Y(v),r:4.5,fill:col}));
      const x=cel.find(t=>t.origen===z.k&&t.cohorte===ORD[i]);
      conTip(g,`<b>${z.et}</b><br>llegaron ${ORD[i]}<br>${nom(ind)}: ${val(v,ind)}`
        +`<br><span class="d">${fmt(x?x.n:0)} personas</span>`);
      sv.append(g)});
    const ult=z.p.map((v,i)=>[v,i]).filter(t=>t[0]!=null).pop();
    if(ult)sv.append(s("text",{x:W-R+10,y:Y(ult[0])+4,"font-size":11,
      "font-weight":600,fill:col},z.et));
  });
  return sv;
}

/* ─────────────── 5 · EL EXPLORADOR ─────────────── */
const EST_EXP={dim:"res",ind:"n",sel:null};
sec("explorador","El explorador",()=>{
  const c=h("div",{class:"stack"});
  c.append(cab("Las 7.487 relaciones",
    "La matriz de quién viene de dónde, y la ficha de cada relación",
    "Cada casilla es una relación entre dos de los nueve municipios. Se pinta por el indicador "
    +"que elijas, y al hacer clic se abre su composición completa."));
  const cont=h("div",{class:"stack"});
  c.append(cont);
  const pintar=()=>{cont.replaceChildren(controlesMatriz(pintar),cajaMatriz(pintar),cajaFicha())};
  pintar();
  return c;
});

const DIMS={res:{et:"Residencia 2019 → 2024",fila:"vivía en",col:"vive ahora en",
                 sub:"se mudó entre 2019 y 2024"},
            nac:{et:"Lugar de nacimiento",fila:"nació en",col:"vive en",
                 sub:"nació en un municipio y vive en otro"},
            con:{et:"Lugar de trabajo",fila:"vive en",col:"trabaja en",
                 sub:"vive en un municipio y trabaja en otro"}};
const INDS=["n","anios_estudio","pct_superior","quintil_medio","privaciones",
  "pct_sin_seguro","pct_alcantarillado","pct_hacinamiento","pct_propia","pct_alquila",
  "pct_ocupado","pct_paga_tres","pct_indigena","edad_mediana"];

function controlesMatriz(repintar){
  const ct=h("div",{class:"controles"});
  const g1=h("div",{class:"grupo"},h("span",{},"dimensión"));
  const sg=h("div",{class:"segm"});
  Object.entries(DIMS).forEach(([k,v])=>sg.append(h("button",
    {"aria-pressed":EST_EXP.dim===k,onclick:()=>{EST_EXP.dim=k;EST_EXP.sel=null;repintar()}},
    v.et)));
  g1.append(sg); ct.append(g1);
  const g2=h("div",{class:"grupo"},h("span",{},"pintar por"));
  const sl=h("select",{onchange:e=>{EST_EXP.ind=e.target.value;repintar()}});
  INDS.forEach(k=>sl.append(h("option",{value:k,selected:EST_EXP.ind===k?"":null},nom(k))));
  g2.append(sl); ct.append(g2);
  return ct;
}

function cajaMatriz(repintar){
  const M=D.matrices[EST_EXP.dim], dim=DIMS[EST_EXP.dim], ind=EST_EXP.ind;
  const vals=[];
  COD9.forEach(o=>COD9.forEach(d=>{const x=M[o]&&M[o][d];
    if(x&&x[ind]!=null)vals.push(x[ind])}));
  const lo=Math.min(...vals),hi=Math.max(...vals);
  const esc=v=>{if(v==null)return 0;
    const t=ind==="n"?Math.sqrt((v-lo)/(hi-lo||1)):(v-lo)/(hi-lo||1);
    return Math.min(5,Math.max(1,Math.ceil(t*5)))};
  const t=h("table",{class:"mx"});
  const cab1=h("tr",{},h("th",{}, ""));
  COD9.forEach(d=>cab1.append(h("th",{class:"col",title:N9[d]},CORTO_MUN[d]||N9[d])));
  t.append(h("thead",{},cab1));
  const tb=h("tbody",{});
  COD9.forEach(o=>{
    const tr=h("tr",{},h("th",{title:N9[o]},CORTO_MUN[o]||N9[o]));
    COD9.forEach(d=>{
      const td=h("td",{});
      if(o===d){td.append(h("div",{class:"celda diag"}));tr.append(td);return}
      const x=M[o]&&M[o][d];
      const n=x?x.n:0, v=x?x[ind]:null, q=esc(v);
      const sel=EST_EXP.sel&&EST_EXP.sel[0]===o&&EST_EXP.sel[1]===d;
      const cl=h("div",{class:"celda"+(sel?" sel":""),
        style:`background:var(--r${v==null?0:q});color:${q>=4?"#fff":"var(--ink-2)"}`,
        "data-clic":x?"1":null,
        onclick:x?()=>{EST_EXP.sel=[o,d];repintar();}:null},
        n?(ind==="n"?(n>=1000?Math.round(n/1000)+"k":n):dec(v,esPct(ind)?0:1)):"");
      conTip(cl,`<b>${N9[o]} → ${N9[d]}</b><br>${dim.fila} ${N9[o]}, ${dim.col} ${N9[d]}`
        +`<br>${fmt(n)} personas`+(v!=null&&ind!=="n"?`<br>${nom(ind)}: ${val(v,ind)}`:"")
        +(x?'<br><span class="d">clic para ver la ficha</span>':""));
      td.append(cl);tr.append(td);
    });
    tb.append(tr);
  });
  t.append(tb);
  const leyenda=h("div",{class:"escala"},h("span",{},"menos"),
    [1,2,3,4,5].map(q=>h("i",{style:`background:var(--r${q})`})),h("span",{},"más"),
    h("span",{style:"color:var(--ink-3);margin-left:8px"},
      `${nom(ind)} · de ${val(lo,ind)} a ${val(hi,ind)}`));
  return h("div",{class:"card"},
    h("div",{style:"display:flex;flex-wrap:wrap;gap:4px 14px;align-items:baseline"},
      h("h3",{},"Filas: "+dim.fila+" · columnas: "+dim.col),
      h("span",{class:"tag"},"la diagonal se omite: son los que no se movieron")),
    h("div",{class:"matriz-box"},t),leyenda);
}

function cajaFicha(){
  if(!EST_EXP.sel)
    return h("div",{class:"card"},h("p",{class:"tag"},
      "Elegí una casilla de la matriz para ver la composición completa de esa relación: "
      +"quién es, qué sabe, de qué vive, cómo vive, con qué cuenta y qué le falta."));
  const [o,d]=EST_EXP.sel, dim=EST_EXP.dim;
  const clave=`${dim}|${o}|${d}`;
  const c=D.fichas[clave]||(D.matrices[dim][o]||{})[d];
  if(!c)return h("div",{class:"card"},h("p",{class:"tag"},"Sin datos para esa relación."));
  const ref = dim==="con" ? REF.region : REF.nativo_del_municipio[d];
  const refNom = dim==="con" ? "el total de la región"
    : "quien ya vivía en "+N9[d]+" en 2019";
  return h("div",{class:"card"},ficha(c,
    N9[o]+" → "+N9[d], DIMS[dim].et+" · "+DIMS[dim].sub, ref, refNom));
}

/* ─────────────── 6 · LOS NUEVE ─────────────── */
const EST_MUN={cod:"070101"};
sec("municipios","Los nueve",()=>{
  const c=h("div",{class:"stack"});
  c.append(cab("Municipio por municipio",
    "Quién vive acá, quién llegó, quién sale a trabajar",
    "La misma información, ordenada como la usa quien gestiona un municipio."));
  const cont=h("div",{class:"stack"});c.append(cont);
  const pintar=()=>{
    const grid=h("div",{class:"muni-grid"});
    COD9.forEach(k=>{
      const r=REF.municipio[k];
      const b=h("button",{class:"muni","aria-pressed":EST_MUN.cod===k,
        onclick:()=>{EST_MUN.cod=k;pintar()}},
        h("span",{class:"nm"},N9[k]),
        h("span",{class:"st"},fmt(r.n)+" personas · "+dec(r.anios_estudio,2)+" años de estudio"),
        h("span",{class:"st"},"quintil "+dec(r.quintil_medio,2)+" · "
          +dec(r.pct_alcantarillado,0)+"% alcantarillado"));
      grid.append(b);
    });
    cont.replaceChildren(grid,fichaMunicipio(EST_MUN.cod));
  };
  pintar();
  return c;
});

function fichaMunicipio(cod){
  const r=REF.municipio[cod], nat=REF.nativo_del_municipio[cod];
  const fams=D.familias_por_municipio.res.filter(x=>x.destino===cod)
    .sort((a,b)=>b.n-a.n);
  const salen=D.corredores.celdas.filter(x=>x.residencia===cod&&x.trabajo!=="mun:"+cod)
    .sort((a,b)=>b.n-a.n).slice(0,8);
  const vienen=D.corredores.celdas.filter(x=>x.trabajo==="mun:"+cod&&x.residencia!==cod)
    .sort((a,b)=>b.n-a.n).slice(0,8);
  const K=["anios_estudio","pct_superior","quintil_medio","privaciones",
           "pct_sin_seguro","pct_alcantarillado","pct_hacinamiento","pct_conmuta"];
  return h("div",{class:"stack"},
    h("div",{class:"card"},ficha(r,N9[cod],"El total del municipio",REF.region,"el total de la región")),
    h("div",{class:"card"},
      h("h3",{},"De dónde llegó quien vive en "+N9[cod]),
      tabla([{t:"Origen",k:"o"},{t:"Personas",k:"n",n:1},...K.map(k=>({t:nom(k),k,n:1}))],
        fams.map(x=>{const f={o:D.familias_de_origen[x.familia]||x.familia,n:fmt(x.n)};
          K.forEach(k=>f[k]=val(x[k],k));return f})
          .concat([(()=>{const f={o:"· quien ya estaba acá ·",n:fmt(nat.n),_c:"ref"};
            K.forEach(k=>f[k]=val(nat[k],k));return f})()]),
        "La última fila es la referencia local: quien ya vivía en "+N9[cod]+" en 2019.")),
    h("div",{class:"card"},
      h("h3",{},"Quién sale de "+N9[cod]+" a trabajar, y quién viene a trabajar acá"),
      h("div",{style:"display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px"},
        h("div",{class:"stack-sm"},h("h4",{style:"color:var(--ink-3)"},"SALEN A TRABAJAR"),
          salen.length?tabla([{t:"Trabaja en",k:"o"},{t:"Personas",k:"n",n:1},
            {t:"Años est.",k:"e",n:1},{t:"% superior",k:"s",n:1}],
            salen.map(x=>({o:x.nom_tra,n:fmt(x.n),e:dec(x.anios_estudio,2),
              s:dec(x.pct_superior,1)+"%"}))):h("p",{class:"tag"},"Sin corredores de tamaño suficiente.")),
        h("div",{class:"stack-sm"},h("h4",{style:"color:var(--ink-3)"},"VIENEN A TRABAJAR"),
          vienen.length?tabla([{t:"Vive en",k:"o"},{t:"Personas",k:"n",n:1},
            {t:"Años est.",k:"e",n:1},{t:"% superior",k:"s",n:1}],
            vienen.map(x=>({o:x.nom_res,n:fmt(x.n),e:dec(x.anios_estudio,2),
              s:dec(x.pct_superior,1)+"%"}))):h("p",{class:"tag"},"Sin corredores de tamaño suficiente."))),
      h("p",{class:"tcap",html:"Sólo se ven los que <b>viven</b> en los nueve municipios. "
        +"Quien vive fuera de la región y viene a trabajar adentro no está en este cuadro: "
        +"para verlo hay que salir del recorte metropolitano y leer el censo nacional."})));
}

/* ─────────────── 7 · MÉTODO ─────────────── */
sec("metodo","Método",()=>{
  const c=h("div",{class:"stack"});
  c.append(cab("Cómo está hecho","Lo que se midió, con qué método y qué no se puede medir"));
  c.append(h("div",{class:"card"},
    h("h3",{},"El índice de riqueza"),
    h("p",{class:"serif",style:"color:var(--ink-2)",html:
      "El censo <b>no pregunta ingreso</b> — se revisaron sus 114 variables de persona y "
      +"44 de vivienda. El nivel de vida se mide con un <b>análisis de componentes "
      +"principales</b> sobre 33 variables de activos, materiales y servicios "
      +"(Filmer &amp; Pritchett, 2001), con la <b>corrección urbano/rural de Rutstein "
      +"(2008)</b>: un índice común, uno propio de cada área, y anclaje por regresión, "
      +"para que al hogar rural no se lo mida con una vara urbana."}),
    h("p",{class:"nota ojo",html:"<span class='lede'>Es ordinal, no es plata</span>"
      +"«Quintil 5» significa «entre el 20% de la región con más activos», <b>no</b> un monto "
      +"en bolivianos. Para llegar a bolivianos haría falta una estimación por áreas pequeñas "
      +"(Elbers, Lanjouw &amp; Lanjouw 2003) con el microdato de la Encuesta de Hogares, que es "
      +"una fase aparte y no está hecha."}),
    tabla([{t:"Validación contra variables que NO entraron al índice",k:"k"},
      {t:"Q1",k:"a",n:1},{t:"Q2",k:"b",n:1},{t:"Q3",k:"c",n:1},{t:"Q4",k:"d",n:1},{t:"Q5",k:"e",n:1}],
      [{k:"Años de estudio (19+)",a:"9,2",b:"10,1",c:"10,9",d:"12,3",e:"14,3"},
       {k:"% con educación superior",a:"9,6",b:"12,5",c:"18,4",d:"29,7",e:"47,1"},
       {k:"% analfabeto (15+)",a:"2,3",b:"1,6",c:"1,3",d:"0,8",e:"0,4"},
       {k:"% sin seguro de salud",a:"34,9",b:"32,7",c:"32,2",d:"31,6",e:"28,1"}],
      "La educación no entró en el índice. Que lo ordene de forma monótona es la prueba "
      +"externa de que el índice mide lo que dice medir.")));

  c.append(h("div",{class:"card"},
    h("h3",{},"Las privaciones"),
    h("p",{class:"serif",style:"color:var(--ink-2)",html:
      "Se publican <b>una por una y con el umbral escrito al lado</b>, en las seis dimensiones "
      +"del NBI. <b>No se rotulan «NBI oficial»</b>: los umbrales exactos del INE no están en el "
      +"diccionario del censo, y ponerles un número propio para poder usar la etiqueta sería "
      +"presentar como oficial algo que no lo es."}),
    tabla([{t:"Privación",k:"p"},{t:"Umbral declarado",k:"u"},{t:"Dimensión",k:"d"}],
      [{p:"Pared precaria",u:"tabique, quinche, caña, palma o tronco",d:"Vivienda · materiales"},
       {p:"Techo precario",u:"paja, palma, caña, barro, jatata o motacú",d:"Vivienda · materiales"},
       {p:"Piso de tierra",u:"piso de tierra",d:"Vivienda · materiales"},
       {p:"Hacinamiento",u:"más de 3 personas por dormitorio",d:"Vivienda · espacio"},
       {p:"Sin cuarto de cocina",u:"sin un cuarto exclusivo para cocinar",d:"Vivienda · espacio"},
       {p:"Agua",u:"no llega por cañería de red ni se distribuye dentro del lote",d:"Servicios básicos"},
       {p:"Saneamiento",u:"sin baño ni letrina, o desagüe a la calle, quebrada o río",d:"Servicios básicos"},
       {p:"Energía",u:"sin energía eléctrica de ninguna fuente",d:"Servicios básicos"},
       {p:"Basura",u:"se bota a un terreno baldío, la calle o el río",d:"Servicios básicos"},
       {p:"Combustible",u:"cocina con leña, guano, bosta o taquia",d:"Insumos energéticos"}])));

  c.append(h("div",{class:"card"},
    h("h3",{},"La capacidad de pago"),
    h("p",{class:"serif",style:"color:var(--ink-2)",html:
      "En vez de estimar un ingreso y aplicarle un umbral de asequibilidad, se lee lo que el "
      +"hogar <b>ya sostiene de hecho</b>: internet fijo, aire acondicionado, lavadora y "
      +"computadora no son necesidades, son gastos voluntarios y recurrentes. Sostenerlos es "
      +"evidencia directa de capacidad de pago y no requiere ningún supuesto sobre el ingreso."})));

  c.append(h("div",{class:"card"},
    h("h3",{},"Lo que el censo no puede dar"),
    h("ul",{style:"margin:0;padding-left:18px;color:var(--ink-2);font-size:.93rem;line-height:1.6"},
      [["Ingreso o gasto","ninguna de las 158 variables lo pregunta"],
       ["Nada por debajo del municipio","ni en residencia anterior ni en lugar de trabajo: no hay zona, unidad vecinal, barrio ni distrito"],
       ["Modo de transporte, tiempo de viaje ni hora de salida","el bloque de movilidad son cuatro variables y ninguna es el viaje"],
       ["Dónde estudia","la conmutación educativa no existe en este censo"],
       ["Más detalle de rama que la sección CIIU","<code>act_eco_2d_13</code> trae 23 categorías y son las secciones A–U, no divisiones a dos dígitos"]]
      .map(([a,b])=>h("li",{html:"<b>"+a+".</b> "+b})))));

  c.append(h("div",{class:"nota",html:"<span class='lede'>Dos avisos de lectura</span>"
    +"<b>Los indicadores de vivienda se leen como personas:</b> «38% con alcantarillado» "
    +"significa que el 38% de esas personas vive en un hogar que lo tiene. Y <b>la no respuesta "
    +"no es aleatoria</b>: quienes no declararon origen tienen 17,5% con superior contra 35,7% "
    +"de la región, así que van siempre en su propia fila."}));
  return c;
});

/* ═══════════ montaje ═══════════ */
const NAV=document.getElementById("nav"), CONT=document.getElementById("secciones");
let actual=null;
function mostrar(id){
  actual=id;
  CONT.replaceChildren();
  const s=SECS.find(x=>x.id===id);
  const el=h("section",{id:"s-"+id},s.construir());
  CONT.append(el);
  [...NAV.children].forEach(b=>b.setAttribute("aria-current",b.dataset.id===id));
  if(location.hash!=="#"+id)history.replaceState(null,"","#"+id);
  scrollTo({top:0,behavior:"instant"});
}
SECS.forEach(s=>NAV.append(h("button",{"data-id":s.id,onclick:()=>mostrar(s.id)},s.rotulo)));
mostrar(SECS.find(s=>"#"+s.id===location.hash)?location.hash.slice(1):"region");
addEventListener("resize",()=>{clearTimeout(window._t);window._t=setTimeout(sinTip,80)});
new MutationObserver(()=>mostrar(actual)).observe(document.documentElement,
  {attributes:true,attributeFilter:["data-theme"]});
