// Package gapspool provides an intentionally narrow local, durable, single-item
// outbox for signed TrapNet coverage-gap notices.
//
// An unacknowledged notice is never discarded or automatically replaced.
// Crash leftovers and ambiguous replies require operator attention.
// This is NOT a distributed queue, an authenticated HUB receipt, or a feed.
package gapspool

import (
 "bytes"
 "crypto/ed25519"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "strings"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

const MaxBytes=8192
const AckStatus="received_unverified"

type PostFunc func(payload []byte)(status int,ack []byte,err error)

func safeParent(path string) error {
 if path=="" || !filepath.IsAbs(path){return errors.New("absolute spool path required")}
 parent:=filepath.Dir(filepath.Clean(path))
 info,err:=os.Lstat(parent)
 if err!=nil{return err}
 if !info.IsDir() || info.Mode()&os.ModeSymlink!=0{
  return errors.New("unsafe spool parent directory")
 }
 if info.Mode().Perm()&0022!=0 {
  return errors.New("spool parent must not be writable by group/other")
 }
 return nil
}

func syncParent(path string) error {
 dir,err:=os.Open(filepath.Dir(path));if err!=nil{return err}
 defer dir.Close()
 return dir.Sync()
}

func acquire(path string)(func(),error){
 if err:=safeParent(path);err!=nil{return nil,err}
 lock:=path+".lock"
 file,err:=os.OpenFile(lock,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return nil,fmt.Errorf("outbox locked or unsafe: %w",err)}
 if err=file.Sync();err!=nil{
  file.Close()
  return nil,fmt.Errorf("cannot sync outbox lock: %w",err)
 }
 if err=file.Close();err!=nil{return nil,err}
 // Even a crash leaving a .lock must NOT silently clear an unverified notice.
 return func(){_ = os.Remove(lock)},nil
}

// Enqueue refuses a pre-existing notice. A caller must not replace the prior
// event ID or signature when the network outcome is ambiguous.
func Enqueue(path string,notice protocol.SignedReport,pub ed25519.PublicKey,now time.Time)error{
 unlock,err:=acquire(path);if err!=nil{return err};defer unlock()
 if notice.Report.Kind!=protocol.CoverageGapKind{return errors.New("only coverage gaps can be queued")}
 if err:=protocol.VerifyReport(notice,pub,now);err!=nil{return fmt.Errorf("invalid signed gap: %w",err)}
 encoded,err:=json.Marshal(notice);if err!=nil{return err}
 if len(encoded)>MaxBytes{return errors.New("gap payload too large")}
 file,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return fmt.Errorf("pending gap already exists or cannot be saved: %w",err)}
 // If writing fails, preserve the partial file. Recovery must fail closed.
 n,werr:=file.Write(encoded)
 if werr==nil && n!=len(encoded){werr=io.ErrShortWrite}
 if werr==nil{werr=file.Sync()}
 cerr:=file.Close()
 if werr!=nil{return fmt.Errorf("gap not durably staged: %w",werr)}
 if cerr!=nil{return cerr}
 if err:=syncParent(path);err!=nil{return fmt.Errorf("outbox directory not durable: %w",err)}
 return nil
}

func openPending(path string)(*os.File,os.FileInfo,[]byte,error){
 meta,err:=os.Lstat(path)
 if err!=nil{return nil,nil,nil,err}
 if !meta.Mode().IsRegular() || meta.Mode()&os.ModeSymlink!=0 || meta.Mode().Perm()&0077!=0{
  return nil,nil,nil,errors.New("unsafe pending gap file")
 }
 if meta.Size()<=0||meta.Size()>MaxBytes{return nil,nil,nil,errors.New("pending gap size invalid")}
 file,err:=os.Open(path);if err!=nil{return nil,nil,nil,err}
 actual,err:=file.Stat()
 if err!=nil{file.Close();return nil,nil,nil,err}
 if !os.SameFile(meta,actual) || !actual.Mode().IsRegular(){
  file.Close();return nil,nil,nil,errors.New("pending gap file changed while opening")
 }
 data,err:=io.ReadAll(io.LimitReader(file,MaxBytes+1))
 if err!=nil||len(data)>MaxBytes||len(data)==0{
  file.Close();return nil,nil,nil,errors.New("unable to read bounded pending gap")
 }
 return file,actual,data,nil
}

