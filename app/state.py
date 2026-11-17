"""Estado del grafo. Los aportes se acumulan: un especialista no pisa al otro."""

import operator
from typing import Annotated

from langgraph.graph import MessagesState
from typing_extensions import NotRequired, TypedDict


class Aporte(TypedDict):
    agente: str
    texto: str
    herramientas: list[str]


class EstadoOrquestador(MessagesState):
    next_agent: str
    task_completed: bool
    instruccion: str
    pasos: int
    aportes: Annotated[list[Aporte], operator.add]
    ruta: Annotated[list[str], operator.add]
    aprobado: NotRequired[bool]
