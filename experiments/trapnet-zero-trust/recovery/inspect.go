// Package recovery provides read-only, offline inspection of HUB evidence
// against an independently pinned off-host Witness history.
package recovery

import (
 "crypto/ed25519"
 "errors"
 "fmt"
 "os"
 "regexp"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

var digestRE = regexp.MustCompile("^[0-9a-f]{64}$")

// Result is advisory forensic evidence, never permission to restart the HUB.
// Independent attestation verifies observed bytes, not the truth of reports.
type Result struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 CheckedAt time.Time `json:"checked_at"`
 LedgerRows uint64 `json:"ledger_rows"`
 LedgerDigest string `json:"ledger_digest"`
 WitnessedRows uint64 `json:"witnessed_rows"`
 WitnessTip string `json:"witness_tip"`
 UnwitnessedRows uint64 `json:"unwitnessed_rows"`
 MayStartHub bool `json:"may_start_hub"`
 OperatorAction string `json:"operator_action"`
}

// Inspect never repairs, truncates, overwrites, clears locks, or restarts.
// The expected tip and public key MUST be acquired independently of HUB.
func Inspect(ledger, history string, pub ed25519.PublicKey, expectedTip string, now time.Time) (Result,error) {
 if !digestRE.MatchString(expectedTip) || len(pub)!=ed25519.PublicKeySize {
  return Result{},errors.New("independent Witness public key and 64-digit hex tip are mandatory")
 }
 if now.IsZero() || ledger=="" || history=="" { return Result{},errors.New("time, ledger and history required") }
 if _,err:=os.Lstat(ledger+".lock");err==nil {
  return Result{},errors.New("HUB lock exists: do not inspect running evidence or automatically remove stale locks")
 }else if !errors.Is(err,os.ErrNotExist) {return Result{},fmt.Errorf("HUB lock check: %w",err)}
 measured,tip,err:=witness.Audit(ledger,history,pub,expectedTip)
 if err!=nil {return Result{},fmt.Errorf("untrusted evidence: %w",err)}
 historyRows,err:=witness.ReadHistory(history,pub)
 if err!=nil || len(historyRows)==0 {return Result{},errors.New("signed history unavailable after audit")}
 last:=historyRows[len(historyRows)-1].Checkpoint
 if tip!=expectedTip || measured.Rows<last.Rows {return Result{},errors.New("witness evidence changed during inspection")}
 result:=Result{
  Schema:"trapnet.recovery-inspection.v0.1",
  Status:"fully_witnessed", CheckedAt:now.UTC(),
  LedgerRows:measured.Rows, LedgerDigest:measured.Digest,
  WitnessedRows:last.Rows, WitnessTip:tip,
  UnwitnessedRows:measured.Rows-last.Rows,
  MayStartHub:false,
  OperatorAction:"Preserve evidence. Independently check latest witness tips, archive generations, and accepted-client receipts. Operator review required before any restart.",
 }
 if last.Rows!=measured.Rows || last.Digest!=measured.Digest {
  result.Status="unwitnessed_tail"
  result.OperatorAction="Quarantine this snapshot: later complete rows are not witnessed. Never trim, silently seal, or restart; review with an independent authority first."
 }
 return result,nil
}
