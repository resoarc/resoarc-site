package main

// HUB hot-reloads signed, short-lived revocation snapshots on every request.
// Missing, stale or altered snapshots make ingestion unavailable, not trusted.

import (
	"crypto/ed25519"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

type revocationCheckpoint struct {
	Version uint64 `json:"version"`
	Digest  string `json:"digest"`
}
type signedRevocationSource struct {
	Path       string
	StatePath  string
	Root       ed25519.PublicKey
	Checkpoint revocationCheckpoint
}

func newRevocationSource(listPath, rootPath string) (*signedRevocationSource, error) {
	raw, err := os.ReadFile(rootPath)
	if err != nil {
		return nil, err
	}
	pub, err := protocol.PublicFromHex(strings.TrimSpace(string(raw)))
	if err != nil {
		return nil, err
	}
	s := &signedRevocationSource{Path: listPath, StatePath: listPath + ".state", Root: pub}
	fi, err := os.Lstat(s.StatePath)
	if err == nil {
		if !fi.Mode().IsRegular() || fi.Size() > 256 {
			return nil, errors.New("invalid revocation state file")
		}
		b, err := os.ReadFile(s.StatePath)
		if err != nil {
			return nil, err
		}
		if err = json.Unmarshal(b, &s.Checkpoint); err != nil {
			return nil, err
		}
		if s.Checkpoint.Version == 0 || len(s.Checkpoint.Digest) != 64 {
			return nil, errors.New("invalid revocation checkpoint")
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	return s, nil
}
func (s *signedRevocationSource) refresh(now time.Time, keys map[string]ed25519.PublicKey) (map[string]bool, error) {
	fi, err := os.Lstat(s.Path)
	if err != nil {
		return nil, err
	}
	if !fi.Mode().IsRegular() || fi.Size() > 65536 {
		return nil, errors.New("invalid signed revocation file")
	}
	f, err := os.Open(s.Path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	dec := json.NewDecoder(io.LimitReader(f, 65537))
	dec.DisallowUnknownFields()
	var envelope protocol.SignedRevocations
	if err = dec.Decode(&envelope); err != nil {
		return nil, err
	}
	if err = dec.Decode(new(any)); err != io.EOF {
		return nil, errors.New("trailing revocation data")
	}
	digest, err := protocol.VerifyRevocations(envelope, s.Root, now)
	if err != nil {
		return nil, err
	}
	ver := envelope.List.Version
	if ver < s.Checkpoint.Version || (ver == s.Checkpoint.Version && digest != s.Checkpoint.Digest) {
		return nil, errors.New("revocation rollback or equivocation")
	}
	revoked := make(map[string]bool, len(envelope.List.NodeIDs))
	for _, id := range envelope.List.NodeIDs {
		if _, ok := keys[id]; !ok {
			return nil, fmt.Errorf("revoked unregistered node %s", id)
		}
		revoked[id] = true
	}
	if ver > s.Checkpoint.Version {
		state := revocationCheckpoint{Version: ver, Digest: digest}
		b, err := json.Marshal(state)
		if err != nil {
			return nil, err
		}
		if err = osWriteAtomic0600(s.StatePath, b); err != nil {
			return nil, err
		}
		s.Checkpoint = state
	}
	return revoked, nil
}

// Restricted local state write. This isn't a defense against privileged local
// compromise; crash failure is detectable by the state-version check.
func osWriteAtomic0600(path string, body []byte) error {
	tmp, err := os.CreateTemp(filepath.Dir(path), ".trapnet-revocation-*")
	if err != nil {
		return err
	}
	defer os.Remove(tmp.Name())
	if err = tmp.Chmod(0600); err != nil {
		tmp.Close()
		return err
	}
	if _, err = tmp.Write(body); err != nil {
		tmp.Close()
		return err
	}
	if err = tmp.Sync(); err != nil {
		tmp.Close()
		return err
	}
	if err = tmp.Close(); err != nil {
		return err
	}
	if err = os.Rename(tmp.Name(), path); err != nil {
		return err
	}
	if runtime.GOOS != "windows" {
		if dir, err := os.Open(filepath.Dir(path)); err == nil {
			err = dir.Sync()
			dir.Close()
			if err != nil {
				return err
			}
		}
	}
	return nil
}
