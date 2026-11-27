#!/usr/bin/env python3
"""Stock by size and color for clothing and lingerie shops.

Reads an inventory CSV with variants (product, color, size, current stock, and minimum stock),
detects variants that are running low or out of stock, and generates:
1. An interactive HTML inventory report with color-coded alerts (red for out of stock / low stock).
2. A supplier replenishment order sheet grouped by supplier with quantities needed to restore safety stock.

Usage:
    python3 stock.py sample_data/stock.csv --out output/
"""
import argparse
import csv
import sys
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Control de Stock por Talle y Color — {title}</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --heading: #f0f6fc;
    --accent: #58a6ff;
    --red-bg: rgba(248, 81, 73, 0.15);
    --red-border: #f85149;
    --red-text: #ff7b72;
    --yellow-bg: rgba(210, 153, 34, 0.15);
    --yellow-border: #d29922;
    --yellow-text: #e3b341;
    --green-badge: rgba(56, 139, 253, 0.15);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
    line-height: 1.4;
  }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  header {{ margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
  h1 {{ font-size: 24px; color: var(--heading); margin-bottom: 6px; }}
  p.subtitle {{ color: #8b949e; font-size: 14px; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px; }}
  .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 18px; }}
  .kpi-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #8b949e; margin-bottom: 4px; }}
  .kpi-val {{ font-size: 24px; font-weight: bold; color: var(--heading); }}
  .kpi-card.alert {{ border-color: var(--red-border); background: var(--red-bg); }}
  .kpi-card.alert .kpi-val {{ color: var(--red-text); }}

  .section-title {{ font-size: 18px; color: var(--heading); margin: 28px 0 14px 0; display: flex; align-items: center; gap: 8px; }}
  
  table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }}
  th, td {{ padding: 10px 14px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }}
  th {{ background: #21262d; color: var(--heading); font-weight: 600; text-transform: uppercase; font-size: 12px; }}
  tr:last-child td {{ border-bottom: none; }}
  
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .badge-danger {{ background: var(--red-bg); border: 1px solid var(--red-border); color: var(--red-text); }}
  .badge-warning {{ background: var(--yellow-bg); border: 1px solid var(--yellow-border); color: var(--yellow-text); }}
  .badge-ok {{ background: var(--green-badge); border: 1px solid var(--accent); color: var(--accent); }}
  
  .supplier-group {{ margin-bottom: 20px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
  .supplier-header {{ font-size: 16px; font-weight: 600; color: var(--heading); margin-bottom: 10px; display: flex; justify-content: space-between; }}
  .order-btn {{
    display: inline-block;
    background: #238636;
    color: white;
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
  }}
  .order-btn:hover {{ background: #2ea043; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>{title} — Stock por Talle y Color</h1>
    <p class="subtitle">Control operativo de inventario por variantes y cálculo automático de reposición</p>
  </header>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">Total Variantes</div>
      <div class="kpi-val">{total_variants}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Unidades en Saldo</div>
      <div class="kpi-val">{total_units}</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-label">Alertas de Reposición</div>
      <div class="kpi-val">{total_alerts}</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-label">Agotados (Stock 0)</div>
      <div class="kpi-val">{out_of_stock}</div>
    </div>
  </div>

  <div class="section-title">🚨 Alertas de Quiebre de Stock ({total_alerts} variantes críticas)</div>
  <table>
    <thead>
      <tr>
        <th>Producto</th>
        <th>Color</th>
        <th>Talle</th>
        <th>Stock</th>
        <th>Mínimo</th>
        <th>Estado</th>
        <th>Sugerido Reponer</th>
      </tr>
    </thead>
    <tbody>
      {alerts_rows}
    </tbody>
  </table>

  <div class="section-title">📦 Lista de Reposición por Proveedor</div>
  {suppliers_cards}

  <div class="section-title">📋 Inventario Completo</div>
  <table>
    <thead>
      <tr>
        <th>Proveedor</th>
        <th>Producto</th>
        <th>Color</th>
        <th>Talle</th>
        <th>Stock Actual</th>
        <th>Mínimo</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>
      {all_rows}
    </tbody>
  </table>
</div>
</body>
</html>
"""


def load_stock(csv_path: Path) -> list[dict]:
    items = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                "supplier": row["supplier"].strip(),
                "product": row["product"].strip(),
                "color": row["color"].strip(),
                "size": row["size"].strip(),
                "stock": int(row["stock"].strip()),
                "min_stock": int(row["min_stock"].strip()),
            })
    return items


def analyze_inventory(items: list[dict], title: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    total_variants = len(items)
    total_units = sum(it["stock"] for it in items)
    
    alerts = []
    for it in items:
        if it["stock"] <= it["min_stock"]:
            needed = max(it["min_stock"] * 2 - it["stock"], it["min_stock"] - it["stock"] + 1)
            alerts.append({**it, "needed": needed})
            
    out_of_stock = sum(1 for it in items if it["stock"] == 0)
    total_alerts = len(alerts)
    
    # Rows for Alerts table
    alerts_rows_html = []
    for it in alerts:
        if it["stock"] == 0:
            badge = '<span class="badge badge-danger">SIN STOCK</span>'
        else:
            badge = f'<span class="badge badge-warning">BAJO MÍNIMO ({it["stock"]})</span>'
            
        alerts_rows_html.append(f"""
        <tr>
          <td><strong>{it['product']}</strong></td>
          <td>{it['color']}</td>
          <td><span class="badge badge-ok">{it['size']}</span></td>
          <td><strong style="color: {'var(--red-text)' if it['stock']==0 else 'var(--yellow-text)'}">{it['stock']}</strong></td>
          <td>{it['min_stock']}</td>
          <td>{badge}</td>
          <td><strong>+{it['needed']} u.</strong></td>
        </tr>
        """)
        
    # Group replenishment by supplier
    suppliers = {}
    for it in alerts:
        sup = it["supplier"]
        suppliers.setdefault(sup, []).append(it)
        
    suppliers_cards_html = []
    for sup, sup_items in suppliers.items():
        total_sup_units = sum(i["needed"] for i in sup_items)
        rows_str = "".join([f"<li><strong>{i['product']}</strong> ({i['color']} - Talle {i['size']}): pedir <strong>{i['needed']} u.</strong> (Stock actual: {i['stock']})</li>" for i in sup_items])
        
        # WhatsApp prefilled order text
        msg_lines = [f"Hola! Te paso el pedido de reposición para *{title}*:"]
        for i in sup_items:
            msg_lines.append(f"• {i['product']} [{i['color']}, Talle {i['size']}]: {i['needed']} u.")
        import urllib.parse
        encoded_msg = urllib.parse.quote("\n".join(msg_lines))
        wa_link = f"https://wa.me/?text={encoded_msg}"
        
        suppliers_cards_html.append(f"""
        <div class="supplier-group">
          <div class="supplier-header">
            <span>🏭 {sup} &nbsp;·&nbsp; <span style="color: var(--accent); font-size: 14px;">{len(sup_items)} variantes críticas ({total_sup_units} u. a pedir)</span></span>
            <a href="{wa_link}" target="_blank" class="order-btn">Enviar Pedido por WhatsApp</a>
          </div>
          <ul style="padding-left: 20px; font-size: 14px; color: #8b949e; line-height: 1.8;">
            {rows_str}
          </ul>
        </div>
        """)
        
    # Full inventory rows
    all_rows_html = []
    for it in items:
        if it["stock"] == 0:
            badge = '<span class="badge badge-danger">SIN STOCK</span>'
        elif it["stock"] <= it["min_stock"]:
            badge = '<span class="badge badge-warning">BAJO MÍNIMO</span>'
        else:
            badge = '<span class="badge badge-ok">NORMAL</span>'
            
        all_rows_html.append(f"""
        <tr>
          <td>{it['supplier']}</td>
          <td><strong>{it['product']}</strong></td>
          <td>{it['color']}</td>
          <td><span class="badge badge-ok">{it['size']}</span></td>
          <td>{it['stock']}</td>
          <td>{it['min_stock']}</td>
          <td>{badge}</td>
        </tr>
        """)
        
    html = HTML_TEMPLATE.format(
        title=title,
        total_variants=total_variants,
        total_units=total_units,
        total_alerts=total_alerts,
        out_of_stock=out_of_stock,
        alerts_rows="".join(alerts_rows_html),
        suppliers_cards="".join(suppliers_cards_html),
        all_rows="".join(all_rows_html)
    )
    
    report_file = out_dir / "stock_report.html"
    report_file.write_text(html, encoding="utf-8")
    print(f"✓ Reporte generado en: {report_file}")
    return report_file


def main():
    parser = argparse.ArgumentParser(description="Control de Stock por Talle y Color")
    parser.add_argument("csv_path", type=Path, help="Ruta al archivo CSV de stock")
    parser.add_argument("--business", default="Tienda Urbana", help="Nombre del negocio")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Carpeta de salida")
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"Error: No existe el archivo {args.csv_path}")
        sys.exit(1)

    items = load_stock(args.csv_path)
    analyze_inventory(items, args.business, args.out)


if __name__ == "__main__":
    main()
