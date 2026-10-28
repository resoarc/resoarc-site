package main

import(
 "os"
 "bytes"
 "encoding/hex"
 "testing"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/correlate"
)

func (rig *hubTestRig) signedGap(t *testing.T,n int,reason string) protocol.SignedReport {
 t.Helper()
 report:=rig.signed(t,n).Report
 report.Kind=protocol.CoverageGapKind
 report.TargetPort=0
 var err error
 report.CampaignFingerprint,err=protocol.CoverageGapFingerprint(reason)
 if err!=nil{t.Fatal(err)}
 signed,err:=protocol.SignReport(report,rig.private)
 if err!=nil{t.Fatal(err)}
 return signed
}

func TestHubPersistsSignedGapAndRejectsReplay(t *testing.T){
 rig:=newRig(t)
 gap:=rig.signedGap(t,101,"storage_full")
 if status:=rig.post(gap);status!=202{t.Fatalf("gap rejected: %d",status)}
 data,err:=os.ReadFile(rig.path);if err!=nil{t.Fatal(err)}
 if !bytes.Contains(data,[]byte(`"coverage_gap"`)){t.Fatal("gap not included in the signed evidence ledger")}
 if status:=rig.post(gap);status!=409{t.Fatalf("replay not rejected: %d",status)}
 rig.open(nil)
 if status:=rig.post(gap);status!=409{t.Fatalf("replay after restart not rejected: %d",status)}
}
func TestHubRejectsTamperedGap(t *testing.T){
 rig:=newRig(t)
 sr:=rig.signedGap(t,102,"log_corrupt")
 sr.Report.CampaignFingerprint,_=protocol.CoverageGapFingerprint("unknown")
 if status:=rig.post(sr);status!=403{t.Fatalf("tampered signed gap accepted: %d",status)}
}
func TestHubRejectsRevokedGap(t *testing.T){
 rig:=newRig(t)
 rig.open(map[string]bool{protocol.NodeID(rig.pub):true})
 if status:=rig.post(rig.signedGap(t,103,"recovery_gap"));status!=403{
  t.Fatalf("revoked node accepted gap: %d",status)
 }
}
func TestHubRejectsGapWithTargetPort(t *testing.T){
 rig:=newRig(t)
 gap:=rig.signedGap(t,104,"transport_outage")
 gap.Report.TargetPort=22
 signed,err:=protocol.SignReport(gap.Report,rig.private)
 if err!=nil{t.Fatal(err)}
 if status:=rig.post(signed);status!=403{t.Fatalf("gap with target port accepted: %d",status)}
}

func TestHubSignedGapForcesOfflineCorrelatorHold(t *testing.T){
 rig:=newRig(t)
 if status:=rig.post(rig.signed(t,105));status!=202{t.Fatalf("ordinary event rejected: %d",status)}
 if status:=rig.post(rig.signedGap(t,106,"storage_full"));status!=202{t.Fatalf("signed gap rejected: %d",status)}
 if status:=rig.post(rig.signed(t,107));status!=202{t.Fatalf("post-gap ordinary event rejected: %d",status)}
 buf,err:=os.ReadFile(rig.path);if err!=nil{t.Fatal(err)}
 trust:=map[string]correlate.TrustedNode{
   protocol.NodeID(rig.pub):{PublicKey:hex.EncodeToString(rig.pub),OperatorGroup:"operator_one",Reviewed:true},
 }
 out,err:=correlate.Analyze(bytes.NewReader(buf),trust,rig.now)
 if err==nil{t.Fatalf("signed gap silently ignored: %+v",out)}
 if out.FeedPublished||out.AutomaticBlocking{t.Fatal("offline HOLD triggered forbidden action")}
}
