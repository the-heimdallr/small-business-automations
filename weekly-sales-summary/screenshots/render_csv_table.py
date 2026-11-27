import subprocess
from pathlib import Path

scr_dir = Path("/media/javier/Archivos/01_Programacion/small-business-automations/weekly-sales-summary/screenshots")

html_table = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    background: #0d1117;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #c9d1d9;
    padding: 20px;
    margin: 0;
  }
  .title { font-size: 16px; font-weight: bold; margin-bottom: 12px; color: #f0f6fc; }
  table { width: 100%; border-collapse: collapse; background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }
  th, td { padding: 9px 12px; text-align: left; font-size: 13px; border-bottom: 1px solid #30363d; }
  th { background: #21262d; color: #f0f6fc; font-size: 11px; text-transform: uppercase; }
  tr:last-child td { border-bottom: none; }
  td.num { text-align: right; }
</style>
</head>
<body>
  <div class="title">📄 sample_data/sales.csv (Registro Diario de Ventas)</div>
  <table>
    <thead>
      <tr>
        <th>Fecha</th>
        <th>Ticket</th>
        <th>Servicio / Producto</th>
        <th>Rubro</th>
        <th class="num">Cant.</th>
        <th class="num">Precio</th>
        <th>Medio Pago</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>2026-12-14</td><td>T-501</td><td><strong>Corte & Brushing</strong></td><td>Peluquería</td><td class="num">1</td><td class="num">$12.000</td><td>MercadoPago</td></tr>
      <tr><td>2026-12-14</td><td>T-502</td><td><strong>Esmaltado Semipermanente</strong></td><td>Uñas</td><td class="num">1</td><td class="num">$9.500</td><td>Efectivo</td></tr>
      <tr><td>2026-12-15</td><td>T-503</td><td><strong>Nutrición Capilar Botox</strong></td><td>Peluquería</td><td class="num">1</td><td class="num">$18.000</td><td>Transferencia</td></tr>
      <tr><td>2026-12-15</td><td>T-504</td><td><strong>Esmaltado Semipermanente</strong></td><td>Uñas</td><td class="num">2</td><td class="num">$9.500</td><td>MercadoPago</td></tr>
      <tr><td>2026-12-16</td><td>T-505</td><td><strong>Corte & Brushing</strong></td><td>Peluquería</td><td class="num">1</td><td class="num">$12.000</td><td>Efectivo</td></tr>
      <tr><td>2026-12-17</td><td>T-506</td><td><strong>Lifting de Pestañas</strong></td><td>Estética</td><td class="num">1</td><td class="num">$11.000</td><td>Transferencia</td></tr>
    </tbody>
  </table>
</body>
</html>
"""
(scr_dir / "table.html").write_text(html_table, encoding="utf-8")
subprocess.run([
    "google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
    "--window-size=750,340",
    f"--screenshot={scr_dir}/sales_csv_table.png",
    f"file://{scr_dir}/table.html"
], check=True)

# Calculation metrics view
html_calc = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    background: #0d1117;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #c9d1d9;
    padding: 24px;
    margin: 0;
  }
  .title { font-size: 16px; font-weight: bold; margin-bottom: 14px; color: #f0f6fc; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
  .label { font-size: 11px; text-transform: uppercase; color: #8b949e; margin-bottom: 4px; }
  .val { font-size: 22px; font-weight: bold; color: #f0f6fc; }
  .val.green { color: #3fb950; }
  .sub { font-size: 12px; color: #58a6ff; margin-top: 4px; }
</style>
</head>
<body>
  <div class="title">📈 Indicadores Semanales Calculados en Python</div>
  <div class="grid">
    <div class="card">
      <div class="label">Total Facturación</div>
      <div class="val green">$191.000</div>
      <div class="sub">+13.7% vs semana anterior ($168.000)</div>
    </div>
    <div class="card">
      <div class="label">Servicio Estrella (Top 1)</div>
      <div class="val">Corte & Brushing</div>
      <div class="sub">7 servicios completados (44% del total)</div>
    </div>
  </div>
</body>
</html>
"""
(scr_dir / "calc.html").write_text(html_calc, encoding="utf-8")
subprocess.run([
    "google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
    "--window-size=700,240",
    f"--screenshot={scr_dir}/metrics_calc.png",
    f"file://{scr_dir}/calc.html"
], check=True)

print("Capturas 02 y 03 listas!")
