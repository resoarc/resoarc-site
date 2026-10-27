// Guardian is explicitly read-only: signed text only; no networking, firewall or commands.
package main
import(
 "crypto/ed25519"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "strings"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
func readHexPub(path string)(ed25519.PublicKey,error){
 raw,err:=os.ReadFile(path);if err!=nil{return nil,err}
 if len(raw)>1024{return nil,errors.New("public key file too large")}
 return protocol.PublicFromHex(strings.TrimSpace(string(raw)))
}
// Release-candidate builds set this to true using -ldflags -X main.requireRootPolicy=true.
// Experimental builds retain -pub for older isolated lab scenarios only.
var requireRootPolicy = "false"
func main(){
 feedPath:=flag.String("feed","","local signed feed")
 pubPath:=flag.String("pub","","EXPERIMENTAL legacy feed signer pub, not for beta distribution")
 policyPath:=flag.String("policy","","root-signed allowed signer policy for beta")
 rootPath:=flag.String("rootpub","","independently pinned offline root pub")
 statePath:=flag.String("state","guardian-state.json","local anti-rollback state")
 flag.Parse()
 if *feedPath==""{panic("-feed required")}
 policyMode:=*policyPath!=""||*rootPath!=""
 if requireRootPolicy=="true" && !policyMode {panic("Guardian beta binary requires -policy and -rootpub: legacy -pub forbidden")}
 if policyMode&&(*policyPath==""||*rootPath==""||*pubPath!=""){panic("policy mode requires -policy and -rootpub and forbids -pub")}
 if !policyMode&&*pubPath==""{panic("use -policy and -rootpub; -pub is experimental legacy mode only")}
 b,err:=os.ReadFile(*feedPath);if err!=nil{panic(err)}
 if len(b)>65536{panic("feed too large")}
 dec:=json.NewDecoder(strings.NewReader(string(b)));dec.DisallowUnknownFields()
 var sf protocol.SignedFeed
 if err=dec.Decode(&sf);err!=nil{panic(err)}
 if err=dec.Decode(new(any));err!=io.EOF{panic("extra feed data")}
 now:=time.Now().UTC()
 var pub ed25519.PublicKey
 var policy *protocol.SignedSignerPolicy
 var rootPub ed25519.PublicKey
 if policyMode{
  root,err:=readHexPub(*rootPath);if err!=nil{panic(err)}
  rootPub=root
  data,err:=os.ReadFile(*policyPath);if err!=nil{panic(err)}
  if len(data)>8192{panic("policy too large")}
  dec:=json.NewDecoder(strings.NewReader(string(data)));dec.DisallowUnknownFields()
  var parsed protocol.SignedSignerPolicy
  if err=dec.Decode(&parsed);err!=nil{panic(err)}
  if err=dec.Decode(new(any));err!=io.EOF{panic("extra signer policy data")}
  pub,err=protocol.VerifyFeedAgainstPolicy(sf,parsed,root,now);if err!=nil{panic(err)}
  policy=&parsed
 }else{
  pub,err=readHexPub(*pubPath);if err!=nil{panic(err)}
 }
 if err=verifyAndRecordWithPolicyTrust(sf,pub,policy,rootPub,*statePath,now);err!=nil{panic(err)}
 fmt.Println("verified informational feed version",sf.Feed.Version)
 for _,w:=range sf.Feed.Warnings{fmt.Printf("[%s] %s\n",w.Category,w.Summary)}
 fmt.Println("No network telemetry, remote commands, or blocking performed.")
}
