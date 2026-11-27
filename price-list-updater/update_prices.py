#!/usr/bin/env python3
"""Batch Price List Updater with Commercial Rounding & Audit Diff.

Updates entire price lists in batch by applying percentage increase rules
defined by supplier or product category. Features:
- Clean commercial retail rounding (ending in 00 or 50).
- Side-by-side audit comparison table showing old price, increase %, new price, and exact difference.
- Generates a print-ready and customer-shareable HTML price list.

Usage:
    python3 update_prices.py sample_data/products.csv --rules sample_data/rules.csv --business "Almacén Central" --out output/
"""
import argparse
import csv
import math
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lista de Precios Actualizada — {business}</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --heading: #f0f6fc;
    --accent: #58a6ff;
    --green: #3fb950;
    --diff-bg: rgba(56, 139, 253, 0.12);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
    line-height: 1.5;
  }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  header {{ margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
  h1 {{ font-size: 26px; color: var(--heading); }}
  .subtitle {{ color: #8b949e; font-size: 14px; margin-top: 4px; }}
  
  .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px; }}
  .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
  .kpi-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #8b949e; margin-bottom: 4px; }}
  .kpi-val {{ font-size: 24px; font-weight: bold; color: var(--heading); }}
  .kpi-card.green {{ border-color: #238636; background: rgba(35, 134, 54, 0.12); }}
  .kpi-card.green .kpi-val {{ color: var(--green); }}

  .section-title {{ font-size: 18px; color: var(--heading); margin: 28px 0 14px 0; }}
  
  table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); margin-bottom: 24px; }}
  th, td {{ padding: 10px 14px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }}
  th {{ background: #21262d; color: var(--heading); font-weight: 600; text-transform: uppercase; font-size: 12px; }}
  tr:last-child td {{ border-bottom: none; }}
  td.num, th.num {{ text-align: right; }}
  
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .badge-diff {{ background: var(--diff-bg); color: var(--accent); border: 1px solid rgba(56, 139, 253, 0.3); }}
  .badge-rule {{ background: #21262d; color: #8b949e; border: 1px solid var(--border); }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>📋 {business} — Lista de Precios Actualizada</h1>
    <p class="subtitle">Actualización en lote por proveedor/rubro con redondeo comercial y auditoría de cambios</p>
  </header>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">Artículos Actualizados</div>
      <div class="kpi-val">{total_items}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Reglas Aplicadas</div>
      <div class="kpi-val">{total_rules} proveedores</div>
    </div>
    <div class="kpi-card green">
      <div class="kpi-label">Aumento Promedio</div>
      <div class="kpi-val">+{avg_increase:.1%}</div>
    </div>
  </div>

  <div class="section-title">📊 1. Control de Cambios: Lista Anterior vs Nueva</div>
  <table>
    <thead>
      <tr>
        <th>SKU</th>
        <th>Producto</th>
        <th>Proveedor</th>
        <th class="num">Precio Anterior</th>
        <th class="num">Aumento</th>
        <th class="num">Precio Nuevo</th>
        <th class="num">Diferencia</th>
      </tr>
    </thead>
    <tbody>
      {diff_rows}
    </tbody>
  </table>

  <div class="section-title">🏷️ 2. Lista Limpia para el Cliente / Mostrador</div>
  <table>
    <thead>
      <tr>
        <th>Categoría</th>
        <th>Producto</th>
        <th class="num">Precio al Público</th>
      </tr>
    </thead>
    <tbody>
      {client_rows}
    </tbody>
  </table>
</div>
</body>
</html>
"""

def round_commercial(price: float) -> int:
    """Rounds to nearest 50 for clean retail pricing."""
    return int(math.ceil(price / 50.0) * 50)

def process_prices(products_csv: Path, rules_csv: Path, business: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    rules = {}
    with open(rules_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rules[r["target_name"].strip()] = float(r["increase_pct"].strip())
            
    products = []
    diff_rows_html = []
    client_rows_html = []
    
    increases = []
    with open(products_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sku = row["sku"].strip()
            prod = row["product"].strip()
            cat = row["category"].strip()
            sup = row["supplier"].strip()
            old_p = float(row["old_price"].strip())
            
            inc_pct = rules.get(sup, rules.get(cat, 0.10))
            increases.append(inc_pct)
            
            raw_new = old_p * (1.0 + inc_pct)
            new_p = round_commercial(raw_new)
            diff = new_p - old_p
            
            diff_rows_html.append(f"""
            <tr>
              <td><code>{sku}</code></td>
              <td><strong>{prod}</strong></td>
              <td><span class="badge badge-rule">{sup}</span></td>
              <td class="num">${old_p:,.0f}</td>
              <td class="num" style="color: var(--accent);">+{inc_pct:.0%}</td>
              <td class="num"><strong style="color: var(--green);">${new_p:,.0f}</strong></td>
              <td class="num"><span class="badge badge-diff">+${diff:,.0f}</span></td>
            </tr>
            """)
            
            client_rows_html.append(f"""
            <tr>
              <td>{cat}</td>
              <td><strong>{prod}</strong></td>
              <td class="num"><strong style="color: var(--green); font-size: 15px;">${new_p:,.0f}</strong></td>
            </tr>
            """)
            
    avg_inc = sum(increases) / len(increases) if increases else 0.0
    
    html = HTML_TEMPLATE.format(
        business=business,
        total_items=len(increases),
        total_rules=len(rules),
        avg_increase=avg_inc,
        diff_rows="".join(diff_rows_html),
        client_rows="".join(client_rows_html)
    )
    
    out_file = out_dir / "price_list_updated.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"✓ Lista de precios generada en: {out_file}")
    return out_file

def main():
    parser = argparse.ArgumentParser(description="Actualizador de Listas de Precios")
    parser.add_argument("products_csv", type=Path, help="CSV de productos con precios viejos")
    parser.add_argument("--rules", type=Path, default=Path("sample_data/rules.csv"))
    parser.add_argument("--business", default="Almacén Central", help="Nombre del comercio")
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    process_prices(args.products_csv, args.rules, args.business, args.out)

if __name__ == "__main__":
    main()
