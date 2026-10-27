// HUB accepts signed reports from explicitly allowlisted sensors. It does NOT
// decide that an IP is malicious, issue commands or publish defense rules.
package main

import (
 "bufio"
 "crypto/ed25519"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "log"
 "net/http"
 "os"
 "strings"
 "sync"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

const perNodeMinuteLimit = 30

type ledgerEntry struct {
 ReceivedAt time.Time `json:"received_at"`
 Evidence protocol.SignedReport `json:"evidence"`
}

type server struct {
 mu sync.Mutex
 keys map[string]ed25519.PublicKey
 revoked map[string]bool
 seen map[string]bool
 recent map[string][]time.Time
 ledger *os.File
 now func() time.Time
}

// restoreLedger persists replay protection and reconstructs recent rate limits
// using HUB reception time, never client-reported observation time.
// Existing v0.1 rows retain replay protection but have no trusted receipt time.
func restoreLedger(f *os.File, now time.Time) (map[string]bool, map[string][]time.Time, error) {
 if _, err := f.Seek(0, io.SeekStart); err != nil { return nil,nil,err }
 seen := make(map[string]bool)
 recent := make(map[string][]time.Time)
 scanner := bufio.NewScanner(f)
 scanner.Buffer(make([]byte,4096),65536)
 for row:=1; scanner.Scan(); row++ {
  raw:=scanner.Bytes()
  var entry ledgerEntry
  if err:=json.Unmarshal(raw,&entry);err!=nil{return nil,nil,fmt.Errorf("ledger line %d: %w",row,err)}
  if entry.ReceivedAt.IsZero() {
   var old protocol.SignedReport
   if err:=json.Unmarshal(raw,&old);err!=nil || old.Report.EventID=="" || old.Report.NodeID=="" {return nil,nil,fmt.Errorf("ledger line %d: invalid evidence",row)}
   seen[old.Report.NodeID+":"+old.Report.EventID]=true
   continue
  }
  if entry.Evidence.Report.EventID=="" || entry.Evidence.Report.NodeID=="" || entry.ReceivedAt.After(now.Add(2*time.Minute)) {return nil,nil,fmt.Errorf("ledger line %d: invalid receipt",row)}
  id:=entry.Evidence.Report.NodeID+":"+entry.Evidence.Report.EventID
  if seen[id] {return nil,nil,fmt.Errorf("ledger line %d: repeated event ID",row)}
  seen[id]=true
  if entry.ReceivedAt.After(now.Add(-time.Minute)) {
   node:=entry.Evidence.Report.NodeID
   recent[node]=append(recent[node],entry.ReceivedAt)
  }
 }
 if err:=scanner.Err();err!=nil{return nil,nil,err}
 if _,err:=f.Seek(0,io.SeekEnd);err!=nil{return nil,nil,err}
 return seen,recent,nil
}

func newServer(keys map[string]ed25519.PublicKey, revoked map[string]bool, ledger *os.File, clock func()time.Time)(*server,error){
 seen,recent,err:=restoreLedger(ledger,clock().UTC())
 if err!=nil{return nil,err}
 return &server{keys:keys,revoked:revoked,seen:seen,recent:recent,ledger:ledger,now:clock},nil
}

func(s *server)report(w http.ResponseWriter,r *http.Request){
 if r.Method!=http.MethodPost {http.Error(w,"method not allowed",405);return}
 if r.Header.Get("Content-Type")!="application/json" {http.Error(w,"json required",415);return}
 r.Body=http.MaxBytesReader(w,r.Body,8192)
 defer r.Body.Close()
 dec:=json.NewDecoder(r.Body)
 dec.DisallowUnknownFields()
 var sr protocol.SignedReport
 if err:=dec.Decode(&sr);err!=nil{http.Error(w,"invalid report",400);return}
 if err:=dec.Decode(new(any));err!=io.EOF{http.Error(w,"extra data",400);return}

 s.mu.Lock()
 defer s.mu.Unlock()
 pub,ok:=s.keys[sr.Report.NodeID]
 if !ok || s.revoked[sr.Report.NodeID] {http.Error(w,"not registered",403);return}
 now:=s.now().UTC()
 if err:=protocol.VerifyReport(sr,pub,now);err!=nil{http.Error(w,"rejected report",403);return}
 id:=sr.Report.NodeID+":"+sr.Report.EventID
 if s.seen[id] {http.Error(w,"duplicate report",409);return}
 times:=s.recent[sr.Report.NodeID][:0]
 for _,t:=range s.recent[sr.Report.NodeID] {
  if t.After(now.Add(-time.Minute)) && !t.After(now) {times=append(times,t)}
 }
 s.recent[sr.Report.NodeID]=times
 if len(times)>=perNodeMinuteLimit {http.Error(w,"rate limited",429);return}
 entry,err:=json.Marshal(ledgerEntry{ReceivedAt:now,Evidence:sr})
 if err!=nil{http.Error(w,"encode failed",500);return}
 if _,err=s.ledger.Write(append(entry,'\n'));err!=nil{http.Error(w,"storage unavailable",503);return}
 if err=s.ledger.Sync();err!=nil{http.Error(w,"storage unavailable",503);return}
 s.seen[id]=true
 s.recent[sr.Report.NodeID]=append(s.recent[sr.Report.NodeID],now)
 w.Header().Set("Content-Type","application/json")
 w.WriteHeader(http.StatusAccepted)
 fmt.Fprintln(w,`{"status":"received_unverified"}`)
}

func loadTrust(allowlistFile,revokedFile string)(map[string]ed25519.PublicKey,map[string]bool,error){
 raw,err:=os.ReadFile(allowlistFile)
 if err!=nil{return nil,nil,err}
 var entries map[string]string
 if err:=json.Unmarshal(raw,&entries);err!=nil{return nil,nil,err}
 if len(entries)==0{return nil,nil,errors.New("empty allowlist")}
 keys:=make(map[string]ed25519.PublicKey)
 for id,h:=range entries{
  pub,err:=protocol.PublicFromHex(strings.TrimSpace(h))
  if err!=nil || protocol.NodeID(pub)!=id{return nil,nil,fmt.Errorf("invalid allowlisted key %q",id)}
  keys[id]=pub
 }
 revoked:=make(map[string]bool)
 if revokedFile!=""{
  b,err:=os.ReadFile(revokedFile)
  if err!=nil{return nil,nil,err}
  var ids []string
  if err:=json.Unmarshal(b,&ids);err!=nil{return nil,nil,err}
  for _,id:=range ids{
   if _,ok:=keys[id];!ok{return nil,nil,fmt.Errorf("revoked node not in allowlist: %q",id)}
   revoked[id]=true
  }
 }
 return keys,revoked,nil
}

func main(){
 addr:=flag.String("listen","127.0.0.1:8788","loopback listen address")
 keysFile:=flag.String("allowlist","allowlist.json","node_id to public key mapping")
 revokedFile:=flag.String("revoked","","optional JSON list of revoked node IDs (required to exist when specified; read at startup)")
 ledgerFile:=flag.String("ledger","ledger.jsonl","local append-only evidence ledger")
 flag.Parse()
 if *addr!="127.0.0.1:8788"{log.Fatal("MVP only listens on 127.0.0.1:8788")}
 keys,revoked,err:=loadTrust(*keysFile,*revokedFile)
 if err!=nil{log.Fatal("invalid trust configuration: ",err)}
 f,err:=os.OpenFile(*ledgerFile,os.O_CREATE|os.O_APPEND|os.O_RDWR,0600)
 if err!=nil{log.Fatal(err)}
 defer f.Close()
 s,err:=newServer(keys,revoked,f,time.Now)
 if err!=nil{log.Fatal("invalid ledger: ",err)}
 mux:=http.NewServeMux()
 mux.HandleFunc("/report",s.report)
 mux.HandleFunc("/health",func(w http.ResponseWriter,r *http.Request){
  if r.Method!=http.MethodGet{w.WriteHeader(405);return}
  fmt.Fprintln(w,"ok")
 })
 log.Println("HUB local-only MVP ready")
 srv:=&http.Server{Addr:*addr,Handler:mux,ReadHeaderTimeout:5*time.Second,ReadTimeout:10*time.Second,WriteTimeout:10*time.Second,IdleTimeout:15*time.Second,MaxHeaderBytes:8192}
 log.Fatal(srv.ListenAndServe())
}
