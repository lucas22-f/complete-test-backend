from app.core.security import create_access_token,hash_password,verify_password
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate,UserResponse

class AuthService:
    def __init__(self,repository:UserRepository):
        self.repository = repository

    def register(self,request:UserCreate) ->UserResponse | None:
        existing_user = self.repository.get_by_email(request.email)
        if existing_user:
            return None

        hashed = hash_password(request.password)

        user = self.repository.create(email=request.email,hashed_password=hashed)

        return UserResponse(id=user.id,email=user.email,is_active=user.is_active,role=user.role,created_at=user.created_at)

    def authenticate(self,email:str,password:str) -> TokenResponse | None:

        user = self.repository.get_by_email(email)

        if user is None:
            return None
        if not user.is_active:
            return None
        if not verify_password(password,user.hashed_password):
            return None

        access_token = create_access_token(user.id)

        return TokenResponse(access_token=access_token)
