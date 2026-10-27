// HUB accepts signed reports from explicitly allowlisted sensors. It does NOT
// decide that an IP is malicious, issue commands or publish defense rules.
package main

import (
	"bufio"
	"crypto/ed25519"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/archive"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
	"github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/witness"
)

const perNodeMinuteLimit = 30
const defaultLedgerMaxBytes int64 = 64 << 20 // 64 MiB; no automatic truncation

type ledgerEntry struct {
	ReceivedAt time.Time             `json:"received_at"`
	Evidence   protocol.SignedReport `json:"evidence"`
}

type server struct {
	mu                sync.Mutex
	keys              map[string]ed25519.PublicKey
	revoked           map[string]bool
	seen              map[string]bool
	recent            map[string][]time.Time
	ledger            *os.File
	maxLedgerBytes    int64
	head              ledgerHead
	poisoned          bool
	signedRevocations *signedRevocationSource
	now               func() time.Time
}

// restoreLedger maintains replay protection across restarts and reconstructs
// recent rate limits from HUB-receipt times, never sensor-asserted timestamps.
// Old v0.1 rows remain valid for replay tracking but cannot prove receipt time.
func restoreLedger(f *os.File, now time.Time) (map[string]bool, map[string][]time.Time, error) {
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return nil, nil, err
	}
	seen := make(map[string]bool)
	recent := make(map[string][]time.Time)
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 4096), 65536)
	for row := 1; scanner.Scan(); row++ {
		raw := scanner.Bytes()
		var entry ledgerEntry
		if err := json.Unmarshal(raw, &entry); err != nil {
			return nil, nil, fmt.Errorf("ledger line %d: %w", row, err)
		}
		if entry.ReceivedAt.IsZero() {
			// Backward-compatible replay tracking for the original v0.1 format.
			var old protocol.SignedReport
			if err := json.Unmarshal(raw, &old); err != nil || old.Report.EventID == "" || old.Report.NodeID == "" {
				return nil, nil, fmt.Errorf("ledger line %d: invalid evidence", row)
			}
			seen[old.Report.NodeID+":"+old.Report.EventID] = true
			continue
		}
		if entry.Evidence.Report.EventID == "" || entry.Evidence.Report.NodeID == "" || entry.ReceivedAt.After(now.Add(2*time.Minute)) {
			return nil, nil, fmt.Errorf("ledger line %d: invalid receipt", row)
		}
		id := entry.Evidence.Report.NodeID + ":" + entry.Evidence.Report.EventID
		if seen[id] {
			return nil, nil, fmt.Errorf("ledger line %d: repeated event ID", row)
		}
		seen[id] = true
		if entry.ReceivedAt.After(now.Add(-time.Minute)) {
			node := entry.Evidence.Report.NodeID
			recent[node] = append(recent[node], entry.ReceivedAt)
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, nil, err
	}
	if _, err := f.Seek(0, io.SeekEnd); err != nil {
		return nil, nil, err
	}
	measured, err := measureLedger(f)
	if err != nil {
		return nil, nil, err
	}
	if _, err = checkLedgerHead(f, measured); err != nil {
		return nil, nil, err
	}
	return seen, recent, nil
}

func newServer(keys map[string]ed25519.PublicKey, revoked map[string]bool, ledger *os.File, clock func() time.Time) (*server, error) {
	now := clock().UTC()
	seen, recent, err := restoreLedger(ledger, now)
	if err != nil {
		return nil, err
	}
	head, err := loadHead(ledger.Name() + ".head")
	if err != nil {
		return nil, err
	}
	return &server{keys: keys, revoked: revoked, seen: seen, recent: recent, ledger: ledger, maxLedgerBytes: defaultLedgerMaxBytes, head: head, now: clock}, nil
}

// restoreArchivedReplay is deliberately invoked only after the live ledger's
// checkpoint has passed integrity verification. All archive material and the
// expected manifest tip must be pinned independently of the HUB data volume.
func (s *server) restoreArchivedReplay(manifest string, root ed25519.PublicKey, pinnedTip string) error {
	archived, timestamps, err := archive.Load(manifest, root, pinnedTip, s.ledger.Name(), s.now().UTC())
	if err != nil {
		return err
	}
	for id := range archived {
		if s.seen[id] {
			return fmt.Errorf("replay identity occurs in both active ledger and witnessed archive: %s", id)
		}
		s.seen[id] = true
	}
	for node, entries := range timestamps {
		s.recent[node] = append(s.recent[node], entries...)
	}
	return nil
}

