// Verify bundle identity using a separately pinned distribution public key.
// This tool NEVER downloads files or executes any binary.
package main
import(
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "strings"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/releaseauth"
)
func run(args []string)error{
 flags:=flag.NewFlagSet("release-verify",flag.ContinueOnError)
 signedFile:=flags.String("signed","","root-signed release manifest")
 pubFile:=flags.String("pub","","independently verified DISTRIBUTION public key")
 dir:=flags.String("bundle","","directory containing exactly three candidate binaries")
 if err:=flags.Parse(args);err!=nil{return err}
 if *signedFile==""||*pubFile==""||*dir==""{return errors.New("required -signed -pub -bundle")}
 rawKey,err:=os.ReadFile(*pubFile);if err!=nil{return err}
 if len(rawKey)>1024{return errors.New("release public key file too large")}
 pub,err:=protocol.PublicFromHex(strings.TrimSpace(string(rawKey)));if err!=nil{return err}
 raw,err:=os.ReadFile(*signedFile);if err!=nil{return err}
 if len(raw)>16384{return errors.New("signed manifest too large")}
 dec:=json.NewDecoder(strings.NewReader(string(raw)));dec.DisallowUnknownFields()
 var signed releaseauth.Signed
 if err:=dec.Decode(&signed);err!=nil{return err}
 if err:=dec.Decode(new(any));err!=io.EOF{return errors.New("extra signed release metadata")}
 return releaseauth.VerifyBundle(signed,pub,*dir,time.Now().UTC())
}
func main(){
 if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"release verification REFUSED:",err);os.Exit(1)}
 fmt.Println("Release metadata signature + all 3 binary SHA-256 digests VERIFIED; operator trust anchor must be checked independently.")
}
