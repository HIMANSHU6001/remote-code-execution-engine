#!/usr/bin/env python3
"""Generate latest DB ERD Mermaid and overwrite docs/ERD.svg.

Flow:
1) Regenerate Mermaid ERD from SQLAlchemy models.
2) Render Mermaid to SVG using Mermaid CLI.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from sqlalchemy import UniqueConstraint
from sqlalchemy.sql.schema import Column, ForeignKeyConstraint, Table

from db.base import Base
import db.models  # noqa: F401  # Import registers models on Base.metadata.

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MMD = ROOT / "docs" / "db-erd.mmd"
DEFAULT_SVG = ROOT / "docs" / "ERD.svg"


def run_command(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}")


def _normalize_type_name(raw: str) -> str:
    value = raw.upper().strip()
    for ch in " ()[],.":
        value = value.replace(ch, "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_") or "TEXT"


def _column_type_label(column: Column) -> str:
    return _normalize_type_name(str(column.type))


def _single_column_unique_names(table: Table) -> set[str]:
    names: set[str] = set()
    for column in table.columns:
        if column.unique:
            names.add(column.name)

    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint) and len(constraint.columns) == 1:
            only_col = next(iter(constraint.columns))
            names.add(only_col.name)

    return names


def _render_table(table: Table) -> list[str]:
    lines = [f"    {table.name.upper()} {{"]
    unique_names = _single_column_unique_names(table)

    for column in table.columns:
        attrs: list[str] = []
        if column.primary_key:
            attrs.append("PK")
        if column.foreign_keys:
            attrs.append("FK")
        if column.name in unique_names:
            attrs.append("UK")

        attr_text = f" {' '.join(attrs)}" if attrs else ""
        lines.append(f"      {_column_type_label(column)} {column.name}{attr_text}")

    lines.append("    }")
    return lines


def _constraint_is_unique(table: Table, local_columns: Iterable[str]) -> bool:
    local_set = set(local_columns)
    if not local_set:
        return False

    pk_set = {c.name for c in table.primary_key.columns}
    if local_set == pk_set:
        return True

    for column in table.columns:
        if column.unique and {column.name} == local_set:
            return True

    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            unique_set = {c.name for c in constraint.columns}
            if unique_set == local_set:
                return True

    return False


def _render_relationships(tables: list[Table]) -> list[str]:
    lines: list[str] = []

    for child in tables:
        for fk_constraint in child.foreign_key_constraints:
            if not isinstance(fk_constraint, ForeignKeyConstraint):
                continue

            elements = list(fk_constraint.elements)
            if not elements:
                continue

            parent = elements[0].column.table
            local_columns = [element.parent.name for element in elements]
            parent_cardinality = "||"
            child_cardinality = "||" if _constraint_is_unique(child, local_columns) else "o{"
            label = ",".join(local_columns)

            lines.append(
                f"    {parent.name.upper()} {parent_cardinality}--{child_cardinality} {child.name.upper()} : {label}"
            )

    return sorted(set(lines))


def build_mermaid() -> str:
    tables = sorted(Base.metadata.tables.values(), key=lambda t: t.name)
    lines = ["erDiagram", ""]

    for table in tables:
        lines.extend(_render_table(table))
        lines.append("")

    relationship_lines = _render_relationships(tables)
    lines.extend(relationship_lines)

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate DB ERD Mermaid and overwrite ERD.svg",
    )
    parser.add_argument(
        "--mmd",
        default=str(DEFAULT_MMD),
        help="Path to Mermaid ERD file (default: docs/db-erd.mmd)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_SVG),
        help="Path to output SVG (default: docs/ERD.svg)",
    )
    parser.add_argument(
        "--skip-refresh",
        action="store_true",
        help="Skip refreshing Mermaid ERD from models and render existing .mmd only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mmd_path = Path(args.mmd)
    svg_path = Path(args.output)

    mmd_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.skip_refresh:
        mmd_path.write_text(build_mermaid(), encoding="utf-8")
        print(f"ERD written to {mmd_path}")

    npx_path = shutil.which("npx")
    if not npx_path:
        raise RuntimeError("npx is required but was not found in PATH.")

    run_command(
        [
            npx_path,
            "--yes",
            "@mermaid-js/mermaid-cli",
            "-i",
            str(mmd_path),
            "-o",
            str(svg_path),
            "-t",
            "default",
            "-b",
            "white",
        ],
        cwd=ROOT,
    )

    print(f"ERD SVG written to {svg_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
