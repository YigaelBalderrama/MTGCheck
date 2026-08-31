# MTG Multi-Card Recognition API

Backend REST en Flask para detectar varias cartas de Magic: The Gathering en una fotografía, corregir perspectiva, leer el nombre con OCR y empatarlo contra un catálogo local basado en Scryfall.

## Arquitectura

La aplicación usa separación Controller-Service-Repository.

- `controllers`: exponen HTTP, validan lo mínimo del request y serializan JSON.
- `services`: contienen el caso de uso y las piezas técnicas de OpenCV, perspectiva, OCR y matching.
- `repositories`: encapsulan SQLite y el catálogo local de cartas.
- `clients`: aíslan la comunicación HTTP con Scryfall.

El controller no ejecuta OpenCV, OCR, Scryfall ni SQL.

## Instalación local

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Variables de entorno

Copia `.env.example` a `.env` y ajusta al menos `SCRYFALL_USER_AGENT` con un identificador/contacto real. Scryfall requiere `User-Agent` descriptivo y `Accept`; además recomienda mantener el tráfico por debajo de 10 solicitudes por segundo y preferir bulk data para cargas grandes. Referencias oficiales: [API overview](https://scryfall.com/docs/api), [rate limits](https://scryfall.com/docs/api/rate-limits) y [bulk data](https://scryfall.com/docs/api/bulk-data).

Variables principales:

- `DATABASE_URL`: SQLite local, por defecto `sqlite:///data/cards_cache.sqlite`.
- `MAX_IMAGE_SIZE_MB`: tamaño máximo de imagen, por defecto `12`.
- `RECOGNITION_CONFIDENCE_THRESHOLD`: umbral mínimo de reconocimiento, por defecto `0.72`.
- `OCR_LANGUAGES`: idiomas para EasyOCR, por defecto `en`.
- `OCR_GPU`: habilita GPU para EasyOCR si está disponible.

## Catálogo Scryfall

Para poblar o actualizar la caché local:

```powershell
$env:FLASK_APP="run.py"
flask update-scryfall-catalog
```

El comando descarga el bulk `default_cards` de Scryfall en `data/` e importa las cartas a SQLite. El endpoint puede consultar Scryfall como respaldo puntual, pero un fallo externo no impide devolver coincidencias del catálogo local.

## Ejecutar la API

Desarrollo:

```powershell
$env:FLASK_APP="run.py"
$env:APP_ENV="development"
flask run --host 0.0.0.0 --port 5000
```

Producción local con Gunicorn:

```bash
gunicorn -b 0.0.0.0:5000 run:app
```

Healthcheck:

```bash
curl http://localhost:5000/health
```

Swagger:

- UI: `http://localhost:5000/docs`
- OpenAPI JSON: `http://localhost:5000/openapi.json`

## Docker

```bash
docker compose up --build
```

## Reconocer cartas

```bash
curl -X POST http://localhost:5000/api/cards/recognize \
  -F "image=@cartas.jpg"
```

Respuesta con reconocimientos:

```json
{
  "cards_detected": 2,
  "cards_recognized": 1,
  "processing_time_ms": 1325,
  "cards": [
    {
      "index": 1,
      "recognized": true,
      "detected_text": "Sol Ring",
      "name": "Sol Ring",
      "confidence": 0.96,
      "scryfall_id": "scryfall-id",
      "set_name": "Commander Masters",
      "set_code": "cmm",
      "collector_number": "396",
      "image_url": "https://...",
      "scryfall_url": "https://...",
      "prices": {"usd": "1.50", "eur": "1.20"},
      "polygon": [{"x": 120, "y": 85}, {"x": 470, "y": 110}, {"x": 450, "y": 610}, {"x": 100, "y": 590}]
    }
  ]
}
```

Si no se detectan cartas:

```json
{
  "cards_detected": 0,
  "cards_recognized": 0,
  "processing_time_ms": 480,
  "cards": []
}
```

Errores usan este formato:

```json
{
  "error": {
    "code": "INVALID_IMAGE",
    "message": "El archivo enviado no es una imagen válida."
  }
}
```

## Pruebas

```powershell
pytest
```

Las pruebas usan mocks para OCR, repositorio y Scryfall; no dependen de Internet.

## Limitaciones

El OCR sobre fotografías reales puede fallar con reflejos, fundas brillantes, baja resolución, cartas parcialmente tapadas, cartas foil, idiomas no configurados o encuadres extremos. El MVP usa contornos y nombre OCR; no identifica arte ni set visualmente.

Mejoras naturales:

- OpenCLIP o embeddings visuales para comparar arte.
- Hashes perceptuales contra imágenes normalizadas.
- Detector entrenado para cartas solapadas.
- Re-ranking por set, idioma, impresión y similitud de imagen.
