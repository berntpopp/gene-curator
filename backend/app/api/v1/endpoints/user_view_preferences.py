"""The signed-in user's saved views: only ever their own (#276)."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.crud.scope_visibility import visible_scope_ids
from app.models import UserNew
from app.models.user_view_preference import UserViewPreference
from app.schemas.user_view_preference import CatalogueView

router = APIRouter()

CATALOGUE = "catalogue"


@router.get("/catalogue", response_model=CatalogueView)
def get_catalogue_view(
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CatalogueView:
    """Your saved catalogue columns; empty when you have not chosen any."""
    pref = db.get(UserViewPreference, (current_user.id, CATALOGUE))
    return CatalogueView.model_validate(pref.value if pref else {})


@router.put("/catalogue", response_model=CatalogueView)
def save_catalogue_view(
    view: CatalogueView,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> CatalogueView:
    """Save your catalogue columns as your default view: scopes you can see, each once."""
    visible = set(db.scalars(visible_scope_ids(current_user.id)))
    view = CatalogueView(
        scope_ids=[i for i in dict.fromkeys(view.scope_ids) if i in visible]
    )
    value = view.model_dump(mode="json")
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    stmt = insert(UserViewPreference).values(
        user_id=current_user.id, view=CATALOGUE, value=value
    )
    # an upsert, so two first saves racing both succeed (last write wins)
    db.execute(
        stmt.on_conflict_do_update(
            index_elements=["user_id", "view"],
            set_={"value": stmt.excluded.value, "updated_at": func.now()},
        )
    )
    db.commit()
    return view
