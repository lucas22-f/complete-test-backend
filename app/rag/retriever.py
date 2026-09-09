"""Construye y consulta el índice vectorial persistente del FAQ de ecommerce.

Este módulo no genera respuestas: prepara contexto relevante para que el nodo
RAG del grafo se lo entregue al modelo junto con la pregunta del usuario.
"""

from pathlib import Path

import pymupdf
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Las rutas se calculan desde este archivo y no desde el directorio actual del
# proceso. Así funcionan igual desde Uvicorn, tests o el contenedor Docker.
ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "data" / "ecommerce_faq.pdf"
# Chroma guarda aquí sus vectores y metadatos para no re-crear el índice en cada
# reinicio. Docker monta este directorio como volumen persistente.
PERSIST_DIRECTORY = ROOT / "vector_store"
COLLECTION_NAME = "ecommerce_faq"


def _load_pdf_pages() -> list[Document]:
    """Extrae cada página del PDF y conserva metadatos para citarla después."""
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"RAG PDF not found: {PDF_PATH}")
    # ``with`` cierra el archivo aunque la extracción falle a mitad de camino.
    with pymupdf.open(PDF_PATH) as pdf:
        return [
            Document(
                page_content=page.get_text("text"),
                # Estos metadatos no participan del embedding, pero permiten que
                # el frontend diga qué PDF y página respaldan la respuesta.
                metadata={"source": PDF_PATH.name, "page": page.number + 1},
            )
            for page in pdf
            if page.get_text("text").strip()
        ]


def build_retriever(api_key: str, k: int = 3):
    """Crea el retriever e indexa el PDF sólo cuando la colección está vacía.

    Un embedding representa el significado de un fragmento como números. Chroma
    compara el embedding de la pregunta contra esos vectores y devuelve los ``k``
    fragmentos semánticamente más cercanos.
    """
    # La clave se usa únicamente para pedir embeddings a OpenAI; no se persiste
    # en Chroma ni se devuelve al cliente.
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(PERSIST_DIRECTORY),
    )
    # La primera consulta crea los embeddings. Luego el índice persistido evita
    # repetir ese costo mientras el PDF y la colección sigan siendo los mismos.
    if store._collection.count() == 0:
        # Los fragmentos se solapan para no cortar una política justo en el límite
        # entre dos chunks y perder contexto relevante.
        splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
        store.add_documents(splitter.split_documents(_load_pdf_pages()))
    # El retriever oculta la búsqueda vectorial detrás de ``invoke``/``ainvoke``.
    return store.as_retriever(search_kwargs={"k": k})


async def retrieve_context(api_key: str, question: str) -> tuple[str, list[dict]]:
    """Devuelve contexto para el modelo y fuentes públicas de una pregunta.

    La tupla separa dos responsabilidades: ``context`` se inyecta al prompt del
    modelo y ``sources`` se envía por SSE al cliente. Así no se mezclan detalles
    de presentación con las instrucciones que recibe el LLM.
    """
    # ``ainvoke`` usa la interfaz asíncrona del retriever y permite esperarlo con
    # ``await`` desde el nodo RAG del grafo.
    documents = await build_retriever(api_key).ainvoke(question)
    sources = [
        {"source": document.metadata["source"], "page": document.metadata["page"]}
        for document in documents
    ]
    # Se etiqueta cada fragmento para que el modelo sepa de dónde proviene. Estas
    # etiquetas también facilitan depurar una respuesta que no esté bien fundada.
    context = "\n\n".join(
        f"[Source: {source['source']}, page {source['page']}]\n{document.page_content}"
        for document, source in zip(documents, sources, strict=True)
    )
    return context, sources
