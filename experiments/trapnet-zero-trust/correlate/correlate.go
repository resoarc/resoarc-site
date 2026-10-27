// Package correlate verifies already received TrapNet reports offline for human triage.
// It never generates a blocklist, feed, or remote command.
package correlate

import (
 "bufio"
 "crypto/ed25519"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sort"
 "strings"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
const MaxRows=8000
const MaxRowBytes=65536
// OperatorGroup must be verified by the operator, never copied from a Sensor.
type TrustedNode struct {
 PublicKey string `json:"public_key"`
 OperatorGroup string `json:"operator_group"`
 Reviewed bool `json:"reviewed"`
}
type LedgerRow struct {
 ReceivedAt time.Time `json:"received_at"`
 Evidence protocol.SignedReport `json:"evidence"`
}
type Case struct {
 Case string `json:"case"`
 Kind string `json:"kind"`
 ReportsBand string `json:"reports_band"`
 OperatorsBand string `json:"reviewed_operator_groups_band"`
 Verdict string `json:"verdict"`
}
type Summary struct {
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 Source string `json:"source"`
 CryptographicVerification bool `json:"cryptographic_verification"`
 OperatorIndependenceProven bool `json:"operator_independence_proven"`
 ReportsInputBand string `json:"reports_input_band"`
 Cases []Case `json:"cases"`
 AutomaticBlocking bool `json:"automatic_blocking"`
 FeedPublished bool `json:"feed_published"`
}
func validateTrust(trust map[string]TrustedNode)(map[string]ed25519.PublicKey,error){
 if len(trust)==0||len(trust)>2000{return nil,errors.New("untrusted registry size")}
 keys:=make(map[string]ed25519.PublicKey,len(trust))
 for id,node:=range trust{
  pub,err:=protocol.PublicFromHex(node.PublicKey)
  if err!=nil||protocol.NodeID(pub)!=id{return nil,errors.New("trust registry public key mismatch")}
  if node.Reviewed{
   if len(node.OperatorGroup)<2||len(node.OperatorGroup)>48{return nil,errors.New("invalid operator group")}
   for _,c:=range node.OperatorGroup{
    if !(c>='a'&&c<='z'||c>='0'&&c<='9'||c=='_'||c=='-'){return nil,errors.New("invalid operator group")}
   }
  }
  keys[id]=pub
 }
 return keys,nil
}
type observation struct{kind,operator string}
func band(n int)string{
 switch{
 case n<2:return "<2"
 case n<5:return "2-4"
 case n<10:return "5-9"
 case n<50:return "10-49"
 default:return "50+"
 }
}
// Analyze refuses a malformed row, invalid signature, unregistered node, or replay.
// Grouping is conservative: even different registered operator groups merely
// create a candidate for manual review, never establish truth or independence.
func Analyze(reader io.Reader,trust map[string]TrustedNode,clock time.Time)(Summary,error){
 keys,err:=validateTrust(trust);if err!=nil{return Summary{},err}
 scanner:=bufio.NewScanner(reader);scanner.Buffer(make([]byte,4096),MaxRowBytes)
 count:=0;seen:=map[string]bool{};casesByKey:=map[string][]observation{}
 for scanner.Scan(){
  count++;if count>MaxRows{return Summary{},errors.New("too many rows")}
  dec:=json.NewDecoder(strings.NewReader(scanner.Text()));dec.DisallowUnknownFields()
  var row LedgerRow
  if err:=dec.Decode(&row);err!=nil{return Summary{},fmt.Errorf("invalid row %d: %w",count,err)}
  if err:=dec.Decode(new(any));err!=io.EOF{return Summary{},fmt.Errorf("extra data at row %d",count)}
  if row.ReceivedAt.IsZero()||row.ReceivedAt.Before(clock.Add(-90*24*time.Hour))||row.ReceivedAt.After(clock.Add(2*time.Minute)){
   return Summary{},fmt.Errorf("invalid receipt time at row %d",count)
  }
  node:=row.Evidence.Report.NodeID
  pub,ok:=keys[node];if !ok{return Summary{},fmt.Errorf("unknown node at row %d",count)}
  if err:=protocol.VerifyReport(row.Evidence,pub,row.ReceivedAt);err!=nil{
   return Summary{},fmt.Errorf("invalid report at row %d: %w",count,err)
  }
  key:=node+":"+row.Evidence.Report.EventID
  if seen[key]{return Summary{},fmt.Errorf("replay at row %d",count)}
  seen[key]=true
  bucket:=row.ReceivedAt.UTC().Truncate(10*time.Minute).Format(time.RFC3339)
  campaign:=row.Evidence.Report.CampaignFingerprint+"|"+row.Evidence.Report.Kind+"|"+fmt.Sprint(row.Evidence.Report.TargetPort)+"|"+bucket
  group:="";if trust[node].Reviewed{group=trust[node].OperatorGroup}
  casesByKey[campaign]=append(casesByKey[campaign],observation{row.Evidence.Report.Kind,group})
 }
 if err:=scanner.Err();err!=nil{return Summary{},err}
 sorted:=make([]string,0,len(casesByKey));for k:=range casesByKey{sorted=append(sorted,k)};sort.Strings(sorted)
 cases:=make([]Case,0,len(sorted))
 for i,k:=range sorted{
  rows:=casesByKey[k];operators:=map[string]bool{}
  for _,r:=range rows{if r.operator!=""{operators[r.operator]=true}}
  verdict:="single_operator_or_unreviewed"
  if len(operators)>=2{verdict="multi_operator_candidate_for_manual_review"}
  cases=append(cases,Case{fmt.Sprintf("case-%03d",i+1),rows[0].kind,band(len(rows)),band(len(operators)),verdict})
 }
 return Summary{Schema:"trapnet.corroboration-offline.v0.1",Classification:"authenticated_reports_not_truth",
 Source:"offline_operator_supplied_ledger_copy",CryptographicVerification:true,OperatorIndependenceProven:false,
 ReportsInputBand:band(count),Cases:cases,AutomaticBlocking:false,FeedPublished:false},nil
}
