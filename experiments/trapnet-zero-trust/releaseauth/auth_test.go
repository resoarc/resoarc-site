package releaseauth
import(
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "testing"
 "time"
)
func TestSignedReleaseRejectsTampering(t *testing.T){
 now:=time.Now().UTC();pub,priv,_:=ed25519.GenerateKey(rand.Reader)
 dir:=t.TempDir();files:=[]File{}
 for _,name:=range expected{
  body:=[]byte("synthetic "+name)
  if err:=os.WriteFile(filepath.Join(dir,name),body,0600);err!=nil{t.Fatal(err)}
  sum:=sha256.Sum256(body);files=append(files,File{Name:name,SHA256:hex.EncodeToString(sum[:]),Size:int64(len(body))})
 }
 meta:=Manifest{Schema:Schema,Release:"v0.16.0-beta.1",SourceCommit:"0123456789abcdef0123456789abcdef01234567",IssuedAt:now,ExpiresAt:now.Add(time.Hour),Files:files}
 signed,err:=Sign(meta,priv,now);if err!=nil{t.Fatal(err)}
 if err:=VerifyBundle(signed,pub,dir,now);err!=nil{t.Fatal(err)}
 wrong,_,_:=ed25519.GenerateKey(rand.Reader)
 if err:=VerifyBundle(signed,wrong,dir,now);err==nil{t.Fatal("untrusted publisher key accepted")}
 altered:=signed;altered.Manifest.Release="v0.16.0-beta.2"
 if err:=VerifyBundle(altered,pub,dir,now);err==nil{t.Fatal("tampered release accepted")}
 if err:=VerifyBundle(signed,pub,dir,now.Add(2*time.Hour));err==nil{t.Fatal("expired release accepted")}
 if err:=os.WriteFile(filepath.Join(dir,expected[0]),[]byte("bad"),0600);err!=nil{t.Fatal(err)}
 if err:=VerifyBundle(signed,pub,dir,now);err==nil{t.Fatal("binary mutation accepted")}
}
func TestReleaseUnexpectedFilesAndSymlinkRefused(t *testing.T){
 now:=time.Now().UTC();pub,priv,_:=ed25519.GenerateKey(rand.Reader);dir:=t.TempDir();files:=[]File{}
 for _,name:=range expected{
  content:=[]byte("bytes")
  if err:=os.WriteFile(filepath.Join(dir,name),content,0600);err!=nil{t.Fatal(err)}
  sum:=sha256.Sum256(content);files=append(files,File{Name:name,SHA256:hex.EncodeToString(sum[:]),Size:int64(len(content))})
 }
 signed,err:=Sign(Manifest{Schema:Schema,Release:"v0.16.0-beta.1",SourceCommit:"0123456789abcdef0123456789abcdef01234567",IssuedAt:now,ExpiresAt:now.Add(time.Hour),Files:files},priv,now)
 if err!=nil{t.Fatal(err)}
 os.WriteFile(filepath.Join(dir,"extra"),[]byte("bad"),0600)
 if err:=VerifyBundle(signed,pub,dir,now);err==nil{t.Fatal("extra file accepted")}
 os.Remove(filepath.Join(dir,"extra"))
 os.Remove(filepath.Join(dir,expected[1]))
 if err:=os.Symlink(filepath.Join(dir,expected[0]),filepath.Join(dir,expected[1]));err==nil{
  if err:=VerifyBundle(signed,pub,dir,now);err==nil{t.Fatal("symlink accepted")}
 }
}
func TestReleaseVersionMustMatchExactFormat(t *testing.T){
 m:=Manifest{Schema:Schema,Release:"v0x16x0-betaX1",IssuedAt:time.Now(),ExpiresAt:time.Now().Add(time.Hour),
 Files:[]File{{Name:expected[0],SHA256:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",Size:1},
 {Name:expected[1],SHA256:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",Size:1},
 {Name:expected[2],SHA256:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",Size:1}}}
 if m.Validate(time.Now())==nil{t.Fatal("loose release regex accepted")}
}

func TestSignedReleaseSourceRevisionMandatory(t *testing.T){
 now:=time.Now().UTC()
 m:=Manifest{Schema:Schema,Release:"v0.16.0-beta.1",IssuedAt:now,ExpiresAt:now.Add(time.Hour)}
 if m.Validate(now)==nil{t.Fatal("unsigned source identity omission accepted")}
 m.SourceCommit="NOT-A-REAL-COMMIT"
 if m.Validate(now)==nil{t.Fatal("malformed source identity accepted")}
}
