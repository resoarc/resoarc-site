package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func writeRevocations(t *testing.T, path string, priv ed25519.PrivateKey, version uint64, now time.Time, ids []string) {
	t.Helper()
	list := protocol.RevocationList{Schema: protocol.RevocationSchema, Version: version, IssuedAt: now, ExpiresAt: now.Add(time.Hour), NodeIDs: ids}
	signed, err := protocol.SignRevocations(list, priv)
	if err != nil {
		t.Fatal(err)
	}
	b, err := json.Marshal(signed)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(path, b, 0600); err != nil {
		t.Fatal(err)
	}
}
func TestSignedRevocationHotReloadAndRollbackResistance(t *testing.T) {
	rig := newRig(t)
	rootPub, rootPriv, _ := ed25519.GenerateKey(rand.Reader)
	dir := t.TempDir()
	root := filepath.Join(dir, "root.hex")
	if err := os.WriteFile(root, []byte(hex.EncodeToString(rootPub)), 0600); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "revocations.json")
	writeRevocations(t, path, rootPriv, 1, rig.now, nil)
	source, err := newRevocationSource(path, root)
	if err != nil {
		t.Fatal(err)
	}
	rig.hub.signedRevocations = source
	if code := rig.post(rig.signed(t, 1)); code != 202 {
		t.Fatalf("initial signed list %d", code)
	}
	writeRevocations(t, path, rootPriv, 2, rig.now, []string{protocol.NodeID(rig.pub)})
	if code := rig.post(rig.signed(t, 2)); code != 403 {
		t.Fatalf("revoked node %d", code)
	}
	if _, err = os.Stat(path + ".state"); err != nil {
		t.Fatal(err)
	}
	// A signed but older list is invalid even after an HUB restart.
	source, err = newRevocationSource(path, root)
	if err != nil {
		t.Fatal(err)
	}
	rig.hub.signedRevocations = source
	writeRevocations(t, path, rootPriv, 1, rig.now, nil)
	if code := rig.post(rig.signed(t, 3)); code != 503 {
		t.Fatalf("rollback accepted: %d", code)
	}
	// Same-version equivocation is also forbidden.
	writeRevocations(t, path, rootPriv, 2, rig.now, nil)
	if code := rig.post(rig.signed(t, 4)); code != 503 {
		t.Fatalf("same-version equivocation accepted: %d", code)
	}
	if err = os.WriteFile(path, []byte(`{"list":{},"signature":"bad"}`), 0600); err != nil {
		t.Fatal(err)
	}
	if code := rig.post(rig.signed(t, 5)); code != 503 {
		t.Fatalf("invalid signature accepted: %d", code)
	}
	if err = os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if code := rig.post(rig.signed(t, 6)); code != 503 {
		t.Fatalf("missing revocation source accepted: %d", code)
	}
}
func TestRevocationConcurrentRequests(t *testing.T) {
	rig := newRig(t)
	rootPub, rootPriv, _ := ed25519.GenerateKey(rand.Reader)
	dir := t.TempDir()
	root := filepath.Join(dir, "root.hex")
	path := filepath.Join(dir, "list.json")
	if err := os.WriteFile(root, []byte(hex.EncodeToString(rootPub)), 0600); err != nil {
		t.Fatal(err)
	}
	writeRevocations(t, path, rootPriv, 1, rig.now, nil)
	source, err := newRevocationSource(path, root)
	if err != nil {
		t.Fatal(err)
	}
	rig.hub.signedRevocations = source
	var wg sync.WaitGroup
	results := make(chan int, 20)
	for i := 1; i <= 20; i++ {
		wg.Add(1)
		go func(i int) { defer wg.Done(); results <- rig.post(rig.signed(t, i)) }(i)
	}
	wg.Wait()
	close(results)
	for code := range results {
		if code != 202 {
			t.Fatalf("concurrent signed report failed: %d", code)
		}
	}
}
func TestExpiredRevocationsFailClosed(t *testing.T) {
	rig := newRig(t)
	rootPub, rootPriv, _ := ed25519.GenerateKey(rand.Reader)
	dir := t.TempDir()
	root := filepath.Join(dir, "root.hex")
	path := filepath.Join(dir, "list.json")
	if err := os.WriteFile(root, []byte(hex.EncodeToString(rootPub)), 0600); err != nil {
		t.Fatal(err)
	}
	writeRevocations(t, path, rootPriv, 1, rig.now.Add(-2*time.Hour), nil)
	source, err := newRevocationSource(path, root)
	if err != nil {
		t.Fatal(err)
	}
	rig.hub.signedRevocations = source
	if code := rig.post(rig.signed(t, 1)); code != 503 {
		t.Fatalf("expired revocation accepted: %d", code)
	}
}
