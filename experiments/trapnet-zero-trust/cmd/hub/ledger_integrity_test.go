package main

import (
	"bytes"
	"os"
	"testing"
	"time"
)

func TestLedgerRejectsModifiedAndDeletedRecords(t *testing.T) {
	rig := newRig(t)
	for i := 1; i <= 3; i++ {
		if code := rig.post(rig.signed(t, i)); code != 202 {
			t.Fatalf("report %d: HTTP %d", i, code)
		}
	}
	original, err := os.ReadFile(rig.path)
	if err != nil {
		t.Fatal(err)
	}
	altered := bytes.Replace(original, []byte("http_probe"), []byte("http_pr0be"), 1)
	if bytes.Equal(original, altered) {
		t.Fatal("test setup failed")
	}
	if err = os.WriteFile(rig.path, altered, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err = newServer(rig.hub.keys, nil, rig.ledger, func() time.Time { return rig.now }); err == nil {
		t.Fatal("tampered ledger accepted")
	}
	if err = os.WriteFile(rig.path, original[:len(original)/2], 0600); err != nil {
		t.Fatal(err)
	}
	if _, err = newServer(rig.hub.keys, nil, rig.ledger, func() time.Time { return rig.now }); err == nil {
		t.Fatal("truncated ledger accepted")
	}
}

func TestLedgerRejectsCheckpointRemoval(t *testing.T) {
	rig := newRig(t)
	if code := rig.post(rig.signed(t, 1)); code != 202 {
		t.Fatalf("HTTP %d", code)
	}
	if err := os.Remove(rig.path + ".head"); err != nil {
		t.Fatal(err)
	}
	if _, err := newServer(rig.hub.keys, nil, rig.ledger, func() time.Time { return rig.now }); err == nil {
		t.Fatal("missing checkpoint accepted")
	}
}

func TestLedgerCrashGapAndIncompleteTail(t *testing.T) {
	rig := newRig(t)
	if code := rig.post(rig.signed(t, 1)); code != 202 {
		t.Fatalf("HTTP %d", code)
	}
	f, err := os.OpenFile(rig.path, os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = f.Write([]byte(`{"partial":true}`)); err != nil {
		t.Fatal(err)
	}
	if err = f.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err = newServer(rig.hub.keys, nil, rig.ledger, func() time.Time { return rig.now }); err == nil {
		t.Fatal("torn append accepted")
	}
}

func TestLedgerRejectsFailedStorageThenLocks(t *testing.T) {
	rig := newRig(t)
	// Closing backing file simulates a broken filesystem/storage writer.
	if err := rig.ledger.Close(); err != nil {
		t.Fatal(err)
	}
	if code := rig.post(rig.signed(t, 1)); code != 503 {
		t.Fatalf("storage failure returned %d", code)
	}
	if !rig.hub.poisoned {
		t.Fatal("storage failure did not poison HUB")
	}
	if code := rig.post(rig.signed(t, 2)); code != 503 {
		t.Fatalf("continued after storage failure: %d", code)
	}
}
