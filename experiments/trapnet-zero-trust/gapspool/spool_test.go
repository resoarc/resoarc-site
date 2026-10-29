package gapspool

import (
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

type fixture struct{
 path string
 pub ed25519.PublicKey
 priv ed25519.PrivateKey
 notice protocol.SignedReport
 now time.Time
}
func rig(t *testing.T)*fixture{
 t.Helper()
 root:=t.TempDir()
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 now:=time.Now().UTC()
 digest,err:=protocol.CoverageGapFingerprint("storage_full");if err!=nil{t.Fatal(err)}
 report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:protocol.NodeID(pub),
  EventID:"0123456789abcdef0123456789abcdef",Kind:protocol.CoverageGapKind,
  TargetPort:0,CampaignFingerprint:digest,ObservedAt:now}
 signed,err:=protocol.SignReport(report,priv);if err!=nil{t.Fatal(err)}
 return &fixture{path:filepath.Join(root,"gap.json"),pub:pub,priv:priv,notice:signed,now:now}
}
func (r *fixture) stage(t *testing.T){t.Helper();if err:=Enqueue(r.path,r.notice,r.pub,r.now);err!=nil{t.Fatal(err)}}
func accepted(payload []byte)(int,[]byte,error){
 return 202,[]byte(`{"status":"received_unverified"}`),nil
}
func rejected(code int)PostFunc {
 return func([]byte)(int,[]byte,error){return code,[]byte(`{"status":"received_unverified"}`),nil}
}

