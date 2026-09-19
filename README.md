# AI Coding Skills

Kumpulan [Agent Skills](https://agentskills.io/) yang dapat langsung dipakai oleh beberapa AI coding agent. Setiap skill berisi `SKILL.md` dan resource pendukung yang dimuat agent hanya saat relevan.

## Agent yang didukung

| Target | Direktori project | Installer |
| --- | --- | --- |
| Zed / Agent Skills-compatible clients | `.agents/skills/` | `agents` |
| Claude Code | `.claude/skills/` | `claude` |
| OpenClaude | `.openclaude/skills/` | `openclaude` |
| Zcode | `.zcode/skills/` | `zcode` |

## Quick start

Clone atau unduh repository ini, lalu jalankan installer dari root repository.

### Instal ke satu project

Semua skill untuk semua agent:

```sh
./install.sh /path/to/project
```

Satu agent saja dipilih dengan `--agent`:

```sh
./install.sh --agent claude /path/to/project
./install.sh --agent agents /path/to/project
./install.sh --agent openclaude /path/to/project
./install.sh --agent zcode /path/to/project
```

Satu skill saja dipilih dengan `--skill`. Tanpa `--agent`, skill tersebut dipasang untuk semua agent:

```sh
./install.sh --skill authula /path/to/project
```

Agent dan skill dapat dipilih sekaligus:

```sh
./install.sh --agent claude --skill authula /path/to/project
```

Jika dijalankan tanpa argumen, semua skill untuk semua agent dipasang ke direktori aktif:

```sh
cd /path/to/project
/path/to/ai-coding-skills/install.sh
```

Installer hanya menyalin skill ke direktori target dan tidak menghapus skill lain yang sudah ada.

### Instal sebagai skill global

Gunakan home directory sebagai destination:

```sh
./install.sh "$HOME"
```

Atau pasang skill tertentu hanya untuk satu agent:

```sh
./install.sh --agent claude --skill authula "$HOME"
```

> Dukungan lokasi global mengikuti agent masing-masing. Claude Code menggunakan `~/.claude/skills/`, sedangkan Zed dan client Agent Skills yang kompatibel dapat menggunakan `~/.agents/skills/`.

## Skill tersedia

### `authula`

Panduan membangun autentikasi dengan [Authula](https://authula.dev/docs), framework auth berbasis plugin untuk Go.

Cakupan utamanya:

- mode library dan standalone;
- email/password, OAuth2, session, JWT, TOTP, magic link, API key, dan plugin lain;
- route mappings dan proteksi endpoint;
- konfigurasi Docker, TOML, environment variable, CORS, dan CSRF;
- custom route, hooks, service hooks, serta custom plugin.

Contoh prompt setelah instalasi:

```text
Buatkan setup Authula standalone dengan PostgreSQL, email-password,
dan session. Lindungi endpoint /me dan sertakan config.toml serta .env.example.
```

```text
Tambahkan Authula ke backend Go ini dengan GitHub OAuth dan session auth.
```

Agent akan mendeteksi `authula` secara otomatis ketika permintaan berkaitan dengan Authula.

## Struktur repository

```text
.
├── skills/                 # Sumber utama seluruh skill
│   └── authula/
│       ├── SKILL.md
│       └── references/
├── agents/                 # Bundle siap dipasang untuk tiap agent
│   ├── .agents/skills/
│   ├── .claude/skills/
│   ├── .openclaude/skills/
│   └── .zcode/skills/
├── scripts/
│   └── sync-agents.sh      # Sinkronkan sumber ke semua bundle
└── install.sh              # Pasang bundle ke project atau home directory
```

## Menambah atau memperbarui skill

1. Buat atau edit skill di `skills/<nama-skill>/`.
2. Pastikan file utamanya bernama `SKILL.md` dan memiliki frontmatter berikut:

   ```md
   ---
   name: nama-skill
   description: Jelaskan fungsi skill dan kapan agent harus menggunakannya.
   ---
   ```

3. Nama direktori harus sama dengan nilai `name`, menggunakan huruf kecil, angka, dan tanda hubung.
4. Sinkronkan perubahan ke semua bundle:

   ```sh
   ./scripts/sync-agents.sh
   ```

5. Periksa bahwa setiap bundle identik dengan sumber:

   ```sh
   diff -qr skills agents/.agents/skills
   diff -qr skills agents/.claude/skills
   diff -qr skills agents/.openclaude/skills
   diff -qr skills agents/.zcode/skills
   ```

`sync-agents.sh` membangun ulang direktori `skills/` di setiap bundle. Simpan perubahan manual hanya di `skills/`, bukan di dalam `agents/`.

## Catatan keamanan

Skill adalah instruksi yang dapat mengarahkan agent untuk membaca file, menjalankan perintah, atau mengakses layanan eksternal. Audit isi `SKILL.md`, script, dan reference sebelum memasang skill dari sumber yang tidak dipercaya.
