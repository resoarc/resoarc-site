package recovery

import (
 "crypto/ed25519"
 "crypto/rand"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

func fixture(t *testing.T)(ledger,history string,pub ed25519.PublicKey,tip string,now time.Time){
 t.Helper()
 d:=t.TempDir();ledger=filepath.Join(d,"ledger.jsonl");history=filepath.Join(d,"offhost-history.jsonl")
 if err:=os.WriteFile(ledger,[]byte("{\"event\":1}\n"),0600);err!=nil{t.Fatal(err)}
 head,err:=witness.Measure(ledger,nil);if err!=nil{t.Fatal(err)}
 b,_:=json.Marshal(head);if err=os.WriteFile(ledger+".head",b,0600);err!=nil{t.Fatal(err)}
 var priv ed25519.PrivateKey
 pub,priv,err=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 now=time.Now().UTC()
 _,tip,err=witness.Attest(ledger,history,priv,now.Add(-time.Minute),"",true)
 if err!=nil{t.Fatal(err)}
 return
}
func TestCompletelyWitnessedStillNeverGrantsRestart(t *testing.T){
 l,h,p,tip,now:=fixture(t)
 r,err:=Inspect(l,h,p,tip,now)
 if err!=nil{t.Fatal(err)}
 if r.Status!="fully_witnessed"||r.LedgerRows!=1||r.MayStartHub{t.Fatalf("unexpected: %+v",r)}
}
func TestUnwitnessedTailNotTrusted(t *testing.T){
 l,h,p,tip,now:=fixture(t)
 f,e:=os.OpenFile(l,os.O_APPEND|os.O_WRONLY,0600);if e!=nil{t.Fatal(e)}
 if _,e=f.Write([]byte("{\"event\":2}\n"));e!=nil{t.Fatal(e)}
 if e=f.Close();e!=nil{t.Fatal(e)}
 head,e:=witness.Measure(l,nil);if e!=nil{t.Fatal(e)}
 b,_:=json.Marshal(head);if e=os.WriteFile(l+".head",b,0600);e!=nil{t.Fatal(e)}
 r,e:=Inspect(l,h,p,tip,now)
 if e!=nil{t.Fatal(e)}
 if r.Status!="unwitnessed_tail"||r.UnwitnessedRows!=1||r.MayStartHub {t.Fatalf("unsafe: %+v",r)}
}
func TestRefusesMissingWrongOrStolenTrustAnchor(t *testing.T){
 l,h,p,tip,now:=fixture(t)
 if _,e:=Inspect(l,h,p,"",now);e==nil{t.Fatal("missing pin allowed")}
 if _,e:=Inspect(l,h,p,strings.Repeat("a",64),now);e==nil{t.Fatal("wrong pin allowed")}
 other,_,_:=ed25519.GenerateKey(rand.Reader)
 if _,e:=Inspect(l,h,other,tip,now);e==nil{t.Fatal("wrong signing key allowed")}
}
func TestRefusesCorruptionAndLock(t *testing.T){
 cases:=[]struct{name string;alter func(string)error}{
  {"mutated",func(p string)error{return os.WriteFile(p,[]byte("{\"event\":9}\n"),0600)}},
  {"missing_head",func(p string)error{return os.Remove(p+".head")}},
  {"torn",func(p string)error{f,e:=os.OpenFile(p,os.O_APPEND|os.O_WRONLY,0600);if e!=nil{return e};_,e=f.WriteString("{\"event\":");c:=f.Close();if e!=nil{return e};return c}},
  {"truncated",func(p string)error{return os.Truncate(p,3)}},
  {"lock",func(p string)error{return os.WriteFile(p+".lock",[]byte("stale"),0600)}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  l,h,p,tip,now:=fixture(t)
  if e:=tc.alter(l);e!=nil{t.Fatal(e)}
  if _,e:=Inspect(l,h,p,tip,now);e==nil{t.Fatal("unsafe evidence accepted")}
 })}
}
func TestRefusesTruncatedWitnessHistoryAndSymlink(t *testing.T){
 l,h,p,tip,now:=fixture(t)
 b,e:=os.ReadFile(h);if e!=nil{t.Fatal(e)}
 if e=os.WriteFile(h,b[:len(b)/2],0600);e!=nil{t.Fatal(e)}
 if _,e:=Inspect(l,h,p,tip,now);e==nil{t.Fatal("history truncation accepted")}
 l,h,p,tip,now=fixture(t)
 symlink:=filepath.Join(t.TempDir(),"linked-ledger")
 if e:=os.Symlink(l,symlink);e==nil {
  if _,e:=Inspect(symlink,h,p,tip,now);e==nil{t.Fatal("symlink accepted")}
 }
}
