// Sensor is an opt-in, one-shot reporter, NOT a network-facing honeypot.
package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/gapspool"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

func main() {
	key := flag.String("key", "", "private.hex location")
	url := flag.String("hub", "http://127.0.0.1:8788/report", "loopback test HUB endpoint")
	kind := flag.String("kind", "http_probe", "event category")
	port := flag.Int("port", 80, "target port")
	fingerprint := flag.String("fingerprint", "demo-non-ip", "non-PII campaign characteristic; never send raw IP or payload")
	gapReason := flag.String("gap-reason", "", "report a strictly typed observation gap; never asserts healthy coverage")
	outboxPath := flag.String("gap-outbox", "", "absolute private spool path for durable signed gap; required with -gap-reason")
	retryGap := flag.Bool("retry-gap-outbox", false, "retry exact saved signed gap; never mint new event ID")
    flag.Parse()
	if *key == "" {
		panic("-key required")
	}
	raw, err := os.ReadFile(*key)
	if err != nil {
		panic(err)
	}
	priv, err := protocol.PrivateFromHex(strings.TrimSpace(string(raw)))
	if err != nil {
		panic(err)
	}
	pub := priv.Public().(ed25519.PublicKey)
	if *retryGap {
        if *outboxPath=="" || *gapReason!="" || *kind!="http_probe" || *port!=80 || *fingerprint!="demo-non-ip" {
            panic("retry requires -gap-outbox only; event content must not change")
        }
        if *url!="http://127.0.0.1:8788/report" {panic("loopback only")}
        if err:=gapspool.Dispatch(*outboxPath,pub,time.Now().UTC(),deliverLoopback);err!=nil{panic(err)}
        fmt.Println("signed gap acknowledged locally, not proof of healthy coverage")
        return
    }
    id, err := protocol.NewEventID()
	if err != nil {
		panic(err)
	}
	kindChosen, portChosen, fpChosen, err := selectReportClass(*kind, *port, *fingerprint, *gapReason)
    if err != nil { panic(err) }
	r := protocol.Report{Schema: protocol.ReportSchema, NodeID: protocol.NodeID(pub), EventID: id, ObservedAt: time.Now().UTC(), Kind: kindChosen, TargetPort: portChosen, CampaignFingerprint: fpChosen}
	if err = r.Validate(time.Now()); err != nil {
		panic(err)
	}
	sr, err := protocol.SignReport(r, priv)
	if err != nil {
		panic(err)
	}
	b, _ := json.Marshal(sr)
    if *gapReason!="" {
        if *outboxPath=="" {panic("signed gaps require a private durable -gap-outbox path")}
        if *url!="http://127.0.0.1:8788/report" {panic("loopback endpoint only")}
        if err:=gapspool.Enqueue(*outboxPath,sr,pub,time.Now().UTC());err!=nil{panic(err)}
        if err:=gapspool.Dispatch(*outboxPath,pub,time.Now().UTC(),deliverLoopback);err!=nil{panic(err)}
        fmt.Println("signed gap acknowledged locally, no automatic all-clear")
        return
    }
    if *outboxPath!="" {panic("-gap-outbox is only for signed coverage gaps")}
	// Demo intentionally refuses remote or public upload before TLS/consent controls are implemented.
	if *url != "http://127.0.0.1:8788/report" {
		panic("MVP permits loopback endpoint only")
	}
	client := &http.Client{Timeout: 5 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error {return http.ErrUseLastResponse}}
	resp, err := client.Post(*url, "application/json", bytes.NewReader(b))
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	reply, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
	fmt.Printf("status=%d response=%s\n", resp.StatusCode, string(reply))
	if resp.StatusCode != http.StatusAccepted {
		os.Exit(1)
	}
}

 // selectReportClass never emits an assertion of healthy coverage. A gap
 // categorically differs from a network event and has no target port.
func selectReportClass(kind string, port int, fingerprint, gapReason string) (string,int,string,error) {
    if gapReason == "" {
        if kind == protocol.CoverageGapKind {
            return "",0,"",fmt.Errorf("coverage_gap requires -gap-reason")
        }
        h := sha256.Sum256([]byte(fingerprint))
        return kind,port,hex.EncodeToString(h[:]),nil
    }
    if kind != "http_probe" || port != 80 || fingerprint != "demo-non-ip" {
        return "",0,"",fmt.Errorf("observation gap cannot be combined with event options")
    }
    digest,err:=protocol.CoverageGapFingerprint(gapReason)
    if err!=nil{return "",0,"",err}
    return protocol.CoverageGapKind,0,digest,nil
}

func deliverLoopback(payload []byte)(int,[]byte,error){
    client:=&http.Client{
        Timeout:5*time.Second,
        CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse},
    }
    resp,err:=client.Post("http://127.0.0.1:8788/report","application/json",bytes.NewReader(payload))
    if err!=nil{return 0,nil,err}
    defer resp.Body.Close()
    ack,err:=io.ReadAll(io.LimitReader(resp.Body,1025))
    if err!=nil{return 0,nil,err}
    if len(ack)>1024{return 0,nil,fmt.Errorf("oversized HUB acknowledgment")}
    return resp.StatusCode,ack,nil
}
