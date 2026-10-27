// HUB accepts signed reports from explicitly allowlisted sensors. It does NOT
// decide that an IP is malicious, issue commands or publish defense rules.
package main

import (
	"crypto/ed25519"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

type server struct {
	mu     sync.Mutex
	keys   map[string]ed25519.PublicKey
	seen   map[string]bool
	count  map[string]int
	bucket time.Time
	ledger *os.File
}

func (s *server) report(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "method not allowed", 405)
		return
	}
	if r.Header.Get("Content-Type") != "application/json" {
		http.Error(w, "json required", 415)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 8192)
	defer r.Body.Close()
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var sr protocol.SignedReport
	if err := dec.Decode(&sr); err != nil {
		http.Error(w, "invalid report", 400)
		return
	}
	if err := dec.Decode(new(any)); err != io.EOF {
		http.Error(w, "extra data", 400)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	pub, ok := s.keys[sr.Report.NodeID]
	if !ok {
		http.Error(w, "not registered", 403)
		return
	}
	if err := protocol.VerifyReport(sr, pub, time.Now().UTC()); err != nil {
		http.Error(w, "rejected report", 403)
		return
	}
	if time.Since(s.bucket) > time.Minute {
		s.bucket = time.Now()
		s.count = map[string]int{}
	}
	if s.count[sr.Report.NodeID] >= 30 {
		http.Error(w, "rate limited", 429)
		return
	}
	id := sr.Report.NodeID + ":" + sr.Report.EventID
	if s.seen[id] {
		http.Error(w, "duplicate report", 409)
		return
	}
	entry, err := json.Marshal(sr)
	if err != nil {
		http.Error(w, "encode failed", 500)
		return
	}
	if _, err = s.ledger.Write(append(entry, '\n')); err != nil {
		http.Error(w, "storage unavailable", 503)
		return
	}
	if err = s.ledger.Sync(); err != nil {
		http.Error(w, "storage unavailable", 503)
		return
	}
	s.seen[id] = true
	s.count[sr.Report.NodeID]++
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(202)
	fmt.Fprintln(w, `{"status":"received_unverified"}`)
}
func main() {
	addr := flag.String("listen", "127.0.0.1:8788", "loopback listen address")
	keysFile := flag.String("allowlist", "allowlist.json", "map from node_id to Ed25519 public key hex")
	ledgerFile := flag.String("ledger", "ledger.jsonl", "local append-only evidence ledger")
	flag.Parse()
	if *addr != "127.0.0.1:8788" {
		log.Fatal("MVP only listens on 127.0.0.1:8788")
	}
	raw, err := os.ReadFile(*keysFile)
	if err != nil {
		log.Fatal(err)
	}
	var entries map[string]string
	if err = json.Unmarshal(raw, &entries); err != nil {
		log.Fatal(err)
	}
	keys := map[string]ed25519.PublicKey{}
	for id, h := range entries {
		pub, err := protocol.PublicFromHex(strings.TrimSpace(h))
		if err != nil || protocol.NodeID(pub) != id {
			log.Fatal("invalid allowlisted key ", id)
		}
		keys[id] = pub
	}
	f, err := os.OpenFile(*ledgerFile, os.O_CREATE|os.O_APPEND|os.O_RDWR, 0600)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()
	seen := map[string]bool{}
	if _, err = f.Seek(0, 0); err != nil {
		log.Fatal(err)
	}
	dec := json.NewDecoder(f)
	for {
		var sr protocol.SignedReport
		err := dec.Decode(&sr)
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Fatal("corrupt ledger: ", err)
		}
		seen[sr.Report.NodeID+":"+sr.Report.EventID] = true
	}
	if _, err = f.Seek(0, io.SeekEnd); err != nil {
		log.Fatal(err)
	}
	s := &server{keys: keys, seen: seen, count: map[string]int{}, bucket: time.Now(), ledger: f}
	mux := http.NewServeMux()
	mux.HandleFunc("/report", s.report)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			w.WriteHeader(405)
			return
		}
		fmt.Fprintln(w, "ok")
	})
	log.Println("HUB local-only MVP ready")
	srv := &http.Server{Addr: *addr, Handler: mux, ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 15 * time.Second, MaxHeaderBytes: 8192}
	log.Fatal(srv.ListenAndServe())
}
