package main

import (
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/json"
 "fmt"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "testing"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/gapspool"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
)

func receiptRig(t *testing.T)(*hubTestRig,ed25519.PublicKey,ed25519.PrivateKey){
 t.Helper()
 rig:=newRig(t)
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 rig.hub.receiptPrivate=priv
 return rig,pub,priv
}
func exactPost(rig *hubTestRig, sr protocol.SignedReport)(int,[]byte){
 rig.t.Helper()
 data,_:=json.Marshal(sr)
 w:=httptest.NewRecorder()
 r:=httptest.NewRequest(http.MethodPost,"/report",bytes.NewReader(data))
 r.Header.Set("Content-Type","application/json")
 rig.hub.report(w,r)
 return w.Code,append([]byte(nil),w.Body.Bytes()...)
}

func TestSignedHUBReceipt202And409AfterRestart(t *testing.T){
 rig,pub,priv:=receiptRig(t)
 signed:=rig.signedGap(t,2401,"storage_full")
 status,body:=exactPost(rig,signed)
 if status!=202||receipt.DecodeAndVerify(body,signed,pub,rig.now)!=nil{t.Fatal("initial receipt not valid")}
 rig.open(nil)
 rig.hub.receiptPrivate=priv
 status,body=exactPost(rig,signed)
 if status!=409{t.Fatalf("duplicate status %d",status)}
 if err:=receipt.DecodeAndVerify(body,signed,pub,rig.now);err!=nil{t.Fatal(err)}
}
func TestLost202RecoveredOnlyWithSigned409Proof(t *testing.T){
 rig,pub,priv:=receiptRig(t)
 n:=rig.signedGap(t,2402,"log_corrupt")
 path:=filepath.Join(t.TempDir(),"pending.json")
 if err:=gapspool.Enqueue(path,n,rig.pub,rig.now);err!=nil{t.Fatal(err)}
 original,_:=os.ReadFile(path)
 err:=gapspool.DispatchSigned(path,rig.pub,pub,rig.now,func(data []byte)(int,[]byte,error){
  status,body,postErr:=postHUBForTest(rig,data)
  if postErr!=nil{t.Fatal(postErr)}
  if status!=202{t.Fatalf("HUB did not store: %d",status)}
  _=body // a lost connection hides the true acknowledgment
  return 0,nil,os.ErrDeadlineExceeded
 })
 if err==nil || gapspool.Status(path)!="PENDING_UNCONFIRMED"{t.Fatal("lost acknowledgment cleared pending")}
 rig.open(nil)
 rig.hub.receiptPrivate=priv
 err=gapspool.DispatchSigned(path,rig.pub,pub,rig.now,func(data []byte)(int,[]byte,error){
  if !bytes.Equal(data,original){t.Fatal("original signature changed")}
  return postHUBForTest(rig,data)
 })
 if err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(path);!os.IsNotExist(err){t.Fatal("signed 409 did not resolve pending")}
}
func TestUnsigned202NeverClearsPinnedMode(t *testing.T){
 rig,pub,_:=receiptRig(t)
 rig.hub.receiptPrivate=nil
 n:=rig.signedGap(t,2403,"transport_outage")
 path:=filepath.Join(t.TempDir(),"pending.json")
 if err:=gapspool.Enqueue(path,n,rig.pub,rig.now);err!=nil{t.Fatal(err)}
 err:=gapspool.DispatchSigned(path,rig.pub,pub,rig.now,func(data []byte)(int,[]byte,error){
  return postHUBForTest(rig,data)
 })
 if err==nil||gapspool.Status(path)!="PENDING_UNCONFIRMED"{t.Fatal("unsigned ACK removed pinned notice")}
}
func TestForgedHUBReceiptIsRejected(t *testing.T){
 rig,pub,_:=receiptRig(t)
 n:=rig.signedGap(t,2404,"unknown")
 path:=filepath.Join(t.TempDir(),"pending.json")
 if err:=gapspool.Enqueue(path,n,rig.pub,rig.now);err!=nil{t.Fatal(err)}
 other,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 err=gapspool.DispatchSigned(path,rig.pub,other,rig.now,func(data []byte)(int,[]byte,error){
  return postHUBForTest(rig,data)
 })
 if err==nil || gapspool.Status(path)!="PENDING_UNCONFIRMED"{t.Fatal("untrusted HUB signer accepted")}
 _=pub
}
func TestArchiveOnlySeenNeverReceivesProof(t *testing.T){
 rig,_,_:=receiptRig(t)
 n:=rig.signedGap(t,2405,"recovery_gap")
 rig.hub.seen[n.Report.NodeID+":"+n.Report.EventID]=true
 status,raw:=exactPost(rig,n)
 if status!=409{t.Fatalf("archive-only status: %d",status)}
 var signed receipt.Signed
 if json.Unmarshal(raw,&signed)==nil && signed.Signature!=""{t.Fatal("archive-only lookup created a fabricated receipt")}
}
func TestSameEventIDDifferentSignedReportCannotClaimReceipt(t *testing.T){
 rig,pub,_:=receiptRig(t)
 n:=rig.signedGap(t,2406,"storage_full")
 status,_:=exactPost(rig,n);if status!=202{t.Fatal("initial report refused")}
 n.Report.CampaignFingerprint,_=protocol.CoverageGapFingerprint("recovery_gap")
 modified,err:=protocol.SignReport(n.Report,rig.private);if err!=nil{t.Fatal(err)}
 status,raw:=exactPost(rig,modified)
 if status!=409 || receipt.DecodeAndVerify(raw,modified,pub,rig.now)==nil{
  t.Fatal("same event ID with changed signed content wrongly acknowledged")
 }
}
func TestCorruptLedgerCheckpointBlocksDuplicateProof(t *testing.T){
 rig,_,_:=receiptRig(t)
 n:=rig.signedGap(t,2407,"log_unavailable")
 status,_:=exactPost(rig,n);if status!=202{t.Fatal("initial report refused")}
 if err:=os.WriteFile(rig.path+".head",[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 status,_=exactPost(rig,n)
 if status!=503 || !rig.hub.poisoned{t.Fatal("corrupt ledger was signed as valid")}
}
func TestReceiptPrivateKeyRefusesUnsafeModeAndSymlink(t *testing.T){
 root:=t.TempDir()
 _,priv,_:=ed25519.GenerateKey(rand.Reader)
 raw:=[]byte(fmt.Sprintf("%x",priv))
 file:=filepath.Join(root,"private.hex")
 if err:=os.WriteFile(file,raw,0644);err!=nil{t.Fatal(err)}
 if _,err:=readPrivateReceiptKey(file);err==nil{t.Fatal("exposed signer accepted")}
 if err:=os.Chmod(file,0600);err!=nil{t.Fatal(err)}
 if _,err:=readPrivateReceiptKey(file);err!=nil{t.Fatal(err)}
 symlink:=filepath.Join(root,"symlink.hex")
 if err:=os.Symlink(file,symlink);err!=nil{t.Skip(err)}
 if _,err:=readPrivateReceiptKey(symlink);err==nil{t.Fatal("signer symlink accepted")}
}
func TestReceiptCannotValidateUnrelatedSigner(t *testing.T){
 rig,pub,_:=receiptRig(t)
 n:=rig.signedGap(t,2408,"log_corrupt")
 status,raw:=exactPost(rig,n);if status!=202{t.Fatal("failed to store")}
 n.Report.ObservedAt=n.Report.ObservedAt.Add(-time.Second)
 if receipt.DecodeAndVerify(raw,n,pub,rig.now)==nil{t.Fatal("receipt not bound to original report")}
}
