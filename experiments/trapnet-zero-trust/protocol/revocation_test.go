package protocol

import (
	"crypto/ed25519"
	"crypto/rand"
	"testing"
	"time"
)

func TestRevocationSignaturesAndStrictSemantics(t *testing.T) {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	now := time.Now().UTC()
	list := RevocationList{Schema: RevocationSchema, Version: 1, IssuedAt: now, ExpiresAt: now.Add(time.Hour), NodeIDs: []string{"0123456789abcdef0123456789abcdef"}}
	signed, err := SignRevocations(list, priv)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = VerifyRevocations(signed, pub, now); err != nil {
		t.Fatal(err)
	}
	signed.List.NodeIDs = nil
	if _, err = VerifyRevocations(signed, pub, now); err == nil {
		t.Fatal("tampered revocations accepted")
	}
	signed, _ = SignRevocations(list, priv)
	if _, err = VerifyRevocations(signed, pub, now.Add(2*time.Hour)); err == nil {
		t.Fatal("expired list accepted")
	}
	list.NodeIDs = []string{"fedcba9876543210fedcba9876543210", "0123456789abcdef0123456789abcdef"}
	if err = list.Validate(now); err == nil {
		t.Fatal("unsorted IDs accepted")
	}
	list.NodeIDs = []string{"0123456789abcdef0123456789abcdef", "0123456789abcdef0123456789abcdef"}
	if err = list.Validate(now); err == nil {
		t.Fatal("duplicate IDs accepted")
	}
}
