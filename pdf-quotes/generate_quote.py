#!/usr/bin/env python3
"""Professional PDF Quote and Proposal Generator for Service Businesses.

Reads quote line items from a CSV spreadsheet and generates an elegant,
print-ready and shareable PDF proposal with logo, itemized pricing, total, and validity terms.
Uses headless Google Chrome to render clean PDF without complex system dependencies.

Usage:
    python3 generate_quote.py sample_data/quotes.csv --business "Velazquez Catering & Eventos" --validity "15 días" --out output/
"""
import argparse
import csv
import subprocess
from datetime import datetime
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Presupuesto {quote_id} — {business}</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 20mm 15mm;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #24292f;
    background: #ffffff;
    line-height: 1.5;
    padding: 30px;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2px solid #0969da;
    padding-bottom: 20px;
    margin-bottom: 30px;
  }}
  .logo-box h1 {{
    font-size: 24px;
    color: #0969da;
    letter-spacing: -0.5px;
  }}
  .logo-box p {{
    font-size: 13px;
    color: #57606a;
  }}
  .quote-meta {{
    text-align: right;
  }}
  .quote-meta .num {{
    font-size: 18px;
    font-weight: bold;
    color: #24292f;
  }}
  .quote-meta .date {{
    font-size: 13px;
    color: #57606a;
  }}
  
  .client-card {{
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 30px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    font-size: 14px;
  }}
  .client-card strong {{ color: #24292f; }}
  
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 30px;
  }}
  th, td {{
    padding: 12px 14px;
    text-align: left;
    font-size: 14px;
    border-bottom: 1px solid #d0d7de;
  }}
  th {{
    background: #f6f8fa;
    font-size: 12px;
    text-transform: uppercase;
    color: #57606a;
    font-weight: 600;
  }}
  td.num, th.num {{ text-align: right; }}
  
  .total-box {{
    margin-left: auto;
    width: 320px;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    background: #f6f8fa;
    padding: 16px;
    margin-bottom: 40px;
  }}
  .total-row {{
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    margin-bottom: 8px;
  }}
  .total-row.final {{
    font-size: 20px;
    font-weight: bold;
    color: #0969da;
    border-top: 2px solid #0969da;
    padding-top: 10px;
    margin-bottom: 0;
  }}
  
  .terms {{
    border-top: 1px solid #d0d7de;
    padding-top: 16px;
    font-size: 12px;
    color: #57606a;
  }}
  .terms ul {{
    padding-left: 20px;
    margin-top: 6px;
  }}
</style>
</head>
<body>
  <div class="header">
    <div class="logo-box">
      <h1>{business}</h1>
      <p>Servicios Profesionales · Formosa, Argentina</p>
    </div>
    <div class="quote-meta">
      <div class="num">PRESUPUESTO #{quote_id}</div>
      <div class="date">Fecha de emisión: {date}</div>
      <div class="date">Validez de la oferta: {validity}</div>
    </div>
  </div>

  <div class="client-card">
    <div>
      <span style="color:#57606a;">Cliente / Razón Social:</span><br>
      <strong>{client}</strong>
    </div>
    <div>
      <span style="color:#57606a;">Contacto:</span><br>
      <strong>{phone} · {email}</strong>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Ítem / Servicio</th>
        <th>Descripción Detallada</th>
        <th class="num">Cant.</th>
        <th class="num">Precio Unit.</th>
        <th class="num">Subtotal</th>
      </tr>
    </thead>
    <tbody>
      {items_rows}
    </tbody>
  </table>

  <div class="total-box">
    <div class="total-row">
      <span>Subtotal neto:</span>
      <strong>${total:,.0f}</strong>
    </div>
    <div class="total-row final">
      <span>TOTAL FINAL:</span>
      <span>${total:,.0f}</span>
    </div>
  </div>

  <div class="terms">
    <strong>Condiciones Comerciales y Validez:</strong>
    <ul>
      <li>Presupuesto válido por <strong>{validity}</strong> a partir de la fecha de emisión.</li>
      <li>Forma de pago: 50% de seña para confirmar la fecha y saldo contra entrega del servicio.</li>
      <li>Precios sujetos a variación si se modifican las cantidades o el alcance detallado arriba.</li>
    </ul>
  </div>
</body>
</html>
"""

def generate_pdf_quote(csv_path: Path, business: str, validity: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
            
    if not rows:
        print("No hay ítems en el CSV.")
        return
        
    first = rows[0]
    quote_id = first["quote_id"].strip()
    date_str = first["date"].strip()
    client = first["client"].strip()
    phone = first["phone"].strip()
    email = first["email"].strip()
    
    items_html = []
    total_val = 0.0
    for r in rows:
        qty = float(r["quantity"].strip())
        price = float(r["unit_price"].strip())
        sub = qty * price
        total_val += sub
        
        items_html.append(f"""
        <tr>
          <td><strong>{r['item'].strip()}</strong></td>
          <td style="color: #57606a; font-size: 13px;">{r['description'].strip()}</td>
          <td class="num">{qty:.0f}</td>
          <td class="num">${price:,.0f}</td>
          <td class="num"><strong>${sub:,.0f}</strong></td>
        </tr>
        """)
        
    html = HTML_TEMPLATE.format(
        business=business,
        quote_id=quote_id,
        date=date_str,
        validity=validity,
        client=client,
        phone=phone,
        email=email,
        items_rows="".join(items_html),
        total=total_val
    )
    
    html_file = out_dir / f"{quote_id}.html"
    pdf_file = out_dir / f"{quote_id}.pdf"
    html_file.write_text(html, encoding="utf-8")
    
    # Render PDF using headless Chrome
    subprocess.run([
        "google-chrome", "--headless=new", "--disable-gpu",
        f"--print-to-pdf={pdf_file}",
        html_file.resolve().as_uri()
    ], check=True, capture_output=True)
    
    print(f"✓ Presupuesto PDF generado con éxito: {pdf_file}")
    return html_file, pdf_file

def main():
    parser = argparse.ArgumentParser(description="Generador de Presupuestos PDF")
    parser.add_argument("csv_path", type=Path, help="CSV con los ítems del presupuesto")
    parser.add_argument("--business", default="Velazquez Catering & Eventos", help="Nombre del comercio")
    parser.add_argument("--validity", default="15 días", help="Validez de la oferta")
    parser.add_argument("--out", type=Path, default=Path("output/presupuestos"))
    args = parser.parse_args()

    generate_pdf_quote(args.csv_path, args.business, args.validity, args.out)

if __name__ == "__main__":
    main()
