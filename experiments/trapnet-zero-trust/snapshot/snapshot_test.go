package snapshot

import(
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)
func rig(t *testing.T)(string,string){
 t.Helper();d:=t.TempDir();ledger:=filepath.Join(d,"ledger.jsonl")
 head:=witness.Head{Revision:1,Rows:0,Digest:"0000000000000000000000000000000000000000000000000000000000000000"}
 b,_:=json.Marshal(head)
 if err:=os.WriteFile(ledger,[]byte{},0600);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(ledger+".head",b,0600);err!=nil{t.Fatal(err)}
 return ledger,filepath.Join(d,"snapshot")
}
func TestSnapshotAtomicAndChecksCopy(t *testing.T){
 l,out:=rig(t);head,err:=Create(l,out);if err!=nil{t.Fatal(err)}
 got,err:=witness.Snapshot(filepath.Join(out,"ledger.jsonl"),nil);if err!=nil||got!=head{t.Fatalf("copy invalid %v",err)}
 if _,err=Create(l,out);err==nil{t.Fatal("overwrote snapshot")}
}
func TestSnapshotRefusesLiveOrStaleLock(t *testing.T){
 l,out:=rig(t);if err:=os.WriteFile(l+".lock",[]byte("live"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Create(l,out);err==nil{t.Fatal("accepted locked ledger")}
 if _,err:=os.Stat(l+".lock");err!=nil{t.Fatal("deleted other writer's lock")}
 if _,err:=os.Stat(out);!os.IsNotExist(err){t.Fatal("published invalid snapshot")}
}
func TestSnapshotRejectsCorruptLedgerAndSymlinks(t *testing.T){
 l,out:=rig(t);if err:=os.WriteFile(l,[]byte("{\"bad\":true}\n"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Create(l,out);err==nil{t.Fatal("accepted incorrect head")}
 if _,err:=os.Stat(out);!os.IsNotExist(err){t.Fatal("published invalid snapshot")}
 _=os.Remove(l);if err:=os.Symlink(l+".head",l);err!=nil{t.Skip("symlink privileges unavailable")}
 if _,err:=Create(l,out);err==nil{t.Fatal("accepted symlink evidence")}
}
func TestSnapshotRejectsMissingCheckpoint(t *testing.T){
 l,out:=rig(t);if err:=os.Remove(l+".head");err!=nil{t.Fatal(err)}
 if _,err:=Create(l,out);err==nil{t.Fatal("missing checkpoint accepted")}
}