package protocol

import (
    "crypto/sha256"
    "encoding/hex"
    "errors"
)

// CoverageGapKind reserves a non-attack report class on the existing
// allowlisted, Ed25519-authenticated HUB report path. It asserts that
// observation may be missing; it NEVER asserts normal coverage.
const CoverageGapKind = "coverage_gap"

// CoverageGapReason names are finite, public categories. Do not transmit
// raw log lines, IP addresses, credentials or operator-supplied narratives.
var gapReasons = map[string]bool{
    "log_unavailable": true,
    "log_corrupt": true,
    "storage_full": true,
    "transport_outage": true,
    "recovery_gap": true,
    "unknown": true,
}

func CoverageGapFingerprint(reason string) (string, error) {
    if !gapReasons[reason] {
        return "", errors.New("invalid observation gap reason")
    }
    sum := sha256.Sum256([]byte("trapnet.coverage-gap.v1:" + reason))
    return hex.EncodeToString(sum[:]), nil
}

func validCoverageGapFingerprint(given string) bool {
    for reason := range gapReasons {
        expected, _ := CoverageGapFingerprint(reason)
        if given == expected {
            return true
        }
    }
    return false
}
