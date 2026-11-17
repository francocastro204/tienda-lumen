"""Trazas hacia Phoenix. Si el colector no está, la API igual arranca."""

from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.otel import register

from app.config import phoenix_endpoint, phoenix_proyecto


def iniciar() -> None:
    try:
        proveedor = register(
            project_name=phoenix_proyecto(),
            endpoint=phoenix_endpoint(),
        )
        LangChainInstrumentor().instrument(tracer_provider=proveedor)
        GoogleGenAIInstrumentor().instrument(tracer_provider=proveedor)
    except Exception as error:
        print(f"Phoenix no quedó conectado: {error}", flush=True)
