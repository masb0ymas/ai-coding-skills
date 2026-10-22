#!/usr/bin/env python3
"""Generate a CRUD resource across every layer of a vine-style frontend.

Writes, following the `organization` reference module:

  lib/api/models/<name>.ts                   response model (+ Models namespace entry)
  lib/api/dtos/<group>/<name>/schema.ts      zod request schema + DTO type
  lib/api/services/types/<name>.ts           declared HTTP methods
  lib/api/services/<name>.ts                 axios resource (+ services registry)
  lib/api/queries/<name>.ts                  TanStack Query options (+ queries registry)
  components/block/<group>/<name>/           column.tsx, form.tsx, table.tsx
  route                                      vinext: app/(app)/<group>/<name>/page.tsx
                                             vite:   src/routes/(app)/<group>/<name>/index.tsx
  data/sidebar-menu.ts                       entry in NAV_<GROUP> when that menu exists

vinext vs vite is detected from the project (src/routes/__root.tsx = vite).

Usage:
  python3 new_resource.py --root . --name product \\
      --fields "name:string:required,price:int:required,description:text,active:bool"
  python3 new_resource.py --root . --name purchase-order --group sales --plural purchase-orders \\
      --fields "code:string:required,ordered_at:date:required,total:float" --dry-run

Field types: string text uuid date int float bool. Flag: required.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TYPES = {"string", "text", "uuid", "date", "int", "float", "bool"}
STRINGISH = {"string", "text", "uuid", "date"}
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
FIELD_RE = re.compile(r"^[a-z][a-z0-9_]*$")
RESERVED = {"id", "created_at", "updated_at", "deleted_at"}


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- naming


def pluralize(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


def pascal(kebab: str) -> str:
    return "".join(p.capitalize() for p in re.split(r"[-_]", kebab))


def camel(kebab: str) -> str:
    p = pascal(kebab)
    return p[0].lower() + p[1:]


def words(name: str) -> str:
    return " ".join(re.split(r"[-_]", name))


class Field:
    def __init__(self, spec: str):
        parts = spec.strip().split(":")
        if len(parts) < 2:
            die(f"field {spec!r}: expected name:type[:required]")
        self.name, self.type, flags = parts[0], parts[1], parts[2:]
        if not FIELD_RE.match(self.name) or self.name in RESERVED:
            die(f"field name {self.name!r} must be snake_case and not one of {sorted(RESERVED)}")
        if self.type not in TYPES:
            die(f"field {self.name}: type {self.type!r} not in {sorted(TYPES)}")
        unknown = set(flags) - {"required"}
        if unknown:
            die(f"field {self.name}: unknown flags {sorted(unknown)}")
        self.required = "required" in flags
        self.attr = words(self.name)  # used in validation messages
        self.label = self.attr.title()

    @property
    def ts(self) -> str:
        if self.type in STRINGISH:
            return "ISO8601DateString" if self.type == "date" else "string"
        return "boolean" if self.type == "bool" else "number"


# ---------------------------------------------------------------- per-field code


def model_line(f: Field) -> str:
    return f"  {f.name}: {f.ts}" if f.required else f"  {f.name}?: {f.ts} | null"


def schema_line(f: Field) -> str:
    if f.type in STRINGISH:
        # Empty optional inputs are sent as absent, not "", so the API stores NULL.
        expr = f"requiredString('{f.attr}')" if f.required else f"optionalString('{f.attr}').transform((v) => v || undefined)"
    elif f.type == "int":
        expr = f"requiredNonNegativeInteger('{f.attr}')" if f.required else f"optionalNumber('{f.attr}')"
    elif f.type == "float":
        expr = f"z.number({{ error: 'The {f.attr} must be a number.' }})" + ("" if f.required else ".optional()")
    else:
        expr = "z.boolean()"
    return f"  {f.name}: {expr},"


def add_default(f: Field) -> str:
    value = {"int": "undefined", "float": "undefined", "bool": "false"}.get(f.type, "''")
    return f"        {f.name}: {value},"


def edit_default(f: Field) -> str:
    v = f"record.{f.name}"
    if f.type == "date":
        expr = f"{v}.slice(0, 10)" if f.required else f"{v}?.slice(0, 10) ?? ''"
    elif f.type in STRINGISH:
        expr = v if f.required else f"{v} ?? ''"
    elif f.type == "bool":
        expr = v if f.required else f"{v} ?? false"
    else:
        expr = v if f.required else f"{v} ?? undefined"
    return f"        {f.name}: {expr},"


def form_field(f: Field) -> str:
    star = "asterisk " if f.required else ""
    if f.type in STRINGISH:
        extra = ' type="date"' if f.type == "date" else f' placeholder="e.g. {f.label}"'
        inner = f"<field.TextField {star}label=\"{f.label}\"{extra} />"
    elif f.type in ("int", "float"):
        scale = "\n            decimalScale={0}" if f.type == "int" else ""
        sign = "\n            allowNegative={false}" if f.type == "int" and f.required else ""
        inner = (
            f"<field.NumberField\n            {star.strip() + chr(10) + '            ' if star else ''}"
            f"label=\"{f.label}\"{scale}{sign}\n"
            "            value={field.state.value ?? ''}\n"
            "            onValueChange={(value) => field.handleChange(value === '' ? undefined : Number(value))}\n"
            "          />"
        )
    else:
        inner = (
            "<Field orientation=\"horizontal\">\n"
            "            <Switch\n"
            "              id={field.name}\n"
            "              checked={field.state.value ?? false}\n"
            "              onCheckedChange={field.handleChange}\n"
            "            />\n"
            f"            <FieldLabel htmlFor={{field.name}}>{f.label}</FieldLabel>\n"
            "          </Field>"
        )
    return (
        "      <form.AppField\n"
        f"        name=\"{f.name}\"\n"
        "        children={(field) => (\n"
        f"          {inner}\n"
        "        )}\n"
        "      />"
    )


def column(f: Field) -> str:
    render = {"bool": "value ? 'Yes' : 'No'", "date": "formatDate(value)"}.get(f.type, "value ?? '-'")
    ts = "string" if f.type == "date" else f.ts
    return (
        "      {\n"
        f"        accessorKey: '{f.name}',\n"
        f"        header: '{f.label}',\n"
        "        cell: (info) => {\n"
        f"          const value = info.getValue() as {ts} | null | undefined\n"
        "          return (\n"
        "            <CellItem loading={loading}>\n"
        f"              <span>{{{render}}}</span>\n"
        "            </CellItem>\n"
        "          )\n"
        "        },\n"
        "      },"
    )


# ---------------------------------------------------------------- templates

MODEL = """\
import type { ISO8601DateString } from '@/types/time'

