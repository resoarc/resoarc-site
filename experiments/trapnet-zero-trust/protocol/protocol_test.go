package protocol

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"testing"
	"time"
)

func sample(t *testing.T) (Report, ed25519.PublicKey, ed25519.PrivateKey) {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256([]byte("test"))
	return Report{Schema: ReportSchema, NodeID: NodeID(pub), EventID: "0123456789abcdef0123456789abcdef", ObservedAt: time.Now().UTC(), Kind: "http_probe", TargetPort: 443, CampaignFingerprint: hex.EncodeToString(sum[:])}, pub, priv
}
func TestSignedReportRejectsForgeryAndTampering(t *testing.T) {
	r, pub, priv := sample(t)
	sr, _ := SignReport(r, priv)
	if err := VerifyReport(sr, pub, time.Now()); err != nil {
		t.Fatal(err)
	}
	sr.Report.TargetPort = 22
	if VerifyReport(sr, pub, time.Now()) == nil {
		t.Fatal("tampered report accepted")
	}
	sr, _ = SignReport(r, priv)
	other, _, _ := ed25519.GenerateKey(rand.Reader)
	if VerifyReport(sr, other, time.Now()) == nil {
		t.Fatal("wrong key accepted")
	}
}
func TestRejectStaleAndMalformed(t *testing.T) {
	r, pub, priv := sample(t)
	r.ObservedAt = time.Now().Add(-20 * time.Minute)
	sr, _ := SignReport(r, priv)
	if VerifyReport(sr, pub, time.Now()) == nil {
		t.Fatal("stale event accepted")
	}
	r.ObservedAt = time.Now()
	r.CampaignFingerprint = "not-a-fingerprint"
	sr, _ = SignReport(r, priv)
	if VerifyReport(sr, pub, time.Now()) == nil {
		t.Fatal("malformed fingerprint accepted")
	}
}
func TestSignedFeedValidation(t *testing.T) {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	now := time.Now().UTC()
	f := Feed{Schema: FeedSchema, Version: 1, IssuedAt: now, ExpiresAt: now.Add(time.Hour), Warnings: []Warning{{Category: "notice", Summary: "testing"}}}
	sf, _ := SignFeed(f, priv)
	if err := VerifyFeed(sf, pub, now); err != nil {
		t.Fatal(err)
	}
	sf.Feed.Warnings[0].Summary = "malicious alteration"
	if VerifyFeed(sf, pub, now) == nil {
		t.Fatal("tampering accepted")
	}
	sf, _ = SignFeed(f, priv)
	if VerifyFeed(sf, pub, now.Add(2*time.Hour)) == nil {
		t.Fatal("expired feed accepted")
	}
}
