from fastapi import APIRouter

from schemas import IgrejaOut, IgrejaUpdate
from views.dependencies import ActiveUser, AdminUser, IgrejaCtrl

router = APIRouter(prefix="/igreja", tags=["igreja"])


@router.get("", response_model=IgrejaOut)
def read_igreja(ator: ActiveUser, controller: IgrejaCtrl):
    return controller.get(ator)


@router.patch("", response_model=IgrejaOut)
def update_igreja(data: IgrejaUpdate, ator: AdminUser, controller: IgrejaCtrl):
    return controller.update(ator, data)
