package main

import (
 "errors"
 "fmt"
 "os"
)

// enforceEmergencyStop is an offline, always-on refusal guard. Operators
// activate it by creating <guardian -state path>.stop. It is not a remotely
// triggered kill command, and removal requires explicit local intervention.
// Even a malformed marker, symlink, or I/O failure fails closed.
func enforceEmergencyStop(statePath string) error {
 if statePath==""{return errors.New("guardian state path required")}
 marker:=statePath+".stop"
 info,err:=os.Lstat(marker)
 if errors.Is(err,os.ErrNotExist){return nil}
 if err!=nil{return fmt.Errorf("emergency stop state unavailable: %w",err)}
 if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink!=0{
  return errors.New("emergency stop marker unsafe: refusing Guardian")
 }
 return errors.New("emergency stop active: refusing Guardian")
}
