# app/main.py

from fastapi import FastAPI

# Importamos el router que contiene los endpoints relacionados con chat.
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router


from app.db.database import engine
from app.models.conversation import Base
from app.api.messages import router as messages_router

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from fastapi.middleware.cors import CORSMiddleware


# Esta sigue siendo nuestra única aplicación FastAPI.
app = FastAPI(
    title="AI Support Backend",
    description="Backend de soporte inteligente con FastAPI y LangGraph",
    version="0.1.0",
)


#Base.metadata.create_all(bind=engine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "AI Support Backend funcionando"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# Incluimos las rutas de chat dentro de la aplicación.
#
# prefix="/api/v1" hace que:
#
# router: /chat
#
# termine expuesto como:
#
# /api/v1/chat
app.include_router(chat_router,prefix="/api/v1",tags=["Chat"])
app.include_router(conversations_router,prefix="/api/v1",tags=["Conversations"])
app.include_router( messages_router,prefix="/api/v1",tags=["Messages"])

app.include_router(
    auth_router,
    prefix="/api/v1",
    tags=["Auth"],
)

app.include_router(
    users_router,
    prefix="/api/v1",
    tags=["Users"],
)