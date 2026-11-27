#!/usr/bin/env python3
"""Static WhatsApp Catalog Generator.

Generates a responsive static web catalog from a simple CSV spreadsheet.
Each item includes a direct "Pedir por WhatsApp" button with a pre-filled wa.me message.
Requires zero database and zero backend server: deployable to Cloudflare Pages for free.

Usage:
    python3 build_catalog.py sample_data/catalog.csv --business "Aura Boutique" --phone "+5493704000010" --out output/
"""
import argparse
import csv
import urllib.parse
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{business} — Catálogo Online</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --heading: #f0f6fc;
      --accent: #58a6ff;
      --whatsapp: #238636;
      --whatsapp-hover: #2ea043;
      --badge-bg: rgba(56, 139, 253, 0.15);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 60px;
    }}
    header {{
      background: var(--card);
      border-bottom: 1px solid var(--border);
      padding: 24px 20px;
      text-align: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    header h1 {{
      font-size: 24px;
      color: var(--heading);
      letter-spacing: -0.5px;
    }}
    header p {{
      font-size: 14px;
      color: #8b949e;
      margin-top: 4px;
    }}
    .container {{
      max-width: 1000px;
      margin: 0 auto;
      padding: 20px;
    }}
    .category-section {{
      margin-bottom: 36px;
    }}
    .category-title {{
      font-size: 18px;
      color: var(--heading);
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 18px;
    }}
    .product-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .product-card:hover {{
      border-color: #58a6ff;
      transform: translateY(-2px);
    }}
    .img-placeholder {{
      height: 180px;
      background: linear-gradient(135deg, #21262d 0%, #161b22 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #8b949e;
      font-size: 40px;
      border-bottom: 1px solid var(--border);
    }}
    .card-body {{
      padding: 16px;
      display: flex;
      flex-direction: column;
      flex-grow: 1;
    }}
    .card-badge {{
      align-self: flex-start;
      background: var(--badge-bg);
      color: var(--accent);
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 12px;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .product-title {{
      font-size: 16px;
      font-weight: 600;
      color: var(--heading);
      margin-bottom: 6px;
    }}
    .product-desc {{
      font-size: 13px;
      color: #8b949e;
      flex-grow: 1;
      margin-bottom: 14px;
    }}
    .card-footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid var(--border);
      padding-top: 12px;
    }}
    .price {{
      font-size: 18px;
      font-weight: 700;
      color: #3fb950;
    }}
    .order-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--whatsapp);
      color: #ffffff;
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      padding: 8px 14px;
      border-radius: 8px;
      transition: background 0.15s ease;
    }}
    .order-btn:hover {{
      background: var(--whatsapp-hover);
    }}
    footer {{
      text-align: center;
      color: #8b949e;
      font-size: 13px;
      margin-top: 40px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{business}</h1>
    <p>Tocá "Pedir por WhatsApp" en cualquier producto para consultar disponibilidad</p>
  </header>

  <div class="container">
    {categories_html}
    <footer>
      <p>Catálogo generado automáticamente con Python · {business} · Pedidos directos vía WhatsApp</p>
    </footer>
  </div>
</body>
</html>
"""

def generate_catalog(csv_path: Path, business: str, phone: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Read CSV
    items_by_cat = {}
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row["category"].strip()
            items_by_cat.setdefault(cat, []).append(row)
            
    categories_parts = []
    
    # Category icon mapping
    icons = {
        "Cosmética": "✨",
        "Moda & Accesorios": "👜",
        "Lencería": "🪞"
    }
    
    clean_phone = "".join([c for c in phone if c.isdigit()])
    
    for cat, items in items_by_cat.items():
        icon = icons.get(cat, "🛍️")
        cards_html = []
        for it in items:
            p_name = it["product"].strip()
            p_desc = it["description"].strip()
            p_price = int(it["price"].strip())
            p_price_fmt = f"${p_price:,.0f}".replace(",", ".")
            
            # WhatsApp link
            msg = f"¡Hola {business}! Me interesa encargar: *{p_name}* ({p_price_fmt}). ¿Tenés disponibilidad para retirar o coordinar envío?"
            encoded_msg = urllib.parse.quote(msg)
            wa_url = f"https://wa.me/{clean_phone}?text={encoded_msg}"
            
            # Card
            cards_html.append(f"""
            <div class="product-card">
              <div class="img-placeholder">{icon}</div>
              <div class="card-body">
                <span class="card-badge">{cat}</span>
                <h3 class="product-title">{p_name}</h3>
                <p class="product-desc">{p_desc}</p>
                <div class="card-footer">
                  <span class="price">{p_price_fmt}</span>
                  <a href="{wa_url}" target="_blank" class="order-btn">Pedir por WhatsApp</a>
                </div>
              </div>
            </div>
            """)
            
        categories_parts.append(f"""
        <section class="category-section">
          <h2 class="category-title">{icon} {cat} ({len(items)})</h2>
          <div class="grid">
            {"".join(cards_html)}
          </div>
        </section>
        """)
        
    full_html = HTML_TEMPLATE.format(
        business=business,
        categories_html="".join(categories_parts)
    )
    
    index_file = out_dir / "index.html"
    index_file.write_text(full_html, encoding="utf-8")
    print(f"✓ Catálogo generado en: {index_file}")
    return index_file

def main():
    parser = argparse.ArgumentParser(description="Generador de Catálogo WhatsApp")
    parser.add_argument("csv_path", type=Path, help="Ruta al catálogo CSV")
    parser.add_argument("--business", default="Aura Boutique", help="Nombre del comercio")
    parser.add_argument("--phone", default="+5493704000010", help="Teléfono WhatsApp con código de país")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Carpeta de destino")
    args = parser.parse_args()
    
    generate_catalog(args.csv_path, args.business, args.phone, args.out)

if __name__ == "__main__":
    main()
