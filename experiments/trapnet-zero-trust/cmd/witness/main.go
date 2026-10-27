// Witness runs OFF-HUB on a stable copy of ledger and ledger.head.
// It never contacts the HUB or accepts a live network connection.
package main

import (
 "flag"
 "fmt"
 "log"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)
func main(){
 mode:=flag.String("mode","verify","attest or verify")
 ledger:=flag.String("ledger","","offline HUB ledger copy (and sibling .head)")
 history:=flag.String("history","","OFF-HUB append-only witness history")
 pub:=flag.String("pub","","pinned witness public key for verify")
 priv:=flag.String("key","","offline private key for attest; NEVER place on HUB")
 tip:=flag.String("expected-tip","","externally pinned hash of most recent signed record")
 flag.Parse()
 if *ledger==""||*history==""{log.Fatal("-ledger and -history are required")}
 switch *mode{
 case "attest":
  if *priv==""||*pub!=""{log.Fatal("attest requires -key (not -pub)")}
  if err:=witness.CheckOffHostInputs(*ledger,*history,*priv);err!=nil{log.Fatal(err)}
  key,err:=witness.ReadPrivateKey(*priv);if err!=nil{log.Fatal(err)}
  signed,hash,err:=witness.Attest(*ledger,*history,key,time.Now().UTC());if err!=nil{log.Fatal(err)}
  fmt.Printf("WITNESSED rows=%d sequence=%d tip=%s\nStore this tip outside HUB and witness host.\n",signed.Checkpoint.Rows,signed.Checkpoint.Sequence,hash)
 case "verify":
  if *pub==""||*priv!=""{log.Fatal("verify requires -pub (not -key)")}
  key,err:=witness.ReadPublicKey(*pub);if err!=nil{log.Fatal(err)}
  measured,hash,err:=witness.Audit(*ledger,*history,key,*tip);if err!=nil{log.Fatal(err)}
  fmt.Printf("VERIFIED rows=%d digest=%s witnessed_tip=%s\n",measured.Rows,measured.Digest,hash)
 default:log.Fatal("unsupported mode")
 }
}
