// Offline recovery inspector; never modifies HUB evidence or starts services.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/recovery"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

func main(){
 ledger:=flag.String("ledger","","closed HUB ledger copy with adjacent .head")
 history:=flag.String("history","","off-HUB Witness history")
 pubPath:=flag.String("pub","","independently pinned Ed25519 Witness public key")
 tip:=flag.String("expected-tip","","independently pinned latest signed-history tip")
 flag.Parse()
 if *ledger=="" || *history=="" || *pubPath=="" || *tip=="" {
  fmt.Fprintln(os.Stderr,"required: -ledger -history -pub -expected-tip (no repair mode)");os.Exit(2)
 }
 pub,err:=witness.ReadPublicKey(*pubPath)
 if err!=nil {fmt.Fprintln(os.Stderr,"key unavailable:",err);os.Exit(2)}
 result,err:=recovery.Inspect(*ledger,*history,pub,*tip,time.Now().UTC())
 if err!=nil {fmt.Fprintln(os.Stderr,"REJECT:",err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(result);err!=nil {
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
 if result.Status!="fully_witnessed" {os.Exit(1)}
}