func (s *server) report(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
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
	if s.poisoned {
		http.Error(w, "ledger requires operator recovery", 503)
		return
	}
	if s.signedRevocations != nil {
		current, err := s.signedRevocations.refresh(s.now().UTC(), s.keys)
		if err != nil {
			http.Error(w, "revocation evidence unavailable", 503)
			return
		}
		s.revoked = current
	}
	pub, ok := s.keys[sr.Report.NodeID]
	if !ok || s.revoked[sr.Report.NodeID] {
		http.Error(w, "not registered", 403)
		return
	}
	now := s.now().UTC()
	if err := protocol.VerifyReport(sr, pub, now); err != nil {
		http.Error(w, "rejected report", 403)
		return
	}
	id := sr.Report.NodeID + ":" + sr.Report.EventID
	if s.seen[id] {
		http.Error(w, "duplicate report", 409)
		return
	}

	times := s.recent[sr.Report.NodeID][:0]
	for _, t := range s.recent[sr.Report.NodeID] {
		if t.After(now.Add(-time.Minute)) && !t.After(now) {
			times = append(times, t)
		}
	}
	s.recent[sr.Report.NodeID] = times
	if len(times) >= perNodeMinuteLimit {
		http.Error(w, "rate limited", 429)
		return
	}

	entry, err := json.Marshal(ledgerEntry{ReceivedAt: now, Evidence: sr})
	if err != nil {
		http.Error(w, "encode failed", 500)
		return
	}
	row := append(entry, '\n')
	// Bound local storage WITHOUT compacting away the replay index. Manual
	// off-host witness and incident-reviewed rotation are required before
	// discarding any records. This is a fail-closed resource guard, not GC.
	fi, statErr := s.ledger.Stat()
	if statErr != nil {
		s.poisoned = true
		http.Error(w, "storage unavailable", http.StatusServiceUnavailable)
		return
	}
	if s.maxLedgerBytes <= 0 || fi.Size() > s.maxLedgerBytes-int64(len(row)) {
		http.Error(w, "ledger full: offline archival required", http.StatusInsufficientStorage)
		return
	}
	next, err := nextHead(s.head, row)
	if err != nil {
		http.Error(w, "ledger digest failed", 500)
		return
	}
	n, err := s.ledger.Write(row)
	if err != nil || n != len(row) {
		s.poisoned = true
		http.Error(w, "storage unavailable", 503)
		return
	}
	if err = s.ledger.Sync(); err != nil {
		s.poisoned = true
		http.Error(w, "storage unavailable", 503)
		return
	}
	if err = saveHead(s.ledger.Name()+".head", next); err != nil {
		s.poisoned = true
		http.Error(w, "checkpoint unavailable", 503)
		return
	}
	s.head = next
	s.seen[id] = true
	s.recent[sr.Report.NodeID] = append(s.recent[sr.Report.NodeID], now)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	fmt.Fprintln(w, `{"status":"received_unverified"}`)
}

func loadTrust(allowlistFile, revokedFile string) (map[string]ed25519.PublicKey, map[string]bool, error) {
	raw, err := os.ReadFile(allowlistFile)
	if err != nil {
		return nil, nil, err
	}
	var entries map[string]string
	if err := json.Unmarshal(raw, &entries); err != nil {
		return nil, nil, err
	}
	if len(entries) == 0 {
		return nil, nil, errors.New("empty allowlist")
	}
	keys := make(map[string]ed25519.PublicKey)
	for id, h := range entries {
		pub, err := protocol.PublicFromHex(strings.TrimSpace(h))
		if err != nil || protocol.NodeID(pub) != id {
			return nil, nil, fmt.Errorf("invalid allowlisted key %q", id)
		}
		keys[id] = pub
	}
	revoked := make(map[string]bool)
	if revokedFile != "" {
		b, err := os.ReadFile(revokedFile)
		if err != nil {
			return nil, nil, err
		} // Fail closed on missing/unreadable revocation source.
		var ids []string
		if err := json.Unmarshal(b, &ids); err != nil {
			return nil, nil, err
		}
		for _, id := range ids {
			if _, ok := keys[id]; !ok {
				return nil, nil, fmt.Errorf("revoked node not in allowlist: %q", id)
			}
			revoked[id] = true
		}
	}
	return keys, revoked, nil
}

