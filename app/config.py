"""Variables de entorno. Nada de modelos ni URLs escritos en el resto del código."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

DATOS = RAIZ / "data"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", str(RAIZ / "chroma")))


def clave_gemini() -> str:
    valor = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not valor:
        raise RuntimeError("Falta GEMINI_API_KEY en .env")
    return valor


def modelo_nombre() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")


def embedding_nombre() -> str:
    return os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")


def redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379")


def phoenix_endpoint() -> str:
    return os.getenv("PHOENIX_ENDPOINT", "http://127.0.0.1:6006/v1/traces")


def phoenix_proyecto() -> str:
    return os.getenv("PHOENIX_PROJECT", "tienda-lumen")
