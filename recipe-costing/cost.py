#!/usr/bin/env python3
"""Recipe and Dish Costing Calculator for Bakeries and Food Businesses.

Calculates the true unit cost of meals, cakes and recipes factoring in:
- Gram-level ingredient quantities with waste/loss percentage (merma).
- Hidden indirect costs: oven gas / electricity per minute, packaging, and shipping.
- Desired gross margin percentage: calculates target selling price, rounded price, and delivery app price (accounting for platform commission).

Usage:
    python3 cost.py sample_data/recipe.csv --ingredients sample_data/ingredients.csv --margin 0.55 --oven-min 45 --out output/
"""
import argparse
import csv
import math
import sys
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ficha de Costeo — {recipe_name}</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --heading: #f0f6fc;
    --accent: #58a6ff;
    --green: #3fb950;
    --gold: #d29922;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
    line-height: 1.5;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  header {{ margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
  h1 {{ font-size: 26px; color: var(--heading); }}
  .subtitle {{ color: #8b949e; font-size: 14px; margin-top: 4px; }}
  
  .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px; }}
  .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
  .kpi-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #8b949e; margin-bottom: 4px; }}
  .kpi-val {{ font-size: 24px; font-weight: bold; color: var(--heading); }}
  .kpi-card.highlight {{ border-color: #388bfd; background: rgba(56, 139, 253, 0.1); }}
  .kpi-card.highlight .kpi-val {{ color: var(--accent); }}
  .kpi-card.price-card {{ border-color: #238636; background: rgba(35, 134, 54, 0.15); }}
  .kpi-card.price-card .kpi-val {{ color: var(--green); }}

  .section-title {{ font-size: 18px; color: var(--heading); margin: 28px 0 14px 0; }}
  
  table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); margin-bottom: 24px; }}
  th, td {{ padding: 10px 14px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }}
  th {{ background: #21262d; color: var(--heading); font-weight: 600; text-transform: uppercase; font-size: 12px; }}
  tr:last-child td {{ border-bottom: none; }}
  td.num, th.num {{ text-align: right; }}
  
  .cost-summary {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }}
  .cost-line {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }}
  .cost-line.total {{ font-size: 18px; font-weight: bold; color: var(--heading); border-bottom: none; border-top: 2px solid var(--border); margin-top: 10px; padding-top: 12px; }}
  
  .pricing-box {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }}
  .pricing-panel {{ background: #161b22; border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
  .pricing-panel.app {{ border-color: var(--gold); background: rgba(210, 153, 34, 0.08); }}
  .pricing-panel h3 {{ font-size: 15px; margin-bottom: 8px; color: var(--heading); }}
  .p-price {{ font-size: 26px; font-weight: bold; color: var(--green); }}
  .pricing-panel.app .p-price {{ color: #e3b341; }}
  .p-note {{ font-size: 12px; color: #8b949e; margin-top: 6px; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🎂 Ficha Técnica y Costeo: {recipe_name}</h1>
    <p class="subtitle">Cálculo de costos directos, merma, costos ocultos y márgenes comerciales</p>
  </header>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">Costo Ingredientes</div>
      <div class="kpi-val">${cost_ingredients:,.0f}</div>
    </div>
    <div class="kpi-card highlight">
      <div class="kpi-label">Costo Total Real</div>
      <div class="kpi-val">${cost_total:,.0f}</div>
    </div>
    <div class="kpi-card price-card">
      <div class="kpi-label">Precio Mostrador ({margin_pct:.0%})</div>
      <div class="kpi-val">${price_suggested:,.0f}</div>
    </div>
    <div class="kpi-card" style="border-color: var(--gold);">
      <div class="kpi-label">Precio Apps Delivery</div>
      <div class="kpi-val" style="color: #e3b341;">${price_delivery_app:,.0f}</div>
    </div>
  </div>

  <div class="section-title">🥣 1. Detalle de Insumos en Gramos & Merma</div>
  <table>
    <thead>
      <tr>
        <th>Ingrediente</th>
        <th class="num">Cantidad</th>
        <th class="num">Costo Base / Unidad</th>
        <th class="num">Merma (%)</th>
        <th class="num">Costo Real</th>
      </tr>
    </thead>
    <tbody>
      {ingredient_rows}
    </tbody>
  </table>

  <div class="section-title">⚡ 2. Costos Ocultos e Indirectos (Gas, Packaging, Envío)</div>
  <div class="cost-summary">
    <div class="cost-line">
      <span>Subtotal Insumos Directos</span>
      <strong>${cost_ingredients:,.2f}</strong>
    </div>
    <div class="cost-line">
      <span>Consumo de Gas/Horno ({oven_min} min @ ${cost_per_gas_min:.1f}/min)</span>
      <strong>${cost_gas:,.2f}</strong>
    </div>
    <div class="cost-line">
      <span>Packaging (Caja pastelera reforzada + base dorada)</span>
      <strong>${cost_packaging:,.2f}</strong>
    </div>
    <div class="cost-line">
      <span>Envío / Reparto propio estimado</span>
      <strong>${cost_shipping:,.2f}</strong>
    </div>
    <div class="cost-line total">
      <span>COSTO TOTAL UNITARIO DE ELABORACIÓN</span>
      <span>${cost_total:,.2f}</span>
    </div>
  </div>

  <div class="section-title">🏷️ 3. Precios de Venta Recomendados</div>
  <div class="pricing-box">
    <div class="pricing-panel">
      <h3>Venta Directa / Mostrador / WhatsApp</h3>
      <div class="p-price">${price_suggested:,.0f}</div>
      <div class="p-note">Asegura un <strong>{margin_pct:.0%} de margen bruto</strong> limpio sobre costos directos e indirectos. Redondeado a centenas.</div>
    </div>
    <div class="pricing-panel app">
      <h3>Apps de Delivery (PedidosYa / Rappi)</h3>
      <div class="p-price">${price_delivery_app:,.0f}</div>
      <div class="p-note">Absorbe la <strong>comisión de plataforma (25%)</strong> para que tu ganancia de bolsillo sea exactamente la misma.</div>
    </div>
  </div>
</div>
</body>
</html>
"""

def compute_costing(recipe_csv: Path, ingredients_csv: Path, margin: float, oven_min: int, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load ingredients cost and waste
    prices = {}
    with open(ingredients_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prices[row["ingredient"].strip()] = {
                "unit": row["unit"].strip(),
                "cost": float(row["cost_per_unit"].strip()),
                "waste": float(row["waste_pct"].strip())
            }
            
    # Load recipe
    items = []
    recipe_name = "Receta"
    with open(recipe_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            recipe_name = row["recipe_name"].strip()
            ing = row["ingredient"].strip()
            qty = float(row["quantity_used"].strip())
            unit = row["unit"].strip()
            items.append({"name": ing, "qty": qty, "unit": unit})
            
    cost_ingredients = 0.0
    cost_packaging = 0.0
    rows_html = []
    
    for it in items:
        ing_meta = prices.get(it["name"], {"unit": it["unit"], "cost": 0.0, "waste": 0.0})
        base_cost = ing_meta["cost"]
        waste = ing_meta["waste"]
        
        # Effective cost accounting for waste
        effective_unit_cost = base_cost / (1.0 - waste) if waste < 1.0 else base_cost
        line_cost = it["qty"] * effective_unit_cost
        
        if "Caja" in it["name"] or "Bandeja" in it["name"]:
            cost_packaging += line_cost
        else:
            cost_ingredients += line_cost
            
        qty_display = f"{it['qty']:.3f} {it['unit']}" if it['unit'] == 'kg' else f"{it['qty']:.0f} {it['unit']}"
        
        rows_html.append(f"""
        <tr>
          <td><strong>{it['name']}</strong></td>
          <td class="num">{qty_display}</td>
          <td class="num">${base_cost:,.0f}</td>
          <td class="num">{waste:.1%}</td>
          <td class="num"><strong>${line_cost:,.2f}</strong></td>
        </tr>
        """)
        
    cost_per_gas_min = 35.0  # $35 per oven minute
    cost_gas = oven_min * cost_per_gas_min
    cost_shipping = 1500.0   # $1500 base delivery
    
    cost_total = cost_ingredients + cost_packaging + cost_gas + cost_shipping
    
    # Margin formula: price = cost / (1 - margin)
    raw_suggested = cost_total / (1.0 - margin)
    # Round to nearest 500
    price_suggested = math.ceil(raw_suggested / 500.0) * 500.0
    
    # Delivery app (absorbs 25% app fee): price_app = price_suggested / (1 - 0.25)
    raw_app = price_suggested / 0.75
    price_delivery_app = math.ceil(raw_app / 500.0) * 500.0
    
    html = HTML_TEMPLATE.format(
        recipe_name=recipe_name,
        cost_ingredients=cost_ingredients,
        cost_gas=cost_gas,
        cost_packaging=cost_packaging,
        cost_shipping=cost_shipping,
        cost_total=cost_total,
        margin_pct=margin,
        price_suggested=price_suggested,
        price_delivery_app=price_delivery_app,
        oven_min=oven_min,
        cost_per_gas_min=cost_per_gas_min,
        ingredient_rows="".join(rows_html)
    )
    
    out_file = out_dir / "recipe_cost_sheet.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"✓ Ficha de costeo generada en: {out_file}")
    return out_file

def main():
    parser = argparse.ArgumentParser(description="Calculadora de Costeo de Recetas")
    parser.add_argument("recipe_csv", type=Path, help="CSV de la receta")
    parser.add_argument("--ingredients", type=Path, default=Path("sample_data/ingredients.csv"))
    parser.add_argument("--margin", type=float, default=0.55, help="Margen bruto deseado (ej: 0.55 para 55%)")
    parser.add_argument("--oven-min", type=int, default=45, help="Minutos de horno")
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    compute_costing(args.recipe_csv, args.ingredients, args.margin, args.oven_min, args.out)

if __name__ == "__main__":
    main()
