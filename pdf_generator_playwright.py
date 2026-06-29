import os
import io
import base64
from pathlib import Path

from flask import Flask, request, send_file, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Clé API simple pour protéger l'endpoint.
# À définir dans les variables d'environnement de l'hébergeur (PAS en dur dans le code).
API_KEY = os.environ.get("CASHVOLT_API_KEY", "change-me")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "certificate_template_light.html"
LOGO_PATH = BASE_DIR / "cashvolt_logo.jpg"


def get_logo_data_uri():
    """Encode le logo en base64 pour l'intégrer directement dans le HTML.
    Évite tout problème de chemin relatif lors du rendu."""
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def build_html(data):
    """Injecte les données reçues de Bubble dans le template HTML."""
    html = TEMPLATE_PATH.read_text(encoding="utf-8")

    health = str(data.get("health", "100"))

    replacements = {
        'id="val-grade">A<':            f'id="val-grade">{data.get("grade", "A")}<',
        'id="val-lifespan">4,2<':       f'id="val-lifespan">{data.get("lifespan", "—")}<',
        'id="val-model">X-Phone 15 Pro<': f'id="val-model">{data.get("model", "Inconnu")}<',
        'id="val-capacity">3274 mAh<':  f'id="val-capacity">{data.get("capacity", "0")} mAh<',
        'id="val-health">94%<':         f'id="val-health">{health}%<',
        'id="val-cycles">312<':         f'id="val-cycles">{data.get("cycles", "0")}<',
        'id="val-cert-id">BC-A-2024-05-21-9847<': f'id="val-cert-id">{data.get("certId", "N/A")}<',
        'id="val-date">21 MAI 2024<':   f'id="val-date">{data.get("date", "")}<',
        # barre de progression "Santé" liée à la vraie valeur
        'style="width: 94%;"':          f'style="width: {health}%;"',
        # logo en base64 (corrige le bug du chemin relatif)
        'src="cashvolt_logo.jpg"':      f'src="{get_logo_data_uri()}"',
    }

    for old, new in replacements.items():
        html = html.replace(old, new)

    return html


def render_pdf(html):
    """Rend le HTML en PDF avec Chromium (Playwright). Renvoie des bytes,
    donc aucun fichier temporaire à nettoyer."""
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        # on attend les polices Google + Chart.js (réseau au repos)
        page.set_content(html, wait_until="networkidle")
        # marge pour laisser Chart.js dessiner le graphique
        page.wait_for_timeout(800)
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
        return pdf_bytes


@app.route("/")
def home():
    return "<h1>Serveur Cashvolt en ligne</h1><p>Endpoint : POST /generate-pdf</p>"


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "Cle API invalide ou manquante"}), 401

    if not TEMPLATE_PATH.exists():
        return jsonify({"error": f"Template introuvable : {TEMPLATE_PATH.name}"}), 404

    data = request.get_json(silent=True) or {}

    try:
        html = build_html(data)
        pdf_bytes = render_pdf(html)
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name="certificat_cashvolt.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        app.logger.exception("Erreur generation PDF")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # En production : NE PAS utiliser debug=True. Lancez plutot via gunicorn.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
