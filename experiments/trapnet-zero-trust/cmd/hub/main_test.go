package main

import (
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "testing"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

type testHub struct {
 t *testing.T
 now time.Time
 pub ed25519.PublicKey
 priv ed25519.PrivateKey
 path string
 file *os.File
 server *server
}
func setupHub(t *testing.T)*testHub{
 pub,priv,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 h:=&testHub{t:t,now:time.Now().UTC(),pub:pub,priv:priv,path:filepath.Join(t.TempDir(),"ledger.jsonl")}
 h.restart(nil)
 t.Cleanup(func(){if h.file!=nil{h.file.Close()}})
 return h
}
func(h *testHub)restart(revoked map[string]bool){
 h.t.Helper()
 if h.file!=nil{if err:=h.file.Close();err!=nil{h.t.Fatal(err)}}
 f,err:=os.OpenFile(h.path,os.O_CREATE|os.O_RDWR|os.O_APPEND,0600)
 if err!=nil{h.t.Fatal(err)}
 h.file=f
 h.server,err=newServer(map[string]ed25519.PublicKey{protocol.NodeID(h.pub):h.pub},revoked,f,func()time.Time{return h.now})
 if err!=nil{h.t.Fatal(err)}
}
func(h *testHub)signed(id int)protocol.SignedReport{
 h.t.Helper()
 event:=make([]byte,16)
 event[0]=byte(id)
 event[1]=byte(id>>8)
 r:=protocol.Report{Schema:protocol.ReportSchema,NodeID:protocol.NodeID(h.pub),EventID:hex.EncodeToString(event),
  ObservedAt:h.now,Kind:"http_probe",TargetPort:443,CampaignFingerprint:"e7f6c011776e8db7cd330b54174fd76f92339faf0c35e882e6d803a95e0e741d"}
 sr,err:=protocol.SignReport(r,h.priv)
 if err!=nil{h.t.Fatal(err)}
 return sr
}
func(h *testHub)post(sr protocol.SignedReport)int{
 b,_:=json.Marshal(sr)
 req:=httptest.NewRequest(http.MethodPost,"/report",bytes.NewReader(b))
 req.Header.Set("Content-Type","application/json")
 w:=httptest.NewRecorder()
 h.server.report(w,req)
 return w.Code
}
func TestRestartReplayAndRateLimit(t *testing.T){
 h:=setupHub(t)
 for i:=1;i<=perNodeMinuteLimit;i++ {
  if code:=h.post(h.signed(i));code!=202{t.Fatalf("event %d => %d",i,code)}
 }
 h.restart(nil)
 if code:=h.post(h.signed(1));code!=409{t.Fatalf("replay after restart => %d",code)}
 if code:=h.post(h.signed(31));code!=429{t.Fatalf("rate after restart => %d",code)}
 h.now=h.now.Add(61*time.Second)
 if code:=h.post(h.signed(31));code!=202{t.Fatalf("rate recovery => %d",code)}
}
func TestRevokedAndForgedReports(t *testing.T){
 h:=setupHub(t)
 h.restart(map[string]bool{protocol.NodeID(h.pub):true})
 if code:=h.post(h.signed(1));code!=403{t.Fatalf("revoked => %d",code)}
 h.restart(nil)
 sr:=h.signed(2)
 sr.Report.TargetPort=22
 if code:=h.post(sr);code!=403{t.Fatalf("tamper => %d",code)}
}
func TestFailClosedRevocationConfig(t *testing.T){
 h:=setupHub(t)
 dir:=t.TempDir()
 allow:=filepath.Join(dir,"allow.json")
 b,_:=json.Marshal(map[string]string{protocol.NodeID(h.pub):hex.EncodeToString(h.pub)})
 if err:=os.WriteFile(allow,b,0600);err!=nil{t.Fatal(err)}
 if _,_,err:=loadTrust(allow,filepath.Join(dir,"missing.json"));err==nil{t.Fatal("missing revocation file accepted")}
 rev:=filepath.Join(dir,"rev.json")
 ids,_:=json.Marshal([]string{protocol.NodeID(h.pub)})
 if err:=os.WriteFile(rev,ids,0600);err!=nil{t.Fatal(err)}
 _,rejected,err:=loadTrust(allow,rev)
 if err!=nil || !rejected[protocol.NodeID(h.pub)] {t.Fatalf("revocation failed: %v",err)}
}
func TestOversizedAndUnknownFieldsRejected(t *testing.T){
 h:=setupHub(t)
 b,_:=json.Marshal(h.signed(1))
 for _,raw:=range [][]byte{append([]byte(`{"extra":true,`),b[1:]...),append(b,bytes.Repeat([]byte(" "),9000)...)}{
  req:=httptest.NewRequest(http.MethodPost,"/report",bytes.NewReader(raw))
  req.Header.Set("Content-Type","application/json")
  w:=httptest.NewRecorder()
  h.server.report(w,req)
  if w.Code!=400{t.Fatalf("malformed payload => %d",w.Code)}
 }
}
func TestLegacyLedgerReplay(t *testing.T){
 h:=setupHub(t)
 sr:=h.signed(1)
 b,_:=json.Marshal(sr)
 if err:=os.WriteFile(h.path,append(b,'\n'),0600);err!=nil{t.Fatal(err)}
 h.restart(nil)
 if code:=h.post(sr);code!=409{t.Fatalf("legacy replay => %d",code)}
}
