package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestGuardianStateLockFailsClosed(t *testing.T) {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	now := time.Now().UTC()
	path := filepath.Join(t.TempDir(), "guardian-state.json")
	f := protocol.Feed{Schema: protocol.FeedSchema, Version: 1, IssuedAt: now, ExpiresAt: now.Add(time.Hour)}
	sf, err := protocol.SignFeed(f, priv)
	if err != nil {
		t.Fatal(err)
	}
	// Simulate an updater with the state file locked (or crashed before release).
	lock, err := os.OpenFile(path+".lock", os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	if err = verifyAndRecord(sf, pub, path, now); err == nil {
		t.Fatal("guardian wrote while state locked")
	}
	lock.Close()
	if err = os.Remove(path + ".lock"); err != nil {
		t.Fatal(err)
	}
	if err = verifyAndRecord(sf, pub, path, now); err != nil {
		t.Fatal(err)
	}
}
