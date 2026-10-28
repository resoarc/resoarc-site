package main
import(
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "path/filepath"
 "strings"
 "testing"
 "time"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)
func TestPolicyRevocationAndPersistedAntiRollback(t *testing.T){
 now:=time.Now().UTC();rootPub,rootPriv,_:=ed25519.GenerateKey(rand.Reader)
 oldPub,oldPriv,_:=ed25519.GenerateKey(rand.Reader);newPub,newPriv,_:=ed25519.GenerateKey(rand.Reader)
 policy:=func(version uint64,pub ed25519.PublicKey)protocol.SignedSignerPolicy{
  p:=protocol.FeedSignerPolicy{Schema:protocol.SignerPolicySchema,Version:version,IssuedAt:now,ExpiresAt:now.Add(time.Hour),SignerPublicKeys:[]string{hex.EncodeToString(pub)}}
  signed,err:=protocol.SignSignerPolicy(p,rootPriv);if err!=nil{t.Fatal(err)};return signed
 }
 feed:=func(version uint64,key ed25519.PrivateKey)protocol.SignedFeed{
  f:=protocol.Feed{Schema:protocol.FeedSchema,Version:version,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]protocol.Warning{{Category:"notice",Summary:"Test only"}}}
  sf,err:=protocol.SignFeed(f,key);if err!=nil{t.Fatal(err)};return sf
 }
 state:=filepath.Join(t.TempDir(),"state.json")
 p1:=policy(1,oldPub);f1:=feed(1,oldPriv)
 key,err:=protocol.VerifyFeedAgainstPolicy(f1,p1,rootPub,now);if err!=nil{t.Fatal(err)}
 if err=verifyAndRecordWithPolicy(f1,key,&p1,state,now);err!=nil{t.Fatal(err)}
 p2:=policy(2,newPub);f2:=feed(2,newPriv)
 key,err=protocol.VerifyFeedAgainstPolicy(f2,p2,rootPub,now);if err!=nil{t.Fatal(err)}
 if err=verifyAndRecordWithPolicy(f2,key,&p2,state,now);err!=nil{t.Fatal(err)}
 if _,err=protocol.VerifyFeedAgainstPolicy(feed(3,oldPriv),p2,rootPub,now);err==nil{t.Fatal("revoked signer still accepted")}
 if err=verifyAndRecordWithPolicy(f1,oldPub,&p1,state,now);err==nil||!strings.Contains(err.Error(),"rollback"){t.Fatal("old signer policy rollback accepted")}
 if err=verifyAndRecord(f2,newPub,state,now);err==nil{t.Fatal("legacy -pub bypassed root pin")}
 altered:=policy(2,oldPub)
 if err=verifyAndRecordWithPolicy(f1,oldPub,&altered,state,now);err==nil||!strings.Contains(err.Error(),"equivocation"){t.Fatal("same version altered policy accepted")}
}
func TestLegacyStateCannotSilentlyBecomeBeta(t *testing.T){
 now:=time.Now().UTC();signerPub,priv,_:=ed25519.GenerateKey(rand.Reader);_,rootPriv,_:=ed25519.GenerateKey(rand.Reader)
 state:=filepath.Join(t.TempDir(),"legacy.json")
 feed:=protocol.Feed{Schema:protocol.FeedSchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]protocol.Warning{{Category:"notice",Summary:"test"}}}
 sf,_:=protocol.SignFeed(feed,priv)
 if err:=verifyAndRecord(sf,signerPub,state,now);err!=nil{t.Fatal(err)}
 p,_:=protocol.SignSignerPolicy(protocol.FeedSignerPolicy{Schema:protocol.SignerPolicySchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),SignerPublicKeys:[]string{hex.EncodeToString(signerPub)}},rootPriv)
 if err:=verifyAndRecordWithPolicy(sf,signerPub,&p,state,now);err==nil{t.Fatal("unreviewed legacy state migrated automatically")}
}
