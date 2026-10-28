// Release signatures use a dedicated OFFLINE distribution key, not the Guardian feed key.
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
 flags:=flag.NewFlagSet("release-sign",flag.ContinueOnError)
 manifest:=flags.String("manifest","","reviewed unsigned release metadata")
 root:=flags.String("key","","offline release-signing private key")
 out:=flags.String("out","","exclusive detached signed manifest path")
 if err:=flags.Parse(args);err!=nil{return err}
 if *manifest==""||*root==""||*out==""{return errors.New("required -manifest -key -out")}
 key,err:=os.ReadFile(*root);if err!=nil{return err}
 if len(key)>1024{return errors.New("release key oversized")}
 private,err:=protocol.PrivateFromHex(strings.TrimSpace(string(key)));if err!=nil{return err}
 raw,err:=os.ReadFile(*manifest);if err!=nil{return err}
 if len(raw)>16384{return errors.New("release metadata oversized")}
 decoder:=json.NewDecoder(strings.NewReader(string(raw)));decoder.DisallowUnknownFields()
 var m releaseauth.Manifest
 if err:=decoder.Decode(&m);err!=nil{return err}
 if err:=decoder.Decode(new(any));err!=io.EOF{return errors.New("extra unsigned release metadata")}
 signed,err:=releaseauth.Sign(m,private,time.Now().UTC());if err!=nil{return err}
 b,err:=json.MarshalIndent(signed,"","  ");if err!=nil{return err}
 f,err:=os.OpenFile(*out,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if err!=nil{return err}
 if _,err=f.Write(append(b,'\n'));err!=nil{f.Close();os.Remove(*out);return err}
 if err=f.Sync();err!=nil{f.Close();os.Remove(*out);return err}
 return f.Close()
}
func main(){if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"offline release signer refused:",err);os.Exit(1)};fmt.Println("signed metadata created; separate publisher approval required")}
