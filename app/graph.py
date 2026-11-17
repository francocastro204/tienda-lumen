"""Grafo: supervisor, investigador, analista, validación y pausa humana."""

import warnings
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents import crear_analista, crear_investigador
from app.config import clave_gemini, modelo_nombre
from app.graph_texto import pregunta_de, texto_de
from app.hitl import nodo_aprobacion, ruta_aprobacion
from app.state import EstadoOrquestador

warnings.filterwarnings("ignore", message="create_react_agent has been moved")

MAX_PASOS = 6
MAX_POR_AGENTE = 2

PROMPT_SUPERVISOR = (
    "Sos el supervisor de Tienda Lumen. No respondas al cliente y no calcules. "
    "Elegí un solo siguiente: "
    "investigador si falta la política, "
    "analista si ya está la política y falta el veredicto, "
    "finalizar solo si los dos ya usaron su herramienta. "
    "La instruccion es una frase para ese especialista. "
    "Si elegís finalizar, dejá la instruccion vacía."
)

PROMPT_SINTESIS = (
    "Escribí la respuesta final en español, en máximo 4 líneas. "
    "Usá solo los aportes. El veredicto es el del analista. "
    "La política es la del investigador. Si un aporte falta, decilo. "
    "No inventes otros plazos ni otros montos."
)


class DecisionSupervisor(BaseModel):
    siguiente: Literal["investigador", "analista", "finalizar"]
    instruccion: str = Field(default="", description="Qué debe hacer el especialista")


def modelo_chat():
    return ChatGoogleGenerativeAI(
        model=modelo_nombre(),
        google_api_key=clave_gemini(),
        temperature=0,
        max_retries=0,
        request_timeout=45,
    )


def faltante(state: EstadoOrquestador) -> str | None:
    """El análisis solo cuenta si llegó después de una búsqueda con herramienta."""
    investigo = False
    analizo_despues = False
    usos_investigador = 0
    usos_analista = 0
    for aporte in state.get("aportes") or []:
        if aporte["agente"] == "investigador":
            usos_investigador += 1
            if "buscar_politica" in aporte["herramientas"]:
                investigo = True
        elif aporte["agente"] == "analista":
            usos_analista += 1
            if investigo and "validar_reembolso" in aporte["herramientas"]:
                analizo_despues = True
    if not investigo and usos_investigador < MAX_POR_AGENTE:
        return "investigador"
    if not analizo_despues and usos_analista < MAX_POR_AGENTE:
        return "analista"
    return None


def instruccion_por_defecto(agente: str) -> str:
    if agente == "analista":
        return (
            "Tomá el plazo y el tope del investigador, y los días, el monto "
            "y el código de la pregunta. Llamá a validar_reembolso."
        )
    return "Buscá en la base la política que aplica a la pregunta. No decidas el caso."


def resumen_aportes(state: EstadoOrquestador) -> str:
    aportes = state.get("aportes") or []
    if not aportes:
        return "Todavía no hay aportes."
    lineas = []
    for aporte in aportes:
        herramientas = ", ".join(aporte["herramientas"]) or "ninguna"
        lineas.append(f"- {aporte['agente']} ({herramientas}): {aporte['texto']}")
    return "\n".join(lineas)


def llamadas_de(mensajes: list[Any]) -> list[str]:
    nombres = []
    for mensaje in mensajes:
        for llamada in getattr(mensaje, "tool_calls", None) or []:
            nombre = llamada.get("name")
            if nombre:
                nombres.append(nombre)
    return nombres


def _usos(state: EstadoOrquestador, agente: str) -> int:
    return sum(1 for aporte in state.get("aportes") or [] if aporte["agente"] == agente)


