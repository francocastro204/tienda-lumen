"""Texto de los mensajes. Gemini a veces devuelve una lista de bloques."""

from typing import Any

from app.state import EstadoOrquestador


def texto_de(mensaje: Any) -> str:
    contenido = getattr(mensaje, "content", mensaje)
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for bloque in contenido:
            if isinstance(bloque, dict):
                partes.append(str(bloque.get("text") or ""))
            else:
                partes.append(str(bloque))
        return "".join(partes)
    return str(contenido)


def pregunta_de(state: EstadoOrquestador) -> str:
    for mensaje in state.get("messages") or []:
        if getattr(mensaje, "type", "") == "human":
            return texto_de(mensaje)
    return ""
