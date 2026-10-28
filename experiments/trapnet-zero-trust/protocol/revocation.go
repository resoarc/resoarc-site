package protocol

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"time"
)

const RevocationSchema = "trapnet.revocations.v0.1"
const revocationDomain = "trapnet-revocations-v0.1\n"

type RevocationList struct {
	Schema    string    `json:"schema"`
	Version   uint64    `json:"version"`
	IssuedAt  time.Time `json:"issued_at"`
	ExpiresAt time.Time `json:"expires_at"`
	NodeIDs   []string  `json:"node_ids"`
}
type SignedRevocations struct {
	List      RevocationList `json:"list"`
	Signature string         `json:"signature"`
}

func (l RevocationList) Validate(now time.Time) error {
	if l.Schema != RevocationSchema || l.Version == 0 {
		return errors.New("invalid revocation schema or version")
	}
	if l.IssuedAt.IsZero() || l.ExpiresAt.IsZero() || l.IssuedAt.After(now.Add(2*time.Minute)) || !l.ExpiresAt.After(now) || l.ExpiresAt.After(l.IssuedAt.Add(24*time.Hour)) || !l.ExpiresAt.After(l.IssuedAt) {
		return errors.New("invalid revocation validity window")
	}
	if len(l.NodeIDs) > 10000 {
		return errors.New("revocation list too large")
	}
	if !sort.StringsAreSorted(l.NodeIDs) {
		return errors.New("unsorted revocations")
	}
	for i, id := range l.NodeIDs {
		if !hex32.MatchString(id) {
			return fmt.Errorf("invalid revoked node at %d", i)
		}
		if i > 0 && id == l.NodeIDs[i-1] {
			return errors.New("duplicate revoked node")
		}
	}
	return nil
}
func revocationBytes(l RevocationList) ([]byte, error) {
	b, err := json.Marshal(l)
	if err != nil {
		return nil, err
	}
	return append([]byte(revocationDomain), b...), nil
}
func SignRevocations(l RevocationList, priv ed25519.PrivateKey) (SignedRevocations, error) {
	b, err := revocationBytes(l)
	if err != nil {
		return SignedRevocations{}, err
	}
	return SignedRevocations{List: l, Signature: hex.EncodeToString(ed25519.Sign(priv, b))}, nil
}
func VerifyRevocations(s SignedRevocations, pub ed25519.PublicKey, now time.Time) (string, error) {
	if err := s.List.Validate(now); err != nil {
		return "", err
	}
	sig, err := hex.DecodeString(s.Signature)
	if err != nil || len(sig) != ed25519.SignatureSize {
		return "", errors.New("invalid revocation signature encoding")
	}
	b, err := revocationBytes(s.List)
	if err != nil {
		return "", err
	}
	if !ed25519.Verify(pub, b, sig) {
		return "", errors.New("revocation signature mismatch")
	}
	digest := sha256.Sum256(b)
	return hex.EncodeToString(digest[:]), nil
}
