package witness

import (
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"
)
func testRig(t *testing.T)(string,string,ed25519.PublicKey,ed25519.PrivateKey){
 t.Helper();dir:=t.TempDir();ledger:=filepath.Join(dir,"hub-copy.jsonl");history:=filepath.Join(dir,"external.witness.jsonl")
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(ledger,nil,0600);err!=nil{t.Fatal(err)}
 appendEvent(t,ledger,1)
 return ledger,history,pub,priv
}
func appendEvent(t *testing.T,path string,n int){
 t.Helper()
 b,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 h:=Head{Revision:1,Digest:zeroDigest}
 if len(b)>0{h,err=Measure(path,nil);if err!=nil{t.Fatal(err)}}
 row:=[]byte(`{"event":`+string('0'+rune(n))+`}`+"\n")
 f,err:=os.OpenFile(path,os.O_APPEND|os.O_WRONLY,0600);if err!=nil{t.Fatal(err)}
 if _,err=f.Write(row);err!=nil{t.Fatal(err)}
 if err=f.Close();err!=nil{t.Fatal(err)}
 next,err:=Measure(path,nil);if err!=nil{t.Fatal(err)}
 if next.Rows!=h.Rows+1{t.Fatal("row count not advanced")}
 encoded,_:=json.Marshal(next)
 if err=os.WriteFile(path+".head",encoded,0600);err!=nil{t.Fatal(err)}
}
func TestWitnessAttestAndAudit(t *testing.T){
 ledger,history,pub,priv:=testRig(t);now:=time.Date(2026,10,27,12,0,0,0,time.UTC)
 first,tip,err:=Attest(ledger,history,priv,now);if err!=nil{t.Fatal(err)}
 if first.Checkpoint.Sequence!=1||first.Checkpoint.Rows!=1||tip==""{t.Fatal("wrong witness")}
 if _,_,err=Audit(ledger,history,pub,tip);err!=nil{t.Fatal(err)}
 appendEvent(t,ledger,2)
 if _,_,err=Audit(ledger,history,pub,tip);err!=nil{t.Fatal("preexisting prefix should remain verifiable: ",err)}
 second,tip2,err:=Attest(ledger,history,priv,now.Add(time.Minute));if err!=nil{t.Fatal(err)}
 if second.Checkpoint.Sequence!=2||second.Checkpoint.PreviousHash!=tip{t.Fatal("broken chain")}
 if _,_,err=Audit(ledger,history,pub,tip2);err!=nil{t.Fatal(err)}
 if _,_,err=Attest(ledger,history,priv,now.Add(2*time.Minute));err==nil{t.Fatal("duplicate attestation")}
}
func TestRewritingLedgerAndLocalHeadIsCaught(t *testing.T){
 ledger,history,pub,priv:=testRig(t)
 _,tip,err:=Attest(ledger,history,priv,time.Now().UTC());if err!=nil{t.Fatal(err)}
 b,err:=os.ReadFile(ledger);if err!=nil{t.Fatal(err)}
 b=bytes.ReplaceAll(b,[]byte(`"event":1`),[]byte(`"event":9`))
 if err=os.WriteFile(ledger,b,0600);err!=nil{t.Fatal(err)}
 modified,err:=Measure(ledger,nil);if err!=nil{t.Fatal(err)}
 head,_:=json.Marshal(modified)
 if err=os.WriteFile(ledger+".head",head,0600);err!=nil{t.Fatal(err)}
 if _,_,err=Audit(ledger,history,pub,tip);err==nil{t.Fatal("forgery of ledger and local head was accepted")}
}
func TestHistoryAlterationAndRollbackAnchoring(t *testing.T){
 ledger,history,pub,priv:=testRig(t);now:=time.Now().UTC()
 _,tip1,err:=Attest(ledger,history,priv,now);if err!=nil{t.Fatal(err)}
 prior,_:=os.ReadFile(history)
 appendEvent(t,ledger,2)
 _,tip2,err:=Attest(ledger,history,priv,now.Add(time.Minute));if err!=nil{t.Fatal(err)}
 if tip1==tip2{t.Fatal("same tip")}
 if err=os.WriteFile(history,prior,0600);err!=nil{t.Fatal(err)}
 if _,_,err=Audit(ledger,history,pub,tip2);err==nil{t.Fatal("history rollback with pinned tip not detected")}
 original,_:=os.ReadFile(history)
 if err=os.WriteFile(history,bytes.Replace(original,[]byte("trapnet.witness.v0.1"),[]byte("trapnet.witness.v0.2"),1),0600);err!=nil{t.Fatal(err)}
 if _,err=ReadHistory(history,pub);err==nil{t.Fatal("modified signature accepted")}
}
func TestMissingOrTruncatedLedgerRejected(t *testing.T){
 ledger,history,pub,priv:=testRig(t)
 _,tip,err:=Attest(ledger,history,priv,time.Now().UTC());if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(ledger,[]byte(`{"event":1}`),0600);err!=nil{t.Fatal(err)}
 if _,_,err=Audit(ledger,history,pub,tip);err==nil{t.Fatal("torn ledger accepted")}
 if err=os.Remove(ledger+".head");err!=nil{t.Fatal(err)}
 if _,_,err=Audit(ledger,history,pub,tip);err==nil{t.Fatal("missing checkpoint accepted")}
}
func TestWitnessSnapshotFailClosed(t *testing.T){
 ledger,history,_,priv:=testRig(t)
 if err:=os.WriteFile(ledger+".head",[]byte(`{"revision":1,"rows":123,"digest":"`+strings.Repeat("f",64)+`"}`),0600);err!=nil{t.Fatal(err)}
 if _,_,err:=Attest(ledger,history,priv,time.Now().UTC());err==nil{t.Fatal("inconsistent snapshot was witnessed")}
}
