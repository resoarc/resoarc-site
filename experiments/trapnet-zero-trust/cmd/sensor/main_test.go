package main

import(
 "testing"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

func TestManualGapRequiresKnownCategory(t *testing.T){
 for _,r:=range []string{"log_unavailable","log_corrupt","storage_full","transport_outage","recovery_gap","unknown"}{
  kind,port,fp,err:=selectReportClass("http_probe",80,"demo-non-ip",r)
  if err!=nil||kind!=protocol.CoverageGapKind||port!=0{t.Fatalf("gap: %q: %v",r,err)}
  expected,_:=protocol.CoverageGapFingerprint(r)
  if fp!=expected{t.Fatal("gap fingerprint mismatch")}
 }
}
func TestManualGapRejectsMixedOptions(t *testing.T){
 cases:=[]struct{kind string;port int;fp string;gap string}{
  {"coverage_gap",0,"demo-non-ip",""},
  {"ssh_probe",22,"demo-non-ip","storage_full"},
  {"http_probe",22,"demo-non-ip","storage_full"},
  {"http_probe",80,"198.51.100.12","storage_full"},
  {"http_probe",80,"demo-non-ip","healthy"},
  {"http_probe",80,"demo-non-ip","x\nsecret"},
 }
 for _,v:=range cases{
  if _,_,_,err:=selectReportClass(v.kind,v.port,v.fp,v.gap);err==nil{
   t.Fatalf("mixed or forged gap allowed: %q",v.gap)
  }
 }
}
func TestNormalReportStillSupported(t *testing.T){
 kind,port,fp,err:=selectReportClass("http_probe",443,"synthetic", "")
 if err!=nil||kind!="http_probe"||port!=443||len(fp)!=64{t.Fatalf("normal report invalid %v",err)}
}
