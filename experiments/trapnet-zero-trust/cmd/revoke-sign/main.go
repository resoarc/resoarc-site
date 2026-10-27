// Offline tool. NEVER copy this signing key onto the HUB machine.
package main

import (
	"encoding/json"
	"flag"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"log"
	"os"
	"sort"
	"strings"
	"time"
)

func main() {
	keyPath := flag.String("key", "", "offline Ed25519 private key path")
	output := flag.String("out", "", "output signed revocation JSON")
	ids := flag.String("ids", "", "comma-separated node IDs (empty means no nodes revoked)")
	version := flag.Uint64("version", 0, "strictly increasing revocation sequence")
	flag.Parse()
	if *keyPath == "" || *output == "" || *version == 0 {
		log.Fatal("-key, -out, -version required")
	}
	raw, err := os.ReadFile(*keyPath)
	if err != nil {
		log.Fatal(err)
	}
	priv, err := protocol.PrivateFromHex(strings.TrimSpace(string(raw)))
	if err != nil {
		log.Fatal(err)
	}
	nodes := []string{}
	if strings.TrimSpace(*ids) != "" {
		for _, v := range strings.Split(*ids, ",") {
			nodes = append(nodes, strings.TrimSpace(v))
		}
	}
	sort.Strings(nodes)
	now := time.Now().UTC()
	list := protocol.RevocationList{Schema: protocol.RevocationSchema, Version: *version, IssuedAt: now, ExpiresAt: now.Add(12 * time.Hour), NodeIDs: nodes}
	if err = list.Validate(now); err != nil {
		log.Fatal(err)
	}
	signed, err := protocol.SignRevocations(list, priv)
	if err != nil {
		log.Fatal(err)
	}
	b, err := json.MarshalIndent(signed, "", "  ")
	if err != nil {
		log.Fatal(err)
	}
	if err = os.WriteFile(*output, append(b, '\n'), 0600); err != nil {
		log.Fatal(err)
	}
}
