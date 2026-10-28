// Offline manifest signer/verifier for operator-controlled ledger rollover.
// The private key MUST remain off-HUB. This utility never deletes evidence.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/archive"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

func now() time.Time { return time.Now().UTC() }
func main() {
	mode := flag.String("mode", "verify", "sign, verify or prepare")
	input := flag.String("manifest", "", "plain manifest for sign; signed manifest for verify/prepare")
	key := flag.String("key", "", "OFF-HUB signer private key for sign only")
	pubFile := flag.String("pub", "", "pinned archive root public key for verify/prepare")
	tip := flag.String("tip", "", "independently pinned signed manifest digest for verify/prepare")
	active := flag.String("active", "", "active ledger path for verify (need not exist)")
	out := flag.String("out", "", "new signed manifest (sign) or new generation directory (prepare)")
	flag.Parse()
	if *input == "" {
		log.Fatal("-manifest required")
	}
	switch *mode {
	case "sign":
		if *key == "" || *out == "" || *pubFile != "" || *tip != "" {
			log.Fatal("sign requires -key and -out, without public verification arguments")
		}
		b, err := os.ReadFile(*input)
		if err != nil {
			log.Fatal(err)
		}
		if len(b) > 131072 {
			log.Fatal("manifest too large")
		}
		var m archive.Manifest
		if err = json.Unmarshal(b, &m); err != nil {
			log.Fatal(err)
		}
		priv, err := witness.ReadPrivateKey(*key)
		if err != nil {
			log.Fatal(err)
		}
		signed, err := archive.Sign(m, priv)
		if err != nil {
			log.Fatal(err)
		}
		raw, err := json.Marshal(signed)
		if err != nil {
			log.Fatal(err)
		}
		f, err := os.OpenFile(*out, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if err != nil {
			log.Fatal(err)
		}
		_, err = f.Write(raw)
		if err == nil {
			err = f.Sync()
		}
		closeErr := f.Close()
		if err != nil {
			log.Fatal(err)
		}
		if closeErr != nil {
			log.Fatal(closeErr)
		}
		hash, _ := archive.Hash(signed)
		fmt.Printf("SIGNED archive_manifest_tip=%s\nPublish/pin this tip OFF-HUB, and protect the signing key.\n", hash)
	case "verify", "prepare":
		if *pubFile == "" || *tip == "" || *key != "" {
			log.Fatal("verify/prepare requires pinned -pub and -tip, without private key")
		}
		b, err := os.ReadFile(*pubFile)
		if err != nil {
			log.Fatal(err)
		}
		pub, err := protocol.PublicFromHex(strings.TrimSpace(string(b)))
		if err != nil {
			log.Fatal(err)
		}
		if *mode == "verify" {
			if *active == "" {
				log.Fatal("verify needs -active")
			}
			seen, _, err := archive.Load(*input, pub, *tip, *active, now())
			if err != nil {
				log.Fatal(err)
			}
			fmt.Printf("VERIFIED witnessed archived replay identifiers=%d\n", len(seen))
		} else {
			if *out == "" {
				log.Fatal("prepare needs -out (new directory)")
			}
			if err := archive.Prepare(*input, pub, *tip, *out); err != nil {
				log.Fatal(err)
			}
			fmt.Printf("PREPARED empty generation: %s\nHUB requires -archives, -archive-root, -archive-tip on EVERY start. Never delete witnessed archives.\n", *out)
		}
	default:
		log.Fatal("unsupported mode")
	}
}
