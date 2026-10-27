package main

import (
	"path/filepath"
	"testing"
)

func TestOnlyOneHubMayWriteLedger(t *testing.T) {
	path := filepath.Join(t.TempDir(), "ledger.jsonl")
	first, err := acquireLedgerLock(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = acquireLedgerLock(path); err == nil {
		t.Fatal("second writer acquired lock")
	}
	first()
	second, err := acquireLedgerLock(path)
	if err != nil {
		t.Fatal(err)
	}
	second()
}
