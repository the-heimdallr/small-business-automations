import subprocess
from pathlib import Path
from PIL import Image

scr_dir = Path("/media/javier/Archivos/01_Programacion/small-business-automations/whatsapp-catalog/screenshots")

# 1) Mobile view already captured: mobile_view.png
# 2) Product detail card crop: capture zoom on single product card
img = Image.open(scr_dir / "mobile_view.png")
# Crop product card with 'Pedir por WhatsApp'
card_crop = img.crop((15, 175, 415, 590))
card_crop.save(scr_dir / "product_detail.png")

# 3) Generate a mock WhatsApp chat bubble screenshot
html_wa = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    background: #0b141a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    margin: 0;
  }
  .bubble {
    background: #005c4b;
    color: #e9edef;
    padding: 16px 20px;
    border-radius: 14px 14px 2px 14px;
    max-width: 420px;
    font-size: 16px;
    line-height: 1.5;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    border: 1px solid rgba(255,255,255,0.08);
  }
  .meta {
    text-align: right;
    font-size: 11px;
    color: #8696a0;
    margin-top: 6px;
  }
</style>
</head>
<body>
  <div class="bubble">
    ¡Hola Aura Boutique! Me interesa encargar: <strong>Serum Ácido Hialurónico</strong> ($14.500). ¿Tenés disponibilidad para retirar o coordinar envío?
    <div class="meta">19:14 ✓✓</div>
  </div>
</body>
</html>
"""
(scr_dir / "wa_preview.html").write_text(html_wa, encoding="utf-8")
subprocess.run([
    "google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
    "--window-size=500,320",
    f"--screenshot={scr_dir}/whatsapp_msg.png",
    f"file://{scr_dir}/wa_preview.html"
], check=True)

print("Screenshots ready!")
