package main
import (
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
func TestRootIdentityPinRejectsValidlySignedReplacement(t *testing.T){
 now:=time.Now().UTC()
 root,rootKey,_:=ed25519.GenerateKey(rand.Reader)
 fakeRoot,fakeKey,_:=ed25519.GenerateKey(rand.Reader)
 old,oldKey,_:=ed25519.GenerateKey(rand.Reader)
 next,nextKey,_:=ed25519.GenerateKey(rand.Reader)
 makePolicy:=func(v uint64,priv ed25519.PrivateKey,pub ed25519.PublicKey)protocol.SignedSignerPolicy{
  p:=protocol.FeedSignerPolicy{Schema:protocol.SignerPolicySchema,Version:v,IssuedAt:now,ExpiresAt:now.Add(time.Hour),SignerPublicKeys:[]string{hex.EncodeToString(pub)}}
  signed,err:=protocol.SignSignerPolicy(p,priv);if err!=nil{t.Fatal(err)};return signed
 }
 makeFeed:=func(v uint64,priv ed25519.PrivateKey)protocol.SignedFeed{
  p:=protocol.Feed{Schema:protocol.FeedSchema,Version:v,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]protocol.Warning{{Category:"notice",Summary:"test"}}}
  signed,err:=protocol.SignFeed(p,priv);if err!=nil{t.Fatal(err)};return signed
 }
 state:=filepath.Join(t.TempDir(),"state.json")
 p1:=makePolicy(1,rootKey,old);f1:=makeFeed(1,oldKey)
 if err:=verifyAndRecordWithPolicyTrust(f1,old,&p1,root,state,now);err!=nil{t.Fatal(err)}
 content,_:=os.ReadFile(state);var stored guardianState
 if err:=json.Unmarshal(content,&stored);err!=nil{t.Fatal(err)}
 fp:=sha256.Sum256(root)
 if stored.RootDigest!=hex.EncodeToString(fp[:]){t.Fatal("Root was not pinned")}
 badPolicy:=makePolicy(2,fakeKey,next);f2:=makeFeed(2,nextKey)
 if err:=protocol.VerifySignerPolicy(badPolicy,fakeRoot,now);err!=nil{t.Fatal(err)}
 if err:=verifyAndRecordWithPolicyTrust(f2,next,&badPolicy,fakeRoot,state,now);err==nil||!strings.Contains(err.Error(),"Root mismatch"){t.Fatalf("substituted Root accepted: %v",err)}
 if err:=verifyAndRecordWithPolicy(f2,next,&badPolicy,state,now);err==nil{t.Fatal("rootless policy bypass accepted")}
 if err:=verifyAndRecord(f2,next,state,now);err==nil{t.Fatal("legacy mode bypass accepted")}
 p2:=makePolicy(2,rootKey,next)
 if err:=verifyAndRecordWithPolicyTrust(f2,next,&p2,root,state,now);err!=nil{t.Fatal("legitimate signer rotation blocked:",err)}
 if err:=verifyAndRecordWithPolicyTrust(f1,old,&p1,root,state,now);err==nil{t.Fatal("old signer policy accepted")}
}
func TestUnpinnedRootStateRequiresExplicitMigration(t *testing.T){
 now:=time.Now().UTC()
 root,key,_:=ed25519.GenerateKey(rand.Reader)
 signer,secret,_:=ed25519.GenerateKey(rand.Reader)
 p,_:=protocol.SignSignerPolicy(protocol.FeedSignerPolicy{Schema:protocol.SignerPolicySchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),SignerPublicKeys:[]string{hex.EncodeToString(signer)}},key)
 f,_:=protocol.SignFeed(protocol.Feed{Schema:protocol.FeedSchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]protocol.Warning{{Category:"notice",Summary:"test"}}},secret)
 path:=filepath.Join(t.TempDir(),"legacy.json")
 if err:=verifyAndRecordWithPolicy(f,signer,&p,path,now);err!=nil{t.Fatal(err)}
 if err:=verifyAndRecordWithPolicyTrust(f,signer,&p,root,path,now);err==nil{t.Fatal("silent Root adoption accepted")}
}
