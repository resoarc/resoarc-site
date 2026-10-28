// Run this binary OFF-HUB on a closed copy of ledger + .head.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"flag"
	"fmt"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
	"log"
	"os"
	"time"
)

func main() {
	mode := flag.String("mode", "verify", "attest or verify")
	ledger := flag.String("ledger", "", "path to immutable offline snapshot; requires adjacent .head")
	history := flag.String("history", "", "off-HUB append-only signed history")
	pub := flag.String("pub", "", "pinned witness public key for verify")
	priv := flag.String("key", "", "offline witness signing private key for attest")
	tip := flag.String("expected-tip", "", "independently pinned SHA256 last witness tip (required except genesis)")
	bootstrap := flag.Bool("bootstrap-history", false, "explicit one-time first attestation; never use to repair lost history")
	flag.Parse()
	if *ledger == "" || *history == "" {
		log.Fatal("-ledger and -history are required")
	}
	switch *mode {
	case "attest":
		if *priv == "" || *pub != "" {
			log.Fatal("-key required for attest; never put it on HUB")
		}
		if err := witness.CheckOffHostInputs(*ledger, *history, *priv); err != nil {
			log.Fatal(err)
		}
		key, err := witness.ReadPrivateKey(*priv)
		if err != nil {
			log.Fatal(err)
		}
		signed, hash, err := witness.Attest(*ledger, *history, key, time.Now().UTC(), *tip, *bootstrap)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("WITNESSED rows=%d sequence=%d tip=%s\nPin this tip independently. Signing key must remain OFF-HUB.\n", signed.Checkpoint.Rows, signed.Checkpoint.Sequence, hash)
	case "verify":
		if *pub == "" || *priv != "" || *tip == "" || *bootstrap {
			log.Fatal("-pub and -expected-tip are required for anchored verification")
		}
		key, err := witness.ReadPublicKey(*pub)
		if err != nil {
			log.Fatal(err)
		}
		measured, hash, err := witness.Audit(*ledger, *history, key, *tip)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("VERIFIED rows=%d digest=%s witnessed_tip=%s\n", measured.Rows, measured.Digest, hash)
	case "sha256": // Convenient hash for a separate immutable anchor, NOT a signature.
		b, err := os.ReadFile(*history)
		if err != nil {
			log.Fatal(err)
		}
		d := sha256.Sum256(b)
		fmt.Println(hex.EncodeToString(d[:]))
	default:
		log.Fatal("unsupported mode")
	}
}
