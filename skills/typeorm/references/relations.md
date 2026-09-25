# TypeORM Relations

Source: https://typeorm.io/docs/relations/relations and the relation sub-pages

## The four relation types

```ts
import { Entity, OneToOne, ManyToOne, OneToMany, ManyToMany, JoinColumn, JoinTable } from "typeorm"

@Entity()
export class PhotoMetadata {
  @OneToOne(() => Photo, (photo) => photo.metadata) // owning side
  @JoinColumn() // required here: this table gets the FK column (photoId)
  photo: Photo
}

@Entity()
export class Photo {
  @ManyToOne(() => Author, (author) => author.photos) // ALWAYS the owning side — FK lives here (authorId)
  author: Author

  @OneToMany(() => Photo, (photo) => photo.author) // inverse only; cannot exist without ManyToOne
  photos: Photo[]

  @ManyToMany(() => Album, (album) => album.photos)
  @JoinTable() // required on ONE side: creates junction table (photo_albums_album_photos)
  albums: Album[]
}
```

- Only one side of a relation **owns** it (holds the FK): the side with `@JoinColumn` (or `@ManyToOne`, or `@JoinTable`).
- Bidirectional relations: pass the inverse property — `@ManyToOne(() => Author, (author) => author.photos)` — prefer the function form over string names (refactor-safe).
- Self-referencing relations (adjacency list trees) are normal relations pointing at the same entity: `@ManyToOne(() => Category, (c) => c.childCategories)`.

## Relation options

| Option | Default | Meaning |
| --- | --- | --- |
| `eager` | `false` | always load with `find*` on this entity. Only one side may be eager. **Ignored by QueryBuilder** — use `leftJoinAndSelect` there |
| `lazy` | `false` | property becomes `Promise<T>`; loaded on first `await` (see below) |
| `cascade` | `false` | `true` or `("insert" | "update" | "remove" | "soft-remove" | "recover")[]` — related objects persisted when saving this side |
| `onDelete` | `RESTRICT` | FK behavior on delete: `RESTRICT`, `CASCADE`, `SET NULL` |
| `nullable` | `true` | `false` makes FK NOT NULL and (for owning ManyToOne/OneToOne) switches loads to INNER JOIN |
| `orphanedRowAction` | `"nullify"` | when parent saves without a still-existing child: `nullify` (FK nulled, or row deleted if FK is NOT NULL), `delete`, `soft-delete`, `disable` |
| `deferrable` | — | `"INITIALLY DEFERRED"` / `"INITIALLY IMMEDIATE"` FK checks (Postgres, better-sqlite3, SAP HANA) |
| `createForeignKeyConstraints` | `true` | set `false` for a relation without a real FK constraint |

Cascade caveats:

- Cascade flows **from the side you set on save** — `photo.metadata = m; save(photo)` cascades to metadata; setting `metadata.photo` does not cascade through `photo`.
- `cascade: ["remove"]`/`true` + `remove()` deletes related entities **only if they are loaded on the instance**. Load relations first: `findOne({ where, relations: { categories: true } })`.

## Eager / lazy / load strategy

```ts
// lazy: declare as Promise — load on demand with await
@ManyToMany(() => Category, (c) => c.questions)
categories: Promise<Category[]>
const categories = await question.categories

// loading strategy: "join" (default, SQL JOINs) or "query" (separate queries per relation)
const photos = await photoRepository.find({ relationLoadStrategy: "query" })
// can be set DataSource-wide too — useful when nested joins explode row counts

// suppress automatic eager loading for one query
const photos = await photoRepository.find({ relations: { albums: true }, loadEagerRelations: false })
```

## Loading relations

```ts
// find* options — supports nested sub-relations
const photos = await photoRepository.find({
  relations: { metadata: true, albums: true },
})

// QueryBuilder — more control (conditions, inner join, ordering)
const photos = await AppDataSource.getRepository(Photo)
  .createQueryBuilder("photo")
  .innerJoinAndSelect("photo.metadata", "metadata")
  .leftJoinAndSelect("photo.albums", "album")
  .getMany()
```

## FK id without loading the relation

Add a `@Column` property named exactly like the generated FK column:

```ts
@Entity()
export class User {
  @Column({ nullable: true })
  profileId: number   // filled on load even when `profile` is not joined

  @OneToOne(() => Profile)
  @JoinColumn()
  profile: Profile
}
```

## FAQ gotchas

- **No relation property initializers.** `photos: Photo[] = []` (or `= []` in the constructor) makes every loaded entity carry `photos: []`; on save, TypeORM interprets that as "all relations removed" and detaches existing rows. Leave relation properties unset.
- **Circular imports between entities**: import types with `import type`, and pass entity names as strings where needed — or use `Relation<T>` in ESM.
- **`orphanedRowAction: "disable"`** if you manage junction rows manually and don't want TypeORM nullifying/deleting orphans.
- Changing `@JoinColumn({ name: "cat_id" })` renames the FK column; `@JoinTable({ name: "question_categories", joinColumn: {...}, inverseJoinColumn: {...} })` customizes the junction table fully.
