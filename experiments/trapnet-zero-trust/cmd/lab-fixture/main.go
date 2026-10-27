// lab-fixture generates deliberately synthetic, offline-signed TrapNet evidence.
// It must never be used as an enrolled live Sensor or as a basis for real alerts.
package main

import (
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/correlate"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)
func create(dir string, now time.Time) error {
 if dir=="" { return errors.New("-out is required") }
 if err:=os.Mkdir(dir,0700);err!=nil{return err}
 cleanup:=true
 defer func(){if cleanup{_ = os.RemoveAll(dir)}}()
 ledger:=filepath.Join(dir,"synthetic-ledger.jsonl")
 trustPath:=filepath.Join(dir,"reviewed-trust.json")
 f,err:=os.OpenFile(ledger,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if err!=nil{return err}
 trust:=map[string]correlate.TrustedNode{}
 anchor:=now.UTC().Truncate(10*time.Minute).Add(time.Minute)
 if anchor.After(now.UTC().Add(time.Minute)){anchor=anchor.Add(-10*time.Minute)}
 for i,group:=range []string{"lab_owner_a","lab_owner_b","lab_owner_a"}{
  pub,priv,e:=ed25519.GenerateKey(rand.Reader);if e!=nil{f.Close();return e}
  id:=protocol.NodeID(pub)
  trust[id]=correlate.TrustedNode{PublicKey:hex.EncodeToString(pub),OperatorGroup:group,Reviewed:true}
  report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:id,
   EventID:fmt.Sprintf("%032x",i+1),ObservedAt:anchor,Kind:"http_probe",
   TargetPort:443,CampaignFingerprint:strings.Repeat("c",64)}
  signed,e:=protocol.SignReport(report,priv);if e!=nil{f.Close();return e}
  b,e:=json.Marshal(correlate.LedgerRow{ReceivedAt:anchor,Evidence:signed});if e!=nil{f.Close();return e}
  if _,e=f.Write(append(b,'\n'));e!=nil{f.Close();return e}
 }
 if err=f.Sync();err!=nil{f.Close();return err}
 if err=f.Close();err!=nil{return err}
 head,err:=witness.Measure(ledger,nil);if err!=nil{return err}
 hb,err:=json.Marshal(head);if err!=nil{return err}
 if err=os.WriteFile(ledger+".head",hb,0600);err!=nil{return err}
 tb,err:=json.MarshalIndent(trust,"","  ");if err!=nil{return err}
 if err=os.WriteFile(trustPath,append(tb,'\n'),0600);err!=nil{return err}
 data,err:=os.ReadFile(ledger);if err!=nil{return err}
 sum:=sha256.Sum256(data)
 tSum:=sha256.Sum256(append(tb,'\n'))
 pins:=fmt.Sprintf("%x  synthetic-ledger.jsonl\n%x  reviewed-trust.json\n",sum,tSum)
 if err=os.WriteFile(filepath.Join(dir,"SHA256SUMS"),[]byte(pins),0600);err!=nil{return err}
 cleanup=false
 return nil
}
func main(){
 out:=flag.String("out","","new empty directory for synthetic-only closed fixture")
 flag.Parse()
 if err:=create(*out,time.Now().UTC());err!=nil{
  fmt.Fprintln(os.Stderr,"fixture refused:",err);os.Exit(1)
 }
 fmt.Println("SYNTHETIC_ONLY=TRUE; fixture generated; no live node secrets and no real observation claims")
}
