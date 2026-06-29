# Image officielle Playwright : Chromium est deja installe.
# La version doit correspondre a celle de requirements.txt (playwright==1.49.0).
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render fournit la variable PORT : gunicorn DOIT ecouter dessus, sinon le service
# est injoignable. Forme shell pour que $PORT soit substitue.
# 1 worker = adapte a 512 MB de RAM (Chromium consomme beaucoup).
CMD gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 120 pdf_generator_playwright:app
