package receiptwitness

import (
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

type auditFixture struct{
 ledger,history,tip string
 sensorPub,hubPub,witnessPub ed25519.PublicKey
 hubPriv ed25519.PrivateKey
 report protocol.SignedReport
 ack receipt.Signed
 now time.Time
}

func fixture(t *testing.T)*auditFixture{
 t.Helper()
 node,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 hub,hubPriv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 independent,witnessPriv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 now:=time.Now().UTC()
 reason,err:=protocol.CoverageGapFingerprint("log_corrupt");if err!=nil{t.Fatal(err)}
 report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:protocol.NodeID(node),
  EventID:"00112233445566778899aabbccddeeff",ObservedAt:now.Add(-time.Minute),
  Kind:protocol.CoverageGapKind,TargetPort:0,CampaignFingerprint:reason}
 signed,err:=protocol.SignReport(report,priv);if err!=nil{t.Fatal(err)}
 root:=t.TempDir()
 ledger:=filepath.Join(root,"offline-ledger.jsonl")
 history:=filepath.Join(root,"offhub-history.jsonl")
 row,err:=json.Marshal(struct{
  ReceivedAt time.Time `json:"received_at"`
  Evidence protocol.SignedReport `json:"evidence"`
 }{now,signed})
 if err!=nil{t.Fatal(err)}
 row=append(row,'\n')
 var length [8]byte
 binary.BigEndian.PutUint64(length[:],uint64(len(row)))
 body:=append(make([]byte,32),length[:]...)
 body=append(body,row...)
 sha:=sha256.Sum256(body)
 digest:=hex.EncodeToString(sha[:])
 if err=os.WriteFile(ledger,row,0600);err!=nil{t.Fatal(err)}
 h,_:=json.Marshal(witness.Head{Revision:1,Rows:1,Digest:digest})
 if err=os.WriteFile(ledger+".head",h,0600);err!=nil{t.Fatal(err)}
 _,tip,err:=witness.Attest(ledger,history,witnessPriv,now.Add(time.Second),"",true)
 if err!=nil{t.Fatal(err)}
 ack,err:=receipt.Sign(signed,digest,1,now,hubPriv)
 if err!=nil{t.Fatal(err)}
 return &auditFixture{ledger,history,tip,node,hub,independent,hubPriv,signed,ack,now}
}
func (f *auditFixture)verify()error{
 return Audit(f.ledger,f.history,f.tip,f.sensorPub,f.hubPub,f.witnessPub,f.report,f.ack,f.now)
}
func TestIndependentWitnessAuditSuccess(t *testing.T){
 f:=fixture(t)
 if err:=f.verify();err!=nil{t.Fatal(err)}
}
func TestRejectForgedHUBReceipt(t *testing.T){
 f:=fixture(t);f.ack.Receipt.LedgerTipSHA256=strings.Repeat("f",64)
 if f.verify()==nil{t.Fatal("forged receipt tip accepted")}
}
func TestRejectHUBSignedDifferentTip(t *testing.T){
 f:=fixture(t)
 signed,err:=receipt.Sign(f.report,strings.Repeat("a",64),1,f.now,f.hubPriv)
 if err!=nil{t.Fatal(err)}
 f.ack=signed
 if f.verify()==nil{t.Fatal("legit HUB signature on wrong ledger tip accepted")}
}
func TestRejectUnanchoredWitness(t *testing.T){
 f:=fixture(t);f.tip=""
 if f.verify()==nil{t.Fatal("missing independently pinned Witness anchor accepted")}
}
func TestRejectWitnessRollback(t *testing.T){
 f:=fixture(t);f.tip=strings.Repeat("e",64)
 if f.verify()==nil{t.Fatal("independent Witness tip mismatch ignored")}
}
func TestRejectWitnessTampering(t *testing.T){
 f:=fixture(t)
 raw,_:=os.ReadFile(f.history)
 raw[0]='X'
 if err:=os.WriteFile(f.history,raw,0600);err!=nil{t.Fatal(err)}
 if f.verify()==nil{t.Fatal("tampered witness history accepted")}
}
func TestRejectLedgerTampering(t *testing.T){
 f:=fixture(t)
 data,_:=os.ReadFile(f.ledger)
 data[0]='X'
 if err:=os.WriteFile(f.ledger,data,0600);err!=nil{t.Fatal(err)}
 if f.verify()==nil{t.Fatal("tampered snapshot accepted")}
}
func TestRejectMissingSensorEntry(t *testing.T){
 f:=fixture(t)
 other,private,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 fp,_:=protocol.CoverageGapFingerprint("unknown")
 changed:=f.report.Report
 changed.NodeID=protocol.NodeID(other)
 changed.CampaignFingerprint=fp
 f.report,err=protocol.SignReport(changed,private);if err!=nil{t.Fatal(err)}
 if f.verify()==nil{t.Fatal("nonexistent report passed")}
}
func TestRejectUntrustedWitnessKey(t *testing.T){
 f:=fixture(t)
 other,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 f.witnessPub=other
 if f.verify()==nil{t.Fatal("untrusted Witness passed")}
}
func TestRejectSameHUBAndWitnessKey(t *testing.T){
 f:=fixture(t);f.witnessPub=f.hubPub
 if f.verify()==nil{t.Fatal("key reuse accepted as independent Witness")}
}
func TestRejectUntrustedSensorSigner(t *testing.T){
 f:=fixture(t)
 wrong,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 f.sensorPub=wrong
 if f.verify()==nil{t.Fatal("wrong Sensor signer passed")}
}
func TestRejectReceiptOutsideOriginalObservationWindow(t *testing.T){
 f:=fixture(t)
 s,err:=receipt.Sign(f.report,f.ack.Receipt.LedgerTipSHA256,1,f.now.Add(12*time.Minute),f.hubPriv)
 if err!=nil{t.Fatal(err)}
 f.ack=s;f.now=f.now.Add(12*time.Minute)
 if f.verify()==nil{t.Fatal("late receipt accepted")}
}
func TestHistoricalReceiptStillAuditableAfterLongOutage(t *testing.T){
 f:=fixture(t)
 // Audit an ALREADY durably acknowledged report much later than the
 // Sensor's 10-minute live ingestion window. This does not permit the
 // original report to be re-sent or to clear an observation gap.
 f.now=f.now.Add(24*time.Hour)
 if err:=f.verify();err!=nil{t.Fatal(err)}
}
func TestRejectValidHUBSignatureClaimingUnwitnessedRows(t *testing.T){
 f:=fixture(t)
 signed,err:=receipt.Sign(f.report,f.ack.Receipt.LedgerTipSHA256,2,f.ack.Receipt.ReceivedAt,f.hubPriv)
 if err!=nil{t.Fatal(err)}
 f.ack=signed
 if f.verify()==nil{t.Fatal("HUB signed receipt for unwitnessed future rows accepted")}
}
func TestRejectSymlinkSnapshot(t *testing.T){
 f:=fixture(t)
 original:=f.ledger+".real"
 if err:=os.Rename(f.ledger,original);err!=nil{t.Fatal(err)}
 if err:=os.Symlink(original,f.ledger);err!=nil{t.Skip(err)}
 if f.verify()==nil{t.Fatal("symlinked snapshot accepted")}
}
func TestRejectNoWitnessHistory(t *testing.T){
 f:=fixture(t)
 if err:=os.Remove(f.history);err!=nil{t.Fatal(err)}
 if f.verify()==nil{t.Fatal("missing off-HUB witness accepted")}
}
