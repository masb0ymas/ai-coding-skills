package middlewares

import (
	"fmt"
	"io/fs"
	"path"
	"strings"

	"github.com/gofiber/fiber/v3"
	"github.com/gofiber/fiber/v3/middleware/static"
)

// SPAConfig configures SPA.
type SPAConfig struct {
	// FS is the build output of the single-page app; it must hold index.html
	// at its root (os.DirFS("web/dist"), or an embed.FS via fs.Sub).
	FS fs.FS
	// Exclude lists path prefixes that belong to the API. A miss under them
	// answers with the API's JSON 404 instead of the app shell, so a typo in
	// an API call never comes back as HTML.
	Exclude []string
}

// assetsPrefix holds the content-hashed files a bundler emits (Vite's
// default). They never change under the same name, so browsers may cache
// them for a year.
const assetsPrefix = "/assets/"

// SPA serves a built single-page app: existing files as they are, and
// index.html for every other GET path so the client-side router can take
// over. Mount it after the API routes, so the API always wins.
//
// index.html is sent with "Cache-Control: no-cache": it names the hashed
// bundles of the current release, and a cached copy would keep loading the
// previous one after a deploy.
func SPA(cfg SPAConfig) (fiber.Handler, error) {
	if cfg.FS == nil {
		return nil, fmt.Errorf("spa: FS is required")
	}
	index, err := fs.ReadFile(cfg.FS, "index.html")
	if err != nil {
		return nil, fmt.Errorf("spa: read index.html: %w", err)
	}

	shell := func(c fiber.Ctx) error {
		c.Set(fiber.HeaderCacheControl, "no-cache")
		c.Set(fiber.HeaderContentType, fiber.MIMETextHTMLCharsetUTF8)
		return c.Status(fiber.StatusOK).Send(index)
	}

	files := static.New("", static.Config{
		FS: cfg.FS,
		ModifyResponse: func(c fiber.Ctx) error {
			if strings.HasPrefix(c.Path(), assetsPrefix) {
				c.Set(fiber.HeaderCacheControl, "public, max-age=31536000, immutable")
			} else {
				c.Set(fiber.HeaderCacheControl, "no-cache")
			}
			return nil
		},
		NotFoundHandler: func(c fiber.Ctx) error {
			// A missing file with an extension is a real 404 (usually an old
			// bundle hash); answering with HTML would fail as a script.
			if path.Ext(c.Path()) != "" {
				return fiber.ErrNotFound
			}
			return shell(c)
		},
	})

	return func(c fiber.Ctx) error {
		if m := c.Method(); m != fiber.MethodGet && m != fiber.MethodHead {
			return c.Next()
		}
		p := c.Path()
		for _, prefix := range cfg.Exclude {
			prefix = strings.TrimSuffix(prefix, "/")
			if p == prefix || strings.HasPrefix(p, prefix+"/") {
				return c.Next()
			}
		}
		if p == "/" || p == "/index.html" {
			return shell(c)
		}
		return files(c)
	}, nil
}
