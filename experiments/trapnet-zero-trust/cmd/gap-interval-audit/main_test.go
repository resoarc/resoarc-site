package main

import (
    "os"
    "path/filepath"
    "strings"
    "testing"
)

type fixture struct {
    A string `json:"a"`
    B int `json:"b"`
}

func write(t *testing.T,value string)string{
    t.Helper()
    file:=filepath.Join(t.TempDir(),"synthetic.json")
    if err:=os.WriteFile(file,[]byte(value),0600);err!=nil{t.Fatal(err)}
    return file
}
func TestCanonicalSignedInputAccepted(t *testing.T){
    var v fixture
    if err:=decodeCanonical(write(t,"{"a":"ok","b":3}
"),200,&v);err!=nil{t.Fatal(err)}
    if v.A!="ok"||v.B!=3{t.Fatalf("%+v",v)}
}
func TestDuplicateJSONKeysRejected(t *testing.T){
    var v fixture
    if err:=decodeCanonical(write(t,"{"a":"first","a":"second","b":3}"),200,&v);err==nil{
        t.Fatal("duplicate key accepted")
    }
}
func TestUnknownOrReorderedFieldsRejected(t *testing.T){
    for _,raw:=range []string{
        "{"a":"ok","b":3,"unreviewed":true}",
        "{"b":3,"a":"ok"}",
        "{"a":"ok","b":3}{"a":"x"}",
    }{
        var v fixture
        if err:=decodeCanonical(write(t,raw),200,&v);err==nil{t.Fatal("noncanonical evidence accepted")}
    }
}
func TestMissingAndOversizedFilesRejected(t *testing.T){
    if _,err:=readBounded("",10);err==nil{t.Fatal("empty path accepted")}
    if _,err:=readBounded(write(t,strings.Repeat("x",20)),10);err==nil{t.Fatal("oversized read accepted")}
}
func TestSymlinkRefused(t *testing.T){
    d:=t.TempDir()
    real:=filepath.Join(d,"real")
    if err:=os.WriteFile(real,[]byte("fixture"),0600);err!=nil{t.Fatal(err)}
    link:=filepath.Join(d,"alias")
    if err:=os.Symlink(real,link);err!=nil{t.Skip("symlink unavailable")}
    if _,err:=readBounded(link,100);err==nil{t.Fatal("symlink evidence accepted")}
}
func TestAbsentCryptoEvidenceCannotPass(t *testing.T){
    if err:=run(nil);err==nil{t.Fatal("missing real signed reports accepted")}
}
