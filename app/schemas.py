"""Contratos de la API."""

from typing import Literal

from pydantic import BaseModel, Field


class Pedido(BaseModel):
    query: str = Field(..., min_length=1, description="El caso, escrito por quien atiende")


class Decision(BaseModel):
    aprobado: bool


class EstadoJob(BaseModel):
    job_id: str
    status: Literal["PENDING", "RUNNING", "WAITING_APPROVAL", "DONE", "FAILED"]
    query: str | None = None
    result: str | None = None
    error: str | None = None
    pregunta: str | None = None
