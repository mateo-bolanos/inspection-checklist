from __future__ import annotations

import sys

from sqlalchemy import create_engine, text

from app.core.config import settings

TABLE_ORDER = [
    "checklist_templates",
    "template_sections",
    "template_items",
    "users",
    "inspections",
    "inspection_responses",
    "corrective_actions",
    "media_files",
]


def main() -> None:
    sqlite_engine = create_engine(settings.sqlite_url, future=True)
    postgres_engine = create_engine(settings.postgres_url, future=True)

    with sqlite_engine.connect() as source_conn, postgres_engine.begin() as target_conn:
        for table in TABLE_ORDER:
            rows = source_conn.execute(text(f"SELECT * FROM {table}"))
            mappings = [dict(row) for row in rows.mappings()]
            if not mappings:
                continue
            cols = mappings[0].keys()
            col_list = ", ".join(cols)
            placeholders = ", ".join(f":{col}" for col in cols)
            target_conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
            target_conn.execute(
                text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"),
                mappings,
            )
    print("Migration complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)
