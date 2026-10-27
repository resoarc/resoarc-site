// Sensor is an opt-in, one-shot reporter, NOT a network-facing honeypot.
package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

func main() {
	key := flag.String("key", "", "private.hex location")
	url := flag.String("hub", "http://127.0.0.1:8788/report", "loopback test HUB endpoint")
	kind := flag.String("kind", "http_probe", "event category")
	port := flag.Int("port", 80, "target port")
	fingerprint := flag.String("fingerprint", "demo-non-ip", "non-PII campaign characteristic; never send raw IP or payload")
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
	pub := priv.Public().(ed25519.PublicKey)
	id, err := protocol.NewEventID()
	if err != nil {
		panic(err)
	}
	hash := sha256.Sum256([]byte(*fingerprint))
	r := protocol.Report{Schema: protocol.ReportSchema, NodeID: protocol.NodeID(pub), EventID: id, ObservedAt: time.Now().UTC(), Kind: *kind, TargetPort: *port, CampaignFingerprint: hex.EncodeToString(hash[:])}
	if err = r.Validate(time.Now()); err != nil {
		panic(err)
	}
	sr, err := protocol.SignReport(r, priv)
	if err != nil {
		panic(err)
	}
	b, _ := json.Marshal(sr)
	// Demo intentionally refuses remote or public upload before TLS/consent controls are implemented.
	if *url != "http://127.0.0.1:8788/report" {
		panic("MVP permits loopback endpoint only")
	}
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Post(*url, "application/json", bytes.NewReader(b))
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	reply, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
	fmt.Printf("status=%d response=%s\n", resp.StatusCode, string(reply))
	if resp.StatusCode != http.StatusAccepted {
		os.Exit(1)
	}
}
