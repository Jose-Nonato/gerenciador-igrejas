from fastapi import APIRouter

from schemas import UserOut
from views.dependencies import CurrentUser

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(user: CurrentUser):
    return user
