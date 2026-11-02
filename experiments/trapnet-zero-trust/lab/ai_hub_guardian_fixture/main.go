// Lab-only ephemeral evidence for a real HUB/Guardian negative-boundary test.
// Generates short-lived Ed25519 keys in memory; never writes private keys.
package main

import (
  "crypto/ed25519"
  "crypto/rand"
  "encoding/hex"
  "encoding/json"
  "flag"
  "fmt"
  "os"
  "path/filepath"
  "strings"
  "time"

  "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
)

func check(err error) {
  if err != nil { panic("synthetic fixture unavailable") }
}
func store(dir, name string, value any) {
  b,err:=json.Marshal(value);check(err)
  check(os.WriteFile(filepath.Join(dir,name),append(b,'\n'),0600))
}
func main() {
  directory:=flag.String("out","","existing empty, private temporary lab directory")
  flag.Parse()
  if *directory=="" {panic("lab-only directory required")}
  info,err:=os.Stat(*directory);check(err)
  if !info.IsDir() {panic("expected lab directory")}
  entries,err:=os.ReadDir(*directory);check(err)
  if len(entries)!=0 {panic("directory must be empty")}
  pub,priv,err:=ed25519.GenerateKey(rand.Reader);check(err)
  otherPub,otherPriv,err:=ed25519.GenerateKey(rand.Reader);check(err)
  feedPub,feedPriv,err:=ed25519.GenerateKey(rand.Reader);check(err)
  otherFeedPub,otherFeedPriv,err:=ed25519.GenerateKey(rand.Reader);check(err)
  now:=time.Now().UTC()
  report:=protocol.Report{Schema:protocol.ReportSchema,NodeID:protocol.NodeID(pub),
    EventID:strings.Repeat("1",32),ObservedAt:now,Kind:"http_probe",TargetPort:443,
    CampaignFingerprint:strings.Repeat("a",64)}
  goodReport,err:=protocol.SignReport(report,priv);check(err)
  check(protocol.VerifyReport(goodReport,pub,now))
  store(*directory,"allowlist.json",map[string]string{protocol.NodeID(pub):hex.EncodeToString(pub)})
  store(*directory,"report_valid.json",goodReport)
  badReport:=goodReport
  badReport.Report.Kind="ai_command"
  store(*directory,"report_tampered.json",badReport)
  noSigReport:=goodReport
  noSigReport.Signature=""
  store(*directory,"report_unsigned.json",noSigReport)
  outsiderReport:=report
  outsiderReport.NodeID=protocol.NodeID(otherPub)
  outsiderReport.EventID=strings.Repeat("2",32)
  otherSignedReport,err:=protocol.SignReport(outsiderReport,otherPriv);check(err)
  store(*directory,"report_unregistered.json",otherSignedReport)

  feed:=protocol.Feed{Schema:protocol.FeedSchema,Version:1,IssuedAt:now,
    ExpiresAt:now.Add(1*time.Hour),
    Warnings:[]protocol.Warning{{Category:"notice",Summary:"Synthetic information only; no blocking permitted"}}}
  goodFeed,err:=protocol.SignFeed(feed,feedPriv);check(err)
  check(protocol.VerifyFeed(goodFeed,feedPub,now))
  check(os.WriteFile(filepath.Join(*directory,"feed_pub.hex"),[]byte(hex.EncodeToString(feedPub)+"\n"),0600))
  store(*directory,"feed_valid.json",goodFeed)
  tamperedFeed:=goodFeed
  tamperedFeed.Feed.Warnings=[]protocol.Warning{{Category:"notice",Summary:"Modified untrusted AI message"}}
  store(*directory,"feed_tampered.json",tamperedFeed)
  outsiderFeed,err:=protocol.SignFeed(feed,otherFeedPriv);check(err)
  store(*directory,"feed_untrusted_signer.json",outsiderFeed)
  badFeed:=goodFeed
  badFeed.Signature=""
  store(*directory,"feed_unsigned.json",badFeed)
  earlier:=feed
  earlier.Version=0 // well-formed cryptographic signature but disallowed version
  signedEarlier,err:=protocol.SignFeed(earlier,feedPriv);check(err)
  store(*directory,"feed_rollback.json",signedEarlier)
  fmt.Println("SYNTHETIC_SIGNED_FIXTURES=CREATED; EPHEMERAL_PRIVATE_KEYS_NOT_SAVED")
}
