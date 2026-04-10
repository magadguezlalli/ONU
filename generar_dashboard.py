"""
generar_dashboard.py
--------------------
Lee los dos CSVs y genera index.html con todos los datos calculados.
No hay valores hardcodeados: todo sale de las fuentes.

Uso:
    python3 generar_dashboard.py

Estructura de carpetas esperada:
    data/722_argentina.csv
    data/llamados-atendidos-violencia-familiar-unificado-201701-202407.csv
"""

import csv
import json
import os
from collections import defaultdict, Counter

# ── Rutas ──────────────────────────────────────────────────────────────────
BASE         = os.path.dirname(os.path.abspath(__file__))
CSV_ANTENAS  = os.path.join(BASE, "data", "722_argentina.csv")
CSV_LLAMADOS = os.path.join(BASE, "data", "llamados-atendidos-violencia-familiar-unificado-201701-202407.csv")
SALIDA       = os.path.join(BASE, "index.html")

# ── Configuración geográfica ───────────────────────────────────────────────
# CABA primero para que tenga prioridad sobre Buenos Aires provincia
PROVINCIAS_BBOX = {
    "CABA":               {"lat_min":-34.70,"lat_max":-34.52,"lon_min":-58.55,"lon_max":-58.33},
    "Buenos Aires":       {"lat_min":-41.0, "lat_max":-33.0, "lon_min":-63.5, "lon_max":-56.5},
    "Córdoba":            {"lat_min":-35.5, "lat_max":-29.0, "lon_min":-66.0, "lon_max":-61.5},
    "Santa Fe":           {"lat_min":-34.5, "lat_max":-28.0, "lon_min":-62.0, "lon_max":-59.0},
    "Misiones":           {"lat_min":-28.2, "lat_max":-25.5, "lon_min":-56.0, "lon_max":-53.5},
    "Corrientes":         {"lat_min":-30.5, "lat_max":-27.0, "lon_min":-59.5, "lon_max":-55.5},
    "Río Negro":          {"lat_min":-42.0, "lat_max":-37.5, "lon_min":-70.5, "lon_max":-62.5},
    "La Pampa":           {"lat_min":-40.0, "lat_max":-35.0, "lon_min":-68.0, "lon_max":-63.5},
    "San Luis":           {"lat_min":-35.5, "lat_max":-32.0, "lon_min":-67.5, "lon_max":-64.5},
    "Tierra del Fuego":   {"lat_min":-55.5, "lat_max":-52.5, "lon_min":-68.5, "lon_max":-63.5},
    "Mendoza":            {"lat_min":-37.5, "lat_max":-32.0, "lon_min":-70.5, "lon_max":-66.5},
    "Entre Ríos":         {"lat_min":-34.0, "lat_max":-30.0, "lon_min":-60.5, "lon_max":-57.5},
    "San Juan":           {"lat_min":-33.0, "lat_max":-28.0, "lon_min":-70.0, "lon_max":-67.0},
    "Santa Cruz":         {"lat_min":-52.0, "lat_max":-46.5, "lon_min":-73.0, "lon_max":-65.0},
    "Neuquén":            {"lat_min":-40.0, "lat_max":-36.0, "lon_min":-71.5, "lon_max":-68.0},
    "Chubut":             {"lat_min":-46.5, "lat_max":-42.0, "lon_min":-71.5, "lon_max":-63.5},
    "Tucumán":            {"lat_min":-28.0, "lat_max":-26.0, "lon_min":-66.5, "lon_max":-64.5},
    "Salta":              {"lat_min":-25.5, "lat_max":-21.5, "lon_min":-68.5, "lon_max":-62.5},
    "Jujuy":              {"lat_min":-24.0, "lat_max":-21.5, "lon_min":-67.5, "lon_max":-64.5},
    "Chaco":              {"lat_min":-27.5, "lat_max":-24.0, "lon_min":-63.0, "lon_max":-59.5},
    "Formosa":            {"lat_min":-25.0, "lat_max":-22.0, "lon_min":-62.5, "lon_max":-58.0},
    "Santiago del Estero":{"lat_min":-30.5, "lat_max":-25.5, "lon_min":-65.5, "lon_max":-61.5},
    "Catamarca":          {"lat_min":-29.5, "lat_max":-25.5, "lon_min":-69.0, "lon_max":-65.0},
    "La Rioja":           {"lat_min":-32.0, "lat_max":-27.5, "lon_min":-69.0, "lon_max":-66.0},
}

