"""Políticas en Chroma. Indexar y buscar usan el mismo embedding."""

import asyncio

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHROMA_DIR, DATOS, clave_gemini, embedding_nombre

COLECCION = "politicas"


def embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=embedding_nombre(),
        google_api_key=clave_gemini(),
    )


def abrir() -> Chroma:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLECCION,
        embedding_function=embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def _documentos() -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    documentos = []
    for ruta in sorted(DATOS.glob("*.md")):
        documentos.extend(
            splitter.split_documents(
                [
                    Document(
                        page_content=ruta.read_text(encoding="utf-8"),
                        metadata={"fuente": ruta.name},
                    )
                ]
            )
        )
    if not documentos:
        raise RuntimeError(f"No hay políticas en {DATOS}")
    return documentos


def ingestar() -> Chroma:
    base = abrir()
    if base._collection.count() > 0:
        return base
    base.add_documents(_documentos())
    return base


def buscar(consulta: str) -> str:
    base = abrir()
    encontrados = base.similarity_search(consulta, k=2)
    if not encontrados:
        return "No encontré una política para esa consulta."
    partes = []
    for doc in encontrados:
        fuente = doc.metadata.get("fuente", "política")
        partes.append(f"[{fuente}]\n{doc.page_content.strip()}")
    return "\n\n".join(partes)


async def buscar_async(consulta: str) -> str:
    return await asyncio.to_thread(buscar, consulta)
