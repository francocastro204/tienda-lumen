"""Investigador y analista. Cada uno tiene una sola herramienta."""

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from app.rag import buscar_async


class BusquedaInput(BaseModel):
    consulta: str = Field(..., description="Tema a buscar, por ejemplo devoluciones")


class ValidacionInput(BaseModel):
    dias: int = Field(..., description="Días desde la compra, según la pregunta")
    monto: int = Field(..., description="Monto del producto, según la pregunta")
    plazo_dias: int = Field(..., description="Días que permite la política")
    tope: int = Field(..., description="Monto máximo que permite la política")
    codigo_canjeado: bool = Field(
        ...,
        description="True si el código de activación ya se canjeó",
    )


def juzgar(
    dias: int,
    monto: int,
    plazo_dias: int,
    tope: int,
    codigo_canjeado: bool,
) -> str:
    """Aplica la política de devoluciones. No busca el texto."""
    motivos: list[str] = []
    if dias > plazo_dias:
        motivos.append(f"pasó el plazo: van {dias} días y el límite es {plazo_dias}")
    if monto > tope:
        motivos.append(f"el monto {monto} supera el tope {tope}")
    if codigo_canjeado:
        motivos.append("el código de activación ya se canjeó")
    if not motivos:
        return (
            f"Corresponde. {dias} días está dentro de {plazo_dias}, "
            f"{monto} está dentro del tope {tope} y el código no se canjeó."
        )
    return f"No corresponde. {' '.join(motivos)}."


@tool(args_schema=BusquedaInput)
async def buscar_politica(consulta: str) -> str:
    """Busca una política de Tienda Lumen. No decide el caso."""
    return await buscar_async(consulta)


@tool(args_schema=ValidacionInput)
def validar_reembolso(
    dias: int,
    monto: int,
    plazo_dias: int,
    tope: int,
    codigo_canjeado: bool,
) -> str:
    """Compara el caso con el plazo, el tope y el uso del código."""
    return juzgar(dias, monto, plazo_dias, tope, codigo_canjeado)


PROMPT_INVESTIGADOR = (
    "Sos el investigador de Tienda Lumen. "
    "Tu única herramienta es buscar_politica. "
    "Buscá y copiá lo que dice la base, con los números. "
    "No digas si el reembolso corresponde. "
    "Si la herramienta no encuentra nada, respondé exactamente: No encontré una política."
)

PROMPT_ANALISTA = (
    "Sos el analista de Tienda Lumen. No busques políticas. "
    "Tu única herramienta es validar_reembolso. "
    "Sacá los días y el monto de la pregunta del usuario. "
    "Sacá plazo_dias y tope del texto del investigador. "
    "codigo_canjeado es true solo si la pregunta dice que el código se canjeó "
    "o que el juego ya se activó. Si dice que no se usó, es false. "
    "Si falta un número o no se sabe el código, no inventes: respondé exactamente Faltan números. "
    "Cuando la herramienta responda, repetí su frase sin cambiar el veredicto."
)


def crear_investigador(modelo):
    return create_react_agent(
        modelo,
        [buscar_politica],
        prompt=PROMPT_INVESTIGADOR,
        name="investigador",
    )


def crear_analista(modelo):
    return create_react_agent(
        modelo,
        [validar_reembolso],
        prompt=PROMPT_ANALISTA,
        name="analista",
    )
