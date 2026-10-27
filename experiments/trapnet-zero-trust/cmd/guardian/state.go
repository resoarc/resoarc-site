package main

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "time"

 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

type guardianState struct {
 Version uint64 `json:"version"`
 Digest string `json:"digest"`
}

// verifyAndRecord never executes feed data. A signed same-version payload
// with different content is equivocation, not an update.
func verifyAndRecord(sf protocol.SignedFeed,pub ed25519.PublicKey,statePath string,now time.Time)error{
 if err:=protocol.VerifyFeed(sf,pub,now);err!=nil{return err}
 feedBody,err:=json.Marshal(sf.Feed)
 if err!=nil{return err}
 sum:=sha256.Sum256(feedBody)
 digest:=hex.EncodeToString(sum[:])
 state:=guardianState{}
 info,err:=os.Lstat(statePath)
 if err==nil{
  if !info.Mode().IsRegular(){return errors.New("state is not a regular file")}
  b,err:=os.ReadFile(statePath)
  if err!=nil{return err}
  if err:=json.Unmarshal(b,&state);err!=nil{return fmt.Errorf("invalid state: %w",err)}
  if state.Version==0{return errors.New("invalid local version")}
  if state.Digest!="" && len(state.Digest)!=64{return errors.New("invalid stored digest")}
 }else if !os.IsNotExist(err){return err}
 if sf.Feed.Version<state.Version{return errors.New("feed rollback detected")}
 if sf.Feed.Version==state.Version{
  // Prior v0.1 state files have no hash; require a new version to migrate.
  if state.Digest=="" || state.Digest!=digest{return errors.New("feed equivocation or legacy state; require a newer version")}
  return nil
 }
 next:=guardianState{Version:sf.Feed.Version,Digest:digest}
 data,err:=json.Marshal(next)
 if err!=nil{return err}
 temp,err:=os.CreateTemp(filepath.Dir(statePath),".trapnet-state-*")
 if err!=nil{return err}
 defer os.Remove(temp.Name())
 if err:=temp.Chmod(0600);err!=nil{temp.Close();return err}
 if _,err:=temp.Write(data);err!=nil{temp.Close();return err}
 if err:=temp.Sync();err!=nil{temp.Close();return err}
 if err:=temp.Close();err!=nil{return err}
 if err:=os.Rename(temp.Name(),statePath);err!=nil{return err}
 return nil
}
