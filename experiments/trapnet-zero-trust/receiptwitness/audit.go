// Package receiptwitness independently cross-audits a HUB-signed receipt
// against a CLOSED, off-HUB ledger snapshot and an externally pinned,
// independently signed Witness history. This is audit evidence, not all-clear.
package receiptwitness

import (
 "bufio"
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

const MaxLedgerBytes = 64<<20
const MaxRecordBytes = 65536

type ledgerRow struct {
 ReceivedAt time.Time `json:"received_at"`
 Evidence protocol.SignedReport `json:"evidence"`
}

// Audit never signs, edits or transfers evidence. Its caller must supply the
// Witness root and history tip independently of the HUB snapshot.
func Audit(ledgerPath,historyPath,expectedWitnessTip string,
 sensorPub,hubPub,witnessPub ed25519.PublicKey,
 report protocol.SignedReport,ack receipt.Signed,now time.Time)error{
 if expectedWitnessTip=="" || len(sensorPub)!=ed25519.PublicKeySize ||
 len(hubPub)!=ed25519.PublicKeySize || len(witnessPub)!=ed25519.PublicKeySize {
  return errors.New("missing independently pinned audit trust")
 }
 if bytes.Equal(hubPub,witnessPub)||bytes.Equal(sensorPub,witnessPub)||bytes.Equal(sensorPub,hubPub){
  return errors.New("Sensor, HUB and Witness signer identities must be distinct")
 }
 // Historical reports are verified at their own observed time, not the
 // current clock; today's auditor cannot re-send them to the HUB.
 if err:=protocol.VerifyReport(report,sensorPub,report.Report.ObservedAt);err!=nil{return fmt.Errorf("Sensor signature invalid: %w",err)}
 if err:=receipt.Verify(ack,report,hubPub,now);err!=nil{return fmt.Errorf("HUB receipt invalid: %w",err)}
 if ack.Receipt.ReceivedAt.Before(report.Report.ObservedAt.Add(-2*time.Minute)) ||
    ack.Receipt.ReceivedAt.After(report.Report.ObservedAt.Add(10*time.Minute)) {
  return errors.New("HUB receipt time inconsistent with validated observation window")
 }
 if err:=safeLedger(ledgerPath);err!=nil{return err}
 measured,_,err:=witness.Audit(ledgerPath,historyPath,witnessPub,expectedWitnessTip)
 if err!=nil{return fmt.Errorf("independent Witness chain failed: %w",err)}
 if ack.Receipt.LedgerRows>measured.Rows {
  return errors.New("receipt claims rows beyond independently witnessed snapshot")
 }
 f,err:=os.Open(ledgerPath);if err!=nil{return err}
 defer f.Close()
 scanner:=bufio.NewScanner(io.LimitReader(f,MaxLedgerBytes+1))
 scanner.Buffer(make([]byte,4096),MaxRecordBytes)
 tip:=make([]byte,32)
 rowCount:=uint64(0)
 seen:=false
 for scanner.Scan(){
  rowCount++
  raw:=append(append([]byte(nil),scanner.Bytes()...),byte('\n'))
  var prefix [8]byte
  binary.BigEndian.PutUint64(prefix[:],uint64(len(raw)))
  data:=make([]byte,0,len(tip)+8+len(raw))
  data=append(data,tip...)
  data=append(data,prefix[:]...)
  data=append(data,raw...)
  sum:=sha256.Sum256(data)
  tip=append(tip[:0],sum[:]...)
  if rowCount<=ack.Receipt.LedgerRows{
   var row ledgerRow
   d:=json.NewDecoder(bytes.NewReader(scanner.Bytes()))
   d.DisallowUnknownFields()
   if err:=d.Decode(&row);err!=nil{return fmt.Errorf("bad audited ledger row: %w",err)}
   if d.Decode(new(any))!=io.EOF{return errors.New("ledger has extra JSON")}
   if row.Evidence.Report.NodeID==report.Report.NodeID && row.Evidence.Report.EventID==report.Report.EventID{
    if seen{return errors.New("repeated original event in audit ledger")}
    source,_:=json.Marshal(row.Evidence)
    expected,_:=json.Marshal(report)
    if !bytes.Equal(source,expected)||!row.ReceivedAt.Equal(ack.Receipt.ReceivedAt){
     return errors.New("audited report and HUB receipt disagree")
    }
    seen=true
   }
  }
  if rowCount==ack.Receipt.LedgerRows && hex.EncodeToString(tip)!=ack.Receipt.LedgerTipSHA256{
   return errors.New("HUB-signed ledger tip not independently reproduced")
  }
 }
 if err:=scanner.Err();err!=nil{return err}
 if rowCount!=measured.Rows||hex.EncodeToString(tip)!=measured.Digest{
  return errors.New("ledger changed between Witness audit and receipt verification")
 }
 if !seen{return errors.New("exact Sensor report not present within signed HUB receipt boundary")}
 return nil
}
func safeLedger(path string)error{
 fi,err:=os.Lstat(path)
 if err!=nil{return err}
 if !fi.Mode().IsRegular() || fi.Size()>MaxLedgerBytes || fi.Size()<=0{
  return errors.New("unsafe or oversized offline snapshot")
 }
 return nil
}
