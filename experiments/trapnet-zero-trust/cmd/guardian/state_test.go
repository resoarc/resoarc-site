package main

import (
 "crypto/ed25519"
 "crypto/rand"
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
func sampleFeed(t *testing.T,priv ed25519.PrivateKey,now time.Time,version uint64,summary string)protocol.SignedFeed{
 t.Helper()
 f:=protocol.Feed{Schema:protocol.FeedSchema,Version:version,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]protocol.Warning{{Category:"notice",Summary:summary}}}
 sf,err:=protocol.SignFeed(f,priv)
 if err!=nil{t.Fatal(err)}
 return sf
}
func TestGuardianRollbackAndEquivocation(t *testing.T){
 pub,priv,_:=ed25519.GenerateKey(rand.Reader)
 now:=time.Now().UTC()
 state:=filepath.Join(t.TempDir(),"state.json")
 sf:=sampleFeed(t,priv,now,2,"good")
 if err:=verifyAndRecord(sf,pub,state,now);err!=nil{t.Fatal(err)}
 if err:=verifyAndRecord(sf,pub,state,now);err!=nil{t.Fatal(err)}
 if err:=verifyAndRecord(sampleFeed(t,priv,now,2,"changed"),pub,state,now);err==nil{t.Fatal("equivocation accepted")}
 if err:=verifyAndRecord(sampleFeed(t,priv,now,1,"old"),pub,state,now);err==nil{t.Fatal("rollback accepted")}
 if err:=verifyAndRecord(sampleFeed(t,priv,now,3,"new"),pub,state,now);err!=nil{t.Fatal(err)}
}
func TestGuardianRejectsInvalidSignatureWithoutSaving(t *testing.T){
 pub,priv,_:=ed25519.GenerateKey(rand.Reader)
 now:=time.Now().UTC()
 state:=filepath.Join(t.TempDir(),"state.json")
 sf:=sampleFeed(t,priv,now,1,"good")
 sf.Feed.Warnings[0].Summary="tampered"
 if err:=verifyAndRecord(sf,pub,state,now);err==nil{t.Fatal("bad signature accepted")}
 if _,err:=os.Stat(state);!os.IsNotExist(err){t.Fatalf("bad feed wrote state: %v",err)}
}
func TestGuardianLegacyStateNeedsVersionIncrease(t *testing.T){
 pub,priv,_:=ed25519.GenerateKey(rand.Reader)
 now:=time.Now().UTC()
 state:=filepath.Join(t.TempDir(),"state.json")
 old,_:=json.Marshal(guardianState{Version:1})
 if err:=os.WriteFile(state,old,0600);err!=nil{t.Fatal(err)}
 if err:=verifyAndRecord(sampleFeed(t,priv,now,1,"old"),pub,state,now);err==nil{t.Fatal("legacy state accepted same version")}
 if err:=verifyAndRecord(sampleFeed(t,priv,now,2,"next"),pub,state,now);err!=nil{t.Fatal(err)}
}
func TestGuardianRejectsSymlinkState(t *testing.T){
 pub,priv,_:=ed25519.GenerateKey(rand.Reader)
 now:=time.Now().UTC()
 dir:=t.TempDir()
 dest:=filepath.Join(dir,"other.json")
 if err:=os.WriteFile(dest,[]byte(`{}`),0600);err!=nil{t.Fatal(err)}
 path:=filepath.Join(dir,"state.json")
 if err:=os.Symlink(dest,path);err!=nil{t.Skip(err)}
 if err:=verifyAndRecord(sampleFeed(t,priv,now,1,"warning"),pub,path,now);err==nil{t.Fatal("symlink accepted")}
}
