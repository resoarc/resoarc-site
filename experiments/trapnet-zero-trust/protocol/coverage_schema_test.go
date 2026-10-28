package protocol

import (
  "encoding/json"
  "os"
  "testing"
)

// Keep public structural JSON Schema aligned with the reserved gap class.
// This is a drift check, not a complete JSON-Schema validation engine.
func TestPublishedSchemaCoverageGapSemantics(t *testing.T) {
  b,err:=os.ReadFile("../../../docs/trapnet/tztp-report.schema.json")
  if err!=nil{t.Fatal(err)}
  var doc struct{
    Properties struct{
      Report struct{
        AllOf []struct{
          If struct{
            Properties struct{Kind struct{Const string `json:"const"`} `json:"kind"`} `json:"properties"`
          } `json:"if"`
          Then struct{
            Properties struct{
              TargetPort struct{Const int `json:"const"`} `json:"target_port"`
              CampaignFingerprint struct{Enum []string `json:"enum"`} `json:"campaign_fingerprint"`
            } `json:"properties"`
          } `json:"then"`
          Else struct{
            Properties struct{TargetPort struct{Minimum int `json:"minimum"`;Maximum int `json:"maximum"`} `json:"target_port"`} `json:"properties"`
          } `json:"else"`
        } `json:"allOf"`
      } `json:"report"`
    } `json:"properties"`
  }
  if err:=json.Unmarshal(b,&doc);err!=nil{t.Fatal(err)}
  rules:=doc.Properties.Report.AllOf
  if len(rules)!=1{t.Fatalf("expected one gap discriminator; got %d",len(rules))}
  rule:=rules[0]
  if rule.If.Properties.Kind.Const!=CoverageGapKind ||
    rule.Then.Properties.TargetPort.Const!=0 ||
    rule.Else.Properties.TargetPort.Minimum!=1 ||
    rule.Else.Properties.TargetPort.Maximum!=65535 {
    t.Fatal("published schema has unsafe coverage_gap port rules")
  }
  expected:=map[string]bool{}
  for reason:=range gapReasons {
    d,err:=CoverageGapFingerprint(reason);if err!=nil{t.Fatal(err)}
    expected[d]=true
  }
  actual:=rule.Then.Properties.CampaignFingerprint.Enum
  if len(actual)!=len(expected){t.Fatalf("fingerprint enum mismatch: %d",len(actual))}
  seen:=map[string]bool{}
  for _,fp:=range actual{
    if !expected[fp]||seen[fp]{t.Fatal("published schema has wrong/duplicate gap fingerprint")}
    seen[fp]=true
  }
}
