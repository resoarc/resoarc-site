package correlate

import (
 "encoding/json"
 "fmt"
 "strings"
 "testing"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

func makeGapLine(t *testing.T,r *rig,i,n int,reason string)string{
 t.Helper()
 fp,err:=protocol.CoverageGapFingerprint(reason);if err!=nil{t.Fatal(err)}
 report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:r.ids[i],
 EventID:fmt.Sprintf("%032x",n),ObservedAt:r.now,Kind:protocol.CoverageGapKind,
 TargetPort:0,CampaignFingerprint:fp}
 signed,err:=protocol.SignReport(report,r.private[i]);if err!=nil{t.Fatal(err)}
 b,err:=json.Marshal(LedgerRow{ReceivedAt:r.now,Evidence:signed});if err!=nil{t.Fatal(err)}
 return string(b)+"\n"
}
func TestSignedGapStopsManualTriage(t *testing.T){
 r:=makeRig(t)
 for _,input:=range []string{
  makeGapLine(t,r,0,50,"storage_full"),
  r.signed(t,0,1,r.now)+makeGapLine(t,r,1,50,"log_corrupt"),
  makeGapLine(t,r,1,50,"recovery_gap")+r.signed(t,0,1,r.now)+r.signed(t,2,2,r.now),
  r.signed(t,0,1,r.now)+r.signed(t,2,2,r.now)+makeGapLine(t,r,1,50,"transport_outage"),
 }{
  out,err:=Analyze(strings.NewReader(input),r.trust,r.now)
  if err==nil{t.Fatalf("gap accepted as attack evidence: %+v",out)}
  if out.FeedPublished||out.AutomaticBlocking{t.Fatal("dangerous side effect on HOLD")}
 }
}
func TestGapTamperingFailsClosed(t *testing.T){
 r:=makeRig(t)
 s:=makeGapLine(t,r,0,50,"storage_full")
 modified:=strings.Replace(s,`"target_port":0`,`"target_port":22`,1)
 if modified==s{t.Fatal("fixture failed")}
 if _,err:=Analyze(strings.NewReader(modified),r.trust,r.now);err==nil{
  t.Fatal("invalid gap target accepted")
 }
}
func TestOrdinaryCorroborationUnaffectedByGapFeature(t *testing.T){
 r:=makeRig(t)
 clean:=r.signed(t,0,1,r.now)+r.signed(t,2,2,r.now)
 result,err:=Analyze(strings.NewReader(clean),r.trust,r.now)
 if err!=nil||len(result.Cases)!=1||result.Cases[0].Verdict!="multi_operator_candidate_for_manual_review"{
  t.Fatalf("ordinary triage unexpectedly changed: %v",err)
 }
}