export interface __Name__ {
  id: string
__MODEL_FIELDS__
  created_at: ISO8601DateString
  updated_at: ISO8601DateString
  deleted_at?: ISO8601DateString | null
}
"""

SCHEMA = """\
import z from 'zod'
__VALIDATION_IMPORT__
export const __Name__FormSchema = z.object({
__SCHEMA_FIELDS__
})

export type __Name__FormDto = z.infer<typeof __Name__FormSchema>
"""

SERVICE_TYPES = """\
import type { HTTP_METHOD, Resources } from '@/types/api'

import type { Models } from '../../models'

/**
 * The methods `__name__Services` actually builds. `resource()` only creates
 * the methods it was given, so this list must match the one in the service.
 */
export type __Name__Methods = [
  HTTP_METHOD.GET,
  HTTP_METHOD.POST,
  HTTP_METHOD.PUT,
  HTTP_METHOD.DELETE,
]

export type __Name__Resources = Resources<__Name__Methods, Models.__Name__>
"""

SERVICE = """\
import { HTTP_METHOD } from '@/types/api'

import type { __Name__Methods, __Name__Resources } from './types/__kebab__'

import { clientResource } from '../resource'

const path = '__api_path__'

// Typed by __Name__Methods so the runtime methods and the declared type
// cannot drift apart.
const methods: __Name__Methods = [
  HTTP_METHOD.GET,
  HTTP_METHOD.POST,
  HTTP_METHOD.PUT,
  HTTP_METHOD.DELETE,
]

