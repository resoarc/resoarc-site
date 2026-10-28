package main
import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"
)
func TestInputPinsRequired(t *testing.T){
 if err:=run([]string{"-ledger","x","-trust","y"},new(bytes.Buffer),time.Now());err==nil{t.Fatal("missing independent pins accepted")}
}
func TestContentTamperRefusedBeforeUse(t *testing.T){
 path:=filepath.Join(t.TempDir(),"evidence.jsonl")
 if err:=os.WriteFile(path,[]byte("evidence"),0600);err!=nil{t.Fatal(err)}
 original:=sha256.Sum256([]byte("evidence"))
 f,err:=os.Open(path);if err!=nil{t.Fatal(err)}
 if err:=verifyFile(f,hex.EncodeToString(original[:]),1024);err!=nil{t.Fatal(err)}
 f.Close()
 if err:=os.WriteFile(path,[]byte("evil replacement"),0600);err!=nil{t.Fatal(err)}
 f,_=os.Open(path);defer f.Close()
 if err:=verifyFile(f,hex.EncodeToString(original[:]),1024);err==nil{t.Fatal("tampered evidence accepted")}
}
func TestInvalidDigestRejected(t *testing.T){
 path:=filepath.Join(t.TempDir(),"ledger")
 if err:=os.WriteFile(path,[]byte("x"),0600);err!=nil{t.Fatal(err)}
 f,err:=os.Open(path);if err!=nil{t.Fatal(err)};defer f.Close()
 if err:=verifyFile(f,strings.Repeat("z",64),1024);err==nil{t.Fatal("invalid digest accepted")}
}
