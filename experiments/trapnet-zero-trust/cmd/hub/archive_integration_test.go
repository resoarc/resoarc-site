package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/archive"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

func TestWitnessedRolloverPreservesReplayAndRateLimit(t *testing.T) {
	rig := newRig(t)
	first := rig.signed(t, 1)
	if code := rig.post(first); code != http.StatusAccepted {
		t.Fatalf("first report: %d", code)
	}
	if err := rig.ledger.Close(); err != nil {
		t.Fatal(err)
	}
	rig.ledger = nil
	d := t.TempDir()
	witnessPub, witnessPriv, _ := ed25519.GenerateKey(rand.Reader)
	history := filepath.Join(d, "witness-history.jsonl")
	_, tip, err := witness.Attest(rig.path, history, witnessPriv, rig.now.Add(time.Minute), "", true)
	if err != nil {
		t.Fatal(err)
	}
	witnessPubPath := filepath.Join(d, "witness-public.hex")
	if err := os.WriteFile(witnessPubPath, []byte(hex.EncodeToString(witnessPub)), 0600); err != nil {
		t.Fatal(err)
	}
	head, err := witness.Snapshot(rig.path, nil)
	if err != nil {
		t.Fatal(err)
	}
	rootPub, rootPriv, _ := ed25519.GenerateKey(rand.Reader)
	m := archive.Manifest{Schema: archive.Schema, Generation: 2, Segments: []archive.Segment{{Ledger: rig.path, History: history, WitnessPublic: witnessPubPath, ExpectedTip: tip, Rows: head.Rows, Digest: head.Digest}}}
	sm, err := archive.Sign(m, rootPriv)
	if err != nil {
		t.Fatal(err)
	}
	manifest := filepath.Join(d, "signed-manifest.json")
	b, _ := json.Marshal(sm)
	if err := os.WriteFile(manifest, b, 0600); err != nil {
		t.Fatal(err)
	}
	hash, _ := archive.Hash(sm)
	newDir := filepath.Join(d, "generation-2")
	if err := archive.Prepare(manifest, rootPub, hash, newDir); err != nil {
		t.Fatal(err)
	}
	rig.path = filepath.Join(newDir, "ledger.jsonl")
	rig.open(nil)
	if err := rig.hub.restoreArchivedReplay(manifest, rootPub, hash); err != nil {
		t.Fatal(err)
	}
	if got := rig.post(first); got != http.StatusConflict {
		t.Fatalf("archived replay accepted: %d", got)
	}
	if got := rig.post(rig.signed(t, 2)); got != http.StatusAccepted {
		t.Fatalf("new generation did not admit fresh evidence: %d", got)
	}
	// Reboot new active generation and reconstruct replay from both locations.
	rig.open(nil)
	if err := rig.hub.restoreArchivedReplay(manifest, rootPub, hash); err != nil {
		t.Fatal(err)
	}
	if got := rig.post(first); got != http.StatusConflict {
		t.Fatalf("archived replay after reboot: %d", got)
	}
	if got := rig.post(rig.signed(t, 2)); got != http.StatusConflict {
		t.Fatalf("new-generation replay after reboot: %d", got)
	}
	if _, _, err := archive.Load(manifest, rootPub, hash, rig.path, rig.now.Add(2*time.Hour)); err != nil {
		t.Fatal("historic attest must not expire by wall clock: ", err)
	}
}
