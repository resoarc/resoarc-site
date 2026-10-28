package archive

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"crypto/ed25519"
	"time"
)

// Prepare creates a NEW empty active generation after validating all witnessed
// archives. It never changes, deletes or truncates earlier evidence. The caller
// must pin the archive signer and tip independently in the service config.
func Prepare(manifestPath string, pub ed25519.PublicKey, tip, outDir string) error {
	absolute, err := filepath.Abs(outDir)
	if err != nil {
		return err
	}
	if _, err = os.Lstat(absolute); err == nil {
		return errors.New("new generation destination already exists")
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	ledger := filepath.Join(absolute, "ledger.jsonl")
	if _, _, err = Load(manifestPath, pub, tip, ledger, time.Now().UTC()); err != nil {
		return err
	}
	parent := filepath.Dir(absolute)
	tmp, err := os.MkdirTemp(parent, ".trapnet-next-generation-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(tmp)
	zero := struct {
		Revision int    `json:"revision"`
		Rows     uint64 `json:"rows"`
		Digest   string `json:"digest"`
	}{Revision: 1, Digest: strings.Repeat("0", 64)}
	head, err := json.Marshal(zero)
	if err != nil {
		return err
	}
	for _, v := range []struct {
		name string
		data []byte
	}{{"ledger.jsonl", []byte{}}, {"ledger.jsonl.head", head}, {"ledger.jsonl.archives-required", []byte("v1: requires pinned offline archive root and hash\n")}} {
		f, e := os.OpenFile(filepath.Join(tmp, v.name), os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if e != nil {
			return e
		}
		if _, e = f.Write(v.data); e == nil {
			e = f.Sync()
		}
		ce := f.Close()
		if e != nil {
			return e
		}
		if ce != nil {
			return ce
		}
	}
	if runtime.GOOS != "windows" {
		d, e := os.Open(tmp)
		if e != nil {
			return e
		}
		e = d.Sync()
		_ = d.Close()
		if e != nil {
			return e
		}
	}
	if _, err = os.Lstat(absolute); err == nil {
		return errors.New("destination appeared during preparation")
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	if err = os.Rename(tmp, absolute); err != nil {
		return err
	}
	if runtime.GOOS != "windows" {
		if d, e := os.Open(parent); e == nil {
			_ = d.Sync()
			_ = d.Close()
		}
	}
	return nil
}
