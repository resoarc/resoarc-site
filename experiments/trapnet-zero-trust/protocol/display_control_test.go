package protocol

import (
 "testing"
 "time"
)
func TestFeedTerminalAndBidiControlsRejected(t *testing.T) {
 now:=time.Now().UTC()
 for _,summary:=range []string{
  "clear\x1b[2J", "line\nspoof", "return\rsp oof", "tab\tspoof",
  "rtl\u202eexe.txt","isolate\u2066bad","zero\u200dwidth","separator\u2028next",
 } {
  feed:=Feed{Schema:FeedSchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]Warning{{Category:"notice",Summary:summary}}}
  if err:=feed.Validate(now);err==nil{t.Errorf("unsafe warning accepted: %q",summary)}
 }
 good:=Feed{Schema:FeedSchema,Version:1,IssuedAt:now,ExpiresAt:now.Add(time.Hour),Warnings:[]Warning{{Category:"notice",Summary:"日本語の注意喚起とテスト: 2026年10月"}}}
 if err:=good.Validate(now);err!=nil{t.Fatal(err)}
}
