package witness

// Fail-closed disaster recovery tests. They intentionally manipulate only
// t.TempDir() evidence; no real network, private data, or deployment files.

import (
 "bytes"
 "os"
 "path/filepath"
 "testing"
 "time"
)

func readTestEvidence(t *testing.T, path string) []byte {
 t.Helper()
 b,err:=os.ReadFile(path)
 if err!=nil {t.Fatal(err)}
 return b
}
func restoreTestEvidence(t *testing.T,path string,b []byte){
 t.Helper()
 if err:=os.WriteFile(path,b,0600);err!=nil{t.Fatal(err)}
}

func TestWitnessCrashLockRequiresHumanRecoveryAndPinnedTip(t *testing.T){
 ledger,history,pub,priv:=testRig(t)
 t0:=time.Date(2026,11,3,12,0,0,0,time.UTC)
 _,tip1,err:=Attest(ledger,history,priv,t0,"",true)
 if err!=nil{t.Fatal(err)}
 snapshot1:=readTestEvidence(t,ledger)
 head1:=readTestEvidence(t,ledger+".head")
 history1:=readTestEvidence(t,history)
 appendEvent(t,ledger,2)
 // Equivalent to a process terminating after taking the exclusive lock:
 // only the test fixture creates this persistent lock; no process is killed.
 lock:=history+".lock"
 restoreTestEvidence(t,lock,[]byte("crash-lock: operator review required\n"))
 if _,_,err=Attest(ledger,history,priv,t0.Add(time.Minute),tip1,false);err==nil{
  t.Fatal("attestation bypassed crash lock")
 }
 if !bytes.Equal(readTestEvidence(t,history),history1){
  t.Fatal("crash-blocked signer modified historical evidence")
 }
 // Do not claim a newly appended unwitnessed row has been witnessed.
 if _,_,err=AuditClosed(ledger,history,pub,tip1);err==nil{
  t.Fatal("unwitnessed new ledger row accepted by strict audit")
 }
 // Prefix-only historical Audit remains intentionally separate: it may
 // verify an old signed checkpoint without attesting later ledger rows.
 if _,_,err=Audit(ledger,history,pub,tip1);err!=nil{
  t.Fatal("historical-prefix audit changed unexpectedly: ",err)
 }
 // Auditing an independently preserved old snapshot still works.
 oldLedger:=filepath.Join(t.TempDir(),"closed-one-row.jsonl")
 restoreTestEvidence(t,oldLedger,snapshot1)
 restoreTestEvidence(t,oldLedger+".head",head1)
 if _,_,err=Audit(oldLedger,history,pub,tip1);err!=nil{t.Fatal(err)}
 // Operator's explicit simulated decision after checking original signed
 // history is modeled by unlinking only this test-created lock.
 if err=os.Remove(lock);err!=nil{t.Fatal(err)}
 _,tip2,err:=Attest(ledger,history,priv,t0.Add(2*time.Minute),tip1,false)
 if err!=nil{t.Fatalf("manual-verified recovery failed: %v",err)}
 if tip2==tip1{t.Fatal("history tip did not advance")}
 if _,_,err=Audit(ledger,history,pub,tip2);err!=nil{t.Fatal(err)}
 if _,_,err=Audit(oldLedger,history,pub,tip2);err==nil{
  t.Fatal("old snapshot accepted against newer externally pinned tip")
 }
}

func TestWitnessTornHistoryRequiresExactBackupBeforeContinuing(t *testing.T){
 ledger,history,pub,priv:=testRig(t)
 start:=time.Date(2026,11,3,12,0,0,0,time.UTC)
 _,tip1,err:=Attest(ledger,history,priv,start,"",true)
 if err!=nil{t.Fatal(err)}
 backup1:=readTestEvidence(t,history)
 appendEvent(t,ledger,2)
 // Simulate an interrupted append that leaves an incomplete JSON row.
 f,err:=os.OpenFile(history,os.O_APPEND|os.O_WRONLY,0600)
 if err!=nil{t.Fatal(err)}
 _,err=f.Write([]byte(`{"checkpoint":`))
 if err!=nil{t.Fatal(err)}
 if err=f.Sync();err!=nil{t.Fatal(err)}
 if err=f.Close();err!=nil{t.Fatal(err)}
 if _,_,err=Attest(ledger,history,priv,start.Add(time.Minute),tip1,false);err==nil{
  t.Fatal("torn history silently repaired or accepted")
 }
 if _,err=ReadHistory(history,pub);err==nil{t.Fatal("torn history parsed")}
 // Restore the *exact bytes* of a separately retained signed history, not
 // an empty file or a newly bootstrapped identity.
 restoreTestEvidence(t,history,backup1)
 if _,_,err=Attest(ledger,history,priv,start.Add(time.Minute),tip1,true);err==nil{
  t.Fatal("bootstrap accepted after history recovery")
 }
 _,tip2,err:=Attest(ledger,history,priv,start.Add(time.Minute),tip1,false)
 if err!=nil{t.Fatal(err)}
 if tip2==tip1{t.Fatal("history did not advance")}
 if _,_,err=Audit(ledger,history,pub,tip2);err!=nil{t.Fatal(err)}
}

