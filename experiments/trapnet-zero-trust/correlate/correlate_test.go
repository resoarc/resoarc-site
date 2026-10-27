package correlate

import(
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "strings"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
const fp="e7f6c011776e8db7cd330b54174fd76f92339faf0c35e882e6d803a95e0e741d"
type rig struct{
 now time.Time
 ids []string
 private []ed25519.PrivateKey
 trust map[string]TrustedNode
}
func makeRig(t *testing.T)*rig{
 t.Helper()
 r:=&rig{now:time.Now().UTC().Truncate(time.Minute),trust:map[string]TrustedNode{}}
 for _,group:=range []string{"group_one","group_one","group_two"}{
  pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
  id:=protocol.NodeID(pub);r.ids=append(r.ids,id);r.private=append(r.private,priv)
  r.trust[id]=TrustedNode{PublicKey:hex.EncodeToString(pub),OperatorGroup:group,Reviewed:true}
 }
 return r
}
func (r *rig) signed(t *testing.T,i,n int,when time.Time)string{
 t.Helper()
 report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:r.ids[i],
  EventID:fmt.Sprintf("%032x",n),ObservedAt:when,Kind:"http_probe",TargetPort:443,CampaignFingerprint:fp}
 sr,err:=protocol.SignReport(report,r.private[i]);if err!=nil{t.Fatal(err)}
 b,err:=json.Marshal(LedgerRow{ReceivedAt:when,Evidence:sr});if err!=nil{t.Fatal(err)}
 return string(b)+"\n"
}
func TestSameOperatorIsNotIndependent(t *testing.T){
 r:=makeRig(t);s:=r.signed(t,0,1,r.now)+r.signed(t,1,2,r.now)
 got,err:=Analyze(strings.NewReader(s),r.trust,r.now)
 if err!=nil{t.Fatal(err)}
 if len(got.Cases)!=1||got.Cases[0].Verdict!="single_operator_or_unreviewed"{t.Fatalf("false corroboration: %+v",got)}
}
func TestDifferentOperatorsOnlyTriggerReview(t *testing.T){
 r:=makeRig(t);s:=r.signed(t,0,1,r.now)+r.signed(t,2,2,r.now)
 got,err:=Analyze(strings.NewReader(s),r.trust,r.now)
 if err!=nil{t.Fatal(err)}
 if len(got.Cases)!=1||got.Cases[0].Verdict!="multi_operator_candidate_for_manual_review"{t.Fatalf("no review candidate: %+v",got)}
 if got.AutomaticBlocking||got.FeedPublished||got.OperatorIndependenceProven{t.Fatal("dangerous automatic action")}
 raw,_:=json.Marshal(got)
 for _,secret:=range []string{fp,r.ids[0],r.ids[2],"group_one","group_two"}{
  if bytes.Contains(raw,[]byte(secret)){t.Fatal("private identifier leaked")}
 }
}
func TestTamperAndReplayRefused(t *testing.T){
 r:=makeRig(t);s:=r.signed(t,0,1,r.now)
 bad:=strings.Replace(s,`"target_port":443`,`"target_port":444`,1)
 if bad==s{t.Fatal("tamper fixture did not change")}
 if _,err:=Analyze(strings.NewReader(bad),r.trust,r.now);err==nil{t.Fatal("accepted modified signature")}
 if _,err:=Analyze(strings.NewReader(s+s),r.trust,r.now);err==nil{t.Fatal("accepted replay")}
}
func TestUnknownNodeAndReviewFlag(t *testing.T){
 r:=makeRig(t);s:=r.signed(t,0,1,r.now)
 delete(r.trust,r.ids[0])
 if _,err:=Analyze(strings.NewReader(s),r.trust,r.now);err==nil{t.Fatal("unknown key accepted")}
 r=makeRig(t)
 for id,node:=range r.trust{node.Reviewed=false;r.trust[id]=node}
 s=r.signed(t,0,1,r.now)+r.signed(t,2,2,r.now)
 got,err:=Analyze(strings.NewReader(s),r.trust,r.now)
 if err!=nil||got.Cases[0].Verdict!="single_operator_or_unreviewed"{t.Fatal("unreviewed group counted")}
}
func TestStaleOrFutureLedgerRefused(t *testing.T){
 r:=makeRig(t)
 for _,when:=range []time.Time{r.now.Add(-91*24*time.Hour),r.now.Add(3*time.Minute)}{
  if _,err:=Analyze(strings.NewReader(r.signed(t,0,1,when)),r.trust,r.now);err==nil{t.Fatal("out-of-window evidence accepted")}
 }
}
func TestIndependentTimeBuckets(t *testing.T){
 r:=makeRig(t)
 s:=r.signed(t,0,1,r.now.Add(-23*time.Minute))+r.signed(t,2,2,r.now)
 got,err:=Analyze(strings.NewReader(s),r.trust,r.now)
 if err!=nil||len(got.Cases)!=2{t.Fatal("different time windows merged")}
}
func TestUntrustedGroupRejected(t *testing.T){
 r:=makeRig(t)
 n:=r.trust[r.ids[0]];n.OperatorGroup="foo\r\nX-Token";r.trust[r.ids[0]]=n
 if _,err:=Analyze(strings.NewReader(r.signed(t,0,1,r.now)),r.trust,r.now);err==nil{t.Fatal("invalid operator group accepted")}
}
