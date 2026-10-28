package main
import(
 "net/http"
 "os"
 "testing"
)
func TestCapacityRefusesAppendWithoutConsumingEvent(t *testing.T){
 rig:=newRig(t);rig.hub.maxLedgerBytes=1;event:=rig.signed(t,1)
 if code:=rig.post(event);code!=http.StatusInsufficientStorage{t.Fatalf("expected 507 got %d",code)}
 if rig.hub.seen[event.Report.NodeID+":"+event.Report.EventID]{t.Fatal("rejected event consumed")}
 info,err:=os.Stat(rig.path);if err!=nil||info.Size()!=0{t.Fatal("ledger mutated despite capacity")}
 rig.hub.maxLedgerBytes=defaultLedgerMaxBytes
 if code:=rig.post(event);code!=http.StatusAccepted{t.Fatalf("recovery failed %d",code)}
 rig.open(nil)
 if code:=rig.post(event);code!=http.StatusConflict{t.Fatalf("replay after restart %d",code)}
}
func TestCapacityNeverDeletesExistingEvidence(t *testing.T){
 rig:=newRig(t)
 if code:=rig.post(rig.signed(t,1));code!=http.StatusAccepted{t.Fatal(code)}
 before,err:=os.ReadFile(rig.path);if err!=nil{t.Fatal(err)}
 rig.hub.maxLedgerBytes=int64(len(before))
 if code:=rig.post(rig.signed(t,2));code!=http.StatusInsufficientStorage{t.Fatal(code)}
 after,err:=os.ReadFile(rig.path);if err!=nil{t.Fatal(err)}
 if string(after)!=string(before){t.Fatal("ledger erased/modified by cap")}
}