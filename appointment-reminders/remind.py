#!/usr/bin/env python3
"""Appointment reminders for small salons, ready to send on WhatsApp.

Reads the agenda the business already keeps (a CSV exported from Excel or Google Sheets),
picks the appointments for a given day (tomorrow by default) and builds a friendly,
personalised WhatsApp message for each client as a wa.me link. A person reviews each
message and taps Send: no WhatsApp API, no bots, no data leaves the computer.

Usage:
    python3 remind.py sample_data/agenda.csv --date 2026-12-02 --business "Nails Studio"
Output:
    output/reminders_<date>.html   one card per client with a "Send on WhatsApp" button
    output/reminders_<date>.csv    the same messages, one per row
"""
import argparse
import csv
import datetime as dt
import html
import re
import urllib.parse
from pathlib import Path

DEFAULT_TEMPLATE = (
    "¡Hola {first_name}! 💅 Te recordamos tu turno de {service} mañana, {weekday} {day}, "
    "a las {time} en {business}. Si no podés venir, avisanos así le damos el lugar a otra clienta. ¡Te esperamos!"
)
WEEKDAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
REQUIRED = {"date", "time", "client", "phone", "service"}


def read_agenda(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    missing = REQUIRED - set(rows[0] if rows else {})
    if missing:
        raise SystemExit(f"The agenda is missing these columns: {', '.join(sorted(missing))}")
    return rows


def wa_number(phone: str) -> str:
    """'+54 9 370 000-0001' -> '5493700000001' (the format wa.me expects)."""
    return re.sub(r"\D", "", phone)


def build_reminders(rows: list[dict], day: dt.date, business: str, template: str) -> list[dict]:
    out = []
    for r in rows:
        if dt.date.fromisoformat(r["date"].strip()) != day:
            continue
        text = template.format(first_name=r["client"].split()[0], service=r["service"].strip().lower(),
                               weekday=WEEKDAYS_ES[day.weekday()], day=day.day, time=r["time"].strip(),
                               business=business)
        out.append({**r, "message": text,
                    "link": f"https://wa.me/{wa_number(r['phone'])}?text={urllib.parse.quote(text)}"})
    return sorted(out, key=lambda x: x["time"])


def write_html(reminders: list[dict], day: dt.date, business: str, path: Path) -> None:
    cards = "\n".join(f"""<div class="card"><div class="top"><span class="time">{html.escape(r['time'])}</span>
<span class="name">{html.escape(r['client'])}</span><span class="service">{html.escape(r['service'])}</span></div>
<p class="msg">{html.escape(r['message'])}</p><a class="btn" href="{html.escape(r['link'])}">Enviar por WhatsApp</a></div>"""
                      for r in reminders)
    path.write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Recordatorios {day:%d/%m}</title>
<style>body{{font-family:system-ui,sans-serif;background:#f6f7f9;margin:0;padding:24px;color:#1f2328}}
h1{{font-size:22px;margin:0 0 4px}}.sub{{color:#57606a;margin:0 0 20px}}
.card{{background:#fff;border-radius:14px;padding:16px 18px;margin-bottom:14px;box-shadow:0 1px 3px #0002}}
.top{{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}}.time{{font-weight:700;color:#1f6feb;font-size:18px}}
.name{{font-weight:600;font-size:17px}}.service{{color:#57606a}}.msg{{margin:10px 0 14px;line-height:1.45}}
.btn{{display:inline-block;background:#25d366;color:#fff;text-decoration:none;padding:9px 16px;border-radius:999px;font-weight:600}}</style>
</head><body><h1>{html.escape(business)}: turnos del {WEEKDAYS_ES[day.weekday()]} {day:%d/%m}</h1>
<p class="sub">{len(reminders)} recordatorios listos. Tocá cada botón, revisá el mensaje y enviá.</p>
{cards}</body></html>""", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("agenda", type=Path, help="CSV with columns date,time,client,phone,service")
    ap.add_argument("--date", type=dt.date.fromisoformat, help="day to remind (YYYY-MM-DD); default: tomorrow")
    ap.add_argument("--business", default="el salón", help="business name used in the message")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="message template")
    ap.add_argument("--out", type=Path, default=Path("output"))
    a = ap.parse_args()
    day = a.date or dt.date.today() + dt.timedelta(days=1)
    reminders = build_reminders(read_agenda(a.agenda), day, a.business, a.template)
    a.out.mkdir(exist_ok=True)
    write_html(reminders, day, a.business, a.out / f"reminders_{day}.html")
    with (a.out / f"reminders_{day}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "client", "phone", "service", "message", "link"], extrasaction="ignore")
        w.writeheader()
        w.writerows(reminders)
    print(f"{len(reminders)} reminders for {day} -> {a.out}/reminders_{day}.html")


if __name__ == "__main__":
    main()
