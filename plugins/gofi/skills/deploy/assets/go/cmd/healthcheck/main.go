// Command healthcheck probes the API's /health endpoint from inside its own
// container. The distroless image has no shell, curl or wget, so Docker's
// HEALTHCHECK and compose's healthcheck run this binary instead.
//
// It exits 0 when /health answers 200 (the database is reachable), 1 otherwise.
package main

import (
	"fmt"
	"net/http"
	"os"
	"time"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	client := http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get("http://127.0.0.1:" + port + "/health")
	if err != nil {
		fmt.Fprintln(os.Stderr, "healthcheck:", err)
		os.Exit(1)
	}
	resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		fmt.Fprintln(os.Stderr, "healthcheck: status", resp.StatusCode)
		os.Exit(1)
	}
}
