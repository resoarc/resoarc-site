// Package witness verifies externally notarized snapshot copies of TrapNet HUB
// evidence. The signing private key and history MUST remain off-HUB.
package witness

import (
 "bufio"
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "regexp"
 "time"
)

const Schema="trapnet.witness.v0.1"
const maxLedgerRow=65536
const maxHistoryRow=4096
const zeroDigest="0000000000000000000000000000000000000000000000000000000000000000"
var digestRE=regexp.MustCompile(\`^[0-9a-f]{64}$\`)

type Head struct {Revision int \`json:"revision"\`; Rows uint64 \`json:"rows"\`; Digest string \`json:"digest"\`}
type Checkpoint struct {
 Schema string \`json:"schema"\`
 Sequence uint64 \`json:"sequence"\`
 Rows uint64 \`json:"rows"\`
 Digest string \`json:"digest"\`
 ObservedAt time.Time \`json:"observed_at"\`
 PreviousHash string \`json:"previous_hash"\`
}
type SignedCheckpoint struct {Checkpoint Checkpoint \`json:"checkpoint"\`; Signature string \`json:"signature"\`}

func Hash(s SignedCheckpoint)(string,error){
 b,err:=json.Marshal(s);if err!=nil{return "",err}
 d:=sha256.Sum256(b);return hex.EncodeToString(d[:]),nil
}
func Sign(c Checkpoint,priv ed25519.PrivateKey)(SignedCheckpoint,error){
 if len(priv)!=ed25519.PrivateKeySize{return SignedCheckpoint{},errors.New("invalid private key")}
 b,err:=json.Marshal(c);if err!=nil{return SignedCheckpoint{},err}
 return SignedCheckpoint{Checkpoint:c,Signature:hex.EncodeToString(ed25519.Sign(priv,b))},nil
}
func Verify(s SignedCheckpoint,pub ed25519.PublicKey)error{
 if len(pub)!=ed25519.PublicKeySize{return errors.New("invalid witness key")}
 c:=s.Checkpoint
 if c.Schema!=Schema||c.Sequence==0||!digestRE.MatchString(c.Digest)||!digestRE.MatchString(c.PreviousHash)||c.ObservedAt.IsZero()||!c.ObservedAt.Equal(c.ObservedAt.UTC()){return errors.New("malformed witness checkpoint")}
 if c.Rows==0&&c.Digest!=zeroDigest{return errors.New("invalid empty checkpoint")}
 sig,err:=hex.DecodeString(s.Signature);if err!=nil||len(sig)!=ed25519.SignatureSize{return errors.New("bad witness signature encoding")}
 b,err:=json.Marshal(c);if err!=nil{return err}
 if !ed25519.Verify(pub,b,sig){return errors.New("witness signature invalid")}
 return nil
}
func regularFile(path string,optional bool)error{
 fi,err:=os.Lstat(path);if optional&&errors.Is(err,os.ErrNotExist){return err}
 if err!=nil{return err};if !fi.Mode().IsRegular(){return fmt.Errorf("not a regular file: %s",path)};return nil
}
func strictJSON(b []byte,value any)error{
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 if err:=d.Decode(value);err!=nil{return err}
 if err:=d.Decode(new(any));err!=io.EOF{return errors.New("extra data")};return nil
}
// Measure uses the same chained SHA-256 algorithm as HUB v0.3.
// The ledger must be a stable, offline snapshot. Never audit live files.
func Measure(path string,checkpoints []SignedCheckpoint)(Head,error){
 if err:=regularFile(path,false);err!=nil{return Head{},err}
 f,err:=os.Open(path);if err!=nil{return Head{},err};defer f.Close()
 reader:=bufio.NewReader(f);h:=Head{Revision:1,Digest:zeroDigest};position:=0
 for {
  row,readErr:=reader.ReadBytes('\n')
  if readErr==io.EOF&&len(row)==0{break}
  if readErr!=nil||len(row)==0||len(row)>maxLedgerRow||row[len(row)-1]!='\n'{return Head{},errors.New("truncated or oversized ledger row")}
  if !json.Valid(bytes.TrimSuffix(row,[]byte{'\n'})){return Head{},errors.New("invalid ledger JSON")}
  old,err:=hex.DecodeString(h.Digest);if err!=nil{return Head{},err}
  data:=make([]byte,0,32+8+len(row));data=append(data,old...)
  var sz [8]byte;binary.BigEndian.PutUint64(sz[:],uint64(len(row)))
  data=append(data,sz[:]...);data=append(data,row...)
  dig:=sha256.Sum256(data);h.Rows++;h.Digest=hex.EncodeToString(dig[:])
  for position<len(checkpoints)&&checkpoints[position].Checkpoint.Rows==h.Rows{
   if checkpoints[position].Checkpoint.Digest!=h.Digest{return Head{},fmt.Errorf("witness mismatch at row %d",h.Rows)}
   position++
  }
 }
 if h.Rows==0{for position<len(checkpoints)&&checkpoints[position].Checkpoint.Rows==0{
  if checkpoints[position].Checkpoint.Digest!=zeroDigest{return Head{},errors.New("invalid empty witness")};position++
 }}
 if position!=len(checkpoints){return Head{},errors.New("missing witnessed rows")}
 return h,nil
}
func Snapshot(ledgerPath string,checkpoints []SignedCheckpoint)(Head,error){
 measured,err:=Measure(ledgerPath,checkpoints);if err!=nil{return Head{},err}
 headPath:=ledgerPath+".head";if err=regularFile(headPath,false);err!=nil{return Head{},err}
 b,err:=os.ReadFile(headPath);if err!=nil{return Head{},err};if len(b)>256{return Head{},errors.New("checkpoint oversized")}
 var head Head;if err=strictJSON(b,&head);err!=nil{return Head{},err}
 if head!=measured{return Head{},errors.New("local HUB checkpoint mismatches snapshot")}
 return measured,nil
}
func ReadHistory(path string,pub ed25519.PublicKey)([]SignedCheckpoint,error){
 if err:=regularFile(path,false);err!=nil{return nil,err}
 f,err:=os.Open(path);if err!=nil{return nil,err};defer f.Close()
 reader:=bufio.NewReader(f);var history []SignedCheckpoint
 prevHash:=zeroDigest;var prev Checkpoint
 for{
  line,readErr:=reader.ReadBytes('\n')
  if readErr==io.EOF&&len(line)==0{break}
  if readErr!=nil||len(line)==0||len(line)>maxHistoryRow||line[len(line)-1]!='\n'{return nil,errors.New("incomplete witness history")}
  var s SignedCheckpoint
  if err:=strictJSON(bytes.TrimSuffix(line,[]byte{'\n'}),&s);err!=nil{return nil,err}
  if err:=Verify(s,pub);err!=nil{return nil,err}
  c:=s.Checkpoint
  if c.Sequence!=uint64(len(history)+1)||c.PreviousHash!=prevHash{return nil,errors.New("history chain broken")}
  if len(history)>0&&(c.Rows<=prev.Rows||!c.ObservedAt.After(prev.ObservedAt)){return nil,errors.New("history is not monotonic")}
  prevHash,err=Hash(s);if err!=nil{return nil,err}
  prev=c;history=append(history,s)
 }
 return history,nil
}
// Audit checks signatures, per-row historical commitments, and local snapshot.
// An expectedTip from an independent channel prevents history rollback.
func Audit(ledgerPath,historyPath string,pub ed25519.PublicKey,expectedTip string)(Head,string,error){
 history,err:=ReadHistory(historyPath,pub);if err!=nil{return Head{},"",err}
 if len(history)==0{return Head{},"",errors.New("witness history empty")}
 tip,err:=Hash(history[len(history)-1]);if err!=nil{return Head{},"",err}
 if expectedTip!=""&&tip!=expectedTip{return Head{},"",errors.New("independently pinned witness tip mismatch")}
 measured,err:=Snapshot(ledgerPath,history);if err!=nil{return Head{},"",err}
 return measured,tip,nil
}
// Attest signs only after checking a copied ledger and all previous witnesses.
// Run on an independent offline machine, never on the production HUB.
func Attest(ledgerPath,historyPath string,priv ed25519.PrivateKey,now time.Time)(SignedCheckpoint,string,error){
 if len(priv)!=ed25519.PrivateKeySize{return SignedCheckpoint{},"",errors.New("invalid key")}
 lock:=historyPath+".lock"
 lf,err:=os.OpenFile(lock,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return SignedCheckpoint{},"",fmt.Errorf("witness lock held: %w",err)}
 if err=lf.Close();err!=nil{return SignedCheckpoint{},"",err}
 defer os.Remove(lock)
 pub:=priv.Public().(ed25519.PublicKey)
 var history []SignedCheckpoint
 if err=regularFile(historyPath,true);err==nil{
  history,err=ReadHistory(historyPath,pub);if err!=nil{return SignedCheckpoint{},"",err}
 }else if !errors.Is(err,os.ErrNotExist){return SignedCheckpoint{},"",err}
 head,err:=Snapshot(ledgerPath,history);if err!=nil{return SignedCheckpoint{},"",err}
 if head.Rows==0{return SignedCheckpoint{},"",errors.New("empty ledger cannot be attested")}
 prevHash:=zeroDigest
 if len(history)>0{
  prev:=history[len(history)-1]
  if head.Rows<=prev.Checkpoint.Rows||!now.UTC().After(prev.Checkpoint.ObservedAt){return SignedCheckpoint{},"",errors.New("witness rows and time must advance")}
  prevHash,err=Hash(prev);if err!=nil{return SignedCheckpoint{},"",err}
 }
 c:=Checkpoint{Schema:Schema,Sequence:uint64(len(history)+1),Rows:head.Rows,Digest:head.Digest,ObservedAt:now.UTC(),PreviousHash:prevHash}
 signed,err:=Sign(c,priv);if err!=nil{return SignedCheckpoint{},"",err}
 b,err:=json.Marshal(signed);if err!=nil{return SignedCheckpoint{},"",err}
 if err=regularFile(historyPath,true);err!=nil&&!errors.Is(err,os.ErrNotExist){return SignedCheckpoint{},"",err}
 hf,err:=os.OpenFile(historyPath,os.O_CREATE|os.O_APPEND|os.O_WRONLY,0600);if err!=nil{return SignedCheckpoint{},"",err}
 n,writeErr:=hf.Write(append(b,'\n'));if writeErr==nil&&n!=len(b)+1{writeErr=io.ErrShortWrite}
 if writeErr==nil{writeErr=hf.Sync()};closeErr:=hf.Close()
 if writeErr!=nil{return SignedCheckpoint{},"",writeErr};if closeErr!=nil{return SignedCheckpoint{},"",closeErr}
 hash,err:=Hash(signed);return signed,hash,err
}
func ReadPrivateKey(path string)(ed25519.PrivateKey,error){
 if err:=regularFile(path,false);err!=nil{return nil,err}
 b,err:=os.ReadFile(path);if err!=nil{return nil,err}
 decoded,err:=hex.DecodeString(string(bytes.TrimSpace(b)))
 if err!=nil||len(decoded)!=ed25519.PrivateKeySize{return nil,errors.New("invalid private key")}
 return ed25519.PrivateKey(decoded),nil
}
func ReadPublicKey(path string)(ed25519.PublicKey,error){
 if err:=regularFile(path,false);err!=nil{return nil,err}
 b,err:=os.ReadFile(path);if err!=nil{return nil,err}
 decoded,err:=hex.DecodeString(string(bytes.TrimSpace(b)))
 if err!=nil||len(decoded)!=ed25519.PublicKeySize{return nil,errors.New("invalid public key")}
 return ed25519.PublicKey(decoded),nil
}
func CheckOffHostInputs(ledgerPath,historyPath,privatePath string)error{
 lp,_:=filepath.Abs(ledgerPath);hp,_:=filepath.Abs(historyPath);kp,_:=filepath.Abs(privatePath)
 if lp==hp||lp==kp||hp==kp{return errors.New("paths must be distinct")};return nil
}
