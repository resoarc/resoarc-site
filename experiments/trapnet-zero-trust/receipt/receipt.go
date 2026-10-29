// Package receipt provides a narrow, offline-verifiable HUB acknowledgment
// for an EXACT signed Sensor report already present in the verified HUB ledger.
// A signature is the HUB's claim, NOT an independent Witness or all-clear.
package receipt

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "bytes"
 "regexp"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

const Schema="trapnet.hub-receipt.v0.1"
const MaxBytes=2048

type Body struct {
 Schema string `json:"schema"`
 HubID string `json:"hub_id"`
 NodeID string `json:"node_id"`
 EventID string `json:"event_id"`
 ReportSHA256 string `json:"report_sha256"`
 LedgerTipSHA256 string `json:"ledger_tip_sha256"`
 LedgerRows uint64 `json:"ledger_rows"`
 ReceivedAt time.Time `json:"received_at"`
}
type Signed struct {
 Receipt Body `json:"receipt"`
 Signature string `json:"signature"`
}

var hex64=regexp.MustCompile(`^[0-9a-f]{64}$`)

func HashReport(report protocol.SignedReport)(string,error){
 data,err:=json.Marshal(report)
 if err!=nil{return "",err}
 digest:=sha256.Sum256(data)
 return hex.EncodeToString(digest[:]),nil
}
func HubID(pub ed25519.PublicKey)string{
 hash:=sha256.Sum256(pub)
 return hex.EncodeToString(hash[:16])
}
func Sign(report protocol.SignedReport,tip string,rows uint64,receivedAt time.Time,priv ed25519.PrivateKey)(Signed,error){
 if len(priv)!=ed25519.PrivateKeySize || !hex64.MatchString(tip) || rows==0 || receivedAt.IsZero(){
  return Signed{},errors.New("incomplete HUB receipt context")
 }
 digest,err:=HashReport(report);if err!=nil{return Signed{},err}
 pub:=priv.Public().(ed25519.PublicKey)
 body:=Body{Schema:Schema,HubID:HubID(pub),NodeID:report.Report.NodeID,
  EventID:report.Report.EventID,ReportSHA256:digest,LedgerTipSHA256:tip,
  LedgerRows:rows,ReceivedAt:receivedAt.UTC()}
 raw,err:=json.Marshal(body);if err!=nil{return Signed{},err}
 return Signed{Receipt:body,Signature:hex.EncodeToString(ed25519.Sign(priv,raw))},nil
}
func Verify(s Signed,report protocol.SignedReport,hubPub ed25519.PublicKey,now time.Time)error{
 r:=s.Receipt
 if len(hubPub)!=ed25519.PublicKeySize || r.Schema!=Schema || r.HubID!=HubID(hubPub) ||
  r.NodeID!=report.Report.NodeID || r.EventID!=report.Report.EventID ||
  !hex64.MatchString(r.LedgerTipSHA256) || r.LedgerRows==0 ||
  r.ReceivedAt.IsZero() || r.ReceivedAt.After(now.Add(2*time.Minute)) {
  return errors.New("HUB receipt context invalid")
 }
 digest,err:=HashReport(report)
 if err!=nil || r.ReportSHA256!=digest{return errors.New("HUB receipt mismatched report")}
 sig,err:=hex.DecodeString(s.Signature)
 if err!=nil||len(sig)!=ed25519.SignatureSize{return errors.New("HUB receipt bad signature encoding")}
 canonical,err:=json.Marshal(r);if err!=nil{return err}
 if !ed25519.Verify(hubPub,canonical,sig){return errors.New("HUB receipt signature invalid")}
 return nil
}
func DecodeAndVerify(raw []byte,report protocol.SignedReport,hubPub ed25519.PublicKey,now time.Time)error{
 if len(raw)==0||len(raw)>MaxBytes{return errors.New("HUB receipt response oversized or empty")}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 var signed Signed
 if err:=dec.Decode(&signed);err!=nil{return fmt.Errorf("HUB receipt not strict JSON: %w",err)}
 if dec.Decode(new(any))!=io.EOF{return errors.New("HUB receipt trailing data")}
 return Verify(signed,report,hubPub,now)
}
