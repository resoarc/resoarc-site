// receipt-audit is read-only and MUST run on a CLOSED/off-HUB snapshot.
// It never signs, replays or automatically clears a coverage-gap incident.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receiptwitness"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
 "time"
)

func strictFile(path string,max int64,out any)error{
 fi,err:=os.Lstat(path);if err!=nil{return err}
 if !fi.Mode().IsRegular() || fi.Size()<=0 || fi.Size()>max{return errors.New("invalid audit input file")}
 b,err:=os.ReadFile(path);if err!=nil{return err}
 dec:=json.NewDecoder(bytes.NewReader(b))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(out);err!=nil{return err}
 if dec.Decode(new(any))!=io.EOF{return errors.New("unexpected trailing audit input")}
 return nil
}

func main(){
 ledger:=flag.String("ledger","","CLOSED offline ledger snapshot with matching .head")
 history:=flag.String("history","","independently retained Witness signed history")
 tip:=flag.String("witness-tip","","independently pinned Witness history SHA256")
 witnessKey:=flag.String("witness-pub","","independently pinned Witness verification key")
 hubKey:=flag.String("hub-pub","","pinned HUB receipt verification key")
 sensorKey:=flag.String("sensor-pub","","pinned originating Sensor public key")
 reportPath:=flag.String("report","","exact signed Sensor coverage gap report (private)")
 receiptPath:=flag.String("receipt","","HUB-signed receipt (202 or 409)")
 flag.Parse()
 if *ledger==""||*history==""||*tip==""||*witnessKey==""||*hubKey==""||
 *sensorKey==""||*reportPath==""||*receiptPath==""{
  panic("all offline audit inputs and independently pinned keys/tip are required")
 }
 wp,err:=witness.ReadPublicKey(*witnessKey);if err!=nil{panic("invalid Witness trust")}
 hp,err:=witness.ReadPublicKey(*hubKey);if err!=nil{panic("invalid HUB trust")}
 sp,err:=witness.ReadPublicKey(*sensorKey);if err!=nil{panic("invalid Sensor trust")}
 var report protocol.SignedReport
 if err=strictFile(*reportPath,8192,&report);err!=nil{panic("invalid original signed report")}
 var ack receipt.Signed
 if err=strictFile(*receiptPath,receipt.MaxBytes,&ack);err!=nil{panic("invalid signed receipt")}
 if err=receiptwitness.Audit(*ledger,*history,*tip,sp,hp,wp,report,ack,time.Now().UTC());err!=nil{
  // Keep the diagnostic categorical: raw logs and attacker data stay private.
  fmt.Fprintln(os.Stderr,"RECEIPT_WITNESS_AUDIT_HOLD")
  os.Exit(3)
 }
 fmt.Println("RECEIPT_WITNESS_AUDIT_PASS (historical receipt only; not an observation all-clear)")
}
