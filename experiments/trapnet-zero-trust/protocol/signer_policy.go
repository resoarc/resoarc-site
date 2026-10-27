package protocol

import (
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "sort"
 "time"
)
const SignerPolicySchema = "trapnet.signer-policy.v1"
type FeedSignerPolicy struct {
 Schema string `json:"schema"`
 Version uint64 `json:"version"`
 IssuedAt time.Time `json:"issued_at"`
 ExpiresAt time.Time `json:"expires_at"`
 SignerPublicKeys []string `json:"signer_public_keys"`
}
type SignedSignerPolicy struct {
 Policy FeedSignerPolicy `json:"policy"`
 Signature string `json:"signature"`
}
func (p FeedSignerPolicy) Validate(now time.Time) error {
 if p.Schema!=SignerPolicySchema||p.Version==0{return errors.New("invalid signer policy schema or version")}
 if p.IssuedAt.IsZero()||p.ExpiresAt.IsZero()||p.IssuedAt.After(now.Add(2*time.Minute))||!p.ExpiresAt.After(now)||!p.ExpiresAt.After(p.IssuedAt)||p.ExpiresAt.After(p.IssuedAt.Add(30*24*time.Hour)){return errors.New("signer policy invalid or expired")}
 if len(p.SignerPublicKeys)<1||len(p.SignerPublicKeys)>8{return errors.New("invalid signer allowlist size")}
 if !sort.StringsAreSorted(p.SignerPublicKeys){return errors.New("signer allowlist must be sorted")}
 last:=""
 for _,v:=range p.SignerPublicKeys{
  if len(v)!=64||!hex64.MatchString(v)||v==last{return errors.New("invalid or duplicate signer public key")}
  if _,err:=PublicFromHex(v);err!=nil{return err}
  last=v
 }
 return nil
}
func SignSignerPolicy(p FeedSignerPolicy,priv ed25519.PrivateKey)(SignedSignerPolicy,error){
 b,err:=json.Marshal(p);if err!=nil{return SignedSignerPolicy{},err}
 return SignedSignerPolicy{Policy:p,Signature:hex.EncodeToString(ed25519.Sign(priv,b))},nil
}
func VerifySignerPolicy(p SignedSignerPolicy,root ed25519.PublicKey,now time.Time)error{
 if err:=p.Policy.Validate(now);err!=nil{return err}
 sig,err:=hex.DecodeString(p.Signature);if err!=nil||len(sig)!=ed25519.SignatureSize{return errors.New("invalid signer policy signature encoding")}
 b,err:=json.Marshal(p.Policy);if err!=nil{return err}
 if !ed25519.Verify(root,b,sig){return errors.New("signer policy root signature failed")}
 return nil
}
func VerifyFeedAgainstPolicy(sf SignedFeed,p SignedSignerPolicy,root ed25519.PublicKey,now time.Time)(ed25519.PublicKey,error){
 if err:=VerifySignerPolicy(p,root,now);err!=nil{return nil,err}
 for _,key:=range p.Policy.SignerPublicKeys{
  pub,_:=PublicFromHex(key)
  if err:=VerifyFeed(sf,pub,now);err==nil{return pub,nil}
 }
 return nil,errors.New("feed not signed by a currently permitted signer")
}
