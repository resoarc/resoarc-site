package protocol
import(
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "testing"
 "time"
)
func TestRootSignerPolicyRejectsTamperAndExpiry(t *testing.T){
 now:=time.Now().UTC()
 rootPub,rootPriv,_:=ed25519.GenerateKey(rand.Reader)
 signerPub,signerPriv,_:=ed25519.GenerateKey(rand.Reader)
 x:=FeedSignerPolicy{Schema:SignerPolicySchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),SignerPublicKeys:[]string{hex.EncodeToString(signerPub)}}
 signed,_:=SignSignerPolicy(x,rootPriv)
 if err:=VerifySignerPolicy(signed,rootPub,now);err!=nil{t.Fatal(err)}
 sf,_:=SignFeed(Feed{Schema:FeedSchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]Warning{{Category:"notice",Summary:"Test message"}}},signerPriv)
 if _,err:=VerifyFeedAgainstPolicy(sf,signed,rootPub,now);err!=nil{t.Fatal(err)}
 corrupt:=signed;corrupt.Policy.Version++
 if err:=VerifySignerPolicy(corrupt,rootPub,now);err==nil{t.Fatal("tampered policy accepted")}
 unknown,_,_:=ed25519.GenerateKey(rand.Reader)
 if err:=VerifySignerPolicy(signed,unknown,now);err==nil{t.Fatal("untrusted root accepted")}
 if err:=VerifySignerPolicy(signed,rootPub,now.Add(2*time.Hour));err==nil{t.Fatal("expired policy accepted")}
 duplicate:=x;duplicate.SignerPublicKeys=[]string{hex.EncodeToString(signerPub),hex.EncodeToString(signerPub)}
 if err:=duplicate.Validate(now);err==nil{t.Fatal("duplicate key accepted")}
}