func strictlyAcceptedAck(status int,body []byte)bool{
 if status!=202||len(body)==0||len(body)>256{return false}
 dec:=json.NewDecoder(bytes.NewReader(body))
 opening,err:=dec.Token()
 if err!=nil || opening!=json.Delim('{'){return false}
 key,err:=dec.Token()
 if err!=nil || key!="status"{return false}
 value,err:=dec.Token()
 if err!=nil || value!=AckStatus{return false}
 closing,err:=dec.Token()
 if err!=nil || closing!=json.Delim('}'){return false}
 _,err=dec.Token()
 return err==io.EOF
}

// Dispatch resends the EXACT persisted report, never signs a new one.
// A 409 duplicate or any ambiguous reply remains pending (HOLD).
func Dispatch(path string,pub ed25519.PublicKey,now time.Time,post PostFunc)error{
 if post==nil{return errors.New("missing transport")}
 unlock,err:=acquire(path);if err!=nil{return err};defer unlock()
 file,meta,data,err:=openPending(path)
 if err!=nil{return fmt.Errorf("pending notice unavailable: %w",err)}
 defer file.Close()
 dec:=json.NewDecoder(bytes.NewReader(data))
 dec.DisallowUnknownFields()
 var notice protocol.SignedReport
 if err:=dec.Decode(&notice);err!=nil{return fmt.Errorf("invalid pending JSON: %w",err)}
 if err:=dec.Decode(new(any));err!=io.EOF{return errors.New("extra data in pending gap")}
 if notice.Report.Kind!=protocol.CoverageGapKind{return errors.New("not a coverage-gap notice")}
 if err:=protocol.VerifyReport(notice,pub,now);err!=nil{
  return fmt.Errorf("pending notice invalid, expired or signed by another key: %w",err)
 }
 // Only a one-shot explicit loopback caller may supply the post callback.
 status,ack,err:=post(append([]byte(nil),data...))
 if err!=nil{return fmt.Errorf("delivery unconfirmed: %w",err)}
 if !strictlyAcceptedAck(status,ack){
  return fmt.Errorf("HUB did not provide an unambiguous 202 acknowledgment (HTTP %d)",status)
 }
 latest,err:=os.Lstat(path);if err!=nil{return err}
 if !os.SameFile(meta,latest) || !latest.Mode().IsRegular() || latest.Size()!=meta.Size(){
  return errors.New("pending file replaced during delivery")
 }
 if _,err:=file.Seek(0,io.SeekStart);err!=nil{return err}
 persisted,err:=io.ReadAll(io.LimitReader(file,MaxBytes+1))
 if err!=nil || !bytes.Equal(persisted,data){
  return errors.New("pending file contents altered during delivery")
 }
 // Keep the pending notice on any failure. A 202 is meaningful only after
 // the HUB has fsynced its ledger/checkpoint, as implemented by the v0.1 HUB.
 if err:=os.Remove(path);err!=nil{return err}
 if err:=syncParent(path);err!=nil{return fmt.Errorf("delivered but local removal not durable: %w",err)}
 return nil
}

// Status deliberately never returns raw event data.
func Status(path string)string{
 if err:=safeParent(path);err!=nil{return "HOLD_INVALID_SPOOL"}
 info,err:=os.Lstat(path)
 if errors.Is(err,os.ErrNotExist){return "NO_PENDING_FILE_NOT_COVERAGE_PROOF"}
 if err!=nil||!info.Mode().IsRegular()||info.Size()>MaxBytes||info.Size()<=0||info.Mode().Perm()&0077!=0{
  return "HOLD_INVALID_PENDING"
 }
 if strings.TrimSpace(path)==""{return "HOLD_INVALID_SPOOL"}
 return "PENDING_UNCONFIRMED"
}
