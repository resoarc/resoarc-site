// Offline signer-policy issuance: do not deploy the root private key to HUB.
package main
import(
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "sort"
 "strings"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
func run(args []string)error{
 flags:=flag.NewFlagSet("feed-policy-sign",flag.ContinueOnError)
 root:=flags.String("root-key","","offline root private key path")
 allowed:=flags.String("allowed-pubs","","comma-separated authorized signer PUBLIC key files")
 out:=flags.String("out","","exclusive output path")
 version:=flags.Uint64("version",0,"monotonic authorization version")
 lifetime:=flags.Duration("lifetime",7*24*time.Hour,"policy expiry <=30 days")
 if err:=flags.Parse(args);err!=nil{return err}
 if *root==""||*allowed==""||*out==""||*version==0||*lifetime<=0||*lifetime>30*24*time.Hour{return errors.New("invalid offline policy flags")}
 raw,err:=os.ReadFile(*root);if err!=nil{return err};if len(raw)>1024{return errors.New("root key file too large")}
 priv,err:=protocol.PrivateFromHex(strings.TrimSpace(string(raw)));if err!=nil{return err}
 filenames:=strings.Split(*allowed,",");if len(filenames)>8{return errors.New("too many allowed keys")}
 keys:=[]string{}
 for _,path:=range filenames{
  b,err:=os.ReadFile(path);if err!=nil{return err};if len(b)>1024{return errors.New("signer key file too large")}
  k:=strings.TrimSpace(string(b));if _,err=protocol.PublicFromHex(k);err!=nil{return err};keys=append(keys,k)
 }
 sort.Strings(keys)
 now:=time.Now().UTC()
 policy:=protocol.FeedSignerPolicy{Schema:protocol.SignerPolicySchema,Version:*version,IssuedAt:now,ExpiresAt:now.Add(*lifetime),SignerPublicKeys:keys}
 if err:=policy.Validate(now);err!=nil{return err}
 signed,err:=protocol.SignSignerPolicy(policy,priv);if err!=nil{return err}
 bytes,err:=json.MarshalIndent(signed,"","  ");if err!=nil{return err}
 file,err:=os.OpenFile(*out,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if err!=nil{return err}
 if _,err=file.Write(append(bytes,'\n'));err!=nil{file.Close();os.Remove(*out);return err}
 if err=file.Sync();err!=nil{file.Close();os.Remove(*out);return err}
 return file.Close()
}
func main(){if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"policy signer refused:",err);os.Exit(1)};fmt.Println("signed allowlist written: operator review required")}