const resources = (): __Name__Resources => {
  return {
    ...clientResource(path, methods),
  }
}

export const __name__Services = resources()
"""

QUERIES = """\
import { mutationOptions, queryOptions } from '@tanstack/react-query'

import { DEFAULT_PAGINATE } from '@/lib/constants/paginate'
import { getQueryClient } from '@/lib/providers/react-query'

import type { __Name__FormDto } from '../dtos/__dto_dir__/schema'
import type { PaginateDto } from '../dtos/paginate'

import { services } from '../services'

export const __NAME___QUERY_KEY = '__names__'

export const LIST___NAME___QUERY_KEY = (params?: PaginateDto) => {
  return [__NAME___QUERY_KEY, 'list', params]
}

export const GET___NAME___QUERY_KEY = (id: string) => {
  return [__NAME___QUERY_KEY, 'detail', id]
}

const list = (params?: PaginateDto & { search?: string; sorted?: string }) =>
  queryOptions({
    queryKey: LIST___NAME___QUERY_KEY(params),
    queryFn: async () => {
      const res = await services.__names__.list(params ?? DEFAULT_PAGINATE)
      return res.data
    },
  })

const get = (id: string) =>
  queryOptions({
    queryKey: GET___NAME___QUERY_KEY(id),
    queryFn: async () => {
      const res = await services.__names__.get(id)
      return res.data
    },
  })

const create = () => {
  const qc = getQueryClient()

  return mutationOptions({
    mutationFn: async (reqBody: __Name__FormDto) => {
      const res = await services.__names__.store(reqBody)
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [__NAME___QUERY_KEY] })
    },
  })
}

const update = (id: string) => {
  const qc = getQueryClient()

  return mutationOptions({
    mutationFn: async (reqBody: __Name__FormDto) => {
      const res = await services.__names__.update(id, reqBody)
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [__NAME___QUERY_KEY] })
    },
  })
}

const del = () => {
  const qc = getQueryClient()

  return mutationOptions({
    mutationFn: async (id: string) => {
      const res = await services.__names__.delete(id)
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [__NAME___QUERY_KEY] })
    },
  })
}

export const __name__Queries = { list, get, create, update, delete: del } as const
"""

COLUMN = """\
__USE_CLIENT__import { useMutation } from '@tanstack/react-query'
import React, { useMemo, useState } from 'react'
import { toast } from 'sonner'

import type { Models } from '@/lib/api/models'
import type { AppColumnDef, BaseColumnProps } from '@/types/column'

import CellItem from '@/components/block/common/cell-item'
import RowColumnAction from '@/components/block/common/row-column-action'
import SimpleAlertDialog from '@/components/block/common/simple-alert-dialog'
import { toastAxiosError } from '@/lib/api/axios-error'
import { queries } from '@/lib/api/queries'
__DATE_IMPORT__
import { Edit__Name__Form } from './form'

type ColumnType = AppColumnDef<Models.__Name__>

// Declared once, and never swapped for a skeleton: the cell owns the row's open
// dialogs, so remounting it on a background refetch would discard them.
const actionCell: ColumnType['cell'] = ({ row }) => <ActionCell record={row.original} />

export function __Name__Column({ loading }: BaseColumnProps) {
  const columns = useMemo<ColumnType[]>(
    () => [
__COLUMNS__
      {
        accessorKey: 'actions',
        header: 'Actions',
        cell: actionCell,
        size: 50,
      },
    ],
    [loading]
  )

  return columns
}

interface ActionCellProps {
  record: Models.__Name__
}

