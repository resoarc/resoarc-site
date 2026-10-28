package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

type hubTestRig struct {
	t       *testing.T
	now     time.Time
	pub     ed25519.PublicKey
	private ed25519.PrivateKey
	path    string
	ledger  *os.File
	hub     *server
}

func newRig(t *testing.T) *hubTestRig {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	rig := &hubTestRig{t: t, now: time.Now().UTC(), pub: pub, private: priv, path: filepath.Join(t.TempDir(), "ledger.jsonl")}
	rig.open(nil)
	t.Cleanup(func() {
		if rig.ledger != nil {
			rig.ledger.Close()
		}
	})
	return rig
}
func (rig *hubTestRig) open(revoked map[string]bool) {
	rig.t.Helper()
	if rig.ledger != nil {
		if err := rig.ledger.Close(); err != nil {
			rig.t.Fatal(err)
		}
	}
	f, err := os.OpenFile(rig.path, os.O_CREATE|os.O_RDWR|os.O_APPEND, 0600)
	if err != nil {
		rig.t.Fatal(err)
	}
	rig.ledger = f
	rig.hub, err = newServer(map[string]ed25519.PublicKey{protocol.NodeID(rig.pub): rig.pub}, revoked, f, func() time.Time { return rig.now })
	if err != nil {
		rig.t.Fatal(err)
	}
}
func (rig *hubTestRig) signed(t *testing.T, n int) protocol.SignedReport {
	t.Helper()
	event := make([]byte, 16)
	for i := 0; i < 16; i++ {
		event[i] = byte(n >> (i % 4 * 8))
	}
	report := protocol.Report{
		Schema: protocol.ReportSchema, NodeID: protocol.NodeID(rig.pub), EventID: hex.EncodeToString(event),
		ObservedAt: rig.now, Kind: "http_probe", TargetPort: 443,
		CampaignFingerprint: "e7f6c011776e8db7cd330b54174fd76f92339faf0c35e882e6d803a95e0e741d",
	}
	sr, err := protocol.SignReport(report, rig.private)
	if err != nil {
		t.Fatal(err)
	}
	return sr
}
func (rig *hubTestRig) post(sr protocol.SignedReport) int {
	rig.t.Helper()
	b, err := json.Marshal(sr)
	if err != nil {
		rig.t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/report", bytes.NewReader(b))
	request.Header.Set("Content-Type", "application/json")
	response := httptest.NewRecorder()
	rig.hub.report(response, request)
	return response.Code
}
func TestReplaySurvivesRestartAndTamperRejected(t *testing.T) {
	rig := newRig(t)
	signed := rig.signed(t, 1)
	if code := rig.post(signed); code != 202 {
		t.Fatalf("initial %d", code)
	}
	rig.open(nil)
	if code := rig.post(signed); code != 409 {
		t.Fatalf("replay after restart: %d", code)
	}
	signed.Report.TargetPort = 80
	if code := rig.post(signed); code != 403 {
		t.Fatalf("tampering: %d", code)
	}
}
func TestRateLimitPersistsAcrossRestart(t *testing.T) {
	rig := newRig(t)
	for i := 1; i <= perNodeMinuteLimit; i++ {
		if code := rig.post(rig.signed(t, i)); code != 202 {
			t.Fatalf("report %d: %d", i, code)
		}
	}
	rig.open(nil)
	if code := rig.post(rig.signed(t, 31)); code != 429 {
		t.Fatalf("limit after restart: %d", code)
	}
	rig.now = rig.now.Add(61 * time.Second)
	if code := rig.post(rig.signed(t, 31)); code != 202 {
		t.Fatalf("limit not lifted: %d", code)
	}
}
func TestRevokedKeyCannotReport(t *testing.T) {
	rig := newRig(t)
	rig.open(map[string]bool{protocol.NodeID(rig.pub): true})
	if code := rig.post(rig.signed(t, 1)); code != 403 {
		t.Fatalf("revoked signed node accepted: %d", code)
	}
}
func TestFailClosedRevocationConfiguration(t *testing.T) {
	rig := newRig(t)
	keys := filepath.Join(t.TempDir(), "allowlist.json")
	b, _ := json.Marshal(map[string]string{protocol.NodeID(rig.pub): hex.EncodeToString(rig.pub)})
	if err := os.WriteFile(keys, b, 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err := loadTrust(keys, filepath.Join(t.TempDir(), "missing.json")); err == nil {
		t.Fatal("missing revocation list accepted")
	}
	rev := filepath.Join(t.TempDir(), "revoked.json")
	data, _ := json.Marshal([]string{protocol.NodeID(rig.pub)})
	if err := os.WriteFile(rev, data, 0600); err != nil {
		t.Fatal(err)
	}
	_, revoked, err := loadTrust(keys, rev)
	if err != nil || !revoked[protocol.NodeID(rig.pub)] {
		t.Fatalf("revocation not loaded: %v", err)
	}
}
func TestOversizedAndUnknownFieldRejected(t *testing.T) {
	rig := newRig(t)
	sr := rig.signed(t, 1)
	b, _ := json.Marshal(sr)
	for _, payload := range [][]byte{
		append([]byte(`{"unknown":true,`), b[1:]...),
		append(b, bytes.Repeat([]byte(" "), 9000)...),
	} {
		req := httptest.NewRequest(http.MethodPost, "/report", bytes.NewReader(payload))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		rig.hub.report(w, req)
		if w.Code != 400 {
			t.Fatalf("unsafe payload accepted: HTTP %d", w.Code)
		}
	}
}
func TestLegacyLedgerReplay(t *testing.T) {
	rig := newRig(t)
	sr := rig.signed(t, 1)
	b, _ := json.Marshal(sr)
	if err := os.WriteFile(rig.path, append(b, '\n'), 0600); err != nil {
		t.Fatal(err)
	}
	// Legacy histories require deliberate review and explicit bootstrap.
	if err := os.Remove(rig.path + ".head"); err != nil {
		t.Fatal(err)
	}
	if err := bootstrapLedgerHead(rig.ledger); err != nil {
		t.Fatal(err)
	}
	rig.open(nil)
	if code := rig.post(sr); code != 409 {
		t.Fatalf("legacy replay %d", code)
	}
}
