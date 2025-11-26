"""introduce normalized locations"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202503150001"
down_revision = "202503070001"
branch_labels = None
depends_on = None

FK_INSPECTION_LOCATION = "fk_inspections_location_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _ensure_locations_table(bind, inspector)

    inspection_columns = {column["name"] for column in inspector.get_columns("inspections")}
    if "location_id" not in inspection_columns:
        with op.batch_alter_table("inspections") as batch_op:
            batch_op.add_column(sa.Column("location_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                FK_INSPECTION_LOCATION,
                "locations",
                ["location_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index("ix_inspections_location_id", "inspections", ["location_id"])

    _backfill_locations(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    inspection_columns = {column["name"] for column in inspector.get_columns("inspections")}
    if "location_id" in inspection_columns:
        op.drop_index("ix_inspections_location_id", table_name="inspections")
        with op.batch_alter_table("inspections") as batch_op:
            batch_op.drop_constraint(FK_INSPECTION_LOCATION, type_="foreignkey")
            batch_op.drop_column("location_id")

    if inspector.has_table("locations"):
        op.drop_index("ix_locations_name", table_name="locations")
        op.drop_table("locations")


def _ensure_locations_table(bind, inspector) -> None:
    if inspector.has_table("locations"):
        columns = inspector.get_columns("locations")
        if _locations_schema_matches(columns):
            return
        existing_names = _extract_existing_locations(bind)
        indexes = {index["name"] for index in inspector.get_indexes("locations")}
        if "ix_locations_name" in indexes:
            op.drop_index("ix_locations_name", table_name="locations")
        op.drop_table("locations")
        _create_locations_table()
        _bulk_insert_locations(bind, existing_names)
    else:
        _create_locations_table()


def _locations_schema_matches(columns: list[dict]) -> bool:
    column_names = {column["name"] for column in columns}
    if not {"id", "name"}.issubset(column_names):
        return False
    if column_names - {"id", "name"}:
        return False
    id_column = next((column for column in columns if column["name"] == "id"), None)
    if not id_column:
        return False
    python_type = getattr(getattr(id_column.get("type"), "python_type", None), "__name__", None)
    autoinc = id_column.get("autoincrement") in {True, "auto", "always"}
    return python_type == "int" and autoinc


def _create_locations_table() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("name", name="uq_locations_name"),
    )
    op.create_index("ix_locations_name", "locations", ["name"], unique=False)


def _extract_existing_locations(bind) -> list[str]:
    metadata = sa.MetaData()
    legacy_locations = sa.Table(
        "locations",
        metadata,
        sa.Column("name", sa.String),
    )
    try:
        result = bind.execute(
            sa.select(sa.distinct(legacy_locations.c.name)).where(
                legacy_locations.c.name.isnot(None)
            )
        )
    except sa.exc.NoSuchTableError:
        return []
    rows = [row[0] for row in result.fetchall() if row[0]]
    return rows


def _bulk_insert_locations(bind, names: list[str]) -> None:
    if not names:
        return
    metadata = sa.MetaData()
    locations = sa.Table(
        "locations",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("name", sa.String),
    )
    seen: set[str] = set()
    for raw_name in names:
        normalized = (raw_name or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        bind.execute(locations.insert().values(name=normalized))
        seen.add(key)


def _backfill_locations(bind) -> None:
    metadata = sa.MetaData()
    inspections = sa.Table(
        "inspections",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("location", sa.String),
        sa.Column("location_id", sa.Integer),
    )
    locations = sa.Table(
        "locations",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("name", sa.String),
    )

    try:
        existing_count = bind.execute(sa.select(sa.func.count()).select_from(locations)).scalar()
    except sa.exc.NoSuchTableError:
        return

    if existing_count and existing_count > 0:
        return

    try:
        existing_locations = bind.execute(
            sa.select(sa.distinct(inspections.c.location)).where(inspections.c.location.isnot(None))
        ).fetchall()
    except sa.exc.NoSuchTableError:
        return

    if not existing_locations:
        return

    seen: dict[str, int] = {}
    for (raw_name,) in existing_locations:
        normalized = (raw_name or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        result = bind.execute(locations.insert().values(name=normalized).returning(locations.c.id))
        location_id = result.scalar_one()
        seen[key] = location_id

    for key, location_id in seen.items():
        bind.execute(
            inspections.update()
            .where(sa.func.lower(inspections.c.location) == key)
            .values(location_id=location_id)
        )
