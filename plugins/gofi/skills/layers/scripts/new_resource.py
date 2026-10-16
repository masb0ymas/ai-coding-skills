#!/usr/bin/env python3
"""Generate a CRUD resource across every gofi layer.

Writes, following the categories module exactly:
  migrations/NNNNNN_create_<table>.{up,down}.sql
  internal/models/<name>.go
  internal/dtos/<name>.go (+ <name>_test.go)
  internal/repositories/<name>.go
  internal/handlers/<name>.go
and wires it into internal/repositories/factory.go, internal/handlers/factory.go
and cmd/api/routes.go. Missing validator rules (Integer, Number, Bool) are
appended to internal/lib/validator/rules.go.

Field spec: comma-separated  name:type[:flag[:flag...]]
  types : string | text | int | float | bool | uuid | time
  flags : required          NOT NULL + Required() + non-pointer Go type
          max=N             MaxLen for string/text (string defaults to 255)
          ref=table         foreign key to table(id) (uuid fields)
          unique            UNIQUE constraint
Example:
  python3 new_resource.py --name product \
    --fields "name:string:required:max=150,price:int:required,description:text,category_id:uuid:ref=categories"

Access modes for routes (--access):
  superuser (default)  reads public, writes need Authorization + SuperUser + idempotency
  auth                 reads public, writes need any signed-in user + idempotency
  private              every route needs Authorization; writes add idempotency
  auth/private do NOT scope rows to their owner: every signed-in user can read
  and change every row. Per-user data: references/patterns.md section 4.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

INITIALISMS = {"id": "ID", "url": "URL", "uuid": "UUID", "api": "API", "http": "HTTP", "ip": "IP", "json": "JSON", "sql": "SQL"}
RESERVED = {"id", "created_at", "updated_at", "deleted_at"}
GO_KEYWORDS = {"break", "case", "chan", "const", "continue", "default", "defer", "else", "fallthrough", "for",
               "func", "go", "goto", "if", "import", "interface", "map", "package", "range", "return", "select",
               "struct", "switch", "type", "var"}
UUID_RE = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
TIME_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"

# go type, sql type, validator chain (without Required)
TYPES = {
    "string": ("string", "VARCHAR", ".String()"),
    "text": ("string", "TEXT", ".String()"),
    "int": ("int64", "BIGINT", ".Integer()"),
    "float": ("float64", "DOUBLE PRECISION", ".Number()"),
    "bool": ("bool", "BOOLEAN", ".Bool()"),
    "uuid": ("uuid.UUID", "UUID", f".Regex(`{UUID_RE}`)"),
    "time": ("time.Time", "TIMESTAMPTZ", f".Regex(`{TIME_RE}`)"),
}


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def pascal(snake: str) -> str:
    return "".join(INITIALISMS.get(p, p.capitalize()) for p in snake.split("_"))


def camel(snake: str) -> str:
    p = pascal(snake)
    head = re.match(r"^[A-Z]+(?=[A-Z][a-z]|$)|^[A-Z]", p).group(0)
    return head.lower() + p[len(head):]


def pluralize(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


@dataclass
class Field:
    name: str
    kind: str
    required: bool = False
    max_len: int | None = None
    ref: str | None = None
    unique: bool = False

    @property
    def go_name(self) -> str:
        return pascal(self.name)

    @property
    def go_type(self) -> str:
        base = TYPES[self.kind][0]
        return base if self.required else "*" + base

    @property
    def sql_type(self) -> str:
        return TYPES[self.kind][1]

    @property
    def searchable(self) -> bool:
        return self.kind in ("string", "text")

    @property
    def sortable(self) -> bool:
        return self.kind != "text"


def parse_fields(spec: str) -> list[Field]:
    fields: list[Field] = []
    for raw in filter(None, (s.strip() for s in spec.split(","))):
        parts = raw.split(":")
        if len(parts) < 2:
            die(f"field {raw!r} must be name:type[:flags]")
        name, kind, flags = parts[0], parts[1], parts[2:]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            die(f"field name {name!r} must be snake_case")
        if name in RESERVED:
            die(f"field {name!r} is added automatically")
        if kind not in TYPES:
            die(f"field {name!r}: unknown type {kind!r} (use {', '.join(TYPES)})")
        f = Field(name, kind)
        for flag in flags:
            if flag == "required":
                f.required = True
            elif flag == "unique":
                f.unique = True
            elif flag.startswith("max="):
                f.max_len = int(flag[4:])
            elif flag.startswith("ref="):
                f.ref = flag[4:]
            else:
                die(f"field {name!r}: unknown flag {flag!r}")
        if f.kind == "string" and f.max_len is None:
            f.max_len = 255
        if f.ref and f.kind != "uuid":
            die(f"field {name!r}: ref= needs type uuid")
        if any(x.name == name for x in fields):
            die(f"duplicate field {name!r}")
        fields.append(f)
    if not fields:
        die("at least one field is required")
    return fields


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #

def render_migration(table: str, fields: list[Field], soft: bool) -> tuple[str, str]:
    cols = [
        '  "id" UUID PRIMARY KEY NOT NULL DEFAULT uuidv7()',
        '  "created_at" TIMESTAMPTZ NOT NULL DEFAULT now()',
        '  "updated_at" TIMESTAMPTZ NOT NULL DEFAULT now()',
    ]
    if soft:
        cols.append('  "deleted_at" TIMESTAMPTZ')
    for f in fields:
        col = f'  "{f.name}" {f.sql_type}'
        if f.required:
            col += " NOT NULL"
        if f.unique:
            col += " UNIQUE"
        if f.ref:
            col += f' REFERENCES "{f.ref}" ("id")'
        cols.append(col)
    idx = [f'CREATE INDEX IF NOT EXISTS idx_{table}_created_at ON "{table}" ("created_at");']
    if soft:
        idx.append(f'CREATE INDEX IF NOT EXISTS idx_{table}_deleted_at ON "{table}" ("deleted_at");')
    for f in fields:
        # Postgres does not index foreign keys on its own; unique columns already have one.
        if (f.ref or f.kind == "string") and not f.unique:
            idx.append(f'CREATE INDEX IF NOT EXISTS idx_{table}_{f.name} ON "{table}" ("{f.name}");')
    up = f'CREATE TABLE IF NOT EXISTS "{table}" (\n' + ",\n".join(cols) + "\n);\n\n" + "\n".join(idx) + "\n"
    down = f'DROP TABLE IF EXISTS "{table}";\n'
    return up, down


def imports_for(fields: list[Field], extra: list[str] | None = None) -> str:
    std, third = [], []
    if any(f.kind == "time" for f in fields):
        std.append('"time"')
    if any(f.kind == "uuid" for f in fields):
        third.append('"github.com/google/uuid"')
    groups = [g for g in (std, third, extra or []) if g]
    if not groups:
        return ""
    body = "\n\n".join("\n".join("\t" + i for i in g) for g in groups)
    return f"import (\n{body}\n)\n\n"


def render_model(T: str, fields: list[Field], soft: bool) -> str:
    lines = ["\tBase"] + (["\tSoftDelete"] if soft else [])
    lines += [f'\t{f.go_name} {f.go_type} `db:"{f.name}" json:"{f.name}"`' for f in fields]
    return f"package models\n\n{imports_for(fields)}type {T} struct {{\n" + "\n".join(lines) + "\n}\n"


def render_dto(T: str, label: str, fields: list[Field], module: str) -> str:
    consts, rules, props = [], [], []
    for f in fields:
        chain = TYPES[f.kind][2]
        if f.max_len:
            cname = f"max{T}{f.go_name}Len"
            consts.append(f"\t{cname} = {f.max_len}")
            chain += f".MaxLen({cname})"
        rules.append(f'\tv.Field("{f.name}"){".Required()" if f.required else ""}{chain}')
        props.append(f'\t{f.go_name} {f.go_type} `json:"{f.name}"`')
    const_block = ("const (\n" + "\n".join(consts) + "\n)\n\n") if consts else ""
    imp = imports_for(fields, [f'"{module}/internal/lib/validator"'])
    return (
        f"package dtos\n\n{imp}{const_block}"
        f"// {T}Body is the create/update payload for a {label}. Optional fields are\n"
        f"// pointers, so an absent key stays nil instead of a zero value.\n"
        f"type {T}Body struct {{\n" + "\n".join(props) + "\n}\n\n"
        f"func (dto {T}Body) Validate(v *validator.MapValidator) {{\n" + "\n".join(rules) + "\n}\n"
    )


def sample_value(f: Field) -> str:
    return {
        "string": '"sample"', "text": '"sample"', "int": "float64(1)", "float": "1.5",
        "bool": "true", "uuid": '"0190a9c4-6f00-7000-8000-000000000001"', "time": '"2026-01-02T15:04:05Z"',
    }[f.kind]


def render_dto_test(T: str, fields: list[Field], module: str) -> str:
    valid = "\n".join(f'\t\t"{f.name}": {sample_value(f)},' for f in fields)
    required = [f for f in fields if f.required]
    missing_case = ""
    if required:
        missing_case = (
            f"\n\tif _, ok := validate{T}(map[string]interface{{}}{{}}); ok {{\n"
            f"\t\tt.Fatal(\"empty body must fail: {', '.join(f.name for f in required)} required\")\n\t}}\n"
        )
    wrong = fields[0]
    wrong_val = '"not-a-number"' if wrong.kind in ("int", "float") else ("\"x\"" if wrong.kind == "bool" else "123")
    return f'''package dtos

import (
\t"testing"

\t"{module}/internal/lib/validator"
)

func validate{T}(data map[string]interface{{}}) (validator.MessageRecord, bool) {{
\tv := validator.NewMapValidator()
\t{T}Body{{}}.Validate(v)
\treturn v.Validate(data)
}}

func Test{T}BodyValidate(t *testing.T) {{
\tif mr, ok := validate{T}(map[string]interface{{}}{{
{valid}
\t}}); !ok {{
\t\tt.Fatalf("valid body rejected: %v", mr)
\t}}
{missing_case}
\tif _, ok := validate{T}(map[string]interface{{}}{{"{wrong.name}": {wrong_val}}}); ok {{
\t\tt.Fatal("{wrong.name} with the wrong type must fail")
\t}}
}}
'''


def render_repository(T: str, label: str, table: str, fields: list[Field], soft: bool,
                      search: list[str], module: str) -> str:
    cols = ["id", "created_at", "updated_at"] + (["deleted_at"] if soft else []) + [f.name for f in fields]
    scan = ["&x.ID", "&x.CreatedAt", "&x.UpdatedAt"] + (["&x.DeletedAt"] if soft else []) + [f"&x.{f.go_name}" for f in fields]
    names = [f.name for f in fields]
    ph = ", ".join(f"${i}" for i in range(1, len(fields) + 2))
    ins_args = ", ".join(["x.ID"] + [f"x.{f.go_name}" for f in fields])
    sets = ", ".join(f"{f.name} = ${i}" for i, f in enumerate(fields, start=2))
    live = " AND deleted_at IS NULL" if soft else ""
    sort_cols = [f.name for f in fields if f.sortable] + ["created_at", "updated_at"]
    sort_map = "\n".join(f'\t"{c}": "{c}",' for c in sort_cols)
    base_cond = "deleted_at IS NULL" if soft else "TRUE"
    search_cols = ", ".join(f'"{s}"' for s in search)
    search_line = f"\tw.search(p.Search, {search_cols})\n" if search else ""
    has_ref = any(f.ref for f in fields)
    ref_msg = "a referenced record does not exist"

    def write_err(var: str = "err") -> str:
        if has_ref:
            return f'translateForeignKey({var}, "{ref_msg}")'
        return var

    c = camel(label.replace(" ", "_"))
    out = f'''package repositories

import (
\t"context"
\t"fmt"

\t"{module}/internal/models"

\t"github.com/google/uuid"
)

// {T}Repository manages {table}.
type {T}Repository struct {{
\tBaseRepository
}}

const {c}Columns = `
\t{", ".join(cols)}`

func scan{T}(row rowScanner) (models.{T}, error) {{
\tvar x models.{T}
\terr := row.Scan({", ".join(scan)})
\treturn x, translateNotFound("{table}", err)
}}

// Insert persists a new {label}.
func (r *{T}Repository) Insert(ctx context.Context, x models.{T}) error {{
\t_, err := r.execContext(ctx, `
\t\tINSERT INTO {table} (id, {", ".join(names)})
\t\tVALUES ({ph})`,
\t\t{ins_args},
\t)
\treturn {write_err()}
}}

// {c}SortColumns whitelists the columns a `sorted` value may order by.
var {c}SortColumns = map[string]string{{
{sort_map}
}}

// {c}Filters builds the WHERE conditions shared by List and Count.
func {c}Filters(p ListParams) *whereBuilder {{
\tw := newWhere(`{base_cond}`)
{search_line}\treturn w
}}

// List returns one page of {table}. Callers clamp offset/limit first
// (see dtos.ListQuery.Clamp).
func (r *{T}Repository) List(ctx context.Context, p ListParams) ([]models.{T}, error) {{
\twhere, args, limit, offset := {c}Filters(p).page(p)

\tquery := fmt.Sprintf(`
\t\tSELECT %s FROM {table}
\t\tWHERE %s
\t\tORDER BY %s
\t\tLIMIT $%d OFFSET $%d`,
\t\t{c}Columns, where,
\t\tresolveOrder(p.Sorted, {c}SortColumns, "created_at DESC"), limit, offset)

\trows, err := r.queryContext(ctx, query, args...)
\tif err != nil {{
\t\treturn nil, err
\t}}
\treturn collectRows(rows, scan{T})
}}

// Count returns how many {table} match the List filters, for the response metadata.
func (r *{T}Repository) Count(ctx context.Context, p ListParams) (int64, error) {{
\treturn r.countRows(ctx, "{table}", {c}Filters(p))
}}

// Get returns one {label} by id.
func (r *{T}Repository) Get(ctx context.Context, id uuid.UUID) (models.{T}, error) {{
\tquery := fmt.Sprintf(`SELECT %s FROM {table} WHERE id = $1{live}`, {c}Columns)
\treturn scan{T}(r.queryRowContext(ctx, query, id))
}}

// Update rewrites a {label}.
func (r *{T}Repository) Update(ctx context.Context, x models.{T}) error {{
\tres, err := r.execContext(ctx, `
\t\tUPDATE {table}
\t\tSET {sets}, updated_at = now()
\t\tWHERE id = $1{live}`,
\t\t{ins_args},
\t)
\tif err != nil {{
\t\treturn {write_err()}
\t}}
\treturn requireAffected(res, "{label}")
}}
'''
    if soft:
        out += f'''
// Delete soft-removes one {label} by stamping deleted_at.
func (r *{T}Repository) Delete(ctx context.Context, id uuid.UUID) error {{
\tres, err := r.execContext(ctx, `
\t\tUPDATE {table}
\t\tSET deleted_at = now(), updated_at = now()
\t\tWHERE id = $1 AND deleted_at IS NULL`,
\t\tid,
\t)
\tif err != nil {{
\t\treturn err
\t}}
\treturn requireAffected(res, "{label}")
}}

// Restore clears deleted_at on a soft-deleted {label}.
func (r *{T}Repository) Restore(ctx context.Context, id uuid.UUID) error {{
\tres, err := r.execContext(ctx, `
\t\tUPDATE {table}
\t\tSET deleted_at = NULL, updated_at = now()
\t\tWHERE id = $1 AND deleted_at IS NOT NULL`,
\t\tid,
\t)
\tif err != nil {{
\t\treturn err
\t}}
\treturn requireAffected(res, "{label}")
}}

// ForceDelete permanently removes the row, whether or not it is trashed.
func (r *{T}Repository) ForceDelete(ctx context.Context, id uuid.UUID) error {{
\tres, err := r.execContext(ctx, `DELETE FROM {table} WHERE id = $1`, id)
\tif err != nil {{
\t\treturn translateForeignKey(err, "{label} is still referenced by other records")
\t}}
\treturn requireAffected(res, "{label}")
}}
'''
    else:
        out += f'''
// Delete permanently removes one {label}.
func (r *{T}Repository) Delete(ctx context.Context, id uuid.UUID) error {{
\tres, err := r.execContext(ctx, `DELETE FROM {table} WHERE id = $1`, id)
\tif err != nil {{
\t\treturn translateForeignKey(err, "{label} is still referenced by other records")
\t}}
\treturn requireAffected(res, "{label}")
}}
'''
    return out


def render_handler(T: str, label: str, fields: list[Field], soft: bool, module: str) -> str:
    h = camel(label.replace(" ", "_")) + "Handler"
    assign = "\n".join(f"\t\t{f.go_name}: body.{f.go_name}," for f in fields)
    out = f'''package handlers

import (
\t"github.com/gofiber/fiber/v3"
\t"github.com/google/uuid"

\t"{module}/internal/app"
\t"{module}/internal/dtos"
\t"{module}/internal/lib"
\t"{module}/internal/models"
\t"{module}/internal/repositories"
)

type {h} struct {{
\tapp *app.Application
}}

func (h *{h}) repo() *repositories.{T}Repository {{
\treturn &h.app.Repositories.{T}
}}

// to{T} maps the validated body onto the model; the id is set by the caller.
func to{T}(body dtos.{T}Body) models.{T} {{
\treturn models.{T}{{
{assign}
\t}}
}}

func (h *{h}) List(c fiber.Ctx) error {{
\tvar q dtos.ListQuery
\tif err := lib.ValidateRequestQuery(c, &q); err != nil {{
\t\treturn err
\t}}
\tq.Clamp()

\tparams := listParams(q)

\titems, err := h.repo().List(c.Context(), params)
\tif err != nil {{
\t\treturn err
\t}}
\ttotal, err := h.repo().Count(c.Context(), params)
\tif err != nil {{
\t\treturn err
\t}}

\treturn dtos.List(c, items, dtos.ListMeta(int(total), q.Offset, q.Limit))
}}

func (h *{h}) Get(c fiber.Ctx) error {{
\tid, err := pathID(c, "{label}")
\tif err != nil {{
\t\treturn err
\t}}

\titem, err := h.repo().Get(c.Context(), id)
\tif err != nil {{
\t\treturn err
\t}}
\treturn dtos.Get(c, item)
}}

func (h *{h}) Create(c fiber.Ctx) error {{
\tvar body dtos.{T}Body
\tif err := lib.ValidateRequestBody(c, &body); err != nil {{
\t\treturn err
\t}}

\titem := to{T}(body)
\tvar err error
\tif item.ID, err = uuid.NewV7(); err != nil {{
\t\treturn err
\t}}

\tif err := h.repo().Insert(c.Context(), item); err != nil {{
\t\treturn err
\t}}

\t// Re-read so the response carries the DB-set timestamps.
\titem, err = h.repo().Get(c.Context(), item.ID)
\tif err != nil {{
\t\treturn err
\t}}
\treturn dtos.Created(c, item, "{label} created")
}}

func (h *{h}) Update(c fiber.Ctx) error {{
\tid, err := pathID(c, "{label}")
\tif err != nil {{
\t\treturn err
\t}}

\tvar body dtos.{T}Body
\tif err := lib.ValidateRequestBody(c, &body); err != nil {{
\t\treturn err
\t}}

\titem := to{T}(body)
\titem.ID = id

\tif err := h.repo().Update(c.Context(), item); err != nil {{
\t\treturn err
\t}}

\titem, err = h.repo().Get(c.Context(), id)
\tif err != nil {{
\t\treturn err
\t}}
\treturn dtos.OK(c, item)
}}

func (h *{h}) Delete(c fiber.Ctx) error {{
\treturn mutateByID(c, "{label}", h.repo().Delete, "{label} deleted")
}}
'''
    if soft:
        out += f'''
func (h *{h}) Restore(c fiber.Ctx) error {{
\treturn mutateByID(c, "{label}", h.repo().Restore, "{label} restored")
}}

func (h *{h}) DeletePermanently(c fiber.Ctx) error {{
\treturn mutateByID(c, "{label}", h.repo().ForceDelete, "{label} permanently deleted")
}}
'''
    return out


def render_routes(T: str, var: str, path: str, soft: bool, access: str, need_idem: bool) -> str:
    if access == "private":
        group = f'v1.Group("/{path}", m.Authorization)'
        guard = "idempotent"
    elif access == "auth":
        group = f'v1.Group("/{path}")'
        guard = "m.Authorization, idempotent"
    else:
        group = f'v1.Group("/{path}")'
        guard = "m.Authorization, m.SuperUser, idempotent"
    lines = [f"\n\t// {T}: generated by gofi:layers ({access})."]
    if need_idem:
        lines.append("\tidempotent := middlewares.Idempotency()")
    lines += [
        f"\t{var} := {group}",
        f'\t{var}.Get("/", h.{T}.List)',
        f'\t{var}.Get("/:id", h.{T}.Get)',
        f'\t{var}.Post("/", {guard}, h.{T}.Create)',
        f'\t{var}.Put("/:id", {guard}, h.{T}.Update)',
        f'\t{var}.Delete("/:id", {guard}, h.{T}.Delete)',
    ]
    if soft:
        lines += [
            f'\t{var}.Put("/:id/restore", {guard}, h.{T}.Restore)',
            f'\t{var}.Delete("/:id/force", {guard}, h.{T}.DeletePermanently)',
        ]
    return "\n".join(lines) + "\n"


VALIDATOR_RULES = {
    'Integer': '''
// Integer reports a failure when the value is present but not a whole JSON
// number (JSON numbers always decode as float64).
func (v *FieldValidator) Integer() *FieldValidator {
	v.registerRule(func(key string, data interface{}) (string, bool) {
		if data == nil {
			return "", true
		}
		if f, ok := data.(float64); !ok || f != float64(int64(f)) {
			return fmt.Sprintf("%s must be an integer", key), false
		}
		return "", true
	})
	return v
}

''',
    'Number': '''
// Number reports a failure when the value is present but not a JSON number.
func (v *FieldValidator) Number() *FieldValidator {
	v.registerRule(func(key string, data interface{}) (string, bool) {
		if _, ok := data.(float64); data != nil && !ok {
			return fmt.Sprintf("%s must be a number", key), false
		}
		return "", true
	})
	return v
}

''',
    'Bool': '''
// Bool reports a failure when the value is present but not a JSON boolean.
func (v *FieldValidator) Bool() *FieldValidator {
	v.registerRule(func(key string, data interface{}) (string, bool) {
		if _, ok := data.(bool); data != nil && !ok {
			return fmt.Sprintf("%s must be a boolean", key), false
		}
		return "", true
	})
	return v
}
''',
}


# --------------------------------------------------------------------------- #
# Patching
# --------------------------------------------------------------------------- #

def append_in_block(text: str, header: str, line: str, closing: str = "\n}") -> str:
    """Insert line before the closing of the first block that starts with header."""
    start = text.find(header)
    if start < 0:
        raise ValueError(f"cannot find {header!r}")
    end = text.find(closing, start)
    if end < 0:
        raise ValueError(f"cannot find end of {header!r}")
    return text[:end] + "\n" + line + text[end:]


def find_func_end(text: str, signature: str) -> int:
    start = text.find(signature)
    if start < 0:
        raise ValueError(f"cannot find {signature!r}")
    end = text.find("\n}\n", start)
    if end < 0:
        end = text.rfind("\n}")
    return end


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="singular snake_case name, e.g. product or order_item")
    ap.add_argument("--fields", required=True, help="field spec, see module doc")
    ap.add_argument("--table", help="table name (default: plural of --name)")
    ap.add_argument("--path", help="URL segment under /v1 (default: table with '-' for '_')")
    ap.add_argument("--search", help="comma-separated columns for ?search= (default: string/text fields)")
    ap.add_argument("--no-soft-delete", action="store_true", help="hard delete, no deleted_at/restore/force")
    ap.add_argument("--access", choices=["superuser", "auth", "private"], default="superuser")
    ap.add_argument("--root", default=".", help="project root (folder with go.mod)")
    ap.add_argument("--no-routes", action="store_true", help="do not touch cmd/api/routes.go")
    ap.add_argument("--dry-run", action="store_true", help="print what would be written")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    gomod = root / "go.mod"
    if not gomod.exists():
        die(f"{root} has no go.mod")
    module = re.search(r"^module\s+(\S+)", gomod.read_text(), re.M).group(1)
    for d in ("internal/models", "internal/dtos", "internal/repositories", "internal/handlers", "migrations"):
        if not (root / d).is_dir():
            die(f"{d} not found: is this a gofi project?")

    name = args.name.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        die("--name must be singular snake_case")
    fields = parse_fields(args.fields)
    soft = not args.no_soft_delete
    table = args.table or pluralize(name)
    path = args.path or table.replace("_", "-")
    T = pascal(name)
    label = name.replace("_", " ")
    var = camel(table)
    if var in GO_KEYWORDS:
        var += "Group"

    known = {f.name for f in fields}
    search = [s.strip() for s in args.search.split(",")] if args.search else [f.name for f in fields if f.searchable]
    for s in search:
        if s not in known:
            die(f"--search column {s!r} is not a field")

    for f in fields:
        if f.ref and not any((root / "migrations").glob(f"*_create_{f.ref}.up.sql")):
            print(f"warning: no create migration found for referenced table {f.ref!r}")

    files = {
        root / "internal/models" / f"{name}.go": render_model(T, fields, soft),
        root / "internal/dtos" / f"{name}.go": render_dto(T, label, fields, module),
        root / "internal/dtos" / f"{name}_test.go": render_dto_test(T, fields, module),
        root / "internal/repositories" / f"{name}.go": render_repository(T, label, table, fields, soft, search, module),
        root / "internal/handlers" / f"{name}.go": render_handler(T, label, fields, soft, module),
    }
    for p in files:
        if p.exists():
            die(f"{p.relative_to(root)} already exists")

    mig_dir = root / "migrations"
    nums = [m.group(1) for p in mig_dir.glob("*.sql") if (m := re.match(r"^(\d+)_", p.name))]
    seq = str(max(map(int, nums), default=0) + 1).zfill(max(map(len, nums), default=6))
    up, down = render_migration(table, fields, soft)
    files[mig_dir / f"{seq}_create_{table}.up.sql"] = up
    files[mig_dir / f"{seq}_create_{table}.down.sql"] = down

    patches: dict[Path, str] = {}
    rf = root / "internal/repositories/factory.go"
    t = rf.read_text()
    if f"{T}Repository" not in t:
        t = append_in_block(t, "type Repositories struct {", f"\t{T} {T}Repository")
        t = append_in_block(t, "return Repositories{", f"\t\t{T}: {T}Repository{{base}},", "\n\t}")
        patches[rf] = t
    hf = root / "internal/handlers/factory.go"
    t = hf.read_text()
    hname = camel(label.replace(" ", "_")) + "Handler"
    if hname not in t:
        t = append_in_block(t, "type Handlers struct {", f"\t{T} *{hname}")
        t = append_in_block(t, "return &Handlers{", f"\t\t{T}: &{hname}{{app: app}},", "\n\t}")
        patches[hf] = t
    vf = root / "internal/lib/validator/rules.go"
    if vf.exists():
        t = vf.read_text()
        missing = [r for r in ("Integer", "Number", "Bool") if f"func (v *FieldValidator) {r}()" not in t]
        if missing:
            patches[vf] = t.rstrip("\n") + "\n" + "".join(VALIDATOR_RULES[r] for r in missing)
    routes_note = ""
    if not args.no_routes:
        rt = root / "cmd/api/routes.go"
        t = rt.read_text() if rt.exists() else ""
        if not t:
            routes_note = "cmd/api/routes.go not found; add the routes by hand"
        elif f'"/{path}"' in t:
            routes_note = f"routes for /{path} already exist; left untouched"
        else:
            need_idem = "idempotent :=" not in t
            block = render_routes(T, var, path, soft, args.access, need_idem)
            end = find_func_end(t, "func routes(")
            patches[rt] = t[:end] + "\n" + block.rstrip("\n") + t[end:]

    if args.dry_run:
        for p, c in {**files, **patches}.items():
            print(f"===== {p.relative_to(root)}\n{c}")
        return

    for p, c in files.items():
        p.write_text(c)
    for p, c in patches.items():
        p.write_text(c)
    touched = [str(p) for p in [*files, *patches] if p.suffix == ".go"]
    if shutil.which("gofmt"):
        res = subprocess.run(["gofmt", "-l", "-w", *touched], capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stderr, file=sys.stderr)
            die("gofmt failed on generated code; inspect the files above")

    print(f"resource {T} ({table}) generated:")
    for p in [*files, *patches]:
        print(f"  {'M' if p in patches else 'A'} {p.relative_to(root)}")
    if routes_note:
        print(f"note: {routes_note}")
    print(f"\nroutes: /v1/{path} access={args.access} soft-delete={'on' if soft else 'off'}")
    if args.access != "superuser":
        print(f"warning: --access {args.access} does not scope rows to their owner; every signed-in user "
              "can read and change every row. For per-user data follow references/patterns.md section 4.")
    print("next: go build ./... && go vet ./... && go test ./... && make db/migrations/up")


if __name__ == "__main__":
    main()
