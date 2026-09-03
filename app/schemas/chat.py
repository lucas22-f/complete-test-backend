from pydantic import BaseModel, Field


# Modelo de entrada del endpoint de chat.
# Representa los datos que esperamos recibir del cliente.
class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


# Modelo de salida del endpoint de chat.
# Representa exactamente la estructura que queremos exponer al cliente.
class ChatResponse(BaseModel):
    thread_id: str
    answer: str