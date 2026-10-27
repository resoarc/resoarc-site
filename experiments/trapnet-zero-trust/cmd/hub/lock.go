package main

import (
	"fmt"
	"os"
)

// Exclusive lock prevents two HUB processes from appending to the same ledger.
// A stale lock intentionally fails closed after crashes; operator reviews the
// ledger and checkpoint before removing it. Never automate stale lock removal.
func acquireLedgerLock(ledgerPath string) (func(), error) {
	path := ledgerPath + ".lock"
	f, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		return nil, fmt.Errorf("ledger locked or inaccessible: %w", err)
	}
	if _, err = f.WriteString(fmt.Sprintf("pid=%d\n", os.Getpid())); err != nil {
		f.Close()
		os.Remove(path)
		return nil, err
	}
	if err = f.Sync(); err != nil {
		f.Close()
		os.Remove(path)
		return nil, err
	}
	return func() { _ = f.Close(); _ = os.Remove(path) }, nil
}