function ActionCell({ record }: ActionCellProps) {
  const [openEdit, setOpenEdit] = useState(false)
  const [openDelete, setOpenDelete] = useState(false)

  const deleteMutation = useMutation(queries.__names__.delete())

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(record.id)
      toast.success('__Label__ deleted successfully')
      setOpenDelete(false)
    } catch (error) {
      toastAxiosError(error)
    }
  }

  return (
    <React.Fragment>
      <RowColumnAction onEdit={() => setOpenEdit(true)} onDelete={() => setOpenDelete(true)} />

      <SimpleAlertDialog
        title="Do you want to delete this __label__?"
        description="This __label__ will be permanently deleted and cannot be undone."
        open={openDelete}
        onOpenChange={setOpenDelete}
        onConfirm={handleDelete}
        confirmText="Delete"
        variant="destructive"
      />

      <Edit__Name__Form open={openEdit} onOpenChange={setOpenEdit} record={record} />
    </React.Fragment>
  )
}
"""

FORM = """\
__USE_CLIENT__import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'

import type { Models } from '@/lib/api/models'
import type { BaseAbstractForm } from '@/types/form'

import SimpleAlertScrollableDialogForm from '@/components/block/common/simple-alert-scrollable-dialog-form'
__SWITCH_IMPORTS__import { useAppForm } from '@/hooks/form'
import { toastAxiosError } from '@/lib/api/axios-error'
import { __Name__FormSchema, type __Name__FormDto } from '@/lib/api/dtos/__dto_dir__/schema'
import { parseDto } from '@/lib/api/dtos/parse'
import { queries } from '@/lib/api/queries'

// Partial: number inputs start empty, so the form state may lack a value the
// DTO requires; the schema reports it and parseDto never lets it through.
type TModel = Partial<__Name__FormDto>
type TMutation = __Name__FormDto
type TDto = __Name__FormDto
type TResponse = Models.__Name__

type AbstractFormProps = BaseAbstractForm<TModel, TMutation, TDto, TResponse> & {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function AbstractForm({
  open,
  onOpenChange,
  defaultValues,
  schema,
  mutation,
  isEdit,
}: AbstractFormProps) {
  const form = useAppForm({
    defaultValues,
    validators: {
      onSubmit: schema,
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await mutation.mutateAsync(parseDto(schema, value))
        toast.success(`__Label__ ${isEdit ? 'updated' : 'created'} successfully`)
        onOpenChange(false)
        form.reset()
      } catch (error) {
        toastAxiosError(error)
      }
    },
  })

  return (
    <SimpleAlertScrollableDialogForm
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
      open={open}
      onOpenChange={onOpenChange}
      title={`${isEdit ? 'Edit' : 'Create'} __Label__`}
      confirmText={isEdit ? 'Update' : 'Save'}
      loading={mutation.isPending}
      size="md"
    >
__FORM_FIELDS__
    </SimpleAlertScrollableDialogForm>
  )
}

type Add__Name__FormProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function Add__Name__Form({ open, onOpenChange }: Add__Name__FormProps) {
  const mutation = useMutation(queries.__names__.create())

  return (
    <AbstractForm
      open={open}
      onOpenChange={onOpenChange}
      defaultValues={{
__ADD_DEFAULTS__
      }}
      schema={__Name__FormSchema}
      mutation={mutation}
    />
  )
}

type Edit__Name__FormProps = Add__Name__FormProps & {
  record: Models.__Name__
}

export function Edit__Name__Form({ open, onOpenChange, record }: Edit__Name__FormProps) {
  const mutation = useMutation(queries.__names__.update(record.id))

  return (
    <AbstractForm
      open={open}
      onOpenChange={onOpenChange}
      defaultValues={{
__EDIT_DEFAULTS__
      }}
      schema={__Name__FormSchema}
      mutation={mutation}
      isEdit
    />
  )
}
"""

TABLE = """\
__USE_CLIENT__import { IconPlus, IconSearch } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useQueryState } from 'nuqs'
import { useEffect, useMemo, useState } from 'react'

import EmptyState from '@/components/block/common/empty-state'
import ReactTable from '@/components/block/common/react-table'
import SectionCard from '@/components/block/common/section-card'
import { Button } from '@/components/ui/button'
import { Input, InputWrapper } from '@/components/ui/input'
import { useDebounce } from '@/hooks/use-debounce'
import { usePaginationQuery } from '@/hooks/use-pagination-query'
import { toastAxiosError } from '@/lib/api/axios-error'
import { queries } from '@/lib/api/queries'

