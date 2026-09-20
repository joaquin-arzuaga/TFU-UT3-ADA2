# Imagen por capas: SO base + runtime Python -> dependencias -> código de la app.
# Si solo cambia el código, se reutilizan las capas de abajo (union filesystem).
FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY demo_cli.py .

# No correr como root dentro del contenedor
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# 1 proceso por contenedor: se escala agregando contenedores (horizontal)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
