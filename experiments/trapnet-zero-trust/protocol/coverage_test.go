package protocol

import (
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "testing"
 "time"
)

func coverageSample(t *testing.T)(Report,ed25519.PublicKey,ed25519.PrivateKey){
 t.Helper()
 pub,priv,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 fingerprint,err:=CoverageGapFingerprint("storage_full");if err!=nil{t.Fatal(err)}
 return Report{Schema:ReportSchema,NodeID:NodeID(pub),EventID:"0123456789abcdef0123456789abcdef",
   ObservedAt:time.Now().UTC(),Kind:CoverageGapKind,TargetPort:0,CampaignFingerprint:fingerprint},pub,priv
}

func TestCoverageGapSignedAndValid(t *testing.T){
 r,pub,priv:=coverageSample(t)
 sr,err:=SignReport(r,priv);if err!=nil{t.Fatal(err)}
 if err:=VerifyReport(sr,pub,time.Now());err!=nil{t.Fatal(err)}
}
func TestCoverageGapRejectsInvalidReason(t *testing.T){
 for _,reason:=range []string{"","all_clear","healthy","192.0.2.1","storage_full\nsecret"} {
  if _,err:=CoverageGapFingerprint(reason);err==nil{t.Errorf("accepted invalid reason")}
 }
}
func TestCoverageGapReasonsDistinct(t *testing.T){
 seen:=map[string]bool{}
 for _,reason:=range []string{"log_unavailable","log_corrupt","storage_full","transport_outage","recovery_gap","unknown"}{
  fp,err:=CoverageGapFingerprint(reason);if err!=nil{t.Fatal(err)}
  if seen[fp] || len(fp)!=64{t.Fatal("invalid or repeated coverage fingerprint")}
  seen[fp]=true
 }
}
func TestCoverageGapRejectsArbitraryFingerprint(t *testing.T){
 r,_,_:=coverageSample(t)
 raw:=sha256.Sum256([]byte("unsanctioned category"))
 r.CampaignFingerprint=hex.EncodeToString(raw[:])
 if err:=r.Validate(time.Now());err==nil{t.Fatal("unrecognized gap reason accepted")}
}
func TestCoverageGapRejectsNetworkTarget(t *testing.T){
 r,_,_:=coverageSample(t)
 r.TargetPort=443
 if err:=r.Validate(time.Now());err==nil{t.Fatal("gap masquerading as network event accepted")}
}
func TestNetworkEventCannotUseGapPort(t *testing.T){
 r,_,_:=coverageSample(t)
 r.Kind="http_probe"
 if err:=r.Validate(time.Now());err==nil{t.Fatal("ordinary report accepted port zero")}
}
func TestCoverageGapRejectsForgery(t *testing.T){
 r,pub,priv:=coverageSample(t)
 sr,_:=SignReport(r,priv)
 sr.Report.CampaignFingerprint,_=CoverageGapFingerprint("recovery_gap")
 if err:=VerifyReport(sr,pub,time.Now());err==nil{t.Fatal("modified category accepted")}
}
func TestCoverageGapRejectsStaleReport(t *testing.T){
 r,pub,priv:=coverageSample(t)
 r.ObservedAt=r.ObservedAt.Add(-20*time.Minute)
 sr,_:=SignReport(r,priv)
 if err:=VerifyReport(sr,pub,time.Now());err==nil{t.Fatal("stale gap accepted")}
}
func TestCoverageGapWrongSignerRefused(t *testing.T){
 r,_,priv:=coverageSample(t)
 other,_,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 sr,_:=SignReport(r,priv)
 if err:=VerifyReport(sr,other,time.Now());err==nil{t.Fatal("unauthorized key accepted")}
}
