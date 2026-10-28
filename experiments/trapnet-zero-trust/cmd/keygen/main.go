package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"os"
	"path/filepath"
)

func main() {
	dir := flag.String("out", "", "new directory for private/public keys (must not exist)")
	flag.Parse()
	if *dir == "" {
		panic("-out directory required")
	}
	if err := os.Mkdir(*dir, 0700); err != nil {
		panic(err)
	}
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		panic(err)
	}
	if err = os.WriteFile(filepath.Join(*dir, "private.hex"), []byte(hex.EncodeToString(priv)+"\n"), 0600); err != nil {
		panic(err)
	}
	if err = os.WriteFile(filepath.Join(*dir, "public.hex"), []byte(hex.EncodeToString(pub)+"\n"), 0644); err != nil {
		panic(err)
	}
	info := map[string]string{"node_id": protocol.NodeID(pub), "public_key": hex.EncodeToString(pub)}
	b, _ := json.MarshalIndent(info, "", "  ")
	if err = os.WriteFile(filepath.Join(*dir, "node.json"), b, 0644); err != nil {
		panic(err)
	}
	fmt.Println("created keypair; private.hex MUST remain private. Node ID:", protocol.NodeID(pub))
}
