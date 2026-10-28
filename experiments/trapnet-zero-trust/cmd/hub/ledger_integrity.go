package main

// Evidence ledger integrity checks make accidental corruption and unilateral
// ledger-file edits detectable against the separately maintained checkpoint.
// A privileged attacker who can rewrite BOTH files remains out of scope: for
// stronger provenance, publish signed checkpoint digests off-host.

import (
	"bufio"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
)

type ledgerHead struct {
	Revision int    `json:"revision"`
	Rows     uint64 `json:"rows"`
	Digest   string `json:"digest"`
}

func initialHead() ledgerHead {
	return ledgerHead{Revision: 1, Digest: hex.EncodeToString(make([]byte, 32))}
}

func nextHead(h ledgerHead, row []byte) (ledgerHead, error) {
	previous, err := hex.DecodeString(h.Digest)
	if err != nil || len(previous) != 32 {
		return ledgerHead{}, errors.New("invalid previous ledger digest")
	}
	if len(row) == 0 || len(row) > 65536 || row[len(row)-1] != '\n' {
		return ledgerHead{}, errors.New("ledger row must end in newline")
	}
	var length [8]byte
	binary.BigEndian.PutUint64(length[:], uint64(len(row)))
	data := make([]byte, 0, 32+8+len(row))
	data = append(data, previous...)
	data = append(data, length[:]...)
	data = append(data, row...)
	next := sha256.Sum256(data)
	return ledgerHead{Revision: 1, Rows: h.Rows + 1, Digest: hex.EncodeToString(next[:])}, nil
}

func loadHead(path string) (ledgerHead, error) {
	fi, err := os.Lstat(path)
	if err != nil {
		return ledgerHead{}, err
	}
	if !fi.Mode().IsRegular() || fi.Size() > 256 {
		return ledgerHead{}, errors.New("invalid checkpoint file")
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return ledgerHead{}, err
	}
	var h ledgerHead
	if err = json.Unmarshal(b, &h); err != nil {
		return ledgerHead{}, err
	}
	digest, err := hex.DecodeString(h.Digest)
	if err != nil || len(digest) != 32 || h.Revision != 1 {
		return ledgerHead{}, errors.New("invalid ledger checkpoint")
	}
	if h.Rows == 0 && h.Digest != initialHead().Digest {
		return ledgerHead{}, errors.New("bad empty checkpoint")
	}
	return h, nil
}

func saveHead(path string, h ledgerHead) error {
	b, err := json.Marshal(h)
	if err != nil {
		return err
	}
	d := filepath.Dir(path)
	tmp, err := os.CreateTemp(d, ".trapnet-ledger-head-*")
	if err != nil {
		return err
	}
	defer os.Remove(tmp.Name())
	if err = tmp.Chmod(0600); err != nil {
		tmp.Close()
		return err
	}
	if _, err = tmp.Write(b); err != nil {
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
	// Directory sync may be unavailable on Windows; file sync and atomic
	// rename remain mandatory. On Linux, failure is fatal.
	if runtime.GOOS != "windows" {
		if dir, err := os.Open(d); err == nil {
			err = dir.Sync()
			dir.Close()
			if err != nil && !errors.Is(err, os.ErrInvalid) {
				return err
			}
		}
	}
	return nil
}

// checkLedgerHead requires a checkpoint for EVERY nonempty ledger. Inability
// to prove continuity always prevents startup; no silent repair or truncation.
func checkLedgerHead(f *os.File, measured ledgerHead) (ledgerHead, error) {
	path := f.Name() + ".head"
	stored, err := loadHead(path)
	if os.IsNotExist(err) && measured.Rows == 0 {
		if err = saveHead(path, measured); err != nil {
			return ledgerHead{}, err
		}
		return measured, nil
	}
	if err != nil {
		return ledgerHead{}, fmt.Errorf("ledger integrity checkpoint unavailable: %w", err)
	}
	if stored != measured {
		return ledgerHead{}, fmt.Errorf("ledger integrity mismatch; possible truncation, rewrite, or crash before checkpoint: stored=%d observed=%d", stored.Rows, measured.Rows)
	}
	return measured, nil
}

// Explicitly opting in is required when sealing an old v0.1/v0.2 ledger.
// Review and back up the entire legacy ledger BEFORE running -bootstrap-ledger.
// This establishes a NEW trust baseline, not proof the legacy data was genuine.
func bootstrapLedgerHead(f *os.File) error {
	if _, err := os.Lstat(f.Name() + ".head"); err == nil {
		return errors.New("checkpoint already exists")
	} else if !os.IsNotExist(err) {
		return err
	}
	measured, err := measureLedger(f)
	if err != nil {
		return err
	}
	if measured.Rows == 0 {
		return errors.New("nothing to migrate")
	}
	return saveHead(f.Name()+".head", measured)
}

func measureLedger(f *os.File) (ledgerHead, error) {
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return ledgerHead{}, err
	}
	fi, err := f.Stat()
	if err != nil {
		return ledgerHead{}, err
	}
	if fi.Size() > 0 {
		var tail [1]byte
		if _, err = f.ReadAt(tail[:], fi.Size()-1); err != nil {
			return ledgerHead{}, err
		}
		if tail[0] != '\n' {
			return ledgerHead{}, errors.New("incomplete ledger tail; refusing repair")
		}
	}
	h := initialHead()
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 4096), 65536)
	for scanner.Scan() {
		row := append(append([]byte(nil), scanner.Bytes()...), '\n')
		if !json.Valid(scanner.Bytes()) {
			return ledgerHead{}, errors.New("invalid JSON ledger record")
		}
		h, err = nextHead(h, row)
		if err != nil {
			return ledgerHead{}, err
		}
	}
	if err = scanner.Err(); err != nil {
		return ledgerHead{}, err
	}
	if _, err = f.Seek(0, io.SeekEnd); err != nil {
		return ledgerHead{}, err
	}
	return h, nil
}
