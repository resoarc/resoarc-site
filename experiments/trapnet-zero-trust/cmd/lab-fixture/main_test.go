package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/correlate"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)
func TestClosedSyntheticFixture(t *testing.T){
 now:=time.Now().UTC()
 dir:=filepath.Join(t.TempDir(),"fixture")
 if err:=create(dir,now);err!=nil{t.Fatal(err)}
 ledger:=filepath.Join(dir,"synthetic-ledger.jsonl")
 head,err:=witness.Snapshot(ledger,nil);if err!=nil{t.Fatal(err)}
 if head.Rows!=3{t.Fatalf("rows=%d",head.Rows)}
 data,err:=os.ReadFile(ledger);if err!=nil{t.Fatal(err)}
 var trust map[string]correlate.TrustedNode
 b,err:=os.ReadFile(filepath.Join(dir,"reviewed-trust.json"));if err!=nil{t.Fatal(err)}
 if err=json.Unmarshal(b,&trust);err!=nil{t.Fatal(err)}
 if len(trust)!=3{t.Fatalf("node count=%d",len(trust))}
 groups:=map[string]int{}
 for _,node:=range trust{groups[node.OperatorGroup]++}
 if groups["lab_owner_a"]!=2||groups["lab_owner_b"]!=1{t.Fatalf("operator groups=%v",groups)}
 lines:=strings.Split(strings.TrimSpace(string(data)),"\n")
 if len(lines)!=3{t.Fatal("wrong row count")}
 for _,line:=range lines{
  var row correlate.LedgerRow
  if err=json.Unmarshal([]byte(line),&row);err!=nil{t.Fatal(err)}
  node:=trust[row.Evidence.Report.NodeID]
  pub,err:=protocol.PublicFromHex(node.PublicKey);if err!=nil{t.Fatal(err)}
  if err=protocol.VerifyReport(row.Evidence,pub,row.ReceivedAt);err!=nil{t.Fatal(err)}
 }
 pin:=sha256.Sum256(data)
 sums,err:=os.ReadFile(filepath.Join(dir,"SHA256SUMS"));if err!=nil{t.Fatal(err)}
 if !strings.Contains(string(sums),hex.EncodeToString(pin[:])){t.Fatal("missing ledger digest")}
 if _,err=os.Stat(filepath.Join(dir,"private.hex"));!os.IsNotExist(err){t.Fatal("fixture persisted key")}
}
func TestDoesNotOverwriteExisting(t *testing.T){
 dir:=filepath.Join(t.TempDir(),"existing")
 if err:=os.Mkdir(dir,0700);err!=nil{t.Fatal(err)}
 marker:=filepath.Join(dir,"sentinel")
 if err:=os.WriteFile(marker,[]byte("keep"),0600);err!=nil{t.Fatal(err)}
 if err:=create(dir,time.Now());err==nil{t.Fatal("existing directory overwritten")}
 data,err:=os.ReadFile(marker);if err!=nil||string(data)!="keep"{t.Fatal("existing contents changed")}
}