def construir(checkpointer):
    investigador = crear_investigador(modelo_chat())
    analista = crear_analista(modelo_chat())
    supervisor_modelo = modelo_chat().with_structured_output(DecisionSupervisor)
    sintesis_modelo = modelo_chat()

    async def nodo_supervisor(state: EstadoOrquestador) -> dict[str, Any]:
        pasos = state.get("pasos", 0) + 1
        if pasos > MAX_PASOS:
            return _cierre(state, pasos)
        instruccion = ""
        try:
            decision = await supervisor_modelo.ainvoke(
                [
                    SystemMessage(content=PROMPT_SUPERVISOR),
                    HumanMessage(
                        content=(
                            f"Pregunta:\n{pregunta_de(state)}\n\n"
                            f"Aportes:\n{resumen_aportes(state)}"
                        )
                    ),
                ]
            )
            elegido = decision.siguiente
            instruccion = (decision.instruccion or "").strip()
        except Exception:
            elegido = faltante(state) or "finalizar"

        falta = faltante(state)
        if falta is None:
            elegido = "finalizar"
        elif elegido != falta:
            elegido = falta
            instruccion = instruccion_por_defecto(falta)
        elif _usos(state, elegido) >= MAX_POR_AGENTE:
            elegido = falta if _usos(state, falta) < MAX_POR_AGENTE else "finalizar"

        if elegido == "finalizar":
            return _cierre(state, pasos)
        if not instruccion:
            instruccion = instruccion_por_defecto(elegido)
        return {
            "pasos": pasos,
            "next_agent": elegido,
            "task_completed": False,
            "instruccion": instruccion,
            "ruta": ["supervisor"],
            "messages": [
                AIMessage(
                    content=f"Supervisor envía a {elegido}: {instruccion}",
                    name="supervisor",
                )
            ],
        }

    def _cierre(state: EstadoOrquestador, pasos: int) -> dict[str, Any]:
        return {
            "pasos": pasos,
            "next_agent": "finalizar",
            "task_completed": faltante(state) is None,
            "instruccion": "",
            "ruta": ["supervisor"],
            "messages": [AIMessage(content="Supervisor envía a validar.", name="supervisor")],
        }

    async def nodo_investigador(state: EstadoOrquestador) -> dict[str, Any]:
        instruccion = state.get("instruccion") or instruccion_por_defecto("investigador")
        return await _correr_especialista(
            investigador,
            "investigador",
            f"Pregunta del usuario:\n{pregunta_de(state)}\n\nTu tarea:\n{instruccion}",
        )

    async def nodo_analista(state: EstadoOrquestador) -> dict[str, Any]:
        instruccion = state.get("instruccion") or instruccion_por_defecto("analista")
        dato = "Todavía no hay dato del investigador."
        for aporte in reversed(state.get("aportes") or []):
            if aporte["agente"] == "investigador":
                dato = aporte["texto"]
                break
        return await _correr_especialista(
            analista,
            "analista",
            (
                f"Pregunta del usuario:\n{pregunta_de(state)}\n\n"
                f"Dato del investigador:\n{dato}\n\n"
                f"Tu tarea:\n{instruccion}"
            ),
        )

    def nodo_validar(state: EstadoOrquestador) -> dict[str, Any]:
        falta = faltante(state)
        if state.get("pasos", 0) > MAX_PASOS:
            falta = None
        if falta:
            instruccion = instruccion_por_defecto(falta)
            return {
                "next_agent": falta,
                "task_completed": False,
                "instruccion": instruccion,
                "ruta": ["validar"],
                "messages": [
                    AIMessage(
                        content=f"Validación: falta {falta}. {instruccion}",
                        name="validar",
                    )
                ],
            }
        return {
            "next_agent": "sintesis",
            "task_completed": True,
            "ruta": ["validar"],
            "messages": [
                AIMessage(
                    content="Validación: hay búsqueda y análisis. Se puede cerrar.",
                    name="validar",
                )
            ],
        }

    async def nodo_sintesis(state: EstadoOrquestador) -> dict[str, Any]:
        try:
            respuesta = await sintesis_modelo.ainvoke(
                [
                    SystemMessage(content=PROMPT_SINTESIS),
                    HumanMessage(
                        content=(
                            f"Pregunta:\n{pregunta_de(state)}\n\n"
                            f"Aportes:\n{resumen_aportes(state)}"
                        )
                    ),
                ]
            )
            texto = texto_de(respuesta).strip()
        except Exception as error:
            texto = (
                f"No pude redactar la síntesis ({error.__class__.__name__}).\n"
                f"{resumen_aportes(state)}"
            )
        return {
            "ruta": ["sintesis"],
            "messages": [AIMessage(content=texto, name="sintesis")],
        }

    workflow = StateGraph(EstadoOrquestador)
    workflow.add_node("supervisor", nodo_supervisor)
    workflow.add_node("investigador", nodo_investigador)
    workflow.add_node("analista", nodo_analista)
    workflow.add_node("validar", nodo_validar)
    workflow.add_node("aprobacion", nodo_aprobacion)
    workflow.add_node("sintesis", nodo_sintesis)
    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        ruta_supervisor,
        {"investigador": "investigador", "analista": "analista", "validar": "validar"},
    )
    workflow.add_edge("investigador", "supervisor")
    workflow.add_edge("analista", "supervisor")
    workflow.add_conditional_edges(
        "validar",
        ruta_validar,
        {"investigador": "investigador", "analista": "analista", "sintesis": "aprobacion"},
    )
    workflow.add_conditional_edges(
        "aprobacion",
        ruta_aprobacion,
        {"sintesis": "sintesis", "fin": END},
    )
    workflow.add_edge("sintesis", END)
    return workflow.compile(checkpointer=checkpointer)


def ruta_supervisor(state: EstadoOrquestador) -> Literal["investigador", "analista", "validar"]:
    elegido = state.get("next_agent")
    if elegido == "analista":
        return "analista"
    if elegido == "finalizar":
        return "validar"
    return "investigador"


def ruta_validar(state: EstadoOrquestador) -> Literal["investigador", "analista", "sintesis"]:
    elegido = state.get("next_agent")
    if elegido == "investigador":
        return "investigador"
    if elegido == "analista":
        return "analista"
    return "sintesis"


async def _correr_especialista(agente, nombre: str, contenido: str) -> dict[str, Any]:
    resultado = await agente.ainvoke(
        {"messages": [HumanMessage(content=contenido)]},
        {"recursion_limit": 8},
    )
    mensajes = resultado["messages"]
    return {
        "aportes": [
            {
                "agente": nombre,
                "texto": texto_de(mensajes[-1]).strip(),
                "herramientas": llamadas_de(mensajes),
            }
        ],
        "ruta": [nombre],
        "messages": [AIMessage(content=texto_de(mensajes[-1]).strip(), name=nombre)],
    }
