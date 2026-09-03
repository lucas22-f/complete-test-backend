from app.schemas.chat import ChatResponse,ChatRequest


class ChatService:
    """
    Servicio encargado de la lógica de aplicación relacionada con chat.

    El router no debería saber cómo se genera una respuesta.
    Su responsabilidad es recibir HTTP y delegar la operación.
    """
    def procesar_mensaje(self,request:ChatRequest) -> ChatResponse:
        """
        Procesa un mensaje de chat.

        Por ahora simulamos la respuesta.
        Más adelante este método será el punto donde
        conectaremos LangGraph.

        """

        return ChatResponse(
            thread_id=request.thread_id,
            answer=f"Mensaje recibido: {request.message}"
        )