// Feed-sign is an offline operator tool; the HUB has no feed-signing key.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"os"
	"strings"
	"time"
)

func main() {
	key := flag.String("key", "", "offline private key file")
	out := flag.String("out", "feed.signed.json", "output")
	version := flag.Uint64("version", 1, "monotonically increasing version")
	summary := flag.String("summary", "Demo warning only; no blocking is permitted", "text-only warning")
	flag.Parse()
	if *key == "" {
		panic("-key required")
	}
	raw, err := os.ReadFile(*key)
	if err != nil {
		panic(err)
	}
	priv, err := protocol.PrivateFromHex(strings.TrimSpace(string(raw)))
	if err != nil {
		panic(err)
	}
	now := time.Now().UTC()
	f := protocol.Feed{Schema: protocol.FeedSchema, Version: *version, IssuedAt: now, ExpiresAt: now.Add(2 * time.Hour), Warnings: []protocol.Warning{{Category: "notice", Summary: *summary}}}
	if err = f.Validate(now); err != nil {
		panic(err)
	}
	sf, err := protocol.SignFeed(f, priv)
	if err != nil {
		panic(err)
	}
	b, _ := json.MarshalIndent(sf, "", "  ")
	if err = os.WriteFile(*out, b, 0600); err != nil {
		panic(err)
	}
	fmt.Println("signed feed written; distribute only after separate review")
}