func main() {
	addr := flag.String("listen", "127.0.0.1:8788", "loopback listen address")
	keysFile := flag.String("allowlist", "allowlist.json", "node_id to public key mapping")
	revokedFile := flag.String("revoked", "", "optional required-to-exist JSON list of revoked node IDs (read at startup)")
	ledgerFile := flag.String("ledger", "ledger.jsonl", "local append-only evidence ledger")
	ledgerLimit := flag.Int64("max-ledger-bytes", defaultLedgerMaxBytes, "bounded evidence size (1 MiB to 1 GiB; no auto-compaction)")
	bootstrap := flag.Bool("bootstrap-ledger", false, "one-time manually reviewed sealing of legacy uncheckpointed ledger")
	signedRevoke := flag.String("signed-revocations", "", "optional path to signed local revocation snapshot; fail-closed and hot-reloaded")
	revokeRoot := flag.String("revocation-root", "", "offline root public key for signed snapshots")
	archiveManifest := flag.String("archives", "", "optional signed archive manifest; mandatory for all rollover generations")
	archiveRoot := flag.String("archive-root", "", "pinned archive manifest signing public key")
	archiveTip := flag.String("archive-tip", "", "independently pinned SHA256 of the signed archive manifest")
	flag.Parse()
	if *ledgerLimit < 1<<20 || *ledgerLimit > 1<<30 {
		log.Fatal("max-ledger-bytes must be 1 MiB to 1 GiB")
	}
	if *addr != "127.0.0.1:8788" {
		log.Fatal("MVP only listens on 127.0.0.1:8788")
	}
	if (*archiveManifest != "") != (*archiveRoot != "") || (*archiveManifest != "") != (*archiveTip != "") {
		log.Fatal("signed archive manifest, pinned root, and independently pinned tip must be provided together")
	}
	if err := requireArchiveSentinel(*ledgerFile, *archiveManifest != ""); err != nil {
		log.Fatal("archive generation configuration refused: ", err)
	}
	if (*signedRevoke == "") != (*revokeRoot == "") || (*signedRevoke != "" && *revokedFile != "") {
		log.Fatal("configure both -signed-revocations and -revocation-root, without -revoked")
	}
	keys, revoked, err := loadTrust(*keysFile, *revokedFile)
	if err != nil {
		log.Fatal("invalid trust configuration: ", err)
	}
	releaseLock, err := acquireLedgerLock(*ledgerFile)
	if err != nil {
		log.Fatal("HUB startup refused: ", err)
	}
	defer releaseLock()
	f, err := os.OpenFile(*ledgerFile, os.O_CREATE|os.O_APPEND|os.O_RDWR, 0600)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()
	if *bootstrap {
		if err := bootstrapLedgerHead(f); err != nil {
			log.Fatal("ledger bootstrap rejected: ", err)
		}
	}
	s, err := newServer(keys, revoked, f, time.Now)
	if err != nil {
		log.Fatal("invalid ledger: ", err)
	}
	info, err := f.Stat()
	if err != nil || info.Size() > *ledgerLimit {
		log.Fatal("ledger capacity exceeded or inaccessible; archive offline before operator-reviewed recovery")
	}
	if *archiveManifest != "" {
		root, err := witness.ReadPublicKey(*archiveRoot)
		if err != nil {
			log.Fatal("archive trust root unavailable: ", err)
		}
		if err := s.restoreArchivedReplay(*archiveManifest, root, *archiveTip); err != nil {
			log.Fatal("witnessed archive verification refused HUB startup: ", err)
		}
	}
	s.maxLedgerBytes = *ledgerLimit
	if *signedRevoke != "" {
		source, err := newRevocationSource(*signedRevoke, *revokeRoot)
		if err != nil {
			log.Fatal("revocation trust initialization failed: ", err)
		}
		s.signedRevocations = source
		latest, err := source.refresh(time.Now().UTC(), keys)
		if err != nil {
			log.Fatal("revocation snapshot unavailable: ", err)
		}
		s.revoked = latest
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/report", s.report)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.WriteHeader(405)
			return
		}
		fmt.Fprintln(w, "ok")
	})
	log.Println("HUB local-only MVP ready")
	srv := &http.Server{Addr: *addr, Handler: mux, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second, IdleTimeout: 15 * time.Second, MaxHeaderBytes: 8192}
	log.Fatal(srv.ListenAndServe())
}
