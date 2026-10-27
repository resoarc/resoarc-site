package main

import (
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
// In-memory five-identity lab. No sockets or externally reachable decoys.
// Multiple cryptographic identities DO NOT prove independent ownership.
func TestFiveIdentityLabFailsClosed(t *testing.T){
 now:=time.Now().UTC()
 keys:=map[string]ed25519.PublicKey{}
 privs:=map[string]ed25519.PrivateKey{}
 ids:=make([]string,5)
 for i:=0;i<5;i++{
  pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
  id:=protocol.NodeID(pub);ids[i]=id;keys[id]=pub;privs[id]=priv
 }
 path:=filepath.Join(t.TempDir(),"lab-ledger.jsonl")
 file,err:=os.OpenFile(path,os.O_CREATE|os.O_RDWR|os.O_APPEND,0600);if err!=nil{t.Fatal(err)}
 defer file.Close()
 hub,err:=newServer(keys,map[string]bool{},file,func()time.Time{return now});if err!=nil{t.Fatal(err)}
 makeReport:=func(id string,ordinal int,when time.Time)protocol.SignedReport{
  t.Helper()
  report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:id,EventID:fmt.Sprintf("%032x",ordinal),ObservedAt:when,Kind:"http_probe",TargetPort:443,CampaignFingerprint:"e7f6c011776e8db7cd330b54174fd76f92339faf0c35e882e6d803a95e0e741d"}
  signed,err:=protocol.SignReport(report,privs[id]);if err!=nil{t.Fatal(err)};return signed
 }
 post:=func(report protocol.SignedReport)(int,string){
  t.Helper();data,err:=json.Marshal(report);if err!=nil{t.Fatal(err)}
  req:=httptest.NewRequest(http.MethodPost,"/report",bytes.NewReader(data));req.Header.Set("Content-Type","application/json")
  res:=httptest.NewRecorder();hub.report(res,req);return res.Code,res.Body.String()
 }
 for i,id:=range ids{
  status,body:=post(makeReport(id,i+1,now))
  if status!=202||!bytes.Contains([]byte(body),[]byte("received_unverified")){t.Fatalf("node %d %d %s",i,status,body)}
 }
 if code,_:=post(makeReport(ids[0],1,now));code!=409{t.Fatalf("replay %d",code)}
 forged:=makeReport(ids[1],200,now);forged.Report.TargetPort=22
 if code,_:=post(forged);code!=403{t.Fatalf("forged signature %d",code)}
 stale:=makeReport(ids[2],201,now.Add(-time.Hour))
 if code,_:=post(stale);code!=403{t.Fatalf("stale claim %d",code)}
 hub.mu.Lock();hub.revoked[ids[3]]=true;hub.mu.Unlock()
 if code,_:=post(makeReport(ids[3],202,now));code!=403{t.Fatalf("revoked identity %d",code)}
 if code,_:=post(makeReport(ids[4],203,now));code!=202{t.Fatalf("unaffected identity %d",code)}
 measured,err:=measureLedger(file);if err!=nil{t.Fatal(err)}
 if measured.Rows!=6{t.Fatalf("expected six unverified observations, got %d",measured.Rows)}
 if _,err=hex.DecodeString(measured.Digest);err!=nil{t.Fatal(err)}
}