func TestWitnessClockRollbackAndRepeatedTimeRefused(t *testing.T){
 ledger,history,pub,priv:=testRig(t)
 start:=time.Date(2026,11,3,12,0,0,0,time.UTC)
 _,tip1,err:=Attest(ledger,history,priv,start,"",true)
 if err!=nil{t.Fatal(err)}
 before:=readTestEvidence(t,history)
 appendEvent(t,ledger,2)
 for _,moment:=range []time.Time{start.Add(-24*time.Hour),start}{
  if _,_,err=Attest(ledger,history,priv,moment,tip1,false);err==nil{
   t.Fatal("clock rollback or duplicate observation time accepted")
  }
  if !bytes.Equal(readTestEvidence(t,history),before){
   t.Fatal("failed clock test mutated history")
  }
 }
 _,tip2,err:=Attest(ledger,history,priv,start.Add(time.Minute),tip1,false)
 if err!=nil{t.Fatal(err)}
 if _,_,err=Audit(ledger,history,pub,tip2);err!=nil{t.Fatal(err)}
}

func TestWitnessRollbackRestoreFailsUntilExactPinnedHistoryRestored(t *testing.T){
 ledger,history,pub,priv:=testRig(t)
 start:=time.Date(2026,11,3,12,0,0,0,time.UTC)
 _,tip1,err:=Attest(ledger,history,priv,start,"",true)
 if err!=nil{t.Fatal(err)}
 oldHistory:=readTestEvidence(t,history)
 oldLedger:=readTestEvidence(t,ledger)
 oldHead:=readTestEvidence(t,ledger+".head")
 appendEvent(t,ledger,2)
 _,tip2,err:=Attest(ledger,history,priv,start.Add(time.Minute),tip1,false)
 if err!=nil{t.Fatal(err)}
 goodHistory:=readTestEvidence(t,history)
 goodLedger:=readTestEvidence(t,ledger)
 goodHead:=readTestEvidence(t,ledger+".head")
 // An attacker restores both apparently valid old ledger and old history.
 restoreTestEvidence(t,ledger,oldLedger)
 restoreTestEvidence(t,ledger+".head",oldHead)
 restoreTestEvidence(t,history,oldHistory)
 if _,_,err=Audit(ledger,history,pub,tip2);err==nil{
  t.Fatal("full valid old backup accepted against independent new tip")
 }
 if _,_,err=Attest(ledger,history,priv,start.Add(2*time.Minute),tip2,false);err==nil{
  t.Fatal("rolled-back signed history silently forked")
 }
 // Only restoration of exact previously signed evidence is accepted.
 restoreTestEvidence(t,ledger,goodLedger)
 restoreTestEvidence(t,ledger+".head",goodHead)
 restoreTestEvidence(t,history,goodHistory)
 if _,_,err=Audit(ledger,history,pub,tip2);err!=nil{
  t.Fatalf("intact pinned backup did not recover: %v",err)
 }
}

func TestWitnessOfflineWithoutNewEvidenceNeverCreatesAllClear(t *testing.T){
 ledger,history,pub,priv:=testRig(t)
 start:=time.Date(2026,11,3,12,0,0,0,time.UTC)
 _,tip1,err:=Attest(ledger,history,priv,start,"",true)
 if err!=nil{t.Fatal(err)}
 original:=readTestEvidence(t,history)
 // A 48-hour partition is represented by no report or ledger append.
 // Historical verification is possible but it must not produce a new
 // checkpoint or an observation-completeness assertion.
 if _,_,err=Audit(ledger,history,pub,tip1);err!=nil{t.Fatal(err)}
 if _,_,err=Attest(ledger,history,priv,start.Add(48*time.Hour),tip1,false);err==nil{
  t.Fatal("stationary ledger was re-attested as new coverage")
 }
 if !bytes.Equal(readTestEvidence(t,history),original){
  t.Fatal("partition generated new history despite zero evidence")
 }
}
