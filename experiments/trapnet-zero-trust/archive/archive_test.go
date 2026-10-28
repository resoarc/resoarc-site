package archive

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

func makeArchive(t *testing.T) (string, ed25519.PublicKey, string, string) {
	t.Helper()
	d := t.TempDir()
	now := time.Now().UTC().Truncate(time.Second)
	node, priv, _ := ed25519.GenerateKey(rand.Reader)
	f := sha256.Sum256([]byte("observed-test"))
	r := protocol.Report{Schema: protocol.ReportSchema, NodeID: protocol.NodeID(node), EventID: "0123456789abcdef0123456789abcdef", ObservedAt: now, Kind: "http_probe", TargetPort: 443, CampaignFingerprint: hex.EncodeToString(f[:])}
	signed, err := protocol.SignReport(r, priv)
	if err != nil {
		t.Fatal(err)
	}
	ledger := filepath.Join(d, "archive.jsonl")
	row, _ := json.Marshal(Event{ReceivedAt: now, Evidence: signed})
	if err = os.WriteFile(ledger, append(row, '\n'), 0600); err != nil {
		t.Fatal(err)
	}
	head, err := witness.Measure(ledger, nil)
	if err != nil {
		t.Fatal(err)
	}
	b, _ := json.Marshal(head)
	if err = os.WriteFile(ledger+".head", b, 0600); err != nil {
		t.Fatal(err)
	}
	wpub, wpriv, _ := ed25519.GenerateKey(rand.Reader)
	wpubPath := filepath.Join(d, "witness.pub")
	if err = os.WriteFile(wpubPath, []byte(hex.EncodeToString(wpub)), 0600); err != nil {
		t.Fatal(err)
	}
	history := filepath.Join(d, "history.jsonl")
	_, wTip, err := witness.Attest(ledger, history, wpriv, now, "", true)
	if err != nil {
		t.Fatal(err)
	}
	m := Manifest{Schema: Schema, Generation: 2, Segments: []Segment{{Ledger: ledger, History: history, WitnessPublic: wpubPath, ExpectedTip: wTip, Rows: head.Rows, Digest: head.Digest}}}
	apub, apriv, _ := ed25519.GenerateKey(rand.Reader)
	sm, err := Sign(m, apriv)
	if err != nil {
		t.Fatal(err)
	}
	p := filepath.Join(d, "signed-archives.json")
	b, _ = json.Marshal(sm)
	if err = os.WriteFile(p, b, 0600); err != nil {
		t.Fatal(err)
	}
	pin, err := Hash(sm)
	if err != nil {
		t.Fatal(err)
	}
	return p, apub, pin, r.NodeID + ":" + r.EventID
}
func TestRestoreReplayFromPinnedWitnessedArchive(t *testing.T) {
	p, pub, pin, id := makeArchive(t)
	seen, recent, err := Load(p, pub, pin, filepath.Join(t.TempDir(), "active.jsonl"), time.Now().UTC())
	if err != nil {
		t.Fatal(err)
	}
	if !seen[id] || len(recent) != 1 {
		t.Fatalf("replay not recovered: %v %v", seen, recent)
	}
}
func TestRejectUnpinnedWrongSignedAndMissingEvidence(t *testing.T) {
	p, pub, _, _ := makeArchive(t)
	active := filepath.Join(t.TempDir(), "active.jsonl")
	if _, _, err := Load(p, pub, strings.Repeat("0", 64), active, time.Now()); err == nil {
		t.Fatal("different manifest pin accepted")
	}
	b, _ := os.ReadFile(p)
	var sm SignedManifest
	if err := json.Unmarshal(b, &sm); err != nil {
		t.Fatal(err)
	}
	sm.Manifest.Segments[0].Rows++
	b, _ = json.Marshal(sm)
	if err := os.WriteFile(p, b, 0600); err != nil {
		t.Fatal(err)
	}
	pin2, _ := Hash(sm)
	if _, _, err := Load(p, pub, pin2, active, time.Now()); err == nil {
		t.Fatal("tampered manifest accepted")
	}
}
func TestRejectWitnessedLedgerMutation(t *testing.T) {
	p, pub, pin, _ := makeArchive(t)
	b, _ := os.ReadFile(p)
	var sm SignedManifest
	json.Unmarshal(b, &sm)
	ledger := sm.Manifest.Segments[0].Ledger
	data, _ := os.ReadFile(ledger)
	data[15] ^= 1
	if err := os.WriteFile(ledger, data, 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err := Load(p, pub, pin, filepath.Join(t.TempDir(), "active"), time.Now()); err == nil {
		t.Fatal("modified witnessed evidence accepted")
	}
}
func TestRejectMissingWitnessAndUnsafePaths(t *testing.T) {
	p, pub, pin, _ := makeArchive(t)
	b, _ := os.ReadFile(p)
	var sm SignedManifest
	json.Unmarshal(b, &sm)
	if err := os.Remove(sm.Manifest.Segments[0].History); err != nil {
		t.Fatal(err)
	}
	if _, _, err := Load(p, pub, pin, filepath.Join(t.TempDir(), "active"), time.Now()); err == nil {
		t.Fatal("missing history accepted")
	}
	sm.Manifest.Segments[0].History = "./relative.jsonl"
	if err := Check(sm.Manifest); err == nil {
		t.Fatal("relative evidence path accepted")
	}
}
func TestPrepareNewGenerationFailClosed(t *testing.T) {
	p, pub, tip, id := makeArchive(t)
	next := filepath.Join(t.TempDir(), "generation-0002")
	if err := Prepare(p, pub, tip, next); err != nil {
		t.Fatal(err)
	}
	for _, suffix := range []string{"", ".head", ".archives-required"} {
		if _, err := os.Stat(filepath.Join(next, "ledger.jsonl") + suffix); err != nil {
			t.Fatal(err)
		}
	}
	if b, err := os.ReadFile(filepath.Join(next, "ledger.jsonl")); err != nil || len(b) != 0 {
		t.Fatal("prepared ledger not empty")
	}
	if err := Prepare(p, pub, tip, next); err == nil {
		t.Fatal("existing generation overwritten")
	}
	seen, _, err := Load(p, pub, tip, filepath.Join(next, "ledger.jsonl"), time.Now().UTC())
	if err != nil || !seen[id] {
		t.Fatalf("missing archived replay after generation switch: %v", err)
	}
	if err := Prepare(p, pub, strings.Repeat("0", 64), filepath.Join(t.TempDir(), "wrong-pin")); err == nil {
		t.Fatal("bad pinned tip could create new generation")
	}
}
func TestArchiveManifestRequiresAllGenerations(t *testing.T) {
	p, _, _, _ := makeArchive(t)
	b, _ := os.ReadFile(p)
	var sm SignedManifest
	json.Unmarshal(b, &sm)
	sm.Manifest.Generation = 3
	if err := Check(sm.Manifest); err == nil {
		t.Fatal("missing archive generation accepted")
	}
}
