from __future__ import annotations

from typing import Any

OPENAPI_SPEC: dict[str, Any] = {
    "openapi": "3.0.3",
    "info": {
        "title": "MTG Multi-Card Recognition API",
        "version": "1.0.0",
        "description": (
            "REST API para detectar varias cartas de Magic: The Gathering en una "
            "fotografia, corregir perspectiva, extraer el nombre con OCR y buscar "
            "coincidencias contra un catalogo local/Scryfall."
        ),
    },
    "servers": [{"url": "http://localhost:5000", "description": "Local"}],
    "tags": [
        {"name": "Health", "description": "Estado de la API"},
        {"name": "Cards", "description": "Reconocimiento de cartas MTG"},
        {"name": "Docs", "description": "Documentacion OpenAPI"},
    ],
    "paths": {
        "/": {
            "get": {
                "tags": ["Health"],
                "summary": "Informacion basica de la API",
                "responses": {
                    "200": {
                        "description": "Metadata de la API",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ApiInfo"}
                            }
                        },
                    }
                },
            }
        },
        "/health": {
            "get": {
                "tags": ["Health"],
                "summary": "Healthcheck",
                "responses": {
                    "200": {
                        "description": "La API esta disponible",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Health"}
                            }
                        },
                    }
                },
            }
        },
        "/docs": {
            "get": {
                "tags": ["Docs"],
                "summary": "Swagger UI",
                "responses": {
                    "200": {
                        "description": "Interfaz HTML de Swagger UI",
                        "content": {"text/html": {"schema": {"type": "string"}}},
                    }
                },
            }
        },
        "/openapi.json": {
            "get": {
                "tags": ["Docs"],
                "summary": "Especificacion OpenAPI",
                "responses": {
                    "200": {
                        "description": "Documento OpenAPI 3",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                            }
                        },
                    }
                },
            }
        },
        "/api/cards/recognize": {
            "post": {
                "tags": ["Cards"],
                "summary": "Reconocer cartas en una imagen",
                "description": (
                    "Recibe una fotografia con una o varias cartas visibles. La API "
                    "valida la imagen, detecta cartas, corrige perspectiva, ejecuta "
                    "OCR sobre la zona del nombre y devuelve coincidencias con "
                    "confianza suficiente."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["image"],
                                "properties": {
                                    "image": {
                                        "type": "string",
                                        "format": "binary",
                                        "description": "Imagen JPG, JPEG, PNG o WebP.",
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Resultado del reconocimiento",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/RecognitionResponse"
                                },
                                "examples": {
                                    "recognized": {
                                        "summary": "Cartas reconocidas y no reconocidas",
                                        "value": {
                                            "cards_detected": 2,
                                            "cards_recognized": 1,
                                            "processing_time_ms": 1325,
                                            "cards": [
                                                {
                                                    "index": 1,
                                                    "recognized": True,
                                                    "detected_text": "Sol Ring",
                                                    "name": "Sol Ring",
                                                    "confidence": 0.96,
                                                    "scryfall_id": "scryfall-id",
                                                    "set_name": "Commander Masters",
                                                    "set_code": "cmm",
                                                    "collector_number": "396",
                                                    "image_url": "https://...",
                                                    "scryfall_url": "https://...",
                                                    "prices": {
                                                        "usd": "1.50",
                                                        "eur": "1.20",
                                                    },
                                                    "polygon": [
                                                        {"x": 120, "y": 85},
                                                        {"x": 470, "y": 110},
                                                        {"x": 450, "y": 610},
                                                        {"x": 100, "y": 590},
                                                    ],
                                                },
                                                {
                                                    "index": 2,
                                                    "recognized": False,
                                                    "detected_text": "Llanow...",
                                                    "name": None,
                                                    "confidence": 0.41,
                                                    "scryfall_id": None,
                                                    "set_name": None,
                                                    "set_code": None,
                                                    "collector_number": None,
                                                    "image_url": None,
                                                    "scryfall_url": None,
                                                    "prices": None,
                                                    "polygon": [
                                                        {"x": 510, "y": 90},
                                                        {"x": 840, "y": 120},
                                                        {"x": 825, "y": 600},
                                                        {"x": 495, "y": 580},
                                                    ],
                                                },
                                            ],
                                        },
                                    },
                                    "empty": {
                                        "summary": "Sin cartas detectadas",
                                        "value": {
                                            "cards_detected": 0,
                                            "cards_recognized": 0,
                                            "processing_time_ms": 480,
                                            "cards": [],
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "400": {"$ref": "#/components/responses/MissingOrInvalidImage"},
                    "413": {"$ref": "#/components/responses/ImageTooLarge"},
                    "415": {"$ref": "#/components/responses/UnsupportedImageType"},
                    "429": {"$ref": "#/components/responses/RateLimitExceeded"},
                    "500": {"$ref": "#/components/responses/RecognitionError"},
                    "503": {"$ref": "#/components/responses/ScryfallUnavailable"},
                },
            }
        },
    },
    "components": {
        "schemas": {
            "ApiInfo": {
                "type": "object",
                "required": ["name", "status", "endpoints"],
                "properties": {
                    "name": {"type": "string"},
                    "status": {"type": "string", "example": "ok"},
                    "endpoints": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
            },
            "Health": {
                "type": "object",
                "required": ["status"],
                "properties": {"status": {"type": "string", "example": "ok"}},
            },
            "Point": {
                "type": "object",
                "required": ["x", "y"],
                "properties": {
                    "x": {"type": "integer", "example": 120},
                    "y": {"type": "integer", "example": 85},
                },
            },
            "RecognizedCard": {
                "type": "object",
                "required": [
                    "index",
                    "recognized",
                    "detected_text",
                    "name",
                    "confidence",
                    "scryfall_id",
                    "set_name",
                    "set_code",
                    "collector_number",
                    "image_url",
                    "scryfall_url",
                    "prices",
                    "polygon",
                ],
                "properties": {
                    "index": {"type": "integer", "example": 1},
                    "recognized": {"type": "boolean", "example": True},
                    "detected_text": {"type": "string", "example": "Sol Ring"},
                    "name": {
                        "type": "string",
                        "nullable": True,
                        "example": "Sol Ring",
                    },
                    "confidence": {
                        "type": "number",
                        "format": "float",
                        "minimum": 0,
                        "maximum": 1,
                        "example": 0.96,
                    },
                    "scryfall_id": {
                        "type": "string",
                        "nullable": True,
                        "example": "scryfall-id",
                    },
                    "set_name": {
                        "type": "string",
                        "nullable": True,
                        "example": "Commander Masters",
                    },
                    "set_code": {
                        "type": "string",
                        "nullable": True,
                        "example": "cmm",
                    },
                    "collector_number": {
                        "type": "string",
                        "nullable": True,
                        "example": "396",
                    },
                    "image_url": {
                        "type": "string",
                        "nullable": True,
                        "format": "uri",
                    },
                    "scryfall_url": {
                        "type": "string",
                        "nullable": True,
                        "format": "uri",
                    },
                    "prices": {
                        "type": "object",
                        "nullable": True,
                        "additionalProperties": True,
                    },
                    "polygon": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Point"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                },
            },
            "RecognitionResponse": {
                "type": "object",
                "required": [
                    "cards_detected",
                    "cards_recognized",
                    "processing_time_ms",
                    "cards",
                ],
                "properties": {
                    "cards_detected": {"type": "integer", "minimum": 0},
                    "cards_recognized": {"type": "integer", "minimum": 0},
                    "processing_time_ms": {"type": "integer", "minimum": 0},
                    "cards": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/RecognizedCard"},
                    },
                },
            },
            "ErrorResponse": {
                "type": "object",
                "required": ["error"],
                "properties": {
                    "error": {
                        "type": "object",
                        "required": ["code", "message"],
                        "properties": {
                            "code": {"type": "string", "example": "INVALID_IMAGE"},
                            "message": {
                                "type": "string",
                                "example": "El archivo enviado no es una imagen valida.",
                            },
                        },
                    }
                },
            },
        },
        "responses": {
            "MissingOrInvalidImage": {
                "description": "Imagen ausente o invalida",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "examples": {
                            "missing": {
                                "value": {
                                    "error": {
                                        "code": "MISSING_IMAGE",
                                        "message": "Debe enviar una imagen en el campo 'image'.",
                                    }
                                }
                            },
                            "invalid": {
                                "value": {
                                    "error": {
                                        "code": "INVALID_IMAGE",
                                        "message": "El archivo enviado no es una imagen valida.",
                                    }
                                }
                            },
                        },
                    }
                },
            },
            "ImageTooLarge": {
                "description": "Imagen demasiado grande",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": {
                                "code": "IMAGE_TOO_LARGE",
                                "message": "La imagen excede el tamano maximo permitido.",
                            }
                        },
                    }
                },
            },
            "UnsupportedImageType": {
                "description": "Tipo de imagen no soportado",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": {
                                "code": "UNSUPPORTED_IMAGE_TYPE",
                                "message": "Solo se aceptan imagenes JPG, JPEG, PNG o WebP.",
                            }
                        },
                    }
                },
            },
            "RateLimitExceeded": {
                "description": "Limite de frecuencia excedido",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                },
            },
            "RecognitionError": {
                "description": "Error interno de reconocimiento",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                },
            },
            "ScryfallUnavailable": {
                "description": "Scryfall no disponible",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                },
            },
        },
    },
}