import { __Name__Column } from './column'
import { Add__Name__Form } from './form'

export default function __Name__Table() {
  const [openAdd, setOpenAdd] = useState(false)
  const { offset, limit, pageIndex } = usePaginationQuery()

  const [search, setSearch] = useQueryState('search')
  const debouncedSearch = useDebounce({ value: search ?? '', delay: 500 })

  const params = useMemo(
    () => ({
      offset,
      limit,
      ...(debouncedSearch ? { search: debouncedSearch } : {}),
    }),
    [offset, limit, debouncedSearch]
  )

  const { data, isFetching, isLoading, isError, error } = useQuery(queries.__names__.list(params))
  const loading = isLoading || isFetching
  const total = data?.metadata?.total ?? 0
  const rows = data?.data ?? []

  useEffect(() => {
    if (isError) toastAxiosError(error)
  }, [isError, error])

  const columns = __Name__Column({ loading })

  return (
    <SectionCard
      title="__Labels__"
      description="Manage __labels__."
      toolbar={
        <div className="flex flex-row items-center gap-2">
          <InputWrapper className="w-72">
            <IconSearch />
            <Input
              placeholder="Search __labels__..."
              value={search ?? ''}
              onChange={(e) => void setSearch(e.target.value || null)}
            />
          </InputWrapper>

          <Button className="h-8.5 rounded-lg" onClick={() => setOpenAdd(true)}>
            <IconPlus />
            <span>Add __Label__</span>
          </Button>
        </div>
      }
    >
      {!loading && rows.length === 0 ? (
        <EmptyState
          title="No __labels__ found"
          description="Adjust the search, or add the first __label__."
          action={
            <Button onClick={() => setOpenAdd(true)}>
              <IconPlus />
              <span>Add __Label__</span>
            </Button>
          }
        />
      ) : (
        <ReactTable columns={columns} data={rows} total={total} pageIndex={pageIndex} pageSize={limit} />
      )}

      <Add__Name__Form open={openAdd} onOpenChange={setOpenAdd} />
    </SectionCard>
  )
}
"""

VINEXT_PAGE = """\
import __Name__Table from '@/components/block/__block_dir__/table'

export default function __Name__Page() {
  return <__Name__Table />
}
"""

VITE_ROUTE = """\
import { createFileRoute } from '@tanstack/react-router'

import __Name__Table from '@/components/block/__block_dir__/table'

export const Route = createFileRoute('/(app)/__url__/')({
  component: RouteComponent,
})

