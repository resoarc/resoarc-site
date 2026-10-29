package main

import (
 "net/http"
 "os"
 "path/filepath"
 "testing"
 "time"
)

func TestGracefulStopDrainsAndSyncsLedger(t *testing.T){
 tmp:=t.TempDir()
 ledger,err:=os.OpenFile(filepath.Join(tmp,"ledger.jsonl"),os.O_CREATE|os.O_RDWR,0600)
 if err!=nil{t.Fatal(err)}
 defer ledger.Close()
 if _,err=ledger.Write([]byte("synthetic-only\n"));err!=nil{t.Fatal(err)}
 hub:=&server{ledger:ledger}
 srv:=&http.Server{Addr:"127.0.0.1:0",Handler:http.NewServeMux()}
 signals:=make(chan os.Signal,1)
 done:=make(chan error,1)
 go func(){done<-serveUntilGracefullyStopped(srv,hub,signals)}()
 time.Sleep(30*time.Millisecond)
 signals<-os.Interrupt
 select{
 case err:=<-done:
  if err!=nil{t.Fatalf("graceful stop failed: %v",err)}
 case <-time.After(3*time.Second):t.Fatal("HUB did not shut down")
 }
 if err:=ledger.Sync();err!=nil{t.Fatal(err)}
 raw,err:=os.ReadFile(ledger.Name());if err!=nil{t.Fatal(err)}
 if string(raw)!="synthetic-only\n"{t.Fatal("graceful shutdown corrupted ledger")}
}

func TestGracefulStopRejectsPoisonedLedger(t *testing.T){
 root:=t.TempDir()
 ledger,err:=os.OpenFile(filepath.Join(root,"ledger.jsonl"),os.O_CREATE|os.O_RDWR,0600)
 if err!=nil{t.Fatal(err)}
 defer ledger.Close()
 hub:=&server{ledger:ledger,poisoned:true}
 srv:=&http.Server{Addr:"127.0.0.1:0",Handler:http.NewServeMux()}
 stop:=make(chan os.Signal,1)
 done:=make(chan error,1)
 go func(){done<-serveUntilGracefullyStopped(srv,hub,stop)}()
 time.Sleep(30*time.Millisecond)
 stop<-os.Interrupt
 select{
 case err:=<-done:
  if err==nil{t.Fatal("poisoned ledger was cleared for normal shutdown")}
 case <-time.After(3*time.Second):t.Fatal("poisoned HUB failed to stop")
 }
}
