package main

import (
 "bufio"
 "bytes"
 "crypto/ed25519"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "os"
 "strings"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
)

// readPrivateReceiptKey accepts only a local, restrictive regular private file.
// It does not generate a key, rotate it or imply off-host key custody.
func readPrivateReceiptKey(path string)(ed25519.PrivateKey,error){
 if path==""{return nil,errors.New("HUB receipt signing key path required")}
 info,err:=os.Lstat(path)
 if err!=nil{return nil,err}
 if !info.Mode().IsRegular() || info.Mode().Perm()&0077!=0 {
  return nil,errors.New("unsafe receipt signing key mode")
 }
 raw,err:=os.ReadFile(path);if err!=nil{return nil,err}
 priv,err:=protocol.PrivateFromHex(strings.TrimSpace(string(raw)))
 if err!=nil{return nil,err}
 return priv,nil
}

// exactLiveReceiptEvidence refuses to issue a receipt from the "seen" index
// alone, as that index may include externally witnessed archives. It also
// refuses a rewritten/uncheckpointed ledger. This operation runs under s.mu.
func (s *server) exactLiveReceiptEvidence(incoming protocol.SignedReport)(receivedAt string,ok bool,err error){
 measured,err:=measureLedger(s.ledger)
 if err!=nil{return "",false,err}
 if measured!=s.head{return "",false,errors.New("ledger head changed")}
 if _,err=checkLedgerHead(s.ledger,measured);err!=nil{return "",false,err}
 input,err:=json.Marshal(incoming);if err!=nil{return "",false,err}
 file,err:=os.Open(s.ledger.Name());if err!=nil{return "",false,err}
 defer file.Close()
 scanner:=bufio.NewScanner(io.LimitReader(file,s.maxLedgerBytes+1))
 scanner.Buffer(make([]byte,4096),65536)
 for scanner.Scan(){
  var row ledgerEntry
  if err:=json.Unmarshal(scanner.Bytes(),&row);err!=nil{return "",false,err}
  if row.ReceivedAt.IsZero(){continue}
  if row.Evidence.Report.NodeID!=incoming.Report.NodeID || row.Evidence.Report.EventID!=incoming.Report.EventID{continue}
  expected,err:=json.Marshal(row.Evidence);if err!=nil{return "",false,err}
  if !bytes.Equal(input,expected){return "",false,nil}
  return row.ReceivedAt.UTC().Format("2006-01-02T15:04:05.999999999Z07:00"),true,nil
 }
 if err:=scanner.Err();err!=nil{return "",false,err}
 return "",false,nil
}

func (s *server) signedDuplicateReceipt(w http.ResponseWriter,sr protocol.SignedReport){
 value,found,err:=s.exactLiveReceiptEvidence(sr)
 if err!=nil{
  s.poisoned=true
  http.Error(w,"ledger cannot prove original report",http.StatusServiceUnavailable)
  return
 }
 if !found{
  http.Error(w,"duplicate report requires external review",http.StatusConflict)
  return
 }
 // Convert verified ledger timestamp only; never use current time as the
 // actual evidence receipt instant.
 timestamp,err:=time.Parse(time.RFC3339Nano,value)
 if err!=nil{
  s.poisoned=true
  http.Error(w,"bad verified receipt timestamp",http.StatusServiceUnavailable)
  return
 }
 s.writeSignedReceipt(w,sr,timestamp,http.StatusConflict)
}

func (s *server) writeSignedReceipt(w http.ResponseWriter,sr protocol.SignedReport,receivedAt time.Time,status int){
 proof,err:=receipt.Sign(sr,s.head.Digest,s.head.Rows,receivedAt,s.receiptPrivate)
 if err!=nil{
  http.Error(w,"HUB receipt signing unavailable",http.StatusServiceUnavailable)
  return
 }
 raw,err:=json.Marshal(proof)
 if err!=nil || len(raw)>receipt.MaxBytes{
  http.Error(w,"HUB receipt encoding unavailable",http.StatusServiceUnavailable)
  return
 }
 w.Header().Set("Content-Type","application/json")
 w.WriteHeader(status)
 _,_=w.Write(raw)
}

