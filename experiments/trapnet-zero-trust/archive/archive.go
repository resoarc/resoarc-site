// Package archive verifies witnessed ledger generations to preserve replay
// protection without allowing the hub to delete, truncate or sign evidence.
package archive

import (
	"bufio"
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

const Schema = "trapnet.archives.v0.1"
const MaxArchives = 32
const MaxRowsPerArchive = 1_000_000
const MaxArchiveBytes int64 = 1 << 30

var hashPattern = regexp.MustCompile(`^[0-9a-f]{64}$`)

type Segment struct {
	Ledger        string `json:"ledger"`
	History       string `json:"history"`
	WitnessPublic string `json:"witness_public"`
	ExpectedTip   string `json:"expected_tip"`
	Rows          uint64 `json:"rows"`
	Digest        string `json:"digest"`
}
type Manifest struct {
	Schema     string    `json:"schema"`
	Generation uint64    `json:"generation"`
	Segments   []Segment `json:"segments"`
}
type SignedManifest struct {
	Manifest  Manifest `json:"manifest"`
	Signature string   `json:"signature"`
}
type Event struct {
	ReceivedAt time.Time             `json:"received_at"`
	Evidence   protocol.SignedReport `json:"evidence"`
}

func strict(b []byte, v any) error {
	d := json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if err := d.Decode(v); err != nil {
		return err
	}
	if err := d.Decode(new(any)); err != io.EOF {
		return errors.New("extra JSON data")
	}
	return nil
}
func Check(m Manifest) error {
	if m.Schema != Schema || m.Generation < 2 || m.Generation != uint64(len(m.Segments))+1 || len(m.Segments) == 0 || len(m.Segments) > MaxArchives {
		return errors.New("invalid archive generation or number of segments")
	}
	paths := map[string]bool{}
	for _, s := range m.Segments {
		if s.Rows == 0 || s.Rows > MaxRowsPerArchive || !hashPattern.MatchString(s.Digest) || !hashPattern.MatchString(s.ExpectedTip) {
			return errors.New("invalid witnessed segment metadata")
		}
		for _, p := range []string{s.Ledger, s.History, s.WitnessPublic} {
			if !filepath.IsAbs(p) {
				return errors.New("archive paths must be absolute")
			}
			clean := filepath.Clean(p)
			if paths[clean] {
				return errors.New("archive paths overlap")
			}
			paths[clean] = true
		}
	}
	return nil
}
func Sign(m Manifest, priv ed25519.PrivateKey) (SignedManifest, error) {
	if err := Check(m); err != nil {
		return SignedManifest{}, err
	}
	if len(priv) != ed25519.PrivateKeySize {
		return SignedManifest{}, errors.New("invalid offline archive signing key")
	}
	raw, err := json.Marshal(m)
	if err != nil {
		return SignedManifest{}, err
	}
	return SignedManifest{Manifest: m, Signature: hex.EncodeToString(ed25519.Sign(priv, raw))}, nil
}
func Verify(s SignedManifest, pub ed25519.PublicKey) error {
	if err := Check(s.Manifest); err != nil {
		return err
	}
	if len(pub) != ed25519.PublicKeySize {
		return errors.New("invalid pinned archive signing key")
	}
	sig, err := hex.DecodeString(s.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return errors.New("bad archive signature")
	}
	raw, err := json.Marshal(s.Manifest)
	if err != nil {
		return err
	}
	if !ed25519.Verify(pub, raw, sig) {
		return errors.New("archive manifest signature mismatch")
	}
	return nil
}
func Hash(s SignedManifest) (string, error) {
	b, err := json.Marshal(s)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:]), nil
}
func ReadSigned(path string) (SignedManifest, error) {
	var s SignedManifest
	fi, err := os.Lstat(path)
	if err != nil {
		return s, err
	}
	if !fi.Mode().IsRegular() || fi.Size() > 131072 {
		return s, errors.New("archive manifest too large or not a regular file")
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return s, err
	}
	if err = strict(b, &s); err != nil {
		return s, err
	}
	return s, nil
}
func regular(path string) error {
	fi, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if !fi.Mode().IsRegular() {
		return errors.New("archive evidence must be regular files")
	}
	return nil
}

// Load verifies an independently pinned signed manifest AND every archive's
// off-hub witness. Accepted event IDs from all generations remain rejected.
func Load(path string, root ed25519.PublicKey, pinnedHash string, activePath string, now time.Time) (map[string]bool, map[string][]time.Time, error) {
	if !hashPattern.MatchString(pinnedHash) {
		return nil, nil, errors.New("independently pinned archive manifest hash required")
	}
	s, err := ReadSigned(path)
	if err != nil {
		return nil, nil, err
	}
	if err = Verify(s, root); err != nil {
		return nil, nil, err
	}
	hash, err := Hash(s)
	if err != nil || hash != pinnedHash {
		return nil, nil, errors.New("archive manifest pin mismatch")
	}
	active, err := filepath.Abs(activePath)
	if err != nil {
		return nil, nil, err
	}
	seen := map[string]bool{}
	recent := map[string][]time.Time{}
	total := int64(0)
	for _, seg := range s.Manifest.Segments {
		if filepath.Clean(seg.Ledger) == active {
			return nil, nil, errors.New("active ledger cannot be archived ledger")
		}
		for _, p := range []string{seg.Ledger, seg.Ledger + ".head", seg.History, seg.WitnessPublic} {
			if err = regular(p); err != nil {
				return nil, nil, err
			}
		}
		info, err := os.Stat(seg.Ledger)
		if err != nil {
			return nil, nil, err
		}
		total += info.Size()
		if total > MaxArchiveBytes {
			return nil, nil, errors.New("archive aggregate exceeds verification bound")
		}
		pub, err := witness.ReadPublicKey(seg.WitnessPublic)
		if err != nil {
			return nil, nil, err
		}
		head, tip, err := witness.Audit(seg.Ledger, seg.History, pub, seg.ExpectedTip)
		if err != nil {
			return nil, nil, fmt.Errorf("witness audit failed: %w", err)
		}
		if head.Rows != seg.Rows || head.Digest != seg.Digest || tip != seg.ExpectedTip {
			return nil, nil, errors.New("archive witness does not match signed manifest")
		}
		f, err := os.Open(seg.Ledger)
		if err != nil {
			return nil, nil, err
		}
		scan := bufio.NewScanner(f)
		scan.Buffer(make([]byte, 4096), 65536)
		rows := uint64(0)
		for scan.Scan() {
			rows++
			var row Event
			if err = strict(scan.Bytes(), &row); err != nil {
				break
			}
			r := row.Evidence.Report
			if r.NodeID == "" || r.EventID == "" || row.ReceivedAt.IsZero() || row.ReceivedAt.After(now.Add(2*time.Minute)) {
				err = errors.New("malformed archive event")
				break
			}
			id := r.NodeID + ":" + r.EventID
			if seen[id] {
				err = errors.New("duplicate replay identity across archive generations")
				break
			}
			seen[id] = true
			if row.ReceivedAt.After(now.Add(-time.Minute)) && !row.ReceivedAt.After(now) {
				recent[r.NodeID] = append(recent[r.NodeID], row.ReceivedAt)
			}
		}
		if err == nil {
			err = scan.Err()
		}
		cerr := f.Close()
		if err != nil {
			return nil, nil, err
		}
		if cerr != nil {
			return nil, nil, cerr
		}
		if rows != seg.Rows {
			return nil, nil, errors.New("archive row count differs from signed manifest")
		}
	}
	return seen, recent, nil
}
