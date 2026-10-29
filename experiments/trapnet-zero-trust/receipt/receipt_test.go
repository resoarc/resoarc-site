package receipt

import (
 "crypto/ed25519"
 "crypto/rand"
 "encoding/json"
 "strings"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
func sample(t *testing.T)(protocol.SignedReport,ed25519.PublicKey,ed25519.PrivateKey){
 t.Helper()
 node,signer,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 hub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 fp,_:=protocol.CoverageGapFingerprint("storage_full")
 r:=protocol.Report{Schema:protocol.ReportSchema,NodeID:protocol.NodeID(node),EventID:"0123456789abcdef0123456789abcdef",
  ObservedAt:time.Now().UTC(),Kind:protocol.CoverageGapKind,TargetPort:0,CampaignFingerprint:fp}
 signed,err:=protocol.SignReport(r,signer);if err!=nil{t.Fatal(err)}
 return signed,hub,priv
}
func signed(t *testing.T)(Signed,protocol.SignedReport,ed25519.PublicKey){
 t.Helper()
 r,pub,priv:=sample(t)
 ack,err:=Sign(r,strings.Repeat("a",64),1,time.Now().UTC(),priv)
 if err!=nil{t.Fatal(err)}
 return ack,r,pub
}
func TestReceiptRoundtrip(t *testing.T){
 ack,r,pub:=signed(t)
 raw,_:=json.Marshal(ack)
 if err:=DecodeAndVerify(raw,r,pub,time.Now());err!=nil{t.Fatal(err)}
}
func TestReceiptRejectsWrongKey(t *testing.T){
 ack,r,_:=signed(t)
 other,_,_:=ed25519.GenerateKey(rand.Reader)
 if Verify(ack,r,other,time.Now())==nil{t.Fatal("untrusted HUB signer accepted")}
}
func TestReceiptBindsFullReport(t *testing.T){
 ack,r,pub:=signed(t)
 r.Report.TargetPort=22
 if Verify(ack,r,pub,time.Now())==nil{t.Fatal("receipt applies to a different report")}
}
func TestReceiptRejectsForgedTip(t *testing.T){
 ack,r,pub:=signed(t)
 ack.Receipt.LedgerTipSHA256=strings.Repeat("b",64)
 if Verify(ack,r,pub,time.Now())==nil{t.Fatal("ledger tip tampering accepted")}
}
func TestReceiptRejectsTamperedRows(t *testing.T){
 ack,r,pub:=signed(t)
 ack.Receipt.LedgerRows++
 if Verify(ack,r,pub,time.Now())==nil{t.Fatal("row count tampering accepted")}
}
func TestReceiptRejectsBadSchemaAndFutureReceipt(t *testing.T){
 ack,r,pub:=signed(t)
 ack.Receipt.Schema="unknown"
 if Verify(ack,r,pub,time.Now())==nil{t.Fatal("unknown receipt schema accepted")}
 ack,r,pub=signed(t)
 ack.Receipt.ReceivedAt=time.Now().Add(3*time.Minute)
 if Verify(ack,r,pub,time.Now())==nil{t.Fatal("future received timestamp accepted")}
}
func TestReceiptStrictParse(t *testing.T){
 ack,r,pub:=signed(t)
 b,_:=json.Marshal(ack)
 for _,v:=range [][]byte{
  []byte(""),[]byte("{}"),append(b,[]byte(" {}")...),
  append(b,make([]byte,MaxBytes)...),
  []byte(`{"receipt":{"schema":"false"},"signature":"none","evil":true}`),
 }{
  if DecodeAndVerify(v,r,pub,time.Now())==nil{t.Fatal("malformed receipt accepted")}
 }
}
func TestReceiptNoEmptyLedgerContext(t *testing.T){
 r,_,priv:=sample(t)
 if _,err:=Sign(r,strings.Repeat("a",64),0,time.Now(),priv);err==nil{t.Fatal("empty ledger accepted")}
 if _,err:=Sign(r,"invalid",1,time.Now(),priv);err==nil{t.Fatal("bad digest accepted")}
}
