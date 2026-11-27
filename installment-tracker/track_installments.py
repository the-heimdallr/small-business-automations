#!/usr/bin/env python3
"""Customer Installment and Credit Accounts Tracker.

Manages informal store credit and installment sales from two simple CSV tables (sales and payments).
Features:
- Dynamically calculates outstanding balances (never hardcoded by hand).
- Calculates days overdue and due dates for upcoming and missed installments.
- Generates polite, personalized WhatsApp payment reminder links (wa.me) for each customer.

Usage:
    python3 track_installments.py sample_data/sales.csv --payments sample_data/payments.csv --business "Modas Elegance" --as-of 2026-12-19 --out output/
"""
import argparse
import csv
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Control de Cuotas y Cobranzas — {business}</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --heading: #f0f6fc;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --red-bg: rgba(248, 81, 73, 0.12);
    --yellow: #d29922;
    --yellow-bg: rgba(210, 153, 34, 0.12);
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
  .kpi-card.alert {{ border-color: var(--red); background: var(--red-bg); }}
  .kpi-card.alert .kpi-val {{ color: var(--red); }}

  .section-title {{ font-size: 18px; color: var(--heading); margin: 28px 0 14px 0; }}
  
  table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); margin-bottom: 24px; }}
  th, td {{ padding: 10px 14px; text-align: left; font-size: 14px; border-bottom: 1px solid var(--border); }}
  th {{ background: #21262d; color: var(--heading); font-weight: 600; text-transform: uppercase; font-size: 12px; }}
  tr:last-child td {{ border-bottom: none; }}
  td.num, th.num {{ text-align: right; }}
  
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .badge-danger {{ background: var(--red-bg); color: #ff7b72; border: 1px solid var(--red); }}
  .badge-warning {{ background: var(--yellow-bg); color: #e3b341; border: 1px solid var(--yellow); }}
  
  .wa-btn {{
    display: inline-block;
    background: #238636;
    color: white;
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
  }}
  .wa-btn:hover {{ background: #2ea043; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>📒 {business} — Control de Cuentas Corrientes y Cuotas</h1>
    <p class="subtitle">Estado de saldos deudores, cuotas vencidas y avisos cordiales al día {as_of_str}</p>
  </header>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">Total Cuentas Activas</div>
      <div class="kpi-val">{total_clients} clientas</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-label">Saldo Total a Cobrar</div>
      <div class="kpi-val">${total_pending:,.0f}</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-label">Cuotas Vencidas / Atraso</div>
      <div class="kpi-val">{total_overdue} cuotas</div>
    </div>
  </div>

  <div class="section-title">🚨 1. Cuotas Vencidas & Avisos Pendientes para Hoy</div>
  <table>
    <thead>
      <tr>
        <th>Clienta</th>
        <th>Artículo</th>
        <th class="num">Cuota</th>
        <th>Vencimiento</th>
        <th class="num">Días Atraso</th>
        <th class="num">Monto Cuota</th>
        <th>Acción Directa</th>
      </tr>
    </thead>
    <tbody>
      {overdue_rows}
    </tbody>
  </table>

  <div class="section-title">👥 2. Resumen General de Saldos por Clienta</div>
  <table>
    <thead>
      <tr>
        <th>Clienta</th>
        <th>Teléfono</th>
        <th class="num">Total Comprado</th>
        <th class="num">Total Abonado</th>
        <th class="num">Saldo Pendiente</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>
      {clients_rows}
    </tbody>
  </table>
</div>
</body>
</html>
"""

def process_installments(sales_csv: Path, payments_csv: Path, business: str, as_of: datetime, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load payments by sale_id
    paid_by_sale = {}
    with open(payments_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            s_id = r["sale_id"].strip()
            paid_by_sale[s_id] = paid_by_sale.get(s_id, 0.0) + float(r["amount_paid"].strip())
            
    sales = []
    with open(sales_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            s_date = datetime.strptime(r["date"].strip(), "%Y-%m-%d")
            total = float(r["total_amount"].strip())
            inst_count = int(r["installments_count"].strip())
            sales.append({
                "sale_id": r["sale_id"].strip(),
                "date": s_date,
                "client": r["client"].strip(),
                "phone": r["phone"].strip(),
                "item": r["item"].strip(),
                "total": total,
                "inst_count": inst_count,
                "inst_amount": total / inst_count
            })
            
    # Calculate overdue installments and client balances
    total_pending_all = 0.0
    overdue_rows_html = []
    clients_rows_html = []
    overdue_count = 0
    
    for s in sales:
        s_id = s["sale_id"]
        paid = paid_by_sale.get(s_id, 0.0)
        balance = s["total"] - paid
        total_pending_all += balance
        
        # Calculate which installments are due/overdue
        paid_installments = int(paid // s["inst_amount"])
        
        # Check next unpaid installment
        for i in range(paid_installments, s["inst_count"]):
            due_date = s["date"] + timedelta(days=30 * (i + 1))
            if due_date <= as_of:
                overdue_count += 1
                days_late = (as_of - due_date).days
                
                # Cordial message template
                first_name = s["client"].split()[0]
                msg = f"¡Hola {first_name}! Te escribimos de {business}. Te recordamos con cariño que tenés una cuota de ${s['inst_amount']:,.0f} de tu compra de {s['item']} que venció el {due_date.strftime('%d/%m')}. Cualquier consulta con tu saldo o medio de pago avisanos. ¡Muchas gracias!"
                clean_phone = "".join([c for c in s["phone"] if c.isdigit()])
                wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
                
                overdue_rows_html.append(f"""
                <tr>
                  <td><strong>{s['client']}</strong></td>
                  <td>{s['item']}</td>
                  <td class="num">{i+1} de {s['inst_count']}</td>
                  <td>{due_date.strftime('%d/%m/%Y')}</td>
                  <td class="num"><span class="badge badge-danger">+{days_late} días</span></td>
                  <td class="num"><strong style="color: var(--red);">${s['inst_amount']:,.0f}</strong></td>
                  <td><a href="{wa_url}" target="_blank" class="wa-btn">Enviar Mensaje Amable</a></td>
                </tr>
                """)
                
        status_badge = '<span class="badge badge-warning">CON SALDO</span>' if balance > 0 else '<span class="badge" style="background:#238636;color:white;">AL DÍA</span>'
        clients_rows_html.append(f"""
        <tr>
          <td><strong>{s['client']}</strong></td>
          <td><code>{s['phone']}</code></td>
          <td class="num">${s['total']:,.0f}</td>
          <td class="num">${paid:,.0f}</td>
          <td class="num"><strong style="color: var(--accent);">${balance:,.0f}</strong></td>
          <td>{status_badge}</td>
        </tr>
        """)
        
    html = HTML_TEMPLATE.format(
        business=business,
        as_of_str=as_of.strftime("%d/%m/%Y"),
        total_clients=len(sales),
        total_pending=total_pending_all,
        total_overdue=overdue_count,
        overdue_rows="".join(overdue_rows_html),
        clients_rows="".join(clients_rows_html)
    )
    
    out_file = out_dir / "installment_report.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"✓ Control de cuotas generado en: {out_file}")
    return out_file

def main():
    parser = argparse.ArgumentParser(description="Control de Cuotas y Cobranzas")
    parser.add_argument("sales_csv", type=Path, help="CSV de ventas en cuotas")
    parser.add_argument("--payments", type=Path, default=Path("sample_data/payments.csv"))
    parser.add_argument("--business", default="Modas Elegance", help="Nombre del comercio")
    parser.add_argument("--as-of", default="2026-12-19", help="Fecha de corte YYYY-MM-DD")
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    as_of_date = datetime.strptime(args.as_of, "%Y-%m-%d")
    process_installments(args.sales_csv, args.payments, args.business, as_of_date, args.out)

if __name__ == "__main__":
    main()
