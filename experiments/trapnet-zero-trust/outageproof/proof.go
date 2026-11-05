// Package outageproof binds an operator-observed downtime interval to an
// existing signed Sensor coverage_gap and an exact, signed HUB receipt.
// An operator signature proves an assertion's provenance, NOT its factual truth,
// independent Witness custody, data completeness or release readiness.
package outageproof

import (
    "bytes"
    "crypto/ed25519"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "errors"
    "fmt"
    "regexp"
    "time"

    "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
    "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
)

const Schema = "trapnet.outage-interval-operator.v0.63"
const MaxSourceBytes = 64 * 1024

var shaRE = regexp.MustCompile("^[0-9a-f]{64}$")

// Interval is a PRIVATE-KEY-SIGNED operator assertion about an observation
// outage. It is NOT a modification to the v0.1 on-wire report protocol.
// It contains hashes and finite category strings only, never raw log data.
type Interval struct {
    Schema string `json:"schema"`
    Start time.Time `json:"gap_start"`
    End time.Time `json:"gap_end"`
    AttestedAt time.Time `json:"attested_at"`
    Source string `json:"source_class"`
    SourceSHA256 string `json:"source_sha256"`
    SensorNodeID string `json:"sensor_node_id"`
    EventID string `json:"event_id"`
    ReportSHA256 string `json:"signed_report_sha256"`
    ReceiptSHA256 string `json:"signed_hub_receipt_sha256"`
    Meaning string `json:"observation_meaning"`
}

type SignedInterval struct {
    Interval Interval `json:"interval"`
    Signature string `json:"signature"`
}

func SHA256(data []byte) string {
    hash := sha256.Sum256(data)
    return hex.EncodeToString(hash[:])
}

func ReceiptSHA256(value receipt.Signed) (string, error) {
    raw, err := json.Marshal(value)
    if err != nil { return "", err }
    return SHA256(raw), nil
}

func validTime(value time.Time) bool {
    return !value.IsZero() && value.Location() == time.UTC
}

func validateBody(b Interval) error {
    if b.Schema != Schema || b.Source != "docker_state_guard_metadata" ||
        b.Meaning != "observation_unknown_not_zero" {
        return errors.New("invalid interval schema, source or semantic label")
    }
    if !validTime(b.Start) || !validTime(b.End) || !validTime(b.AttestedAt) ||
        !b.End.After(b.Start) || b.End.Sub(b.Start) > 30*24*time.Hour ||
        b.AttestedAt.Before(b.End) {
        return errors.New("invalid UTC outage interval")
    }
    if !shaRE.MatchString(b.SourceSHA256) || !shaRE.MatchString(b.ReportSHA256) ||
        !shaRE.MatchString(b.ReceiptSHA256) {
        return errors.New("invalid pinned source or receipt hash")
    }
    // The v0.1 report identifiers are exactly 32 lowercase hex characters.
    _, errNode := hex.DecodeString(b.SensorNodeID)
    _, errEvent := hex.DecodeString(b.EventID)
    if len(b.SensorNodeID) != 32 || len(b.EventID) != 32 ||
        errNode != nil || errEvent != nil ||
        b.SensorNodeID != fmt.Sprintf("%x", mustHex(b.SensorNodeID)) ||
        b.EventID != fmt.Sprintf("%x", mustHex(b.EventID)) {
        return errors.New("invalid signed report identity")
    }
    return nil
}

func mustHex(v string) []byte {
    b, _ := hex.DecodeString(v)
    return b
}

// Sign creates an offline attestation with a SEPARATELY CONTROLLED operator
// key. The operator must personally inspect the source evidence first.
// No keys are generated, copied, or sent over the network by this package.
func Sign(b Interval, operatorPrivate ed25519.PrivateKey) (SignedInterval, error) {
    if len(operatorPrivate) != ed25519.PrivateKeySize { return SignedInterval{}, errors.New("operator signing key invalid") }
    if err := validateBody(b); err != nil { return SignedInterval{}, err }
    raw, err := json.Marshal(b)
    if err != nil { return SignedInterval{}, err }
    return SignedInterval{Interval: b, Signature: hex.EncodeToString(ed25519.Sign(operatorPrivate, raw))}, nil
}

