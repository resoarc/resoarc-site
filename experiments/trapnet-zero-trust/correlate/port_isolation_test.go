package correlate

import (
 "encoding/json"
 "fmt"
 "strings"
 "testing"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
func TestSameFingerprintDifferentTargetPortsStaySeparate(t *testing.T) {
 r:=makeRig(t)
 mk:=func(node,n,port int)string{
  report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:r.ids[node],
   EventID:fmt.Sprintf("%032x",n),ObservedAt:r.now,Kind:"http_probe",
   TargetPort:port,CampaignFingerprint:fp}
  sr,err:=protocol.SignReport(report,r.private[node]);if err!=nil{t.Fatal(err)}
  b,err:=json.Marshal(LedgerRow{ReceivedAt:r.now,Evidence:sr});if err!=nil{t.Fatal(err)}
  return string(b)+"\n"
 }
 evidence:=mk(0,1,443)+mk(2,2,22)
 result,err:=Analyze(strings.NewReader(evidence),r.trust,r.now)
 if err!=nil{t.Fatal(err)}
 if len(result.Cases)!=2{t.Fatalf("unrelated target ports were correlated: %+v",result)}
 for _,item:=range result.Cases {
  if item.Verdict!="single_operator_or_unreviewed"{t.Fatal("unrelated observation falsely upgraded")}
 }
}
