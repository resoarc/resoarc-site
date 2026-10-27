// Guardian is explicitly read-only: it verifies signed text warnings; no
// firewall modification, background collection, command execution or telemetry.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"io"
	"os"
	"strings"
	"time"
)

func main() {
	feedPath := flag.String("feed", "", "local signed feed")
	pubPath := flag.String("pub", "", "pinned offline-signer public key")
	statePath := flag.String("state", "guardian-state.json", "local anti-rollback state")
	flag.Parse()
	if *feedPath == "" || *pubPath == "" {
		panic("-feed and -pub required")
	}
	raw, err := os.ReadFile(*pubPath)
	if err != nil {
		panic(err)
	}
	pub, err := protocol.PublicFromHex(strings.TrimSpace(string(raw)))
	if err != nil {
		panic(err)
	}
	b, err := os.ReadFile(*feedPath)
	if err != nil {
		panic(err)
	}
	if len(b) > 65536 {
		panic("feed too large")
	}
	dec := json.NewDecoder(strings.NewReader(string(b)))
	dec.DisallowUnknownFields()
	var sf protocol.SignedFeed
	if err = dec.Decode(&sf); err != nil {
		panic(err)
	}
	if err = dec.Decode(new(any)); err != io.EOF {
		panic("extra feed data")
	}
	if err = protocol.VerifyFeed(sf, pub, time.Now().UTC()); err != nil {
		panic(err)
	}
	if err = verifyAndRecord(sf, pub, *statePath, time.Now().UTC()); err != nil {
		panic(err)
	}
	fmt.Println("verified informational feed version", sf.Feed.Version)
	for _, w := range sf.Feed.Warnings {
		fmt.Printf("[%s] %s\n", w.Category, w.Summary)
	}
	fmt.Println("No network telemetry, remote commands, or blocking performed.")
}