// Verify requires THREE distinct pinned Ed25519 principals and the exact
// signed HUB receipt and source manifest. It never fabricates a missing Sensor
// event or signed Witness history, nor claims that a historical assertion
// originated at the time of the outage.
func Verify(
    att SignedInterval,
    signedReport protocol.SignedReport,
    signedReceipt receipt.Signed,
    sourceManifest []byte,
    sensorPub, hubPub, operatorPub ed25519.PublicKey,
    now time.Time,
) error {
    if len(sourceManifest)==0 || len(sourceManifest)>MaxSourceBytes {
        return errors.New("source manifest must be bounded and nonempty")
    }
    if len(sensorPub)!=ed25519.PublicKeySize || len(hubPub)!=ed25519.PublicKeySize ||
        len(operatorPub)!=ed25519.PublicKeySize || bytes.Equal(sensorPub,hubPub) ||
        bytes.Equal(sensorPub,operatorPub) || bytes.Equal(hubPub,operatorPub) {
        return errors.New("three distinct pinned principals required")
    }
    b := att.Interval
    if err := validateBody(b); err != nil { return err }
    if b.AttestedAt.After(now.Add(2*time.Minute)) { return errors.New("operator attestation is in future") }
    if b.SourceSHA256 != SHA256(sourceManifest) { return errors.New("source manifest hash changed") }
    if signedReport.Report.Kind != protocol.CoverageGapKind ||
        signedReport.Report.TargetPort != 0 ||
        signedReport.Report.CampaignFingerprint != mustRecoveryGapFingerprint() {
        return errors.New("not a signed recovery-gap Sensor report")
    }
    // Authentic Sensor signing is checked against HUB receipt time, not
    // against a falsely backdated time. Only a report accepted in its original
    // freshness window is eligible for a historical sidecar.
    if err := protocol.VerifyReport(signedReport, sensorPub, signedReceipt.Receipt.ReceivedAt); err != nil {
        return fmt.Errorf("Sensor signature or freshness invalid: %w", err)
    }
    if err := receipt.Verify(signedReceipt, signedReport, hubPub, now); err != nil {
        return fmt.Errorf("HUB signed receipt invalid: %w", err)
    }
    if signedReceipt.Receipt.ReceivedAt.Before(signedReport.Report.ObservedAt.Add(-2*time.Minute)) ||
        b.End.After(signedReport.Report.ObservedAt) ||
        b.AttestedAt.Before(signedReceipt.Receipt.ReceivedAt) {
        return errors.New("gap times and HUB acceptance are inconsistent")
    }
    reportHash, err := receipt.HashReport(signedReport)
    if err != nil { return err }
    ackHash, err := ReceiptSHA256(signedReceipt)
    if err != nil { return err }
    if b.SensorNodeID != signedReport.Report.NodeID ||
        b.EventID != signedReport.Report.EventID ||
        b.ReportSHA256 != reportHash || b.ReceiptSHA256 != ackHash {
        return errors.New("operator assertion does not bind exact signed report and HUB receipt")
    }
    sig, err := hex.DecodeString(att.Signature)
    if err != nil || len(sig)!=ed25519.SignatureSize { return errors.New("operator signature encoding invalid") }
    canonical, err := json.Marshal(b)
    if err != nil { return err }
    if !ed25519.Verify(operatorPub, canonical, sig) { return errors.New("operator signature rejected") }
    return nil
}

func mustRecoveryGapFingerprint() string {
    fp, _ := protocol.CoverageGapFingerprint("recovery_gap")
    return fp
}
