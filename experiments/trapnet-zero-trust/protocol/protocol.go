// Package protocol contains the intentionally small, non-executable evidence and
// warning-feed formats used by the experimental TrapNet MVP.
package protocol

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"time"
)

const ReportSchema = "trapnet.report.v0.1"
const FeedSchema = "trapnet.feed.v0.1"

var token = regexp.MustCompile(`^[a-z0-9][a-z0-9_-]{0,63}$`)
var hex64 = regexp.MustCompile(`^[0-9a-f]{64}$`)
var hex32 = regexp.MustCompile(`^[0-9a-f]{32}$`)

type Report struct {
	Schema              string    `json:"schema"`
	NodeID              string    `json:"node_id"`
	EventID             string    `json:"event_id"`
	ObservedAt          time.Time `json:"observed_at"`
	Kind                string    `json:"kind"`
	TargetPort          int       `json:"target_port"`
	CampaignFingerprint string    `json:"campaign_fingerprint"`
}
type SignedReport struct {
	Report    Report `json:"report"`
	Signature string `json:"signature"`
}
type Warning struct {
	Category string `json:"category"`
	Summary  string `json:"summary"`
}
type Feed struct {
	Schema    string    `json:"schema"`
	Version   uint64    `json:"version"`
	IssuedAt  time.Time `json:"issued_at"`
	ExpiresAt time.Time `json:"expires_at"`
	Warnings  []Warning `json:"warnings"`
}
type SignedFeed struct {
	Feed      Feed   `json:"feed"`
	Signature string `json:"signature"`
}

func NodeID(pub ed25519.PublicKey) string {
	sum := sha256.Sum256(pub)
	return hex.EncodeToString(sum[:16])
}
func NewEventID() (string, error) {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return hex.EncodeToString(buf), nil
}
func PrivateFromHex(s string) (ed25519.PrivateKey, error) {
	b, err := hex.DecodeString(s)
	if err != nil || len(b) != ed25519.PrivateKeySize {
		return nil, errors.New("invalid Ed25519 private key")
	}
	return ed25519.PrivateKey(b), nil
}
func PublicFromHex(s string) (ed25519.PublicKey, error) {
	b, err := hex.DecodeString(s)
	if err != nil || len(b) != ed25519.PublicKeySize {
		return nil, errors.New("invalid Ed25519 public key")
	}
	return ed25519.PublicKey(b), nil
}

func (r Report) Validate(now time.Time) error {
	if r.Schema != ReportSchema {
		return errors.New("unknown report schema")
	}
	if !hex32.MatchString(r.NodeID) || !hex32.MatchString(r.EventID) {
		return errors.New("invalid node or event id")
	}
	if !token.MatchString(r.Kind) || r.TargetPort < 1 || r.TargetPort > 65535 {
		return errors.New("invalid event type or port")
	}
	if !hex64.MatchString(r.CampaignFingerprint) {
		return errors.New("invalid fingerprint")
	}
	if r.ObservedAt.IsZero() || r.ObservedAt.Before(now.Add(-10*time.Minute)) || r.ObservedAt.After(now.Add(2*time.Minute)) {
		return errors.New("stale/future event")
	}
	return nil
}
func SignReport(r Report, priv ed25519.PrivateKey) (SignedReport, error) {
	b, err := json.Marshal(r)
	if err != nil {
		return SignedReport{}, err
	}
	return SignedReport{Report: r, Signature: hex.EncodeToString(ed25519.Sign(priv, b))}, nil
}
func VerifyReport(sr SignedReport, pub ed25519.PublicKey, now time.Time) error {
	if err := sr.Report.Validate(now); err != nil {
		return err
	}
	if sr.Report.NodeID != NodeID(pub) {
		return errors.New("node ID mismatch")
	}
	sig, err := hex.DecodeString(sr.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return errors.New("bad signature encoding")
	}
	b, _ := json.Marshal(sr.Report)
	if !ed25519.Verify(pub, b, sig) {
		return errors.New("signature failed")
	}
	return nil
}
func (f Feed) Validate(now time.Time) error {
	if f.Schema != FeedSchema || f.Version == 0 {
		return errors.New("invalid feed schema or version")
	}
	if f.IssuedAt.IsZero() || f.ExpiresAt.IsZero() || f.IssuedAt.After(now.Add(2*time.Minute)) || !f.ExpiresAt.After(now) || f.ExpiresAt.After(f.IssuedAt.Add(24*time.Hour)) || !f.ExpiresAt.After(f.IssuedAt) {
		return errors.New("expired or invalid feed timing")
	}
	if len(f.Warnings) > 100 {
		return errors.New("too many warnings")
	}
	for _, w := range f.Warnings {
		if !token.MatchString(w.Category) || len(w.Summary) == 0 || len(w.Summary) > 500 {
			return fmt.Errorf("invalid warning")
		}
	}
	return nil
}
func SignFeed(f Feed, priv ed25519.PrivateKey) (SignedFeed, error) {
	b, err := json.Marshal(f)
	if err != nil {
		return SignedFeed{}, err
	}
	return SignedFeed{Feed: f, Signature: hex.EncodeToString(ed25519.Sign(priv, b))}, nil
}
func VerifyFeed(sf SignedFeed, pub ed25519.PublicKey, now time.Time) error {
	if err := sf.Feed.Validate(now); err != nil {
		return err
	}
	sig, err := hex.DecodeString(sf.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return errors.New("bad feed signature encoding")
	}
	b, _ := json.Marshal(sf.Feed)
	if !ed25519.Verify(pub, b, sig) {
		return errors.New("feed signature failed")
	}
	return nil
}