REGIONES_BBOX = {
    "Metropolitana": {"lat_min":-35.5,"lat_max":-34.0,"lon_min":-59.5,"lon_max":-57.5},
    "Pampeana":      {"lat_min":-40.0,"lat_max":-30.0,"lon_min":-65.0,"lon_max":-57.0},
    "NOA":           {"lat_min":-28.0,"lat_max":-21.0,"lon_min":-69.0,"lon_max":-62.0},
    "NEA":           {"lat_min":-30.0,"lat_max":-21.0,"lon_min":-62.0,"lon_max":-53.0},
    "Cuyo":          {"lat_min":-36.0,"lat_max":-27.0,"lon_min":-70.0,"lon_max":-65.0},
    "Patagonia":     {"lat_min":-55.0,"lat_max":-39.0,"lon_min":-73.0,"lon_max":-62.0},
}

REGION_MAP = {
    "Metropolitana":"Metropolitana","Pampeana":"Pampeana","PAMPEANA":"Pampeana",
    "NOA":"NOA","NEA":"NEA","Cuyo":"Cuyo","Patagonia":"Patagonia",
}

ORDEN_PROVINCIAS = [
    "CABA","Buenos Aires","Córdoba","Santa Fe","Misiones","Corrientes",
    "Río Negro","La Pampa","San Luis","Tierra del Fuego","Mendoza",
    "Entre Ríos","San Juan","Santa Cruz",
]

ORDEN_REGIONES = ["Metropolitana","Pampeana","NEA","NOA","Cuyo","Patagonia"]

ETIQUETAS_DERIV = {
    "Llamante solicitó información y/o orientación":                          "Solo información y orientación",
    "Se trata de un conflicto familiar":                                      '"Conflicto familiar" (no violencia)',
    "No se desplazó un Equipo móvil por tratarse de un caso fuera de CABA":  "Fuera de CABA, no se desplazó",
    "La víctima no aceptó la intervención del Equipo Móvil":                  "Víctima no aceptó intervención",
    "No había móviles y/o Equipos para realizar la intervención":             "Sin móvil disponible",
    "Desplazamiento de un Equipo Móvil a donde se encontraba la/s víctima/s":"Equipo móvil desplazado",
}

COLORES_DERIV = {
    "Solo información y orientación":      "#D85A30",
    '"Conflicto familiar" (no violencia)': "#BA7517",
    "Fuera de CABA, no se desplazó":       "#BA7517",
    "Víctima no aceptó intervención":      "#EF9F27",
    "Sin móvil disponible":                "#E24B4A",
    "Equipo móvil desplazado":             "#639922",
}

CATS_VIOLENCIA = [
    ("Psicológica",   ["psicológica","psicologica"]),
    ("Física",        ["física","fisica"]),
    ("Económica",     ["económica","economica"]),
    ("Sexual",        ["sexual"]),
    ("Otras / Trata", ["otras","trata"]),
]

# ── 1. Procesar antenas ────────────────────────────────────────────────────
print("Procesando antenas...")
antenas_prov  = defaultdict(lambda: defaultdict(int))
antenas_reg   = defaultdict(lambda: defaultdict(int))
total_antenas = 0

with open(CSV_ANTENAS, encoding="utf-8") as f:
    for row in csv.reader(f):
        try:
            tipo = row[0].strip()
            lon  = float(row[6])
            lat  = float(row[7])
            total_antenas += 1
            for prov, bb in PROVINCIAS_BBOX.items():
                if bb["lat_min"] <= lat <= bb["lat_max"] and bb["lon_min"] <= lon <= bb["lon_max"]:
                    antenas_prov[prov][tipo] += 1
                    break
            for reg, bb in REGIONES_BBOX.items():
                if bb["lat_min"] <= lat <= bb["lat_max"] and bb["lon_min"] <= lon <= bb["lon_max"]:
                    antenas_reg[reg][tipo] += 1
                    break
        except Exception:
            pass

print(f"  Total antenas: {total_antenas}")

# ── 2. Procesar llamados ───────────────────────────────────────────────────
print("Procesando llamados...")
total_llamados    = 0
llamados_por_año  = defaultdict(int)
derivaciones_cnt  = Counter()
violencia_cnt     = Counter()
denuncias_region  = Counter()
equipo_desplazado = 0

