"""Pausa el grafo si el reembolso saldría. Si no corresponde, no hay plata en juego."""

from typing import Any, Literal

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from app.graph_texto import pregunta_de


def es_critico(state: dict) -> bool:
    """Corresponde pagar. «No corresponde» no entra: no empieza con «corresponde»."""
    for aporte in reversed(state.get("aportes") or []):
        if aporte.get("agente") != "analista":
            continue
        texto = (aporte.get("texto") or "").strip().lower()
        return texto.startswith("corresponde")
    return False


def nodo_aprobacion(state: dict) -> dict[str, Any]:
    if not es_critico(state):
        return {"aprobado": True, "ruta": ["aprobacion"]}

    decision = interrupt(
        {
            "pregunta": "El analista dice que corresponde el reembolso. ¿Lo aprobás?",
            "caso": pregunta_de(state),
        }
    )
    if decision == "si":
        return {"aprobado": True, "ruta": ["aprobacion"]}
    return {
        "aprobado": False,
        "ruta": ["aprobacion"],
        "messages": [
            AIMessage(content="Reembolso rechazado por el revisor.", name="aprobacion")
        ],
    }


def ruta_aprobacion(state: dict) -> Literal["sintesis", "fin"]:
    if state.get("aprobado"):
        return "sintesis"
    return "fin"
