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
- `CARD_LOOKUP_MODE`: `sqlite` usa catálogo local; `scryfall_api` evita SQLite en reconocimiento y consulta Scryfall por cada texto OCR.
- `MAX_IMAGE_SIZE_MB`: tamaño máximo de imagen, por defecto `12`.
- `RECOGNITION_CONFIDENCE_THRESHOLD`: umbral mínimo de reconocimiento, por defecto `0.72`.
- `RECOVERY_CONFIDENCE_THRESHOLD`: umbral desde el que se intenta OCR de recuperación, por defecto `0.55`.
- `MAX_CARDS_PER_IMAGE`: máximo de regiones completas a devolver, por defecto `20`.
- `DETECTION_TARGET_MAX_DIMENSION`: lado mayor de la copia de detección, por defecto `1500`.
- `CARD_WARP_WIDTH` y `CARD_WARP_HEIGHT`: resolución normalizada por carta, por defecto `448x624`.
- `ENABLE_RECOGNITION_CACHE`: activa caché SHA-256 por contenido, por defecto `true`.
- `RECOGNITION_CACHE_TTL_SECONDS` y `RECOGNITION_CACHE_MAX_ITEMS`: TTL y tamaño de caché.
- `ENABLE_DIAGNOSTIC_METRICS`: incluye métricas internas en el JSON si está en `true`.
- `OPENCV_NUM_THREADS`: threads de OpenCV. `0` deja la ejecución en modo controlado por OpenCV.
- `OCR_LANGUAGES`: idiomas para EasyOCR, por defecto `en`.
- `OCR_GPU`: habilita GPU para EasyOCR si está disponible.
- `OCR_PRELOAD`: inicializa EasyOCR al arrancar la app si está en `true`.

## Catálogo Scryfall

Para poblar o actualizar la caché local:

```powershell
$env:FLASK_APP="run.py"
flask update-scryfall-catalog
```

El comando descarga el bulk `all_cards` de Scryfall en `data/` e importa las cartas a SQLite, incluyendo `printed_name`, `oracle_name` y `lang` cuando están disponibles. El endpoint de reconocimiento no realiza consultas HTTP individuales a Scryfall; usa únicamente el índice local cargado en memoria.

Modo sin SQLite:

```env
CARD_LOOKUP_MODE=scryfall_api
```

En este modo no se carga el índice local al arrancar y el reconocimiento consulta `cards/named` de Scryfall con `fuzzy=<texto OCR>`. Es más simple para desarrollo, pero depende de Internet, agrega latencia por carta detectada y está sujeto a rate limits. La caché en memoria del cliente evita repetir consultas por el mismo texto dentro del proceso.

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

## Benchmark

Ejecuta:

```bash
python -m benchmarks.recognition_benchmark \
  tests/fixtures/multi_cards_reference.png \
  --iterations 5 \
  --warmup 1
```

Por defecto el benchmark desactiva la caché para medir detección, perspectiva, OCR y matching reales. Para medir caché:

```bash
python -m benchmarks.recognition_benchmark tests/fixtures/multi_cards_reference.png --use-cache
```

Salida incluida:

- tiempo anterior, si puede medirse;
- promedio, mediana y P95;
- cartas detectadas y reconocidas;
- exactitud contra la lista esperada;
- métricas por etapa: `decode_ms`, `detection_ms`, `perspective_ms`, `title_preprocessing_ms`, `ocr_ms`, `matching_ms`, `total_ms`.

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
      "printed_name": "Sol Ring",
      "oracle_name": "Sol Ring",
      "language": "en",
      "confidence": 0.96,
      "ocr_confidence": 0.91,
      "name_match_confidence": 1.0,
      "detection_confidence": 0.98,
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

La fotografía de regresión debe existir en:

```text
tests/fixtures/multi_cards_reference.png
```

En este workspace no se encontró una imagen adjunta fuera del `.venv`, por lo que la prueba de integración real se omite hasta que el archivo esté disponible. Cuando exista y el catálogo local esté importado, valida `cards_detected == 14` y `cards_recognized >= 13`.

## Cambios de rendimiento

| Área | Antes | Después |
|---|---|---|
| OCR | OCR por carta y por varias rotaciones | OCR batch sobre barras de título |
| Orientación | 0, 90, 180 y 270 grados como camino normal | 0 grados en fase rápida; 180 y variantes solo en recuperación |
| Resolución por carta | `630x880` | `448x624` configurable |
| Matching | Consultas SQLite frecuentes y fallback HTTP Scryfall | Índice local en memoria y sin HTTP en reconocimiento |
| Multidioma | Principalmente `name` | `name`, `printed_name`, `oracle_name`, `lang` desde `all_cards` |
| Repetición exacta | Reprocesa imagen | Caché SHA-256 con TTL y tamaño máximo |

Resultado medido en este entorno sin imagen adjunta:

- Pruebas automatizadas: `33 passed, 1 skipped`.
- La prueba omitida corresponde a `tests/fixtures/multi_cards_reference.png`.
- Benchmark real contra la fotografía solicitada: no ejecutado porque el archivo no está en el workspace.

## Limitaciones

El OCR sobre fotografías reales puede fallar con reflejos, fundas brillantes, baja resolución, cartas parcialmente tapadas, cartas foil, idiomas no configurados o encuadres extremos. El MVP usa contornos y nombre OCR; no identifica arte ni set visualmente.

Mejoras naturales:

- OpenCLIP o embeddings visuales para comparar arte.
- Hashes perceptuales contra imágenes normalizadas.
- Detector entrenado para cartas solapadas.
- Re-ranking por set, idioma, impresión y similitud de imagen.
