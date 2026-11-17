"""Cinco solicitudes. La primera que se pausa se rechaza. La segunda se aprueba."""

import asyncio
import json
import os
import urllib.request

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")

CASOS = [
    "Pedrito compró el FIFA 26 en caja a 21000 pesos hace 9 días. El código de activación no se canjeó. ¿Corresponde la devolución?",
    "Ana compró un juego digital de 14500 pesos hace 12 días. El código no se canjeó. ¿Corresponde la devolución?",
    "Luis compró un juego digital de 8000 pesos hace 3 días. El código de activación no se canjeó. ¿Corresponde la devolución?",
    "Marta compró un juego en caja de 18000 pesos hace 10 días. El código ya se canjeó. ¿Corresponde la devolución?",
    "Sofía compró un juego digital de 19000 pesos hace 5 días. El código no se canjeó. ¿Corresponde la devolución?",
]


def pedir(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


pausas = {"n": 0}
candado = asyncio.Lock()


async def uno(query: str, indice: int) -> None:
    alta = await asyncio.to_thread(pedir, "POST", "/tasks", {"query": query})
    job_id = alta["job_id"]
    print(f"{indice} encolado {job_id[:8]} {alta['status']}", flush=True)
    ya_decidido = False
    for _ in range(90):
        await asyncio.sleep(2)
        estado = await asyncio.to_thread(pedir, "GET", f"/tasks/{job_id}")
        if estado["status"] not in {"DONE", "FAILED", "WAITING_APPROVAL"}:
            continue
        if estado["status"] == "WAITING_APPROVAL":
            if ya_decidido:
                continue
            ya_decidido = True
            async with candado:
                aprobado = pausas["n"] > 0
                pausas["n"] += 1
            print(f"{indice} pausa, aprobado={aprobado}", flush=True)
            await asyncio.to_thread(
                pedir, "POST", f"/tasks/{job_id}/approve", {"aprobado": aprobado}
            )
            continue
        texto = estado.get("result") or estado.get("error") or ""
        print(f"{indice} {estado['status']} {texto[:180]}", flush=True)
        return
    print(f"{indice} siguió en curso", flush=True)


async def main() -> None:
    await asyncio.gather(*(uno(caso, i) for i, caso in enumerate(CASOS)))


if __name__ == "__main__":
    asyncio.run(main())
