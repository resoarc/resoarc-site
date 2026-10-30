package protocol

import (
    "crypto/ed25519"
    "crypto/rand"
    "encoding/json"
    "testing"
    "time"
)

// AI review records are intentionally NOT signed Sensor reports or Guardian
// feeds. Even if such JSON is forwarded accidentally, signature verification
// cannot promote a model-generated suggestion into operational authority.
func TestAIReviewCannotCrossSignedProtocolBoundary(t *testing.T) {
    pub, _, err := ed25519.GenerateKey(rand.Reader)
    if err != nil {
        t.Fatal(err)
    }
    now := time.Now().UTC()
    payloads := []struct {
        name string
        data string
    }{
        {
            "quarantined",
            `{"schema":"trapnet.ai-offline-review.v1","status":"quarantined_advisory","advisory_code":"review_api_activity","confidence":"low","allowed_actions":[],"can_execute_commands":false,"can_trigger_blocking":false,"sent_to_hub":false,"sent_to_guardian":false,"can_sign_feeds":false}`,
        },
        {
            "injected_model",
            `{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"block_ip","confidence":"high","can_execute_commands":true,"signature":"spoof"}`,
        },
        {
            "fake_signed_feed",
            `{"feed":{"schema":"trapnet.feed.v0.1","version":1},"signature":"spoof"}`,
        },
        {
            "fake_signed_report",
            `{"report":{"schema":"trapnet.report.v0.1","kind":"observation"},"signature":"spoof"}`,
        },
        {
            "role_spoofing",
            `{"role":"system","approve_release":true,"override":true,"feed":{"warnings":[]},"report":{}}`,
        },
    }

    for _, tc := range payloads {
        t.Run(tc.name, func(t *testing.T) {
            var signedFeed SignedFeed
            if err := json.Unmarshal([]byte(tc.data), &signedFeed); err == nil {
                if err := VerifyFeed(signedFeed, pub, now); err == nil {
                    t.Fatal("AI-originated text incorrectly authenticated as a signed feed")
                }
            }
            var signedReport SignedReport
            if err := json.Unmarshal([]byte(tc.data), &signedReport); err == nil {
                if err := VerifyReport(signedReport, pub, now); err == nil {
                    t.Fatal("AI-originated text incorrectly authenticated as a signed report")
                }
            }
        })
    }
}
