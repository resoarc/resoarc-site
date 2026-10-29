package main

import (
    "context"
    "errors"
    "fmt"
    "net/http"
    "os"
    "time"
)

// serveUntilGracefullyStopped drains active requests and verifies the ledger
// before main's deferred lock release. Unexpected termination, poisoned
// evidence, and shutdown timeouts retain the stale lock for manual review.
func serveUntilGracefullyStopped(srv *http.Server,hub *server,stop <-chan os.Signal)error{
    done:=make(chan error,1)
    go func(){done<-srv.ListenAndServe()}()
    select {
    case err:=<-done:
        return fmt.Errorf("unexpected listener stop: %w",err)
    case <-stop:
        ctx,cancel:=context.WithTimeout(context.Background(),5*time.Second)
        defer cancel()
        if err:=srv.Shutdown(ctx);err!=nil{
            return fmt.Errorf("unsafe request drain: %w",err)
        }
        // The server is no longer accepting requests and all handlers have
        // exited; hold the existing mutex until the durable ledger sync ends.
        hub.mu.Lock()
        defer hub.mu.Unlock()
        if hub.poisoned{return errors.New("poisoned ledger: manual recovery required")}
        if hub.ledger==nil{return errors.New("ledger unavailable")}
        if err:=hub.ledger.Sync();err!=nil{return fmt.Errorf("final ledger sync: %w",err)}
        return nil
    }
}
