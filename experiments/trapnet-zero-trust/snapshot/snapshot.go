// Package snapshot creates consistent, operator-reviewed offline copies of HUB
// evidence while HUB is STOPPED. It never opens a listener or changes live data.
package snapshot

import (
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "runtime"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

func regular(path string) error {
 st,err:=os.Lstat(path)
 if err!=nil{return err}
 if !st.Mode().IsRegular(){return fmt.Errorf("non-regular evidence file: %q",path)}
 return nil
}

func copyDurable(src,dest string)error{
 if err:=regular(src);err!=nil{return err}
 from,err:=os.Open(src);if err!=nil{return err};defer from.Close()
 to,err:=os.OpenFile(dest,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{return err}
 if _,err=io.Copy(to,from);err!=nil{_ = to.Close();return err}
 if err=to.Sync();err!=nil{_=to.Close();return err}
 return to.Close()
}

// Create refuses active/stale HUB writer locks, validates source content,
// verifies its durable copy, then atomically publishes a new output directory.
// Separately administered off-HUB witnessing remains a REQUIRED later step.
func Create(ledgerPath,outputDir string)(witness.Head,error){
 ledger,err:=filepath.Abs(ledgerPath);if err!=nil{return witness.Head{},err}
 out,err:=filepath.Abs(outputDir);if err!=nil{return witness.Head{},err}
 if out==filepath.Dir(ledger)||out==ledger||out==ledger+".head"{return witness.Head{},errors.New("unsafe snapshot target")}
 if _,err=os.Lstat(out);err==nil{return witness.Head{},errors.New("snapshot destination already exists")}else if !errors.Is(err,os.ErrNotExist){return witness.Head{},err}
 lock:=ledger+".lock"
 lf,err:=os.OpenFile(lock,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return witness.Head{},fmt.Errorf("HUB running or stale lock exists: %w",err)}
 defer func(){_=lf.Close();_=os.Remove(lock)}()
 if _,err=lf.WriteString("snapshot: HUB must be stopped\n");err!=nil{return witness.Head{},err}
 if err=lf.Sync();err!=nil{return witness.Head{},err}
 head,err:=witness.Snapshot(ledger,nil);if err!=nil{return witness.Head{},fmt.Errorf("invalid source ledger: %w",err)}
 parent:=filepath.Dir(out)
 tmp,err:=os.MkdirTemp(parent,".trapnet-snapshot-");if err!=nil{return witness.Head{},err}
 defer os.RemoveAll(tmp)
 newLedger:=filepath.Join(tmp,"ledger.jsonl")
 if err=copyDurable(ledger,newLedger);err!=nil{return witness.Head{},err}
 if err=copyDurable(ledger+".head",newLedger+".head");err!=nil{return witness.Head{},err}
 copied,err:=witness.Snapshot(newLedger,nil)
 if err!=nil||copied!=head{return witness.Head{},errors.New("snapshot content mismatch; source may have changed")}
 if runtime.GOOS!="windows" {
  d,e:=os.Open(tmp);if e!=nil{return witness.Head{},e}
  e=d.Sync();_=d.Close();if e!=nil{return witness.Head{},e}
 }
 if _,err=os.Lstat(out);err==nil{return witness.Head{},errors.New("destination appeared during snapshot")}else if !errors.Is(err,os.ErrNotExist){return witness.Head{},err}
 if err=os.Rename(tmp,out);err!=nil{return witness.Head{},err}
 if runtime.GOOS!="windows" {if d,e:=os.Open(parent);e==nil{_=d.Sync();_=d.Close()}}
 return head,nil
}