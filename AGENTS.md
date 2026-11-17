Proyecto: Tienda Lumen, entrega final de Coderhouse. Repo público https://github.com/francocastro204/tienda-lumen. Carpeta local /Users/franco/developer/tienda-lumen. El repo del curso (/Users/franco/developer/coderhouse-ai) no se toca.

Qué es: un asistente de devoluciones. Lumen vende el mismo juego en copia digital o en caja. Las dos traen código de activación. "Sin uso" = el código no se canjeó. No hay base de pedidos ni de clientes: el monto, los días y el código vienen escritos en la pregunta.

Reglas, sin cambiar los números:
- Devolución: hasta 10 días, hasta 20000 pesos, código sin canjear.
- Envío: gratis desde 15000 pesos; si no, 2500. Solo si el pedido incluye una caja.
- Garantía: 90 días por falla de fábrica. No cubre golpes ni humedad.

Arquitectura ya armada:
- POST /tasks encola y devuelve job_id. GET /tasks/{id}. POST /tasks/{id}/approve.
- Redis guarda el estado (PENDING, RUNNING, WAITING_APPROVAL, DONE, FAILED) y el checkpointer de LangGraph.
- Grafo: supervisor, investigador (RAG en Chroma, data/*.md), analista (Pydantic, validar_reembolso), validación, pausa humana si el veredicto empieza con "Corresponde", síntesis.
- Phoenix, proyecto tienda-lumen. Capturas en screenshots/: trazas.png, latencia-p95.png (p95 cerca de 21 s), costo.png (bajo $0.01).
- Arranque previsto: ./run.sh (docker compose). En esta Mac no hay Docker. Redis ya está en 6379 (con RediSearch y ReJSON) y Phoenix en http://127.0.0.1:6006.
- La API de Tienda Lumen está en http://127.0.0.1:8001. El puerto 8000 es la pre-entrega 7 del curso, no este proyecto.
- Modelo que funciona: gemini-flash-lite-latest, temperature 0, max_retries 0, timeout 45. gemini-3.1-flash-lite se queda sin cupo (429). Embeddings: gemini-embedding-001, sin task_type.
- Perfil git: personal, francocastro204. No usar la cuenta del banco.

Estado de las cinco pruebas: plazo vencido y código canjeado respondieron "No corresponde". Una pausa se rechazó y otra se aprobó. El resto quedó FAILED por 429 de Gemini. Eso es el cupo, no un bug del grafo.

El `.env` local ya existe y está en `.gitignore`. Tiene `GEMINI_API_KEY` y `GEMINI_MODEL=gemini-flash-lite-latest`. No copies el `.env` entero del curso: ese archivo trae `gemini-3.1-flash-lite` y las llamadas vuelven a caer en 429. No uses `HF_TOKEN` ni `HF_MODEL`: este proyecto no llama a Hugging Face.
