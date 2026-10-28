// Offline operator review only: no network listeners, Guardian commands or feeds.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "strings"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/correlate"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)
const maxLedgerBytes int64=8<<20
const maxTrustBytes int64=512<<10

func verifyFile(f *os.File,expectedHex string,maxBytes int64)error{
 expected,err:=hex.DecodeString(expectedHex)
 if err!=nil||len(expected)!=sha256.Size{return errors.New("invalid independently pinned SHA-256")}
 stat,err:=f.Stat();if err!=nil{return err}
 if !stat.Mode().IsRegular()||stat.Size()>maxBytes{return errors.New("unsafe input file type or size")}
 if _,err=f.Seek(0,io.SeekStart);err!=nil{return err}
 h:=sha256.New()
 if _,err=io.Copy(h,io.LimitReader(f,maxBytes+1));err!=nil{return err}
 if !strings.EqualFold(hex.EncodeToString(h.Sum(nil)),expectedHex){return errors.New("pinned SHA-256 does not match")}
 _,err=f.Seek(0,io.SeekStart);return err
}
// openPinnedRegular refuses symlinks and ensures path and descriptor identify
// the same regular file before reading a sensitive closed snapshot.
func openPinnedRegular(path,pin string,maxBytes int64)(*os.File,error){
 info,err:=os.Lstat(path);if err!=nil{return nil,err}
 if !info.Mode().IsRegular(){return nil,errors.New("input must be a regular file, not a symlink")}
 f,err:=os.Open(path);if err!=nil{return nil,err}
 if err:=verifySamePath(f,path);err!=nil{f.Close();return nil,err}
 if err:=verifyFile(f,pin,maxBytes);err!=nil{f.Close();return nil,err}
 return f,nil
}
func verifySamePath(f *os.File,path string)error{
 entry,err:=os.Lstat(path);if err!=nil{return err}
 if !entry.Mode().IsRegular(){return errors.New("input path changed type or became a symlink")}
 opened,err:=f.Stat();if err!=nil{return err}
 if !os.SameFile(entry,opened){return errors.New("input path was replaced")}
 return nil
}
func run(args []string,output io.Writer,clock time.Time)error{
 flags:=flag.NewFlagSet("corroborate",flag.ContinueOnError);flags.SetOutput(io.Discard)
 ledgerPath:=flags.String("ledger","","closed verified ledger snapshot")
 trustPath:=flags.String("trust","","independently curated node trust registry")
 ledgerPin:=flags.String("ledger-sha256","","independently pinned SHA-256 of ledger")
 trustPin:=flags.String("trust-sha256","","independently pinned SHA-256 of trust registry")
 witnessHistory:=flags.String("witness-history","","off-HUB Witness history")
 witnessPub:=flags.String("witness-pub","","independently trusted Witness public key")
 witnessTip:=flags.String("witness-tip","","independently pinned Witness tip")
 if err:=flags.Parse(args);err!=nil{return err}
 if *ledgerPath==""||*trustPath==""||*ledgerPin==""||*trustPin==""||*witnessHistory==""||*witnessPub==""||*witnessTip==""{
  return errors.New("all seven required flags must be supplied; witnessed attestation mandatory")
 }
 f,err:=openPinnedRegular(*ledgerPath,*ledgerPin,maxLedgerBytes);if err!=nil{return fmt.Errorf("ledger: %w",err)};defer f.Close()
 t,err:=openPinnedRegular(*trustPath,*trustPin,maxTrustBytes);if err!=nil{return fmt.Errorf("trust registry: %w",err)};defer t.Close()
 buf,err:=io.ReadAll(io.LimitReader(t,maxTrustBytes+1));if err!=nil||len(buf)>int(maxTrustBytes){return errors.New("oversized trust registry")}
 var registry map[string]correlate.TrustedNode
 dec:=json.NewDecoder(strings.NewReader(string(buf)));dec.DisallowUnknownFields()
 if err:=dec.Decode(&registry);err!=nil{return errors.New("invalid trust registry")}
 if err:=dec.Decode(new(any));err!=io.EOF{return errors.New("extra JSON in trust registry")}
// An independently pinned digest is necessary but is NOT an attestation.
 // Audit externally signed Witness history and require full coverage.
 pub,err:=witness.ReadPublicKey(*witnessPub)
 if err!=nil{return fmt.Errorf("witness key: %w",err)}
 measured,tip,err:=witness.Audit(*ledgerPath,*witnessHistory,pub,*witnessTip)
 if err!=nil{return fmt.Errorf("witness audit: %w",err)}
 if tip!=*witnessTip{return errors.New("witness tip not pinned")}
 checkpoints,err:=witness.ReadHistory(*witnessHistory,pub)
 if err!=nil||len(checkpoints)==0{return errors.New("witness history empty or invalid")}
 last:=checkpoints[len(checkpoints)-1].Checkpoint
 if last.Rows!=measured.Rows||last.Digest!=measured.Digest{return errors.New("unwitnessed ledger tail refused")}
 // Detect snapshot mutation between path-based witnessing and analysis.
 if err:=verifyFile(f,*ledgerPin,maxLedgerBytes);err!=nil{return fmt.Errorf("snapshot changed during witness audit: %w",err)}
 if err:=verifySamePath(f,*ledgerPath);err!=nil{return fmt.Errorf("ledger path: %w",err)}
 if err:=verifySamePath(t,*trustPath);err!=nil{return fmt.Errorf("trust path: %w",err)}
 result,err:=correlate.Analyze(f,registry,clock);if err!=nil{return err}
 // Recheck the exact file descriptors AND the signed off-host chain before any output.
 if err:=verifySamePath(f,*ledgerPath);err!=nil{return fmt.Errorf("ledger path replaced: %w",err)}
 if err:=verifySamePath(t,*trustPath);err!=nil{return fmt.Errorf("trust path replaced: %w",err)}
 if err:=verifyFile(f,*ledgerPin,maxLedgerBytes);err!=nil{return fmt.Errorf("ledger changed during analysis: %w",err)}
 if err:=verifyFile(t,*trustPin,maxTrustBytes);err!=nil{return fmt.Errorf("trust changed during analysis: %w",err)}
 measuredFinal,tipFinal,err:=witness.Audit(*ledgerPath,*witnessHistory,pub,*witnessTip)
 if err!=nil||tipFinal!=tip||measuredFinal!=measured{return errors.New("signed witness evidence changed during analysis")}
 data,err:=json.MarshalIndent(result,"","  ");if err!=nil{return err}
 _,err=fmt.Fprintln(output,string(data));return err
}
func main(){
 if err:=run(os.Args[1:],os.Stdout,time.Now().UTC());err!=nil{
  fmt.Fprintln(os.Stderr,"triage refused:",err);os.Exit(1)
 }
}
