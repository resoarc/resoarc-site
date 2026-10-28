package main

import (
 "bytes"
 "encoding/json"
 "os"
 "testing"
 "time"
)

// These are deterministic crash-window simulations, not physical power cuts.
func TestCrashSyncedRowBeforeCheckpointFailsClosed(t *testing.T) {
 rig:=newRig(t)
 if c:=rig.post(rig.signed(t,1));c!=202{t.Fatalf("HTTP %d",c)}
 b,e:=json.Marshal(ledgerEntry{ReceivedAt:rig.now,Evidence:rig.signed(t,2)});if e!=nil{t.Fatal(e)}
 f,e:=os.OpenFile(rig.path,os.O_APPEND|os.O_WRONLY,0600);if e!=nil{t.Fatal(e)}
 if _,e=f.Write(append(b,'\n'));e!=nil{t.Fatal(e)}
 if e=f.Sync();e!=nil{t.Fatal(e)}
 if e=f.Close();e!=nil{t.Fatal(e)}
 ledgerBefore,_:=os.ReadFile(rig.path);headBefore,_:=os.ReadFile(rig.path+".head")
 if _,e=newServer(rig.hub.keys,nil,rig.ledger,func()time.Time{return rig.now});e==nil{t.Fatal("crash window silently healed")}
 ledgerAfter,_:=os.ReadFile(rig.path);headAfter,_:=os.ReadFile(rig.path+".head")
 if !bytes.Equal(ledgerBefore,ledgerAfter)||!bytes.Equal(headBefore,headAfter){t.Fatal("recovery attempt changed forensic evidence")}
}
func TestCrashAdvancedCheckpointBeforeLedgerTailDurableFailsClosed(t *testing.T) {
 rig:=newRig(t)
 if c:=rig.post(rig.signed(t,1));c!=202{t.Fatalf("HTTP %d",c)}
 b,e:=json.Marshal(ledgerEntry{ReceivedAt:rig.now,Evidence:rig.signed(t,2)});if e!=nil{t.Fatal(e)}
 next,e:=nextHead(rig.hub.head,append(b,'\n'));if e!=nil{t.Fatal(e)}
 if e=saveHead(rig.path+".head",next);e!=nil{t.Fatal(e)}
 if _,e=newServer(rig.hub.keys,nil,rig.ledger,func()time.Time{return rig.now});e==nil{t.Fatal("checkpoint ahead accepted")}
}