with open(CSV_LLAMADOS, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        total_llamados += 1
        fecha = row.get("llamado_fecha", "")
        if fecha:
            llamados_por_año[fecha[:4]] += 1
        deriv = row.get("llamado_derivacion", "").strip()
        derivaciones_cnt[deriv] += 1
        if "desplazamiento" in deriv.lower() and "equipo" in deriv.lower():
            equipo_desplazado += 1
        vt = row.get("violencia_tipo", "").strip()
        if vt.lower() not in ("no aplica","ns/nc","sin dato","no es un caso de violencia familiar",""):
            violencia_cnt[vt] += 1
        reg = REGION_MAP.get(row.get("llamado_provincia", "").strip())
        if reg:
            denuncias_region[reg] += 1

print(f"  Total llamados: {total_llamados}")
print(f"  Equipo desplazado: {equipo_desplazado}")

# ── 3. Métricas derivadas ──────────────────────────────────────────────────
pct_desplazado = round(equipo_desplazado / total_llamados * 100, 1)
sin_region     = total_llamados - sum(denuncias_region.values())
pct_sin_region = round(sin_region / total_llamados * 100)

cats_violencia_data = {}
for cat, keywords in CATS_VIOLENCIA:
    n = sum(c for t, c in violencia_cnt.items() if any(k in t.lower() for k in keywords))
    cats_violencia_data[cat] = round(n / total_llamados * 100, 1)

años_labels = sorted(llamados_por_año.keys())
años_vals   = [llamados_por_año[a] for a in años_labels]
años_labels_display = [a if a != max(años_labels) else a + "*" for a in años_labels]

derivaciones_display = []
for orig, label in ETIQUETAS_DERIV.items():
    n   = derivaciones_cnt.get(orig, 0)
    pct = round(n / total_llamados * 100, 1)
    derivaciones_display.append({"label": label, "pct": pct, "color": COLORES_DERIV[label]})

def clasificar_region(reg):
    ant   = antenas_reg.get(reg, {})
    total = sum(ant.values())
    lte   = ant.get("LTE", 0)
    if total == 0:                         return "riesgo"
    if total < 300 or lte/total < 0.5:    return "riesgo"
    if total < 1000 or lte/total < 0.7:   return "warn"
    return "ok"

max_ant_reg = max((sum(antenas_reg[r].values()) for r in ORDEN_REGIONES), default=1)

regiones_data = []
for r in ORDEN_REGIONES:
    ant   = antenas_reg.get(r, {})
    total = sum(ant.values())
    lte, gsm, umts = ant.get("LTE",0), ant.get("GSM",0), ant.get("UMTS",0)
    tipo  = clasificar_region(r)
    regiones_data.append({
        "nombre": r, "denuncias": denuncias_region.get(r, 0),
        "total": total, "gsm": gsm, "umts": umts, "lte": lte,
        "pct_lte": round(lte/total*100) if total else 0,
        "pct_bar": round(total/max_ant_reg*100),
        "tipo": tipo,
    })

regiones_riesgo = sum(1 for r in regiones_data if r["tipo"] == "riesgo")

prov_labels, prov_gsm, prov_umts, prov_lte = [], [], [], []
for p in ORDEN_PROVINCIAS:
    ant = antenas_prov.get(p, {})
    g, u, l = ant.get("GSM",0), ant.get("UMTS",0), ant.get("LTE",0)
    if g+u+l > 0:
        label = "Bs. Aires" if p=="Buenos Aires" else ("T. del Fuego" if p=="Tierra del Fuego" else p)
        prov_labels.append(label)
        prov_gsm.append(g); prov_umts.append(u); prov_lte.append(l)

# ── 4. Helpers HTML ────────────────────────────────────────────────────────
def fmt(n):
    return f"{n:,}".replace(",",".")

def badge(tipo):
    if tipo=="ok":   return "badge-ok",    "cobertura adecuada", "#639922"
    if tipo=="warn": return "badge-warn",  "cobertura media",    "#EF9F27"
    return                  "badge-danger","riesgo alto",         "#D85A30"

def region_card(r):
    bc, bt, fc = badge(r["tipo"])
    cls = "region-card riesgo" if r["tipo"]=="riesgo" else "region-card"
    return f"""  <div class="{cls}" data-region="{r['nombre']}" data-gsm="{r['gsm']}" data-umts="{r['umts']}" data-lte="{r['lte']}">
    <p class="region-name">{r['nombre']}</p>
    <p class="region-stat">{fmt(r['denuncias'])} denuncias</p>
    <p class="region-stat antena-total">{fmt(r['total'])} antenas</p>
    <div class="antena-desglose">
      <div class="antena-row" data-tipo="GSM"><span class="antena-tag tag-gsm">GSM</span> {fmt(r['gsm'])} antenas</div>
      <div class="antena-row" data-tipo="UMTS"><span class="antena-tag tag-umts">UMTS</span> {fmt(r['umts'])} antenas</div>
      <div class="antena-row" data-tipo="LTE"><span class="antena-tag tag-lte">LTE</span> {fmt(r['lte'])} antenas</div>
    </div>
    <div class="ratio-bar"><div class="ratio-fill" style="width:{r['pct_bar']}%;background:{fc};"></div></div>
    <span class="badge {bc}">{bt}</span>
  </div>"""

def tipo_row(label, pct, max_pct):
    w = round(pct/max_pct*100, 1)
    return f"""  <div class="tipo-row">
    <span class="tipo-label">{label}</span>
    <div class="tipo-bar-wrap"><div class="tipo-bar-fill" style="width:{w}%;"></div></div>
    <span class="tipo-count">{str(pct).replace('.',',')}%</span>
  </div>"""

# ── 5. Generar HTML ────────────────────────────────────────────────────────
region_cards_html = "\n".join(region_card(r) for r in regiones_data)
max_viol_pct      = max(cats_violencia_data.values())
tipos_rows_html   = "\n".join(tipo_row(cat, pct, max_viol_pct) for cat, pct in cats_violencia_data.items())
aria_bar  = ", ".join(f"{l} {g+u+lt}" for l,g,u,lt in zip(prov_labels,prov_gsm,prov_umts,prov_lte))
aria_años = ", ".join(f"{a}:{v}" for a,v in zip(años_labels_display, años_vals))
pct_info  = derivaciones_display[0]["pct"]

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radiografía de los Dispositivos Electrónicos de Protección — Argentina 2017–2024</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #141412; color: #e8e6e0; padding: 2rem; max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 20px; font-weight: 500; color: #e8e6e0; margin-bottom: 4px; }}
  .subtitle {{ font-size: 13px; color: #5f5e5a; margin-bottom: 2rem; }}
  .kpis {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 2rem; }}
  .kpi {{ width: 180px; flex-shrink: 0; background: #f5f4f0; border-radius: 8px; padding: 14px 16px; }}
  @media (max-width: 480px) {{ .kpi {{ width: calc(50% - 5px); }} }}
  .kpi-label {{ font-size: 12px; color: #5f5e5a; margin-bottom: 4px; }}
  .kpi-value {{ font-size: 24px; font-weight: 500; color: #1a1a18; }}
  .kpi-sub {{ font-size: 11px; color: #888780; margin-top: 3px; }}
  .section-title {{ font-size: 11px; font-weight: 500; color: #5f5e5a; letter-spacing: 0.06em; text-transform: uppercase; margin: 2rem 0 1rem; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: #888780; margin-bottom: 1rem; }}
  .legend span {{ display: flex; align-items: center; gap: 5px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; display: inline-block; }}
  .region-grid {{ display: grid; grid-template-columns: repeat(3, 220px); justify-content: center; gap: 10px; margin-bottom: 2rem; }}
  @media (max-width: 720px) {{ .region-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media (max-width: 480px) {{ .region-grid {{ grid-template-columns: 1fr; }} }}
  .region-card {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 12px; padding: 14px; }}
  .region-card.riesgo {{ border: 1.5px solid #D85A30; }}
  .region-name {{ font-size: 14px; font-weight: 500; color: #1a1a18; margin-bottom: 8px; }}
  .region-stat {{ font-size: 12px; color: #5f5e5a; margin: 3px 0; }}
  .ratio-bar {{ height: 4px; border-radius: 2px; background: #d3d1c7; margin: 10px 0 5px; }}
  .ratio-fill {{ height: 4px; border-radius: 2px; }}
  .badge {{ display: inline-block; font-size: 10px; padding: 3px 8px; border-radius: 6px; margin-top: 6px; font-weight: 500; }}
  .badge-danger {{ background: #FAECE7; color: #993C1D; }}
  .badge-ok {{ background: #EAF3DE; color: #3B6D11; }}
  .badge-warn {{ background: #FAEEDA; color: #854F0B; }}
  .filter-bar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 1rem; }}
  .filter-bar label {{ font-size: 13px; color: #888780; }}
  .filter-bar select {{ font-size: 13px; padding: 6px 10px; border: 0.5px solid rgba(255,255,255,0.15); border-radius: 8px; background: #1e1e1b; color: #e8e6e0; cursor: pointer; }}
  .filter-sep {{ width: 0.5px; height: 24px; background: rgba(255,255,255,0.1); }}
  .region-card.hidden {{ display: none; }}
  .antena-desglose {{ margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }}
  .antena-row {{ display: flex; align-items: center; gap: 6px; font-size: 11px; color: #5f5e5a; transition: opacity 0.2s; }}
  .antena-tag {{ font-size: 10px; font-weight: 500; padding: 1px 5px; border-radius: 4px; min-width: 38px; text-align: center; }}
  .tag-gsm  {{ background: #E6F1FB; color: #185FA5; }}
  .tag-umts {{ background: #FAEEDA; color: #854F0B; }}
  .tag-lte  {{ background: #EAF3DE; color: #3B6D11; }}
  .antena-row.dimmed {{ opacity: 0.2; }}
  .insights {{ display: flex; flex-direction: column; gap: 10px; margin-bottom: 2rem; }}
  .insight {{ background: #1e1e1b; border-left: 3px solid #D85A30; border-radius: 0 8px 8px 0; padding: 12px 16px; font-size: 13px; color: #b4b2a9; line-height: 1.7; border-top: 0.5px solid rgba(255,255,255,0.06); border-right: 0.5px solid rgba(255,255,255,0.06); border-bottom: 0.5px solid rgba(255,255,255,0.06); }}
  .tipos-wrap {{ background: #1e1e1b; border: 0.5px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }}
  .tipo-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 13px; }}
  .tipo-label {{ min-width: 200px; color: #b4b2a9; }}
  .tipo-bar-wrap {{ flex: 1; height: 6px; background: #2c2c2a; border-radius: 3px; }}
  .tipo-bar-fill {{ height: 6px; border-radius: 3px; background: #D85A30; }}
  .tipo-count {{ min-width: 60px; text-align: right; color: #888780; font-size: 12px; }}
  .deriv-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
  .deriv-label {{ font-size: 12px; color: #b4b2a9; width: 220px; flex-shrink: 0; }}
  .deriv-bar {{ flex: 1; height: 6px; background: #2c2c2a; border-radius: 3px; }}
  .deriv-fill {{ height: 6px; border-radius: 3px; }}
  .deriv-pct {{ font-size: 12px; font-weight: 500; min-width: 40px; text-align: right; }}
  .footer {{ font-size: 11px; color: #444441; border-top: 0.5px solid rgba(255,255,255,0.06); padding-top: 1rem; margin-top: 1rem; }}
</style>
</head>
<body>

<h1>Radiografía de los Dispositivos Electrónicos de Protección en Argentina 2017–2024</h1>
<p class="subtitle">Cruce de llamados a Línea 137, cobertura de antenas celulares y brechas en la cadena de protección</p>

<div class="kpis">
  <div class="kpi"><p class="kpi-label">Llamados a Línea 137</p><p class="kpi-value">{fmt(total_llamados)}</p><p class="kpi-sub">2017 – jul.2024</p></div>
  <div class="kpi"><p class="kpi-label">Equipo móvil desplazado</p><p class="kpi-value">{fmt(equipo_desplazado)}</p><p class="kpi-sub">solo el {pct_desplazado}% de los llamados</p></div>
  <div class="kpi"><p class="kpi-label">Antenas registradas</p><p class="kpi-value">{fmt(total_antenas)}</p><p class="kpi-sub">GSM + UMTS + LTE</p></div>
  <div class="kpi" style="border:1.5px dashed #D85A30;background:#f5f4f0;">
    <p class="kpi-label" style="color:#D85A30;">Botones antipánico asignados</p>
    <p class="kpi-value" style="color:#D85A30;">SIN DATO</p>
    <p class="kpi-sub">no hay registro público</p>
  </div>
  <div class="kpi" style="border:1.5px dashed #D85A30;background:#f5f4f0;">
    <p class="kpi-label" style="color:#D85A30;">Activaciones exitosas con respuesta</p>
    <p class="kpi-value" style="color:#D85A30;">SIN DATO</p>
    <p class="kpi-sub">no hay registro público</p>
  </div>
</div>

<p class="section-title">Cobertura vs. denuncias por región</p>
<div class="legend">
  <span><span class="dot" style="background:#D85A30;"></span>Riesgo alto</span>
  <span><span class="dot" style="background:#EF9F27;"></span>Riesgo medio</span>
  <span><span class="dot" style="background:#639922;"></span>Cobertura adecuada</span>
</div>
<div class="filter-bar">
  <label for="filtroRegion">Región:</label>
  <select id="filtroRegion" onchange="aplicarFiltros()">
    <option value="todas">Todas</option>
    {"".join(f'<option value="{r["nombre"]}">{r["nombre"]}</option>' for r in regiones_data)}
  </select>
  <span class="filter-sep"></span>
  <label for="filtroTipo">Tipo de antena:</label>
  <select id="filtroTipo" onchange="aplicarFiltros()">
    <option value="todos">Todos</option>
    <option value="GSM">GSM (2G)</option>
    <option value="UMTS">UMTS (3G)</option>
    <option value="LTE">LTE (4G)</option>
  </select>
</div>
<div class="region-grid" id="regionGrid">
{region_cards_html}
</div>

<p class="section-title">Tipos de violencia presentes en los llamados</p>
<div class="tipos-wrap">
  <p style="font-size:11px;color:#888780;margin-bottom:14px;">Un caso puede incluir múltiples tipos. Porcentaje sobre {fmt(total_llamados)} llamados totales.</p>
{tipos_rows_html}
</div>

<p class="section-title">La cadena que se rompe — ¿qué pasó con los llamados? (2017–2024)</p>
<div style="background:#1e1e1b;border:0.5px solid rgba(255,255,255,0.06);border-radius:12px;padding:1.5rem;margin-bottom:2rem;">
  <div style="display:flex;flex-wrap:wrap;gap:2rem;align-items:flex-start;">
    <div style="flex:1;min-width:260px;">
      <p style="font-size:12px;color:#888780;margin-bottom:1rem;">Derivación de cada llamado atendido</p>
      <div id="derivaciones-list"></div>
    </div>
    <div style="flex:0 0 260px;min-width:220px;">
      <p style="font-size:12px;color:#888780;margin-bottom:0.5rem;">Llamados por año</p>
      <div style="position:relative;width:100%;height:200px;">
        <canvas id="añosChart" role="img" aria-label="Llamados por año">{aria_años}</canvas>
      </div>
      <div style="background:#4A1B0C;border-radius:8px;padding:10px 12px;margin-top:12px;font-size:12px;color:#F0997B;line-height:1.6;">
        Solo el <strong>{pct_desplazado}%</strong> de los llamados resultó en desplazamiento de un equipo móvil. El <strong>{pct_info}%</strong> solo recibió información y orientación.
      </div>
    </div>
  </div>
</div>

<p class="section-title">Densidad de antenas por provincia</p>
<div style="background:#1e1e1b;border:0.5px solid rgba(255,255,255,0.06);border-radius:12px;padding:1.5rem;margin-bottom:2rem;">
  <p style="font-size:11px;color:#5f5e5a;margin-bottom:1rem;">Solo se muestran provincias con antenas registradas en OpenCellID.</p>
  <div style="position:relative;width:100%;height:320px;">
    <canvas id="barChart" role="img" aria-label="Antenas por provincia">{aria_bar}</canvas>
  </div>
</div>

<p class="section-title">¿Qué pasa cuando no hay datos?</p>
<div class="insights">
  <div class="insight">El botón antipánico envía la ubicación GPS de la víctima en tiempo real. <strong style="color:#e8e6e0;">Sin datos móviles, este envío no llega.</strong> En zonas con solo antenas GSM (2G), la conexión puede ser demasiado lenta para transmitir la ubicación en tiempo crítico.</div>
  <div class="insight">Patagonia y Cuyo concentran la menor cantidad de antenas LTE del país. En zonas rurales de estas regiones, el dispositivo puede quedar intentando conectarse sin éxito al activar el botón.</div>
  <div class="insight">El {pct_sin_region}% de los llamados no tiene región registrada — un sub-registro que probablemente es mayor en zonas con menos infraestructura para reportar, sesgando los resultados hacia las regiones más conectadas.</div>
</div>

<p class="footer">Fuentes: OpenCellID · Ministerio de las Mujeres, Géneros y Diversidad — llamados atendidos violencia familiar 2017–2024</p>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const provLabels = {json.dumps(prov_labels, ensure_ascii=False)};
const datosProv = {{
  GSM:  {json.dumps(prov_gsm)},
  UMTS: {json.dumps(prov_umts)},
  LTE:  {json.dumps(prov_lte)},
}};
const antenasTotal = provLabels.map((_,i) => datosProv.GSM[i]+datosProv.UMTS[i]+datosProv.LTE[i]);

function heatColors(vals) {{
  const max = Math.max(...vals) || 1;
  return vals.map(n => {{
    const t = Math.pow(n/max, 0.45);
    return `rgb(${{Math.round(240+(30-240)*t)}},${{Math.round(244+(58-244)*t)}},${{Math.round(255+(138-255)*t)}})`;
  }});
}}

const barChart = new Chart(document.getElementById('barChart'), {{
  type: 'bar',
  data: {{ labels: provLabels, datasets: [{{ label:'Antenas', data: antenasTotal, backgroundColor: heatColors(antenasTotal), borderRadius:4, borderSkipped:false }}] }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{display:false}}, tooltip:{{callbacks:{{label:ctx=>` ${{ctx.parsed.y.toLocaleString('es-AR')}} antenas`}}}} }},
    scales:{{
      x:{{ ticks:{{font:{{size:11}},autoSkip:false,maxRotation:35,color:'#888780'}}, grid:{{display:false}} }},
      y:{{ ticks:{{font:{{size:11}},callback:v=>v.toLocaleString('es-AR'),color:'#888780'}}, grid:{{color:'rgba(255,255,255,0.05)'}} }}
    }}
  }}
}});

function actualizarGrafico(tipo) {{
  const vals = tipo==='todos' ? antenasTotal : datosProv[tipo];
  barChart.data.datasets[0].data = vals;
  barChart.data.datasets[0].backgroundColor = heatColors(vals);
  barChart.update();
}}

function aplicarFiltros() {{
  const region = document.getElementById('filtroRegion').value;
  const tipo   = document.getElementById('filtroTipo').value;
  document.querySelectorAll('#regionGrid .region-card').forEach(card => {{
    const matchRegion = region==='todas' || card.dataset.region===region;
    card.classList.toggle('hidden', !matchRegion);
    card.querySelectorAll('.antena-row').forEach(row => {{
      if (tipo==='todos') row.classList.remove('dimmed');
      else row.classList.toggle('dimmed', row.dataset.tipo!==tipo);
    }});
  }});
  actualizarGrafico(tipo);
}}

const valsAño   = {json.dumps(años_vals)};
const labelsAño = {json.dumps(años_labels_display)};
new Chart(document.getElementById('añosChart'), {{
  type: 'bar',
  data: {{
    labels: labelsAño,
    datasets: [{{ data: valsAño,
      backgroundColor: valsAño.map(n => {{
        const t = n/Math.max(...valsAño);
        return `rgb(${{Math.round(234+(15-234)*t)}},${{Math.round(128+(98-128)*t)}},48)`;
      }}),
      borderRadius:3, borderSkipped:false }}]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>` ${{ctx.parsed.y.toLocaleString('es-AR')}} llamados`}}}}}},
    scales:{{
      x:{{ticks:{{font:{{size:10}},color:'#888780'}},grid:{{display:false}}}},
      y:{{ticks:{{font:{{size:10}},callback:v=>v>=1000?(v/1000).toFixed(0)+'k':v,color:'#888780'}},grid:{{color:'rgba(255,255,255,0.05)'}}}}
    }}
  }}
}});

const derivaciones = {json.dumps(derivaciones_display, ensure_ascii=False)};
const maxPct = Math.max(...derivaciones.map(d=>d.pct));
const lista  = document.getElementById('derivaciones-list');
derivaciones.forEach(d => {{
  lista.innerHTML += `<div class="deriv-row">
    <span class="deriv-label">${{d.label}}</span>
    <div class="deriv-bar"><div class="deriv-fill" style="width:${{(d.pct/maxPct*100).toFixed(1)}}%;background:${{d.color}};"></div></div>
    <span class="deriv-pct" style="color:${{d.color}}">${{d.pct}}%</span>
  </div>`;
}});
</script>
</body>
</html>"""

with open(SALIDA, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"\nDashboard generado: {SALIDA}")
print(f"  Regiones en riesgo: {regiones_riesgo}")
print(f"  Sin región: {pct_sin_region}%")
print(f"  Pct desplazado: {pct_desplazado}%")
