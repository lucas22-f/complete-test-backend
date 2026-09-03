# app/api/chat.py

# APIRouter nos permite agrupar endpoints relacionados.
# En este archivo vamos a colocar únicamente endpoints de chat.
from fastapi import APIRouter


# Importamos los contratos de entrada y salida
# desde la capa de schemas.
from app.schemas.chat import ChatRequest,ChatResponse
from app.services.chat import ChatService


# Creamos un router independiente.
router = APIRouter()
chat_service = ChatService()




@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=200,
)
def chat(request: ChatRequest):
    """
    El router se ocupa de HTTP.

    La lógica de procesar el mensaje se delega al service.
    """
    return chat_service.procesar_mensaje(request)