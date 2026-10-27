"""Prompt templates and versions: drafts, diff, publish (#489). Platform admins only.

Published versions are immutable (database trigger); editing one creates a new draft.
Placeholders are plain {name} from the allowlist in app.llm.prompts; no Jinja.
"""

import difflib
import uuid
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin_user
from app.llm.prompts import PromptTemplateError, template_placeholders
from app.models import UserNew
from app.models.llm import PromptTemplate, PromptTemplateVersion
from app.schemas.llm import (
    Revision,
    TemplateCreate,
    TemplateOut,
    VersionCreate,
    VersionDiff,
    VersionOut,
    VersionUpdate,
)
from app.services.llm_config import audit, prompt_sha256, save_revision

router = APIRouter()
Admin = Depends(get_current_admin_user)
CONTENT = ("system_text", "user_text", "output_schema", "few_shot_examples")


def _check_placeholders(fields: dict[str, Any]) -> None:
    try:
        template_placeholders(fields["system_text"])
        template_placeholders(fields["user_text"])
    except PromptTemplateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _version(db: Session, version_id: UUID) -> PromptTemplateVersion:
    row = db.get(PromptTemplateVersion, version_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return row


def _new_draft(
    db: Session,
    user: UserNew,
    template_id: UUID,
    fields: dict[str, Any],
    derived_from: UUID | None = None,
) -> PromptTemplateVersion:
    _check_placeholders(fields)
    number = (
        db.scalar(
            select(func.max(PromptTemplateVersion.version)).where(
                PromptTemplateVersion.template_id == template_id
            )
        )
        or 0
    ) + 1
    draft = PromptTemplateVersion(
        id=uuid.uuid4(),
        template_id=template_id,
        version=number,
        derived_from=derived_from,
        created_by=user.id,
        **fields,
    )
    audit(
        db,
        user,
        "prompt_template_versions",
        draft.id,
        "CREATE",
        {"template_id": template_id, "version": number, "derived_from": derived_from},
    )
    db.add(draft)
    try:
        db.commit()
    except IntegrityError:  # two drafts raced for the same number
        db.rollback()
        raise HTTPException(status_code=409, detail="Retry: version taken") from None
    return draft


@router.get("/prompt-templates", response_model=list[TemplateOut])
def list_templates(
    db: Session = Depends(get_db), user: UserNew = Admin
) -> Sequence[PromptTemplate]:
    return db.scalars(select(PromptTemplate).order_by(PromptTemplate.key)).all()


@router.post("/prompt-templates", response_model=TemplateOut, status_code=201)
def create_template(
    body: TemplateCreate, db: Session = Depends(get_db), user: UserNew = Admin
) -> PromptTemplate:
    template = PromptTemplate(id=uuid.uuid4(), created_by=user.id, **body.model_dump())
    audit(db, user, "prompt_templates", template.id, "CREATE", body.model_dump())
    db.add(template)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Template key exists") from None
    return template


@router.get("/prompt-templates/{template_id}/versions", response_model=list[VersionOut])
def list_versions(
    template_id: UUID, db: Session = Depends(get_db), user: UserNew = Admin
) -> Sequence[PromptTemplateVersion]:
    return db.scalars(
        select(PromptTemplateVersion)
        .where(PromptTemplateVersion.template_id == template_id)
        .order_by(PromptTemplateVersion.version.desc())
    ).all()


@router.post(
    "/prompt-templates/{template_id}/versions",
    response_model=VersionOut,
    status_code=201,
)
def create_version(
    template_id: UUID,
    body: VersionCreate,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> PromptTemplateVersion:
    if db.get(PromptTemplate, template_id) is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return _new_draft(db, user, template_id, body.model_dump())


@router.patch("/prompt-versions/{version_id}", response_model=VersionOut)
def update_version(
    version_id: UUID,
    body: VersionUpdate,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> PromptTemplateVersion:
    """Edit a draft in place; editing a published version creates a new draft from it."""
    current = _version(db, version_id)
    values = body.model_dump(exclude_unset=True, exclude={"lock_version"})
    if current.published_at is not None:
        fields = {k: values.get(k, getattr(current, k)) for k in CONTENT}
        return _new_draft(db, user, current.template_id, fields, current.id)
    _check_placeholders({k: values.get(k, getattr(current, k)) for k in CONTENT})
    audit(db, user, "prompt_template_versions", current.id, "UPDATE", values)
    save_revision(db, PromptTemplateVersion, current.id, body.lock_version, values)
    db.refresh(current)
    return current


@router.post("/prompt-versions/{version_id}/publish", response_model=VersionOut)
def publish_version(
    version_id: UUID,
    body: Revision,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> PromptTemplateVersion:
    current = _version(db, version_id)
    if current.published_at is not None:
        raise HTTPException(status_code=409, detail="Already published")
    fields = {k: getattr(current, k) for k in CONTENT}
    _check_placeholders(fields)
    digest = prompt_sha256(fields)
    audit(
        db, user, "prompt_template_versions", current.id, "PUBLISH", {"sha256": digest}
    )
    save_revision(
        db,
        PromptTemplateVersion,
        current.id,
        body.lock_version,
        {"published_at": func.now(), "sha256": digest},
    )
    db.refresh(current)
    return current


@router.get("/prompt-versions/{version_id}/diff", response_model=VersionDiff)
def diff_versions(
    version_id: UUID,
    against: UUID,
    db: Session = Depends(get_db),
    user: UserNew = Admin,
) -> VersionDiff:
    """Unified diff from `against` (old) to `version_id` (new)."""
    new, old = _version(db, version_id), _version(db, against)

    def udiff(a: str, b: str, name: str) -> str:
        return "".join(
            difflib.unified_diff(
                a.splitlines(keepends=True),
                b.splitlines(keepends=True),
                f"v{old.version}/{name}",
                f"v{new.version}/{name}",
            )
        )

    return VersionDiff(
        from_id=old.id,
        to_id=new.id,
        system_diff=udiff(old.system_text, new.system_text, "system"),
        user_diff=udiff(old.user_text, new.user_text, "user"),
        output_schema_changed=old.output_schema != new.output_schema,
        few_shot_examples_changed=old.few_shot_examples != new.few_shot_examples,
    )
