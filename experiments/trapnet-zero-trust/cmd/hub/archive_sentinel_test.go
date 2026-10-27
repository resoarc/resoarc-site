package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestArchiveSentinelConfiguration(t *testing.T) {
	d := t.TempDir()
	ledger := filepath.Join(d, "ledger.jsonl")
	if err := requireArchiveSentinel(ledger, false); err != nil {
		t.Fatal(err)
	}
	if err := requireArchiveSentinel(ledger, true); err == nil {
		t.Fatal("archive args accepted without sentinel")
	}
	if err := os.WriteFile(ledger+".archives-required", []byte("required"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := requireArchiveSentinel(ledger, false); err == nil {
		t.Fatal("archive history silently skipped")
	}
	if err := requireArchiveSentinel(ledger, true); err != nil {
		t.Fatal(err)
	}
}
