"""
generar_dashboard.py
--------------------
Lee los dos CSVs y genera dashboard_antipanico.html con datos reales.

Uso:
    python3 generar_dashboard.py

Los CSVs tienen que estar en la misma carpeta que este script:
    - 722_argentina.csv
    - llamados-atendidos-violencia-familiar-unificado-201701-202407.csv
"""

import csv
import json
import os
from collections import defaultdict, Counter

# ── Rutas ──────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
CSV_ANTENAS   = "/mnt/user-data/uploads/722_argentina.csv"
CSV_DENUNCIAS = "/mnt/user-data/uploads/llamados-atendidos-violencia-familiar-unificado-201701-202407.csv"
SALIDA        = "dashboard_antipanico.html"

# ── Bounding boxes por región ──────────────────────────────────────────────
REGIONES_BBOX = {
    "Metropolitana": {"lat_min": -35.5, "lat_max": -34.0, "lon_min": -59.5, "lon_max": -57.5},
    "Pampeana":      {"lat_min": -40.0, "lat_max": -30.0, "lon_min": -65.0, "lon_max": -57.0},
    "NOA":           {"lat_min": -28.0, "lat_max": -21.0, "lon_min": -69.0, "lon_max": -62.0},
    "NEA":           {"lat_min": -30.0, "lat_max": -21.0, "lon_min": -62.0, "lon_max": -53.0},
    "Cuyo":          {"lat_min": -36.0, "lat_max": -27.0, "lon_min": -70.0, "lon_max": -65.0},
    "Patagonia":     {"lat_min": -55.0, "lat_max": -39.0, "lon_min": -73.0, "lon_max": -62.0},
}

REGION_MAP = {
    "Metropolitana": "Metropolitana",
    "Pampeana": "Pampeana", "PAMPEANA": "Pampeana",
    "NOA": "NOA", "NEA": "NEA", "Cuyo": "Cuyo", "Patagonia": "Patagonia",
}

ORDEN_REGIONES = ["Metropolitana", "Pampeana", "NEA", "NOA", "Cuyo", "Patagonia"]

COLORES_LINEA = {
    "Metropolitana": "#185FA5",
    "Pampeana":      "#3B6D11",
    "NEA":           "#7F77DD",
    "NOA":           "#D85A30",
    "Cuyo":          "#BA7517",
    "Patagonia":     "#888780",
}

DASH_LINEA = {
    "Metropolitana": [],
    "Pampeana":      [5, 3],
    "NEA":           [3, 3],
    "NOA":           [2, 2],
    "Cuyo":          [8, 3],
    "Patagonia":     [6, 2],
}

# ── Procesamiento de antenas ───────────────────────────────────────────────
print("Procesando antenas...")
antenas_region = defaultdict(lambda: defaultdict(int))
total_antenas = 0

with open(CSV_ANTENAS, encoding="utf-8") as f:
    for row in csv.reader(f):
        try:
            tipo = row[0].strip()
            lon  = float(row[6])
            lat  = float(row[7])
            total_antenas += 1
            for region, bbox in REGIONES_BBOX.items():
                if bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lon_min"] <= lon <= bbox["lon_max"]:
                    antenas_region[region][tipo] += 1
                    break
        except Exception:
            pass

print(f"  Total antenas: {total_antenas}")

# ── Procesamiento de denuncias ─────────────────────────────────────────────
print("Procesando denuncias...")
denuncias_region_año = defaultdict(lambda: defaultdict(int))
total_denuncias = 0
sin_region = 0
tipos_violencia = Counter()

