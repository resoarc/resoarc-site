package main

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

type guardianState struct {
	Version uint64 `json:"version"`
	Digest  string `json:"digest"`
}

// verifyAndRecord never executes the contents of a feed. A signed feed with
// the same version but a different payload is equivocation, not an update.
func verifyAndRecord(sf protocol.SignedFeed, pub ed25519.PublicKey, statePath string, now time.Time) error {
	if err := protocol.VerifyFeed(sf, pub, now); err != nil {
		return err
	}
	// O_EXCL is an OS-wide inter-process lock: a concurrent or interrupted
	// updater cannot race to overwrite a later version. A stale lock is
	// deliberately NOT auto-deleted; manual review is required.
	lock, err := os.OpenFile(statePath+".lock", os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		return fmt.Errorf("guardian state busy or locked: %w", err)
	}
	defer func() { lock.Close(); os.Remove(statePath + ".lock") }()
	feedBody, err := json.Marshal(sf.Feed)
	if err != nil {
		return err
	}
	sum := sha256.Sum256(feedBody)
	digest := hex.EncodeToString(sum[:])
	state := guardianState{}
	info, err := os.Lstat(statePath)
	if err == nil {
		if !info.Mode().IsRegular() {
			return errors.New("state is not a regular file")
		}
		b, err := os.ReadFile(statePath)
		if err != nil {
			return err
		}
		if err := json.Unmarshal(b, &state); err != nil {
			return fmt.Errorf("invalid state: %w", err)
		}
		if state.Version == 0 {
			return errors.New("invalid local version")
		}
		if state.Digest != "" && len(state.Digest) != 64 {
			return errors.New("invalid stored digest")
		}
	} else if !os.IsNotExist(err) {
		return err
	}
	if sf.Feed.Version < state.Version {
		return errors.New("feed rollback detected")
	}
	if sf.Feed.Version == state.Version {
		// Older state files had no content hash. Do not accept ambiguous
		// same-version updates during migration; require a version increase.
		if state.Digest == "" || state.Digest != digest {
			return errors.New("feed equivocation or legacy state; require a newer version")
		}
		return nil
	}
	next := guardianState{Version: sf.Feed.Version, Digest: digest}
	data, err := json.Marshal(next)
	if err != nil {
		return err
	}
	dir := filepath.Dir(statePath)
	temp, err := os.CreateTemp(dir, ".trapnet-state-*")
	if err != nil {
		return err
	}
	defer os.Remove(temp.Name())
	if err := temp.Chmod(0600); err != nil {
		temp.Close()
		return err
	}
	if _, err := temp.Write(data); err != nil {
		temp.Close()
		return err
	}
	if err := temp.Sync(); err != nil {
		temp.Close()
		return err
	}
	if err := temp.Close(); err != nil {
		return err
	}
	if err := os.Rename(temp.Name(), statePath); err != nil {
		return err
	}
	return nil
}
