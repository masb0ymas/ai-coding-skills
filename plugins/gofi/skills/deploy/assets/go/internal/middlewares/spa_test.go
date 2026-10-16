package middlewares

import (
	"io"
	"net/http/httptest"
	"testing"
	"testing/fstest"

	"github.com/gofiber/fiber/v3"
)

func TestSPA(t *testing.T) {
	const shell = "<!doctype html><title>app</title>"
	files := fstest.MapFS{
		"index.html":        {Data: []byte(shell)},
		"assets/app-abc.js": {Data: []byte("console.log(1)")},
		"favicon.ico":       {Data: []byte("ico")},
	}

	spa, err := SPA(SPAConfig{FS: files, Exclude: []string{"/v1", "/health"}})
	if err != nil {
		t.Fatal(err)
	}

	app := fiber.New()
	app.Get("/v1/ping", func(c fiber.Ctx) error { return c.SendString("pong") })
	app.Use(spa)

	cases := []struct {
		method, path string
		status       int
		body, cache  string
	}{
		{"GET", "/", 200, shell, "no-cache"},
		{"GET", "/index.html", 200, shell, "no-cache"},
		{"GET", "/dashboard/settings", 200, shell, "no-cache"},
		{"GET", "/assets/app-abc.js", 200, "console.log(1)", "public, max-age=31536000, immutable"},
		{"GET", "/favicon.ico", 200, "ico", "no-cache"},
		// An old bundle hash must not come back as HTML.
		{"GET", "/assets/app-old.js", 404, "", ""},
		// The API keeps its own routes and its own 404s.
		{"GET", "/v1/ping", 200, "pong", ""},
		{"GET", "/v1/missing", 404, "", ""},
		{"GET", "/health/deep", 404, "", ""},
		// Writes are never answered by the app shell.
		{"POST", "/dashboard", 404, "", ""},
	}
	for _, tc := range cases {
		resp, err := app.Test(httptest.NewRequest(tc.method, tc.path, nil))
		if err != nil {
			t.Fatalf("%s %s: %v", tc.method, tc.path, err)
		}
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		if resp.StatusCode != tc.status {
			t.Errorf("%s %s: status %d, want %d", tc.method, tc.path, resp.StatusCode, tc.status)
		}
		if tc.body != "" && string(body) != tc.body {
			t.Errorf("%s %s: body %q, want %q", tc.method, tc.path, body, tc.body)
		}
		if tc.cache != "" && resp.Header.Get(fiber.HeaderCacheControl) != tc.cache {
			t.Errorf("%s %s: Cache-Control %q, want %q", tc.method, tc.path, resp.Header.Get(fiber.HeaderCacheControl), tc.cache)
		}
	}
}

func TestSPARequiresIndex(t *testing.T) {
	if _, err := SPA(SPAConfig{FS: fstest.MapFS{}}); err == nil {
		t.Fatal("an FS without index.html must be refused at startup")
	}
}
