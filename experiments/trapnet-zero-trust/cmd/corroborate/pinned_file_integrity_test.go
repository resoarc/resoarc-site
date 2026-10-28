package main
import(
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "runtime"
 "testing"
)
func testDigest(b []byte)string{d:=sha256.Sum256(b);return hex.EncodeToString(d[:])}
func TestPinnedSymlinkRejected(t *testing.T){
 d:=t.TempDir();path:=filepath.Join(d,"trusted.json")
 b:=[]byte("test");if err:=os.WriteFile(path,b,0600);err!=nil{t.Fatal(err)}
 link:=filepath.Join(d,"linked.json")
 if err:=os.Symlink(path,link);err!=nil{if runtime.GOOS=="windows"{t.Skip("symlink unavailable")};t.Fatal(err)}
 f,err:=openPinnedRegular(link,testDigest(b),1024)
 if f!=nil{f.Close()}
 if err==nil{t.Fatal("accepted symlinked evidence")}
}
func TestPinnedReplacedPathRejected(t *testing.T){
 d:=t.TempDir();path:=filepath.Join(d,"ledger.jsonl");b:=[]byte("test\n")
 if err:=os.WriteFile(path,b,0600);err!=nil{t.Fatal(err)}
 f,err:=openPinnedRegular(path,testDigest(b),1024);if err!=nil{t.Fatal(err)};defer f.Close()
 alt:=filepath.Join(d,"replacement")
 if err:=os.WriteFile(alt,b,0600);err!=nil{t.Fatal(err)}
 if err:=os.Rename(alt,path);err!=nil{if runtime.GOOS=="windows"{t.Skip("Windows prohibits rename over opened file")};t.Fatal(err)}
 if err:=verifySamePath(f,path);err==nil{t.Fatal("replaced pathname accepted")}
}
func TestPinnedInPlaceMutationRejected(t *testing.T){
 d:=t.TempDir();path:=filepath.Join(d,"ledger.jsonl");b:=[]byte("test\n")
 if err:=os.WriteFile(path,b,0600);err!=nil{t.Fatal(err)}
 f,err:=openPinnedRegular(path,testDigest(b),1024);if err!=nil{t.Fatal(err)};defer f.Close()
 if err:=os.WriteFile(path,[]byte("bad!\n"),0600);err!=nil{t.Fatal(err)}
 if err:=verifyFile(f,testDigest(b),1024);err==nil{t.Fatal("mutated evidence accepted")}
}
func TestPinnedDirectoryRejected(t *testing.T){
 f,err:=openPinnedRegular(t.TempDir(),testDigest(nil),1024)
 if f!=nil{f.Close()}
 if err==nil{t.Fatal("directory accepted as evidence")}
}
