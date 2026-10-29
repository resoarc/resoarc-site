package main

import (
 "bytes"
 "errors"
 "io"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "testing"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/gapspool"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

func postHUBForTest(rig *hubTestRig, payload []byte)(int,[]byte,error) {
 req:=httptest.NewRequest(http.MethodPost,"/report",bytes.NewReader(payload))
 req.Header.Set("Content-Type","application/json")
 w:=httptest.NewRecorder()
 rig.hub.report(w,req)
 return w.Code,append([]byte(nil),w.Body.Bytes()...),nil
}

func TestSignedGapOutboxToHUBConfirmed(t *testing.T){
 rig:=newRig(t)
 notice:=rig.signedGap(t,405,"storage_full")
 path:=filepath.Join(t.TempDir(),"pending-gap.json")
 if err:=gapspool.Enqueue(path,notice,rig.pub,rig.now);err!=nil{t.Fatal(err)}
 if err:=gapspool.Dispatch(path,rig.pub,rig.now,func(payload []byte)(int,[]byte,error){
  return postHUBForTest(rig,payload)
 });err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(path);!errors.Is(err,os.ErrNotExist){t.Fatal("confirmed notice remained pending")}
 if code:=rig.post(notice);code!=http.StatusConflict{t.Fatalf("HUB ledger lost delivered report: %d",code)}
}

func TestSignedGapOutboxSurvivesHUBOutageAndRetriesExactly(t *testing.T){
 rig:=newRig(t)
 notice:=rig.signedGap(t,406,"log_corrupt")
 path:=filepath.Join(t.TempDir(),"pending-gap.json")
 if err:=gapspool.Enqueue(path,notice,rig.pub,rig.now);err!=nil{t.Fatal(err)}
 original,_:=os.ReadFile(path)
 err:=gapspool.Dispatch(path,rig.pub,rig.now,func([]byte)(int,[]byte,error){
  return http.StatusServiceUnavailable,nil,errors.New("HUB stopped")
 })
 if err==nil{t.Fatal("lost outage state")}
 if status:=gapspool.Status(path);status!="PENDING_UNCONFIRMED"{t.Fatalf("outbox not retained: %s",status)}
 if err:=gapspool.Dispatch(path,rig.pub,rig.now,func(payload []byte)(int,[]byte,error){
  if !bytes.Equal(payload,original){t.Fatal("the retry minted a different event")}
  return postHUBForTest(rig,payload)
 });err!=nil{t.Fatal(err)}
 if _,err:=os.Lstat(path);!errors.Is(err,os.ErrNotExist){t.Fatal("confirmed report not removed")}
}

func TestLostAckAfterHUBDurablyAcceptedRetainsHOLD(t *testing.T){
 rig:=newRig(t)
 notice:=rig.signedGap(t,407,"transport_outage")
 path:=filepath.Join(t.TempDir(),"pending-gap.json")
 if err:=gapspool.Enqueue(path,notice,rig.pub,rig.now);err!=nil{t.Fatal(err)}
 original,_:=os.ReadFile(path)
 // HUB has written + synced its ledger and returned 202, but simulated network
 // truncation means the Sensor cannot know that receipt is durable.
 err:=gapspool.Dispatch(path,rig.pub,rig.now,func(payload []byte)(int,[]byte,error){
  status,_,postErr:=postHUBForTest(rig,payload)
  if postErr!=nil||status!=http.StatusAccepted{t.Fatalf("HUB did not receive fixture: %d %v",status,postErr)}
  return 0,nil,io.ErrUnexpectedEOF
 })
 if err==nil{t.Fatal("unconfirmed response accepted")}
 // A repeat with same signature is a genuine 409 from the persisted HUB replay
 // index. It is still ambiguous to the sender without signed receipt proof.
 err=gapspool.Dispatch(path,rig.pub,rig.now,func(payload []byte)(int,[]byte,error){
  if !bytes.Equal(payload,original){t.Fatal("retry changed signed report")}
  status,body,postErr:=postHUBForTest(rig,payload)
  if status!=http.StatusConflict{t.Fatalf("replayed notice status: %d",status)}
  return status,body,postErr
 })
 if err==nil{t.Fatal("409 wrongly cleared a lost-ACK event")}
 if status:=gapspool.Status(path);status!="PENDING_UNCONFIRMED"{t.Fatalf("ambiguous event discarded: %s",status)}
}

func TestRevokedSensorGapKeepsPending(t *testing.T){
 rig:=newRig(t)
 notice:=rig.signedGap(t,408,"recovery_gap")
 path:=filepath.Join(t.TempDir(),"pending-gap.json")
 if err:=gapspool.Enqueue(path,notice,rig.pub,rig.now);err!=nil{t.Fatal(err)}
 rig.open(map[string]bool{protocol.NodeID(rig.pub):true})
 err:=gapspool.Dispatch(path,rig.pub,rig.now,func(payload []byte)(int,[]byte,error){
  status,body,postErr:=postHUBForTest(rig,payload)
  if status!=http.StatusForbidden{t.Fatalf("revoked key accepted: %d",status)}
  return status,body,postErr
 })
 if err==nil{t.Fatal("revoked notice marked delivered")}
 if status:=gapspool.Status(path);status!="PENDING_UNCONFIRMED"{t.Fatal("revoked gap lost")}
}