func TestStagePersistsSignedReportAndExclusive(t *testing.T){
 r:=rig(t);r.stage(t)
 b,err:=os.ReadFile(r.path);if err!=nil{t.Fatal(err)}
 if !bytes.Contains(b,[]byte(`"coverage_gap"`)){t.Fatal("signed notice absent")}
 if err:=Enqueue(r.path,r.notice,r.pub,r.now);err==nil{t.Fatal("overwrote an unconfirmed gap")}
}
func TestAcceptedDispatchRemovesPending(t *testing.T){
 r:=rig(t);r.stage(t)
 if err:=Dispatch(r.path,r.pub,r.now,accepted);err!=nil{t.Fatal(err)}
 if _,err:=os.Lstat(r.path);!errors.Is(err,os.ErrNotExist){t.Fatal("notice not removed after confirmed acceptance")}
}
func TestRetryReusesSameSignatureAndEventID(t *testing.T){
 r:=rig(t);r.stage(t)
 original,err:=os.ReadFile(r.path);if err!=nil{t.Fatal(err)}
 if err:=Dispatch(r.path,r.pub,r.now,func(data []byte)(int,[]byte,error){
  if !bytes.Equal(original,data){t.Fatal("changed signed event while retrying")}
  return 503,nil,nil
 });err==nil{t.Fatal("failure accepted")}
 if err:=Dispatch(r.path,r.pub,r.now,func(data []byte)(int,[]byte,error){
  if !bytes.Equal(original,data){t.Fatal("new event minted during retry")}
  return accepted(data)
 });err!=nil{t.Fatal(err)}
}
func TestUnknownDeliveryLeavesPending(t *testing.T){
 for _,status:=range []int{200,201,202,400,403,409,429,500,503}{
  t.Run(fmt.Sprintf("%d",status),func(t *testing.T){
   r:=rig(t);r.stage(t)
   callback:=rejected(status)
   if status==202 {
    callback=func([]byte)(int,[]byte,error){return 202,[]byte(`{"status":"other"}`),nil}
   }
   if Dispatch(r.path,r.pub,r.now,callback)==nil{t.Fatal("accepted unconfirmed response")}
   if Status(r.path)!="PENDING_UNCONFIRMED"{t.Fatal("pending removed on ambiguous response")}
  })
 }
}
func TestTransportErrorLeavesPending(t *testing.T){
 r:=rig(t);r.stage(t)
 err:=Dispatch(r.path,r.pub,r.now,func([]byte)(int,[]byte,error){
  return 0,nil,errors.New("connection refused")
 })
 if err==nil||Status(r.path)!="PENDING_UNCONFIRMED"{t.Fatal("delivery failure discarded notice")}
}
func TestAckMustBeExactlyExpectedObject(t *testing.T){
 for _,ack:=range []string{"","{}","[]",`{"status":"received_unverified","extra":"x"}`,
  `{"status":"received_unverified"}{}`,`{"status":"received_unverified","status":"other"}`,
  `{"status":"success"}`}{
  r:=rig(t);r.stage(t)
  err:=Dispatch(r.path,r.pub,r.now,func([]byte)(int,[]byte,error){
   return 202,[]byte(ack),nil
  })
  if err==nil{t.Fatalf("accepted unsafe ack: %q",ack)}
 }
}
func TestExpiredGapRemainsPendingWithoutPost(t *testing.T){
 r:=rig(t);r.stage(t);called:=false
 err:=Dispatch(r.path,r.pub,r.now.Add(11*time.Minute),func([]byte)(int,[]byte,error){
  called=true;return accepted(nil)
 })
 if err==nil||called||Status(r.path)!="PENDING_UNCONFIRMED"{t.Fatal("expired gap was sent or lost")}
}
func TestTamperedGapRefusedWithoutPost(t *testing.T){
 r:=rig(t);r.stage(t);b,err:=os.ReadFile(r.path);if err!=nil{t.Fatal(err)}
 b=bytes.Replace(b,[]byte("coverage_gap"),[]byte("coverage_bad"),1)
 if err:=os.WriteFile(r.path,b,0600);err!=nil{t.Fatal(err)}
 called:=false
 err=Dispatch(r.path,r.pub,r.now,func([]byte)(int,[]byte,error){
  called=true;return accepted(nil)
 })
 if err==nil||called{t.Fatal("transmitted altered gap")}
}
func TestWrongKeyRefused(t *testing.T){
 r:=rig(t);r.stage(t)
 other,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 if Dispatch(r.path,other,r.now,accepted)==nil{t.Fatal("accepted wrong signer")}
}
func TestStageInvalidSignatureRefused(t *testing.T){
 r:=rig(t)
 n:=r.notice;n.Signature=strings.Repeat("0",128)
 if Enqueue(r.path,n,r.pub,r.now)==nil{t.Fatal("accepted forged gap")}
 if Status(r.path)=="PENDING_UNCONFIRMED"{t.Fatal("created forged pending notice")}
}
func TestNormalEventCannotBeStaged(t *testing.T){
 r:=rig(t)
 n:=r.notice
 n.Report.Kind="http_probe";n.Report.TargetPort=443
 n.Report.CampaignFingerprint=hex.EncodeToString(make([]byte,32))
 signed,err:=protocol.SignReport(n.Report,r.priv);if err!=nil{t.Fatal(err)}
 if Enqueue(r.path,signed,r.pub,r.now)==nil{t.Fatal("queued ordinary event as a gap")}
}
func TestPrivateSpoolPermissions(t *testing.T){
 r:=rig(t);r.stage(t)
 fi,err:=os.Stat(r.path);if err!=nil{t.Fatal(err)}
 if fi.Mode().Perm()&0077!=0{t.Fatal("readable by other users")}
}
func TestSymlinkPendingRefused(t *testing.T){
 r:=rig(t)
 target:=filepath.Join(filepath.Dir(r.path),"target")
 if err:=os.WriteFile(target,[]byte("secret"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Symlink(target,r.path);err!=nil{t.Skip(err)}
 if Enqueue(r.path,r.notice,r.pub,r.now)==nil{t.Fatal("followed symlink on stage")}
 if Dispatch(r.path,r.pub,r.now,accepted)==nil{t.Fatal("followed symlink on send")}
 b,_:=os.ReadFile(target);if string(b)!="secret"{t.Fatal("target overwritten")}
}
func TestMissingParentFailsClosed(t *testing.T){
 r:=rig(t);r.path=filepath.Join(filepath.Dir(r.path),"missing","gap")
 if Enqueue(r.path,r.notice,r.pub,r.now)==nil{t.Fatal("created unsolicited directory")}
}
func TestRelativePathFailsClosed(t *testing.T){
 r:=rig(t);if Enqueue("gap.json",r.notice,r.pub,r.now)==nil{t.Fatal("relative spool accepted")}
}
func TestWorldWritableParentFailsClosed(t *testing.T){
 r:=rig(t)
 if err:=os.Chmod(filepath.Dir(r.path),0777);err!=nil{t.Skip(err)}
 defer os.Chmod(filepath.Dir(r.path),0700)
 if Enqueue(r.path,r.notice,r.pub,r.now)==nil{t.Fatal("writable parent accepted")}
}
func TestStaleLockRequiresOperatorReview(t *testing.T){
 r:=rig(t);r.stage(t)
 if err:=os.WriteFile(r.path+".lock",[]byte("crashed"),0600);err!=nil{t.Fatal(err)}
 if Dispatch(r.path,r.pub,r.now,accepted)==nil{t.Fatal("auto-cleared stale lock")}
 if Status(r.path)!="PENDING_UNCONFIRMED"{t.Fatal("pending gap lost")}
}
func TestMalformedPendingFailsClosed(t *testing.T){
 r:=rig(t)
 if err:=os.WriteFile(r.path,[]byte("{invalid"),0600);err!=nil{t.Fatal(err)}
 if Dispatch(r.path,r.pub,r.now,accepted)==nil{t.Fatal("transmitted malformed pending notice")}
}
func TestConcurrentReplacementNotDeleted(t *testing.T){
 r:=rig(t);r.stage(t)
 err:=Dispatch(r.path,r.pub,r.now,func([]byte)(int,[]byte,error){
  if err:=os.Remove(r.path);err!=nil{t.Fatal(err)}
  if err:=os.WriteFile(r.path,[]byte("replacement"),0600);err!=nil{t.Fatal(err)}
  return accepted(nil)
 })
 if err==nil{t.Fatal("deleted replacement of pending spool")}
 b,_:=os.ReadFile(r.path);if string(b)!="replacement"{t.Fatal("replacement was deleted")}
}
func TestInPlaceMutationAfterSendDoesNotDeleteSpool(t *testing.T){
 r:=rig(t);r.stage(t)
 err:=Dispatch(r.path,r.pub,r.now,func([]byte)(int,[]byte,error){
  data,readErr:=os.ReadFile(r.path);if readErr!=nil{t.Fatal(readErr)}
  data[len(data)-1]^=1
  if writeErr:=os.WriteFile(r.path,data,0600);writeErr!=nil{t.Fatal(writeErr)}
  return accepted(nil)
 })
 if err==nil{t.Fatal("cleared a notice modified in place")}
 if _,err:=os.Stat(r.path);err!=nil{t.Fatal("mutated pending notice deleted")}
}
func TestDuplicateAckKeyCannotBeAccepted(t *testing.T){
 for _,raw:=range []string{
  `{"status":"received_unverified","status":"received_unverified"}`,
  `{"status":"wrong","status":"received_unverified"}`,
 }{
  if strictlyAcceptedAck(202,[]byte(raw)){t.Fatal("duplicate response key accepted")}
 }
}
func TestNoSpoolIsNotEvidenceOfContinuousObservation(t *testing.T){
 r:=rig(t)
 if Status(r.path)!="NO_PENDING_FILE_NOT_COVERAGE_PROOF"{t.Fatal("absent file treated as evidence of health")}
}
func TestNoTransportRefused(t *testing.T){
 r:=rig(t);r.stage(t)
 if Dispatch(r.path,r.pub,r.now,nil)==nil{t.Fatal("missing transport accepted")}
}
