package witness

import (
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func testRig(t *testing.T) (string, string, ed25519.PublicKey, ed25519.PrivateKey) {
	t.Helper()
	dir := t.TempDir()
	ledger := filepath.Join(dir, "hub-copy.jsonl")
	history := filepath.Join(dir, "external.witness.jsonl")
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(ledger, nil, 0600); err != nil {
		t.Fatal(err)
	}
	appendEvent(t, ledger, 1)
	return ledger, history, pub, priv
}
func appendEvent(t *testing.T, path string, n int) {
	t.Helper()
	var h Head
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	h = Head{Revision: 1, Digest: zeroDigest}
	if len(b) > 0 {
		h, err = Measure(path, nil)
		if err != nil {
			t.Fatal(err)
		}
	}
	row := []byte(`{"event":` + string('0'+rune(n)) + `}` + "\n")
	f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = f.Write(row); err != nil {
		t.Fatal(err)
	}
	if err = f.Close(); err != nil {
		t.Fatal(err)
	}
	// Test uses the real HUB compatible digest algorithm.
	next, err := Measure(path, nil)
	if err != nil {
		t.Fatal(err)
	}
	if next.Rows != h.Rows+1 {
		t.Fatal("row count not advanced")
	}
	encoded, _ := json.Marshal(next)
	if err = os.WriteFile(path+".head", encoded, 0600); err != nil {
		t.Fatal(err)
	}
}
func TestWitnessAttestAndAudit(t *testing.T) {
	ledger, history, pub, priv := testRig(t)
	now := time.Date(2026, 10, 27, 12, 0, 0, 0, time.UTC)
	first, tip, err := Attest(ledger, history, priv, now, "", true)
	if err != nil {
		t.Fatal(err)
	}
	if first.Checkpoint.Sequence != 1 || first.Checkpoint.Rows != 1 || tip == "" {
		t.Fatal("wrong first witness")
	}
	if _, _, err = Audit(ledger, history, pub, tip); err != nil {
		t.Fatal(err)
	}
	appendEvent(t, ledger, 2)
	if _, _, err = Audit(ledger, history, pub, tip); err != nil {
		t.Fatal("strict snapshot audit should reject uncheckpointed tail: ", err)
	}
	second, tip2, err := Attest(ledger, history, priv, now.Add(time.Minute), tip, false)
	if err != nil {
		t.Fatal(err)
	}
	if second.Checkpoint.Sequence != 2 || second.Checkpoint.PreviousHash != tip {
		t.Fatal("broken chain")
	}
	if _, _, err = Audit(ledger, history, pub, tip2); err != nil {
		t.Fatal(err)
	}
	if _, _, err = Attest(ledger, history, priv, now.Add(2*time.Minute), tip2, false); err == nil {
		t.Fatal("duplicate snapshot attested")
	}
}
func TestRewritingLedgerAndLocalHeadIsCaught(t *testing.T) {
	ledger, history, pub, priv := testRig(t)
	_, tip, err := Attest(ledger, history, priv, time.Now().UTC(), "", true)
	if err != nil {
		t.Fatal(err)
	}
	// Privileged HUB attacker rewrites the evidence AND recomputes local head.
	b, err := os.ReadFile(ledger)
	if err != nil {
		t.Fatal(err)
	}
	b = bytes.ReplaceAll(b, []byte(`"event":1`), []byte(`"event":9`))
	if err = os.WriteFile(ledger, b, 0600); err != nil {
		t.Fatal(err)
	}
	modified, err := Measure(ledger, nil)
	if err != nil {
		t.Fatal(err)
	}
	h, _ := json.Marshal(modified)
	if err = os.WriteFile(ledger+".head", h, 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err = Audit(ledger, history, pub, tip); err == nil {
		t.Fatal("privileged rewrite not detected")
	}
}
func TestHistoryAlterationAndRollbackAnchoring(t *testing.T) {
	ledger, history, pub, priv := testRig(t)
	now := time.Now().UTC()
	_, tip1, err := Attest(ledger, history, priv, now, "", true)
	if err != nil {
		t.Fatal(err)
	}
	prior, _ := os.ReadFile(history)
	appendEvent(t, ledger, 2)
	_, tip2, err := Attest(ledger, history, priv, now.Add(time.Minute), tip1, false)
	if err != nil {
		t.Fatal(err)
	}
	if tip1 == tip2 {
		t.Fatal("same tip")
	}
	if err = os.WriteFile(history, prior, 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err = Audit(ledger, history, pub, tip2); err == nil {
		t.Fatal("history rollback with pinned tip not detected")
	}
	original, _ := os.ReadFile(history)
	if err = os.WriteFile(history, bytes.Replace(original, []byte("trapnet.witness.v0.1"), []byte("trapnet.witness.v0.2"), 1), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err = ReadHistory(history, pub); err == nil {
		t.Fatal("modified signed history accepted")
	}
}
func TestMissingOrTruncatedLedgerRejected(t *testing.T) {
	ledger, history, pub, priv := testRig(t)
	_, tip, err := Attest(ledger, history, priv, time.Now().UTC(), "", true)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(ledger, []byte(`{"event":1}`), 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err = Audit(ledger, history, pub, tip); err == nil {
		t.Fatal("torn ledger accepted")
	}
	if err = os.Remove(ledger + ".head"); err != nil {
		t.Fatal(err)
	}
	if _, _, err = Audit(ledger, history, pub, tip); err == nil {
		t.Fatal("missing local checkpoint accepted")
	}
}
func TestWitnessSnapshotFailClosed(t *testing.T) {
	ledger, history, _, priv := testRig(t)
	if err := os.WriteFile(ledger+".head", []byte(`{"revision":1,"rows":123,"digest":"`+strings.Repeat("f", 64)+`"}`), 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err := Attest(ledger, history, priv, time.Now().UTC(), "", true); err == nil {
		t.Fatal("inconsistent head witnessed")
	}
}

func TestAttestRequiresPinnedContinuityAndExplicitGenesis(t *testing.T) {
	ledger, history, _, priv := testRig(t)
	now := time.Now().UTC()
	if _, _, err := Attest(ledger, history, priv, now, "", false); err == nil {
		t.Fatal("unsigned genesis without explicit bootstrap accepted")
	}
	if _, _, err := Attest(ledger, history, priv, now, strings.Repeat("f", 64), true); err == nil {
		t.Fatal("genesis unexpectedly accepted a prior anchor")
	}
	_, tip, err := Attest(ledger, history, priv, now, "", true)
	if err != nil {
		t.Fatal(err)
	}
	appendEvent(t, ledger, 2)
	if _, _, err := Attest(ledger, history, priv, now.Add(time.Minute), "", false); err == nil {
		t.Fatal("continued attestation without independent anchor")
	}
	if _, _, err := Attest(ledger, history, priv, now.Add(time.Minute), strings.Repeat("f", 64), false); err == nil {
		t.Fatal("continued attestation with false anchor")
	}
	if _, _, err := Attest(ledger, history, priv, now.Add(time.Minute), tip, true); err == nil {
		t.Fatal("bootstrap flag accepted on existing history")
	}
	_, tip2, err := Attest(ledger, history, priv, now.Add(time.Minute), tip, false)
	if err != nil {
		t.Fatal(err)
	}
	if tip == tip2 {
		t.Fatal("tip not advanced")
	}
}

func TestAttestRejectsRolledBackHistoryDespiteValidSignature(t *testing.T) {
	ledger, history, _, priv := testRig(t)
	now := time.Now().UTC()
	_, tip1, err := Attest(ledger, history, priv, now, "", true)
	if err != nil {
		t.Fatal(err)
	}
	backup, err := os.ReadFile(history)
	if err != nil {
		t.Fatal(err)
	}
	appendEvent(t, ledger, 2)
	_, tip2, err := Attest(ledger, history, priv, now.Add(time.Minute), tip1, false)
	if err != nil {
		t.Fatal(err)
	}
	appendEvent(t, ledger, 3)
	// A complete, valid old history is restored, with the correct old signature.
	// Only the externally pinned tip2 prevents a secret fork.
	if err := os.WriteFile(history, backup, 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err := Attest(ledger, history, priv, now.Add(2*time.Minute), tip2, false); err == nil {
		t.Fatal("history rollback went undetected during new attestation")
	}
}

func TestLargeMalformedInputsBoundedAndRejected(t *testing.T) {
	ledger, history, pub, priv := testRig(t)
	now := time.Now().UTC()
	_, tip, err := Attest(ledger, history, priv, now, "", true)
	if err != nil {
		t.Fatal(err)
	}
	// A malformed line much larger than maxHistoryRow must be rejected.
	f, err := os.OpenFile(history, os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	_, err = f.Write(append(bytes.Repeat([]byte("x"), maxHistoryRow+1), '\n'))
	if err != nil {
		t.Fatal(err)
	}
	if err = f.Close(); err != nil {
		t.Fatal(err)
	}
	if _, _, err := Audit(ledger, history, pub, tip); err == nil {
		t.Fatal("oversized witness row accepted")
	}
	if _, err := ReadHistory(history, pub); err == nil {
		t.Fatal("malformed history accepted")
	}
}
