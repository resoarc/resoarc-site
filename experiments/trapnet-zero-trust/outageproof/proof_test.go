package outageproof

import (
    "crypto/ed25519"
    "crypto/sha256"
    "encoding/json"
    "strings"
    "testing"
    "time"

    "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
    "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
)

type fixture struct {
    report protocol.SignedReport
    receipt receipt.Signed
    att SignedInterval
    manifest []byte
    sensor ed25519.PublicKey
    hub ed25519.PublicKey
    operator ed25519.PublicKey
    now time.Time
}

func key(name string) ed25519.PrivateKey {
    sum:=sha256.Sum256([]byte("trapnet-v063-synthetic-fixture-"+name))
    return ed25519.NewKeyFromSeed(sum[:])
}
func makeFixture(t *testing.T) fixture {
    t.Helper()
    now:=time.Date(2026,11,5,15,0,0,0,time.UTC)
    sensorPrivate,hubPrivate,operatorPrivate:=key("sensor"),key("hub"),key("operator")
    sensorPublic:=sensorPrivate.Public().(ed25519.PublicKey)
    hubPublic:=hubPrivate.Public().(ed25519.PublicKey)
    operatorPublic:=operatorPrivate.Public().(ed25519.PublicKey)
    id:="aabbccddeeff00112233445566778899"
    fp,_:=protocol.CoverageGapFingerprint("recovery_gap")
    report,err:=protocol.SignReport(protocol.Report{
        Schema:protocol.ReportSchema,NodeID:protocol.NodeID(sensorPublic),
        EventID:id,ObservedAt:now.Add(-40*time.Minute),
        Kind:protocol.CoverageGapKind,TargetPort:0,CampaignFingerprint:fp,
    },sensorPrivate)
    if err!=nil{t.Fatal(err)}
    hubReceipt,err:=receipt.Sign(report,strings.Repeat("b",64),1,now.Add(-39*time.Minute),hubPrivate)
    if err!=nil{t.Fatal(err)}
    reportHash,err:=receipt.HashReport(report);if err!=nil{t.Fatal(err)}
    ackHash,err:=ReceiptSHA256(hubReceipt);if err!=nil{t.Fatal(err)}
    source:=[]byte("SYNTHETIC ONLY: stop time, start time, privacy-respecting evidence digest")
    b:=Interval{Schema:Schema,
        Start:now.Add(-14*time.Hour),End:now.Add(-time.Hour),
        AttestedAt:now.Add(-20*time.Minute),
        Source:"docker_state_guard_metadata", SourceSHA256:SHA256(source),
        SensorNodeID:report.Report.NodeID,EventID:report.Report.EventID,
        ReportSHA256:reportHash,ReceiptSHA256:ackHash,
        Meaning:"observation_unknown_not_zero",
    }
    signed,err:=Sign(b,operatorPrivate);if err!=nil{t.Fatal(err)}
    return fixture{report:report,receipt:hubReceipt,att:signed,manifest:source,
        sensor:sensorPublic,hub:hubPublic,operator:operatorPublic,now:now}
}
func (f fixture) verify() error {
    return Verify(f.att,f.report,f.receipt,f.manifest,f.sensor,f.hub,f.operator,f.now)
}
func TestSyntheticSignedGapIntervalAndExactHubReceipt(t *testing.T){
    f:=makeFixture(t)
    if err:=f.verify();err!=nil{t.Fatal(err)}
    if f.att.Interval.Meaning!="observation_unknown_not_zero"{t.Fatal("false coverage")}
}
func TestRejectAlteredGapEnd(t *testing.T){
    f:=makeFixture(t);f.att.Interval.End=f.att.Interval.End.Add(time.Second)
    if err:=f.verify();err==nil{t.Fatal("tampered historical interval accepted")}
}
func TestRejectAlteredGapStart(t *testing.T){
    f:=makeFixture(t);f.att.Interval.Start=f.att.Interval.Start.Add(time.Second)
    if err:=f.verify();err==nil{t.Fatal("tampered start accepted")}
}
func TestRejectTruncatedSourceManifest(t *testing.T){
    f:=makeFixture(t);f.manifest=f.manifest[:len(f.manifest)-1]
    if err:=f.verify();err==nil{t.Fatal("mismatched source manifest accepted")}
}
func TestRejectEmptyOrOversizedSource(t *testing.T){
    f:=makeFixture(t);f.manifest=nil
    if err:=f.verify();err==nil{t.Fatal("empty evidence accepted")}
    f=makeFixture(t);f.manifest=make([]byte,MaxSourceBytes+1)
    if err:=f.verify();err==nil{t.Fatal("oversized evidence accepted")}
}
func TestRejectTamperedSensorSignature(t *testing.T){
    f:=makeFixture(t);f.report.Signature=strings.Repeat("0",128)
    if err:=f.verify();err==nil{t.Fatal("forged Sensor accepted")}
}
func TestRejectTamperedHUBReceipt(t *testing.T){
    f:=makeFixture(t);f.receipt.Receipt.LedgerTipSHA256=strings.Repeat("c",64)
    if err:=f.verify();err==nil{t.Fatal("HUB ledger tip tampering accepted")}
}
func TestRejectWrongHUBKey(t *testing.T){
    f:=makeFixture(t);f.hub=key("impostor").Public().(ed25519.PublicKey)
    if err:=f.verify();err==nil{t.Fatal("forged HUB key accepted")}
}
func TestRejectWrongOperatorKey(t *testing.T){
    f:=makeFixture(t);f.operator=key("impostor").Public().(ed25519.PublicKey)
    if err:=f.verify();err==nil{t.Fatal("forged operator accepted")}
}
func TestRejectSameIdentityForMultipleRoles(t *testing.T){
    f:=makeFixture(t);f.operator=f.sensor
    if err:=f.verify();err==nil{t.Fatal("same key in distinct roles accepted")}
}
func TestRejectReportNotRecoveryGap(t *testing.T){
    f:=makeFixture(t)
    f.report.Report.Kind="http_probe"
    if err:=f.verify();err==nil{t.Fatal("normal event treated as outage")}
}
func TestRejectUnboundEventID(t *testing.T){
    f:=makeFixture(t);f.att.Interval.EventID=strings.Repeat("a",32)
    if err:=f.verify();err==nil{t.Fatal("unbound event ID accepted")}
}
func TestRejectBackdatedReportComparedToHUBReceipt(t *testing.T){
    f:=makeFixture(t)
    private:=key("sensor")
    f.report.Report.ObservedAt=f.receipt.Receipt.ReceivedAt.Add(-12*time.Minute)
    f.report,_=protocol.SignReport(f.report.Report,private)
    f.receipt,_=receipt.Sign(f.report,strings.Repeat("b",64),1,
        f.receipt.Receipt.ReceivedAt,key("hub"))
    if err:=f.verify();err==nil{t.Fatal("stale/badly dated report accepted")}
}
func TestRejectAttestationBeforeHubAcceptance(t *testing.T){
    f:=makeFixture(t);f.att.Interval.AttestedAt=f.receipt.Receipt.ReceivedAt.Add(-time.Minute)
    if err:=f.verify();err==nil{t.Fatal("operator attested before HUB receipt")}
}
func TestRejectFutureAttestation(t *testing.T){
    f:=makeFixture(t);f.att.Interval.AttestedAt=f.now.Add(3*time.Minute)
    if err:=f.verify();err==nil{t.Fatal("future attestation accepted")}
}
func TestRejectFalseZeroAttackMeaningAtSign(t *testing.T){
    f:=makeFixture(t);f.att.Interval.Meaning="no_attacks_observed"
    if _,err:=Sign(f.att.Interval,key("operator"));err==nil{t.Fatal("false all clear signed")}
}
func TestRejectNonUTCInterval(t *testing.T){
    f:=makeFixture(t)
    f.att.Interval.Start=f.att.Interval.Start.In(time.FixedZone("JST",9*3600))
    if _,err:=Sign(f.att.Interval,key("operator"));err==nil{t.Fatal("non-UTC start accepted")}
}
func TestRejectInvalidDurationOrOrder(t *testing.T){
    f:=makeFixture(t)
    f.att.Interval.End=f.att.Interval.Start
    if _,err:=Sign(f.att.Interval,key("operator"));err==nil{t.Fatal("empty interval accepted")}
    f=makeFixture(t)
    f.att.Interval.Start=f.att.Interval.End.Add(-31*24*time.Hour)
    if _,err:=Sign(f.att.Interval,key("operator"));err==nil{t.Fatal("unbounded outage accepted")}
}
func TestRejectZeroEvidenceDigest(t *testing.T){
    f:=makeFixture(t)
    f.att.Interval.SourceSHA256="not-a-real-sha"
    if _,err:=Sign(f.att.Interval,key("operator"));err==nil{t.Fatal("invalid sha accepted")}
}
func TestJSONRoundTripHasNoRawAttackData(t *testing.T){
    f:=makeFixture(t)
    data,err:=json.Marshal(f.att)
    if err!=nil{t.Fatal(err)}
    if strings.Contains(string(data),"password") || strings.Contains(string(data),"192.0.2.") {t.Fatal("private data leaked")}
    var got SignedInterval
    if err:=json.Unmarshal(data,&got);err!=nil{t.Fatal(err)}
    f.att=got
    if err:=f.verify();err!=nil{t.Fatal(err)}
}
