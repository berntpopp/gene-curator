"""Idempotent methodology bundle import (#575).

Plans every object first (create, unchanged, new version, update) and validates the whole
bundle with the publish gate; only a valid, non-dry-run import writes, in one transaction.
Published methodology versions are never changed: changed content publishes the next one.
"""

from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.schema_repository import (
    SNAPSHOT_KEYS,
    _schema_content_hash,
    publish_errors,
    schema_crud,
    workflow_pair_crud,
)
from app.models import AuditLogNew, CurationSchema, Scope, WorkflowPair
from app.models.methodology import MethodologyVersion
from app.schemas.methodology_import import (
    BundleWorkflowPair,
    ImportItem,
    MethodologyBundle,
    MethodologyImportResult,
)
from app.schemas.schema_repository import CurationSchemaCreate

PAIR_TYPES = {
    "precuration_schema": ("precuration", "combined"),
    "curation_schema": ("curation", "combined"),
}


def _latest(db: Session, schema_id: UUID) -> MethodologyVersion | None:
    return db.scalar(
        select(MethodologyVersion)
        .where(MethodologyVersion.schema_id == schema_id)
        .order_by(MethodologyVersion.version.desc())
        .limit(1)
    )


def _snapshot(source: Any) -> dict[str, Any]:
    get = source.get if isinstance(source, dict) else lambda k: getattr(source, k)
    return {key: get(key) for key in SNAPSHOT_KEYS}


def _stamp_column_order(node: Any) -> None:
    """jsonb reorders keys: a table column without ``order`` gets its place in the bundle
    file, so tables show in authored order (monkey B10). Mutates ``node``."""
    if isinstance(node, list):
        for item in node:
            _stamp_column_order(item)
    elif isinstance(node, dict):
        columns = node.get("columns")
        if isinstance(columns, dict):
            for i, column in enumerate(columns.values(), start=1):
                if isinstance(column, dict):
                    column.setdefault("order", i)
        for value in node.values():
            _stamp_column_order(value)


def _plan_schema(
    db: Session, spec: CurationSchemaCreate
) -> tuple[ImportItem, CurationSchema | None, str | None]:
    """The schema's planned action, its existing row and why it cannot be imported."""
    item = ImportItem(
        kind="schema", name=spec.name, version=spec.version, action="create"
    )
    row = schema_crud.get_by_name_and_version(db, name=spec.name, version=spec.version)
    if row is None:
        item.methodology_version = 1
        return item, None, None
    item.id = row.id
    if row.schema_type != spec.schema_type:
        return item, row, f"schema {spec.name}: is a {row.schema_type.value} schema"
    latest = _latest(db, row.id)
    published = latest.snapshot if latest else None
    wanted, current = _snapshot(spec.model_dump()), _snapshot(row)
    if published == wanted and current == wanted:
        item.action = "unchanged"
        item.methodology_version = latest.version if latest else None
        return item, row, None
    if current not in (published, wanted):  # never overwrite unpublished UI edits
        return (
            item,
            row,
            (
                f"schema {spec.name}: has unpublished edits; publish or discard them first"
            ),
        )
    item.action = "new_version"
    item.methodology_version = (latest.version if latest else 0) + 1
    return item, row, None


def _bundle_errors(db: Session, bundle: MethodologyBundle) -> list[str]:
    """References and types the schema validator cannot see."""
    errors = [
        f"schema {name}: appears more than once"
        for name, n in Counter(s.name for s in bundle.schemas).items()
        if n > 1
    ]
    errors += [
        f"workflow pair {name}: appears more than once"
        for name, n in Counter(p.name for p in bundle.workflow_pairs).items()
        if n > 1
    ]
    types = {s.name: s.schema_type for s in bundle.schemas}
    for pair in bundle.workflow_pairs:
        for ref, allowed in PAIR_TYPES.items():
            name = getattr(pair, ref)
            if name not in types:
                errors.append(f"workflow pair {pair.name}: no bundle schema {name}")
            elif types[name] not in allowed:
                errors.append(
                    f"workflow pair {pair.name}: {ref} {name} is a {types[name]} schema"
                )
    if default := bundle.scope_default:
        if not db.scalar(select(Scope.id).where(Scope.name == default.scope_name)):
            errors.append(f"scope_default: no scope {default.scope_name}")
        if default.workflow_pair not in {p.name for p in bundle.workflow_pairs}:
            errors.append(
                f"scope_default: no bundle workflow pair {default.workflow_pair}"
            )
    return errors