function RouteComponent() {
  return <__Name__Table />
}
"""


# ---------------------------------------------------------------- registry edits


def insert_before_last(text: str, marker: str, line: str) -> str:
    idx = text.rfind(marker)
    if idx < 0:
        raise ValueError(marker)
    return text[:idx] + line + "\n" + text[idx:]


def add_import(text: str, line: str) -> str:
    imports = list(re.finditer(r"^import .*$", text, re.M))
    end = imports[-1].end() if imports else 0
    return text[:end] + ("\n" if imports else "") + line + ("" if imports else "\n") + text[end:]


def add_menu_item(text: str, group: str, item: str) -> str | None:
    m = re.search(rf"const NAV_{group.upper().replace('-', '_')}\b[^=]*=\s*\{{", text)
    if not m:
        return None
    items = text.find("items: [", m.end())
    if items < 0:
        return None
    depth, i = 0, items + len("items: ")
    while i < len(text):
        depth += {"[": 1, "]": -1}.get(text[i], 0)
        if depth == 0:
            break
        i += 1
    body = text[items + len("items: [") : i].rstrip()
    if body.endswith(","):
        body = body[:-1]
    joined = f"{body}, {item}" if body.strip() else item
    return text[: items + len("items: [")] + joined + text[i:]


# ---------------------------------------------------------------- main


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="app directory (holds package.json)")
    p.add_argument("--name", required=True, help="singular kebab-case name, e.g. product or purchase-order")
    p.add_argument("--plural", help="plural kebab-case name (default: naive English plural)")
    p.add_argument("--group", default="master", help="folder + menu group, e.g. master; '' for top level")
    p.add_argument("--fields", required=True, help="name:type[:required],... (types: %s)" % " ".join(sorted(TYPES)))
    p.add_argument("--api-path", help="REST path (default /api/v1/<plural>)")
    p.add_argument("--no-route", action="store_true", help="skip the page/route file")
    p.add_argument("--no-menu", action="store_true", help="skip the sidebar entry")
    p.add_argument("--force", action="store_true", help="overwrite existing files")
    p.add_argument("--dry-run", action="store_true", help="print what would be written")
    args = p.parse_args()

    root = Path(args.root).resolve()
    if (root / "src" / "routes" / "__root.tsx").exists():
        kind, base = "vite", root / "src"
    elif (root / "app" / "layout.tsx").exists():
        kind, base = "vinext", root
    else:
        die(f"{root}: neither src/routes/__root.tsx (vite) nor app/layout.tsx (vinext) found")
    if not (base / "lib" / "api" / "services" / "index.ts").exists():
        die("lib/api/services/index.ts missing; this does not look like a vine app")

    if not NAME_RE.match(args.name):
        die("--name must be kebab-case, e.g. product or purchase-order")
    plural = args.plural or re.sub(r"[a-z0-9]+$", lambda m: pluralize(m.group()), args.name)
    if not NAME_RE.match(plural):
        die("--plural must be kebab-case, e.g. people")
    group = args.group.strip("/")
    if group and not NAME_RE.match(group):
        die("--group must be kebab-case")
    fields = [Field(s) for s in args.fields.split(",") if s.strip()]
    if not fields:
        die("--fields is empty")
    if len({f.name for f in fields}) != len(fields):
        die("duplicate field names")

    block_dir = f"{group}/{args.name}" if group else args.name
    subs = {
        "__USE_CLIENT__": "'use client'\n\n" if kind == "vinext" else "",
        "__NAME__": args.name.upper().replace("-", "_"),
        "__Name__": pascal(args.name),
        "__name__": camel(args.name),
        "__names__": camel(plural),
        "__kebab__": args.name,
        "__Labels__": words(plural).title(),
        "__Label__": words(args.name).title(),
        "__labels__": words(plural),
        "__label__": words(args.name),
        "__dto_dir__": block_dir,
        "__block_dir__": block_dir,
        "__url__": block_dir,
        "__api_path__": args.api_path or f"/api/v1/{plural}",
    }
    helpers = sorted({re.match(r"\w+", schema_line(f).split(": ", 1)[1]).group() for f in fields} - {"z"})
    subs["__MODEL_FIELDS__"] = "\n".join(model_line(f) for f in fields)
    subs["__SCHEMA_FIELDS__"] = "\n".join(schema_line(f) for f in fields)
    subs["__VALIDATION_IMPORT__"] = f"\nimport {{ {', '.join(helpers)} }} from '@/lib/validation'\n" if helpers else ""
    subs["__FORM_FIELDS__"] = "\n\n".join(form_field(f) for f in fields)
    subs["__ADD_DEFAULTS__"] = "\n".join(add_default(f) for f in fields)
    subs["__EDIT_DEFAULTS__"] = "\n".join(edit_default(f) for f in fields)
    subs["__COLUMNS__"] = "\n".join(column(f) for f in fields if f.type != "text")
    has_date = any(f.type == "date" for f in fields if f.type != "text")
    subs["__DATE_IMPORT__"] = "import { formatDate } from '@/lib/date'\n" if has_date else ""
    has_bool = any(f.type == "bool" for f in fields)
    subs["__SWITCH_IMPORTS__"] = (
        "import { Field, FieldLabel } from '@/components/ui/field'\nimport { Switch } from '@/components/ui/switch'\n"
        if has_bool else ""
    )

    # One pass, longest key first: __NAME___QUERY_KEY is not eaten by __Name__,
    # and inserted values (field names, paths) are never substituted again.
    placeholder = re.compile("|".join(re.escape(k) for k in sorted(subs, key=len, reverse=True)))

    def render(tpl: str) -> str:
        return placeholder.sub(lambda m: subs[m.group()], tpl)

    api = base / "lib" / "api"
    files = {
        api / "models" / f"{args.name}.ts": MODEL,
        api / "dtos" / block_dir / "schema.ts": SCHEMA,
        api / "services" / "types" / f"{args.name}.ts": SERVICE_TYPES,
        api / "services" / f"{args.name}.ts": SERVICE,
        api / "queries" / f"{args.name}.ts": QUERIES,
        base / "components" / "block" / block_dir / "column.tsx": COLUMN,
        base / "components" / "block" / block_dir / "form.tsx": FORM,
        base / "components" / "block" / block_dir / "table.tsx": TABLE,
    }
    if not args.no_route:
        if kind == "vinext":
            files[base / "app" / "(app)" / block_dir / "page.tsx"] = VINEXT_PAGE
        else:
            files[base / "routes" / "(app)" / block_dir / "index.tsx"] = VITE_ROUTE

    existing = [str(f.relative_to(root)) for f in files if f.exists()]
    if existing and not args.force:
        die(f"already exists (use --force): {existing}")

    # Registry edits are planned before anything is written, so a failure
    # leaves the project untouched.
    edits: dict[Path, str] = {}
    try:
        models = (api / "models" / "index.ts").read_text()
        if f"import('./{args.name}')" not in models:
            line = f"  export type {subs['__Name__']} = import('./{args.name}').{subs['__Name__']}"
            edits[api / "models" / "index.ts"] = insert_before_last(models, "}", line)
        for layer, suffix in (("services", "Services"), ("queries", "Queries")):
            path = api / layer / "index.ts"
            text = path.read_text()
            symbol = f"{subs['__name__']}{suffix}"
            if not re.search(rf"\b{symbol}\b", text):
                text = add_import(text, f"import {{ {symbol} }} from './{args.name}'")
                text = insert_before_last(text, "} as const", f"  {subs['__names__']}: {symbol},")
                edits[path] = text
    except ValueError as missing:
        die(f"could not find {missing} in a registry index.ts; register the resource by hand")

    notes = []
    menu = base / "data" / "sidebar-menu.ts"
    if not args.no_route and not args.no_menu and group and menu.exists():
        text = menu.read_text()
        url = f"/{block_dir}"
        if f"'{url}'" not in text:
            icon = "IconFolders" if "IconFolders" in text else None
            item = f"{{ title: '{subs['__Label__']}', url: '{url}'" + (f", icon: {icon} }}" if icon else " }")
            new = add_menu_item(text, group, item)
            if new is None:
                notes.append(f"no NAV_{group.upper()} menu in data/sidebar-menu.ts: add {url} by hand (and to MENUS per role)")
            else:
                edits[menu] = new

    for path, tpl in files.items():
        content = render(tpl)
        if args.dry_run:
            print(f"--- {path.relative_to(root)}\n{content}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"  created  {path.relative_to(root)}")
    for path, content in edits.items():
        if args.dry_run:
            print(f"--- (edit) {path.relative_to(root)}")
            continue
        path.write_text(content)
        print(f"  updated  {path.relative_to(root)}")

    if kind == "vite" and not args.no_route and not args.dry_run:
        tsr = root / "node_modules" / ".bin" / "tsr"
        if tsr.exists() and subprocess.run([str(tsr), "generate"], cwd=root).returncode == 0:
            print("  updated  src/routeTree.gen.ts")
        else:
            notes.append("run `pnpm generate-routes` (or pnpm dev/build) to refresh src/routeTree.gen.ts")
    if not shutil.which("pnpm"):
        notes.append("pnpm not found on PATH")
    for note in notes:
        print(f"  note     {note}")
    print(f"\n{kind}: {subs['__Name__']} wired to {subs['__api_path__']}; verify with `npx tsc --noEmit` and `pnpm build`.")


if __name__ == "__main__":
    main()
