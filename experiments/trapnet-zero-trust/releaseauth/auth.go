// Package releaseauth verifies Guardian public-beta artifacts using an independent
// release-signing key, distinct from the signer of informational warning feeds.
package releaseauth
import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "regexp"
 "sort"
 "time"
)
const Schema="trapnet.guardian-release.v1"
var versionPattern=regexp.MustCompile(`^v[0-9]+\.[0-9]+\.[0-9]+-beta\.[0-9]+// Package releaseauth verifies Guardian public-beta artifacts using an independent
// release-signing key, distinct from the signer of informational warning feeds.
package releaseauth
import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "regexp"
 "sort"
 "time"
)
const Schema="trapnet.guardian-release.v1"
var versionPattern=)
var expected=[]string{"guardian-linux-amd64","guardian-linux-arm64","guardian-windows-amd64.exe"}
type File struct{Name string `json:"name"`;SHA256 string `json:"sha256"`;Size int64 `json:"size"`}
type Manifest struct{Schema string `json:"schema"`;Release string `json:"release"`;IssuedAt time.Time `json:"issued_at"`;ExpiresAt time.Time `json:"expires_at"`;Files []File `json:"files"`}
type Signed struct{Manifest Manifest `json:"manifest"`;Signature string `json:"signature"`}
func(m Manifest)Validate(now time.Time)error{
 if m.Schema!=Schema||!versionPattern.MatchString(m.Release){return errors.New("invalid release metadata")}
 if m.IssuedAt.IsZero()||m.IssuedAt.After(now.Add(2*time.Minute))||m.ExpiresAt.IsZero()||!m.ExpiresAt.After(now)||!m.ExpiresAt.After(m.IssuedAt)||m.ExpiresAt.After(m.IssuedAt.Add(30*24*time.Hour)){return errors.New("expired or future release metadata")}
 if len(m.Files)!=3{return errors.New("bundle must contain three platforms")}
 names:=make([]string,0,3)
 for _,f:=range m.Files{
  if len(f.SHA256)!=64{return errors.New("invalid file digest length")}
  b,e:=hex.DecodeString(f.SHA256);if e!=nil||len(b)!=sha256.Size||hex.EncodeToString(b)!=f.SHA256{return errors.New("invalid file digest")}
  if f.Size<=0||f.Size>32*1024*1024{return errors.New("invalid file size")}
  names=append(names,f.Name)
 }
 sort.Strings(names)
 for i,n:=range expected{if names[i]!=n{return errors.New("unexpected filename or duplicate")}}
 return nil
}
func Sign(m Manifest,secret ed25519.PrivateKey,now time.Time)(Signed,error){
 if err:=m.Validate(now);err!=nil{return Signed{},err}
 body,err:=json.Marshal(m);if err!=nil{return Signed{},err}
 return Signed{Manifest:m,Signature:hex.EncodeToString(ed25519.Sign(secret,body))},nil
}
func Verify(s Signed,pub ed25519.PublicKey,now time.Time)error{
 if err:=s.Manifest.Validate(now);err!=nil{return err}
 sig,err:=hex.DecodeString(s.Signature);if err!=nil||len(sig)!=ed25519.SignatureSize{return errors.New("malformed release signature")}
 body,err:=json.Marshal(s.Manifest);if err!=nil{return err}
 if !ed25519.Verify(pub,body,sig){return errors.New("release signature invalid")}
 return nil
}
func VerifyBundle(s Signed,pub ed25519.PublicKey,dir string,now time.Time)error{
 if err:=Verify(s,pub,now);err!=nil{return err}
 base,err:=os.Lstat(dir);if err!=nil{return err}
 if !base.IsDir()||base.Mode()&os.ModeSymlink!=0{return errors.New("unsafe release directory")}
 entries,err:=os.ReadDir(dir);if err!=nil{return err}
 if len(entries)!=3{return errors.New("unexpected extra files in release directory")}
 for _,f:=range s.Manifest.Files{
  path:=filepath.Join(dir,f.Name)
  info,err:=os.Lstat(path);if err!=nil{return err}
  if !info.Mode().IsRegular()||info.Size()!=f.Size{return fmt.Errorf("unsafe release file %s",f.Name)}
  file,err:=os.Open(path);if err!=nil{return err}
  opened,err:=file.Stat();if err!=nil{file.Close();return err}
  if !os.SameFile(info,opened){file.Close();return errors.New("path changed while opening")}
  h:=sha256.New();size,err:=io.Copy(h,io.LimitReader(file,32*1024*1024+1));file.Close();if err!=nil{return err}
  if size!=f.Size||hex.EncodeToString(h.Sum(nil))!=f.SHA256{return fmt.Errorf("binary altered: %s",f.Name)}
  after,err:=os.Lstat(path);if err!=nil{return err}
  if !os.SameFile(info,after){return errors.New("release file replaced during verification")}
 }
 return nil
}
