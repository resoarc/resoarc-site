package main

import (
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/correlate"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)
type witnessTrial struct{
 ledger,history,trust,pubfile string
 ledgerHash,trustHash,tip string
 now time.Time
 nodes []ed25519.PrivateKey
 public []ed25519.PublicKey
}
func fileHash(t *testing.T,path string)string{
 t.Helper();b,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 h:=sha256.Sum256(b);return hex.EncodeToString(h[:])
}
func (r *witnessTrial) add(t *testing.T,node,num int){
 t.Helper()
 report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:protocol.NodeID(r.public[node]),
 EventID:fmt.Sprintf("%032x",num),ObservedAt:r.now,Kind:"http_probe",TargetPort:443,CampaignFingerprint:strings.Repeat("c",64)}
 signed,err:=protocol.SignReport(report,r.nodes[node]);if err!=nil{t.Fatal(err)}
 raw,err:=json.Marshal(correlate.LedgerRow{ReceivedAt:r.now,Evidence:signed});if err!=nil{t.Fatal(err)}
 f,err:=os.OpenFile(r.ledger,os.O_CREATE|os.O_APPEND|os.O_WRONLY,0600);if err!=nil{t.Fatal(err)}
 if _,err=f.Write(append(raw,'\n'));err!=nil{t.Fatal(err)}
 if err=f.Close();err!=nil{t.Fatal(err)}
 measured,err:=witness.Measure(r.ledger,nil);if err!=nil{t.Fatal(err)}
 b,err:=json.Marshal(measured);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(r.ledger+".head",b,0600);err!=nil{t.Fatal(err)}
 r.ledgerHash=fileHash(t,r.ledger)
}
func newWitnessTrial(t *testing.T)*witnessTrial{
 t.Helper()
 d:=t.TempDir()
 r:=&witnessTrial{ledger:filepath.Join(d,"ledger.jsonl"),history:filepath.Join(d,"witness.jsonl"),
 trust:filepath.Join(d,"trust.json"),pubfile:filepath.Join(d,"witness.pub"),
 now:time.Now().UTC().Truncate(time.Minute)}
 trust:=map[string]correlate.TrustedNode{}
 for _,group:=range []string{"same_operator","other_operator","same_operator"}{
  pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
  r.public=append(r.public,pub);r.nodes=append(r.nodes,priv)
  trust[protocol.NodeID(pub)]=correlate.TrustedNode{PublicKey:hex.EncodeToString(pub),OperatorGroup:group,Reviewed:true}
 }
 data,_:=json.Marshal(trust);if err:=os.WriteFile(r.trust,data,0600);err!=nil{t.Fatal(err)}
 r.trustHash=fileHash(t,r.trust)
 r.add(t,0,1);r.add(t,1,2)
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(r.pubfile,[]byte(hex.EncodeToString(pub)),0600);err!=nil{t.Fatal(err)}
 _,tip,err:=witness.Attest(r.ledger,r.history,priv,r.now.Add(time.Second),"",true)
 if err!=nil{t.Fatal(err)};r.tip=tip
 return r
}
func (r *witnessTrial) args()[]string{
 return []string{"-ledger",r.ledger,"-trust",r.trust,"-ledger-sha256",r.ledgerHash,
 "-trust-sha256",r.trustHash,"-witness-history",r.history,"-witness-pub",r.pubfile,"-witness-tip",r.tip}
}
func TestMandatoryWitnessGoodTriagedLedger(t *testing.T){
 r:=newWitnessTrial(t);var out bytes.Buffer
 if err:=run(r.args(),&out,r.now);err!=nil{t.Fatal(err)}
 var got correlate.Summary
 if err:=json.Unmarshal(out.Bytes(),&got);err!=nil{t.Fatal(err)}
 if len(got.Cases)!=1||got.Cases[0].Verdict!="multi_operator_candidate_for_manual_review"||
 got.AutomaticBlocking||got.FeedPublished||got.OperatorIndependenceProven{t.Fatal("unsafe outcome")}
 for _,s:=range []string{protocol.NodeID(r.public[0]),r.tip,"same_operator",strings.Repeat("c",64)}{
  if bytes.Contains(out.Bytes(),[]byte(s)){t.Fatal("sensitive identifier in output")}
 }
}
func TestMandatoryWitnessUnwitnessedTailFailsClosed(t *testing.T){
 r:=newWitnessTrial(t);r.add(t,2,3)
 var out bytes.Buffer
 if err:=run(r.args(),&out,r.now);err==nil{t.Fatal("accepted unwitnessed tail")}
 if out.Len()!=0{t.Fatal("partial result published")}
}
func TestMandatoryWitnessWrongTipFailsClosed(t *testing.T){
 r:=newWitnessTrial(t);a:=r.args();a[len(a)-1]=strings.Repeat("a",64)
 if err:=run(a,&bytes.Buffer{},r.now);err==nil{t.Fatal("wrong external anchor accepted")}
}
func TestMandatoryWitnessWrongSignerFailsClosed(t *testing.T){
 r:=newWitnessTrial(t);pub,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(r.pubfile,[]byte(hex.EncodeToString(pub)),0600);err!=nil{t.Fatal(err)}
 if err=run(r.args(),&bytes.Buffer{},r.now);err==nil{t.Fatal("substituted Witness key accepted")}
}
func TestMandatoryWitnessTruncatedHistoryFailsClosed(t *testing.T){
 r:=newWitnessTrial(t)
 if err:=os.WriteFile(r.history,nil,0600);err!=nil{t.Fatal(err)}
 if err:=run(r.args(),&bytes.Buffer{},r.now);err==nil{t.Fatal("history rollback accepted")}
}
