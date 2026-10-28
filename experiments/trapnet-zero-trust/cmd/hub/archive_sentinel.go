package main

import (
	"errors"
	"fmt"
	"os"
)

// An ordinary missing runtime flag must not silently disable the replay
// history on an operator-prepared new ledger generation. This is NOT a defense
// against a privileged attacker able to delete the sentinel and reconfigure
// the service; the external archive pin must live outside HUB authority.
func requireArchiveSentinel(ledger string, configured bool) error {
	fi, err := os.Lstat(ledger + ".archives-required")
	if errors.Is(err, os.ErrNotExist) {
		if configured {
			return errors.New("archive parameters supplied, but active ledger lacks rollover sentinel")
		}
		return nil
	}
	if err != nil {
		return err
	}
	if !fi.Mode().IsRegular() {
		return errors.New("archive sentinel is not a regular file")
	}
	if !configured {
		return fmt.Errorf("ledger requires independently pinned signed archive config")
	}
	return nil
}
