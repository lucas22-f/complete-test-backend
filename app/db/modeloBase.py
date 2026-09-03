from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Clase base para todos nuestros modelos SQLAlchemy.

    Más adelante probablemente la moveremos a app/db/base.py,
    porque no debería pertenecer específicamente a Conversation.
    Por ahora la dejamos acá para entender primero el concepto.
    """

    pass