with open(CSV_DENUNCIAS, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_denuncias += 1
        region = REGION_MAP.get(row.get("llamado_provincia", "").strip())
        fecha  = row.get("llamado_fecha", "")
        if region and fecha:
            año = fecha[:4]
            denuncias_region_año[region][año] += 1
        else:
            sin_region += 1
        tipos_violencia[row.get("violencia_tipo", "Sin dato").strip()] += 1

pct_sin_region = round(sin_region / total_denuncias * 100) if total_denuncias else 0
print(f"  Total denuncias: {total_denuncias}")
print(f"  Sin región: {sin_region} ({pct_sin_region}%)")

# ── Armado de datos para el HTML ───────────────────────────────────────────
años = sorted({a for r in denuncias_region_año.values() for a in r})

def clasificar(region):
    antenas = antenas_region.get(region, {})
    total   = sum(antenas.values())
    lte     = antenas.get("LTE", 0)
    if total == 0:
        return "riesgo"
    pct_lte = lte / total
    if total < 300 or pct_lte < 0.5:
        return "riesgo"
    if total < 1000 or pct_lte < 0.7:
        return "warn"
    return "ok"

regiones_data = []
max_antenas = max((sum(antenas_region[r].values()) for r in ORDEN_REGIONES), default=1)

for r in ORDEN_REGIONES:
    ant   = antenas_region.get(r, {})
    total = sum(ant.values())
    lte   = ant.get("LTE", 0)
    pct_lte  = round(lte / total * 100) if total else 0
    pct_bar  = round(total / max_antenas * 100)
    den   = sum(denuncias_region_año.get(r, {}).values())
    tipo  = clasificar(r)
    regiones_data.append({
        "nombre":   r,
        "denuncias": den,
        "antenas":  total,
        "lte":      lte,
        "pct_lte":  pct_lte,
        "pct_bar":  pct_bar,
        "tipo":     tipo,
    })

datasets_linea = []
for r in ORDEN_REGIONES:
    datos_año = denuncias_region_año.get(r, {})
    datasets_linea.append({
        "label":       r,
        "data":        [datos_año.get(a, 0) for a in años],
        "borderColor": COLORES_LINEA[r],
        "borderDash":  DASH_LINEA[r],
    })

top_tipos = [(t, c) for t, c in tipos_violencia.most_common(5) if t not in ("No aplica", "No Aplica")]

# ── Generación del HTML ────────────────────────────────────────────────────
regiones_riesgo = sum(1 for r in regiones_data if r["tipo"] == "riesgo")

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Botón antipánico y cobertura móvil — Argentina 2017–2024</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f4f0; color: #1a1a18; padding: 2rem; max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 20px; font-weight: 500; margin-bottom: 4px; }}
  .subtitle {{ font-size: 13px; color: #5f5e5a; margin-bottom: 2rem; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 2rem; }}
  .kpi {{ background: #ebebea; border-radius: 8px; padding: 14px 16px; }}
  .kpi-label {{ font-size: 12px; color: #5f5e5a; margin-bottom: 4px; }}
  .kpi-value {{ font-size: 24px; font-weight: 500; }}
  .kpi-sub {{ font-size: 11px; color: #888780; margin-top: 3px; }}
  .section-title {{ font-size: 11px; font-weight: 500; color: #888780; letter-spacing: 0.06em; text-transform: uppercase; margin: 2rem 0 1rem; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: #5f5e5a; margin-bottom: 1rem; }}
  .legend span {{ display: flex; align-items: center; gap: 5px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; display: inline-block; }}
  .region-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 2rem; }}
  .region-card {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 12px; padding: 14px; }}
  .region-card.riesgo {{ border: 1.5px solid #D85A30; }}
  .region-name {{ font-size: 14px; font-weight: 500; margin-bottom: 8px; }}
  .region-stat {{ font-size: 12px; color: #5f5e5a; margin: 3px 0; }}
  .ratio-bar {{ height: 4px; border-radius: 2px; background: #d3d1c7; margin: 10px 0 5px; }}
  .ratio-fill {{ height: 4px; border-radius: 2px; }}
  .badge {{ display: inline-block; font-size: 10px; padding: 3px 8px; border-radius: 6px; margin-top: 6px; font-weight: 500; }}
  .badge-danger {{ background: #FAECE7; color: #993C1D; }}
  .badge-ok {{ background: #EAF3DE; color: #3B6D11; }}
  .badge-warn {{ background: #FAEEDA; color: #854F0B; }}
  .chart-wrap {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }}
  .chart-inner {{ position: relative; width: 100%; height: 260px; }}
  .insights {{ display: flex; flex-direction: column; gap: 10px; margin-bottom: 2rem; }}
  .insight {{ background: #fff; border-left: 3px solid #D85A30; border-radius: 0 8px 8px 0; padding: 12px 16px; font-size: 13px; line-height: 1.7; border-top: 0.5px solid rgba(0,0,0,0.08); border-right: 0.5px solid rgba(0,0,0,0.08); border-bottom: 0.5px solid rgba(0,0,0,0.08); }}
  .tipos-wrap {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }}
  .tipo-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 13px; }}
  .tipo-label {{ min-width: 180px; color: #2c2c2a; }}
  .tipo-bar-wrap {{ flex: 1; height: 6px; background: #ebebea; border-radius: 3px; }}
  .tipo-bar-fill {{ height: 6px; border-radius: 3px; background: #D85A30; }}
  .tipo-count {{ min-width: 60px; text-align: right; color: #5f5e5a; font-size: 12px; }}
  .footer {{ font-size: 11px; color: #888780; border-top: 0.5px solid rgba(0,0,0,0.12); padding-top: 1rem; margin-top: 1rem; }}
</style>
</head>
<body>

<h1>Botón antipánico y cobertura de datos móviles</h1>
<p class="subtitle">Cruce de denuncias de violencia familiar (2017–2024) con infraestructura de antenas celulares — Argentina</p>

<div class="kpis">
  <div class="kpi">
    <p class="kpi-label">Denuncias totales</p>
    <p class="kpi-value">{total_denuncias:,}</p>
    <p class="kpi-sub">2017 – 2024</p>
  </div>
  <div class="kpi">
    <p class="kpi-label">Antenas registradas</p>
    <p class="kpi-value">{total_antenas:,}</p>
    <p class="kpi-sub">GSM + UMTS + LTE</p>
  </div>
  <div class="kpi">
    <p class="kpi-label">Regiones en riesgo</p>
    <p class="kpi-value">{regiones_riesgo}</p>
    <p class="kpi-sub">baja cobertura relativa</p>
  </div>
  <div class="kpi">
    <p class="kpi-label">Sin datos de región</p>
    <p class="kpi-value">{pct_sin_region}%</p>
    <p class="kpi-sub">de las denuncias</p>
  </div>
</div>

<p class="section-title">Cobertura vs. denuncias por región</p>
<div class="legend">
  <span><span class="dot" style="background:#D85A30;"></span>Riesgo alto</span>
  <span><span class="dot" style="background:#EF9F27;"></span>Riesgo medio</span>
  <span><span class="dot" style="background:#639922;"></span>Cobertura adecuada</span>
</div>

<div class="region-grid">
{"".join(f'''
  <div class="region-card{"" if r["tipo"] != "riesgo" else " riesgo"}">
    <p class="region-name">{r["nombre"]}</p>
    <p class="region-stat">{r["denuncias"]:,} denuncias</p>
    <p class="region-stat">{r["antenas"]:,} antenas</p>
    <p class="region-stat">{r["pct_lte"]}% LTE</p>
    <div class="ratio-bar"><div class="ratio-fill" style="width:{r["pct_bar"]}%;background:{"#639922" if r["tipo"]=="ok" else "#EF9F27" if r["tipo"]=="warn" else "#D85A30"};"></div></div>
    <span class="badge badge-{"ok" if r["tipo"]=="ok" else "warn" if r["tipo"]=="warn" else "danger"}">{"cobertura adecuada" if r["tipo"]=="ok" else "cobertura media" if r["tipo"]=="warn" else "riesgo alto"}</span>
  </div>''' for r in regiones_data)}
</div>

<p class="section-title">Evolución de denuncias con región registrada</p>
<div class="chart-wrap">
  <div class="chart-inner">
    <canvas id="lineChart" role="img" aria-label="Línea de tiempo de denuncias por región 2021 a 2024">Denuncias por región entre {años[0]} y {años[-1]}.</canvas>
  </div>
  <div class="legend" id="lineLegend" style="margin-top:1rem;margin-bottom:0;"></div>
</div>

<p class="section-title">Tipos de violencia más frecuentes</p>
<div class="tipos-wrap">
{"".join(f'''  <div class="tipo-row">
    <span class="tipo-label">{t}</span>
    <div class="tipo-bar-wrap"><div class="tipo-bar-fill" style="width:{round(c/top_tipos[0][1]*100)}%;"></div></div>
    <span class="tipo-count">{c:,}</span>
  </div>''' for t, c in top_tipos)}
</div>

<p class="section-title">¿Qué pasa cuando no hay datos?</p>
<div class="insights">
  <div class="insight">El botón antipánico envía la ubicación GPS de la víctima en tiempo real. <strong>Sin datos móviles, este envío no llega.</strong> En zonas con solo antenas GSM (2G), la conexión es tan lenta que el mensaje puede demorar minutos críticos o no enviarse.</div>
  <div class="insight">Patagonia y Cuyo concentran la menor cantidad de antenas LTE por km² del país. Si una víctima activa el botón en una zona rural de estas regiones, el dispositivo puede quedar intentando conectarse sin éxito.</div>
  <div class="insight">El {pct_sin_region}% de las denuncias del dataset no tiene región registrada — un sub-registro sistemático que probablemente sea mayor en zonas con menos infraestructura para reportar.</div>
</div>

<p class="footer">Fuentes: OpenCellID (722_argentina.csv) · Ministerio de las Mujeres, Géneros y Diversidad — llamados atendidos violencia familiar 2017–2024</p>

<script>
const años = {json.dumps(años)};
const datasets = {json.dumps(datasets_linea)};

new Chart(document.getElementById('lineChart'), {{
  type: 'line',
  data: {{
    labels: años,
    datasets: datasets.map(d => ({{
      ...d,
      backgroundColor: 'transparent',
      tension: 0.3,
      pointRadius: 4,
      pointHoverRadius: 6,
      borderDash: d.borderDash || []
    }}))
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ autoSkip: false, font: {{ size: 12 }} }}, grid: {{ display: false }} }},
      y: {{ ticks: {{ font: {{ size: 11 }}, callback: v => v.toLocaleString('es-AR') }}, grid: {{ color: 'rgba(0,0,0,0.06)' }} }}
    }}
  }}
}});

const legendEl = document.getElementById('lineLegend');
datasets.forEach(d => {{
  legendEl.innerHTML += `<span><span class="dot" style="background:${{d.borderColor}};"></span>${{d.label}}</span>`;
}});
</script>
</body>
</html>"""

with open(SALIDA, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"\nDashboard generado: {SALIDA}")