def _write_schema(
    db: Session,
    spec: CurationSchemaCreate,
    row: CurationSchema | None,
    version: int,
    user_id: UUID,
) -> CurationSchema:
    """Create the row (v1) or overwrite it and publish `version`."""
    data = spec.model_dump()
    data["schema_hash"] = _schema_content_hash(data)
    if row is None:
        row = CurationSchema(**data, created_by=user_id)
        db.add(row)
        db.flush()
        if db.get_bind().dialect.name == "postgresql":
            return row  # the 042 trigger published v1 on insert
    else:
        # serialize with publish_version on the next number
        db.execute(
            select(CurationSchema.id)
            .where(CurationSchema.id == row.id)
            .with_for_update()
        )
        latest = db.scalar(
            select(func.max(MethodologyVersion.version)).where(
                MethodologyVersion.schema_id == row.id
            )
        )
        version = (latest or 0) + 1
        for key in (*SNAPSHOT_KEYS, "schema_hash"):
            setattr(row, key, data[key])
    db.add(
        MethodologyVersion(
            schema_id=row.id,
            version=version,
            snapshot=_snapshot(data),
            published_at=datetime.now(UTC),
            created_by=user_id,
        )
    )
    db.flush()
    return row


def _import_pair(
    db: Session,
    spec_pair: BundleWorkflowPair,
    ids: dict[str, UUID | None],
    *,
    user_id: UUID,
    write: bool,
) -> ImportItem:
    """Create the pair, repoint it to the bundle's schemas, or leave it unchanged."""
    target = {
        "precuration_schema_id": ids.get(spec_pair.precuration_schema),
        "curation_schema_id": ids.get(spec_pair.curation_schema),
        "description": spec_pair.description,
    }
    pair = workflow_pair_crud.get_by_name_and_version(
        db, name=spec_pair.name, version=spec_pair.version
    )
    item = ImportItem(
        kind="workflow_pair",
        name=spec_pair.name,
        version=spec_pair.version,
        action="create" if pair is None else "unchanged",
        id=pair.id if pair else None,
    )
    if pair is not None and any(getattr(pair, k) != v for k, v in target.items()):
        item.action = "update"
    if write and item.action != "unchanged":
        pair = pair or WorkflowPair(
            name=spec_pair.name, version=spec_pair.version, created_by=user_id
        )
        for key, value in target.items():
            setattr(pair, key, value)
        db.add(pair)
        db.flush()
        item.id = pair.id
    return item


def _inactive_errors(
    bundle: MethodologyBundle,
    planned: list[tuple[CurationSchemaCreate, ImportItem, CurationSchema | None]],
) -> list[str]:
    """A pair (and so a scope default) needs active schemas, as in create_workflow_pair."""
    inactive = {
        spec.name
        for spec, _, row in planned
        if not spec.is_active or (row is not None and not row.is_active)
    }
    return [
        f"workflow pair {pair.name}: schema {name} is inactive"
        for pair in bundle.workflow_pairs
        for name in dict.fromkeys((pair.precuration_schema, pair.curation_schema))
        if name in inactive
    ]


def import_bundle(
    db: Session, bundle: MethodologyBundle, *, user_id: UUID, dry_run: bool
) -> MethodologyImportResult:
    """Plan, validate and (unless dry_run or invalid) apply a methodology bundle."""
    for spec in bundle.schemas:
        _stamp_column_order(spec.field_definitions)
    errors = _bundle_errors(db, bundle)
    planned = []
    for spec in bundle.schemas:
        item, row, error = _plan_schema(db, spec)
        errors += [error] if error else []
        errors += [
            f"schema {spec.name}: {e}" for e in publish_errors(spec.model_dump())
        ]
        planned.append((spec, item, row))
    errors += _inactive_errors(bundle, planned)
    write = not dry_run and not errors

    ids: dict[str, UUID | None] = {}
    for spec, item, row in planned:
        if write and item.action != "unchanged":
            assert item.methodology_version is not None
            row = _write_schema(db, spec, row, item.methodology_version, user_id)
            item.id = row.id
        ids[spec.name] = item.id

    items = [item for _, item, _ in planned]
    pair_ids: dict[str, UUID | None] = {}
    for spec_pair in bundle.workflow_pairs:
        item = _import_pair(db, spec_pair, ids, user_id=user_id, write=write)
        pair_ids[spec_pair.name] = item.id
        items.append(item)

    if (default := bundle.scope_default) and not errors:
        scope = db.scalars(select(Scope).where(Scope.name == default.scope_name)).one()
        pair_id = pair_ids[default.workflow_pair]
        changed = scope.default_workflow_pair_id != pair_id or pair_id is None
        items.append(
            ImportItem(
                kind="scope_default",
                name=default.scope_name,
                action="update" if changed else "unchanged",
                id=scope.id,
            )
        )
        if write and changed:
            scope.default_workflow_pair_id = pair_id

    if write:
        db.add(
            AuditLogNew(
                entity_type="methodology_import",
                entity_id=items[0].id if items and items[0].id else user_id,
                operation="IMPORT",
                change_type="methodology_import",
                user_id=user_id,
                changes={"items": [i.model_dump(mode="json") for i in items]},
            )
        )
        db.commit()
    return MethodologyImportResult(dry_run=dry_run, errors=errors, items=items)
