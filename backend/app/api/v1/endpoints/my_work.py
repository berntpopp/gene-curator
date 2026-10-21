"""My Work inbox: the current user's work grouped by next action."""

from typing import get_args

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, set_rls_context
from app.crud.my_work import get_my_work
from app.models import UserNew
from app.schemas.my_work import MyWorkResponse, WorkTab

router = APIRouter()


@router.get("/me/work", response_model=MyWorkResponse)
def read_my_work(
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> MyWorkResponse:
    set_rls_context(db, current_user)
    items = get_my_work(db, current_user)
    counts: dict[WorkTab, int] = {
        t: sum(i.tab == t for i in items) for t in get_args(WorkTab)
    }
    return MyWorkResponse(items=items, counts=counts)
