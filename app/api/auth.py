from fastapi import APIRouter,Depends,HTTPException,status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.dependencies import db_get
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate,UserResponse
from app.services.auth import AuthService


router = APIRouter()


def build_service(db:Session)->AuthService:
    return AuthService(
        UserRepository(db)
    )

@router.post("/auth/register",response_model=UserResponse,status_code=status.HTTP_201_CREATED)
def register(request:UserCreate,db:Session = Depends(db_get)):
    service = build_service(db)

    user = service.register(request)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )    

    return user

@router.post("/auth/login",response_model=TokenResponse)
def login(form:OAuth2PasswordRequestForm = Depends(),db:Session = Depends(db_get)):
    service = build_service(db)

    token = service.authenticate(email=form.username,password=form.password)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={
                "WWW-Authenticate":"Bearer"
            }
        )

    return token



