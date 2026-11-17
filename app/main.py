"""API. El request encola y devuelve el id. El grafo corre en el worker."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from redis import asyncio as aioredis
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.config import redis_url
from app.graph import construir
from app.observability import iniciar
from app.rag import ingestar
from app.schemas import Decision, EstadoJob, Pedido
from app.worker import bucle, crear, leer, reanudar


@asynccontextmanager
async def vida(app: FastAPI):
    iniciar()
    await asyncio.to_thread(ingestar)
    app.state.redis = aioredis.from_url(
        redis_url(), decode_responses=True, socket_timeout=None
    )
    app.state.checkpointer = AsyncRedisSaver(redis_url=redis_url())
    await app.state.checkpointer.asetup()
    app.state.graph = construir(app.state.checkpointer)
    app.state.fondo = set()
    tarea = asyncio.create_task(bucle(app.state.redis, app.state.graph))
    try:
        yield
    finally:
        tarea.cancel()
        await app.state.redis.aclose()


app = FastAPI(title="Tienda Lumen", lifespan=vida)


@app.post("/tasks", response_model=EstadoJob)
async def crear_tarea(pedido: Pedido):
    dato = await crear(app.state.redis, pedido.query)
    return {"query": pedido.query, "result": None, "error": None, "pregunta": None, **dato}


@app.get("/tasks/{job_id}", response_model=EstadoJob)
async def estado(job_id: str):
    dato = await leer(app.state.redis, job_id)
    if dato is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return {"job_id": job_id, **dato}


@app.post("/tasks/{job_id}/approve", response_model=EstadoJob)
async def aprobar(job_id: str, decision: Decision):
    dato = await leer(app.state.redis, job_id)
    if dato is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if dato["status"] != "WAITING_APPROVAL":
        raise HTTPException(status_code=409, detail="Ese job no está esperando aprobación")
    tarea = asyncio.create_task(
        reanudar(app.state.redis, app.state.graph, job_id, decision.aprobado)
    )
    app.state.fondo.add(tarea)
    tarea.add_done_callback(app.state.fondo.discard)
    return {"job_id": job_id, **dato, "status": "RUNNING"}
