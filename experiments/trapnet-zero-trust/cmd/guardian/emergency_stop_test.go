package main

import(
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestEmergencyStopAbsentDoesNotAlterNormalValidation(t *testing.T){
 p:=filepath.Join(t.TempDir(),"guardian-state.json")
 if err:=enforceEmergencyStop(p);err!=nil{t.Fatal(err)}
}
func TestEmergencyStopMarkerBlocks(t *testing.T){
 p:=filepath.Join(t.TempDir(),"state.json")
 if err:=os.WriteFile(p+".stop",[]byte("OPERATOR OFFLINE STOP"),0600);err!=nil{t.Fatal(err)}
 if err:=enforceEmergencyStop(p);err==nil||!strings.Contains(err.Error(),"emergency stop"){
  t.Fatal("failed to stop Guardian")
 }
}
func TestEmergencyStopMalformedMarkerAlsoBlocks(t *testing.T){
 p:=filepath.Join(t.TempDir(),"state.json")
 if err:=os.Mkdir(p+".stop",0700);err!=nil{t.Fatal(err)}
 if enforceEmergencyStop(p)==nil{t.Fatal("directory marker bypass")}
}
func TestEmergencyStopSymlinkAlsoBlocks(t *testing.T){
 p:=filepath.Join(t.TempDir(),"state.json")
 target:=filepath.Join(filepath.Dir(p),"target")
 if err:=os.WriteFile(target,[]byte("safe"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Symlink(target,p+".stop");err!=nil{t.Skip(err)}
 if enforceEmergencyStop(p)==nil{t.Fatal("symlink marker bypass")}
}
func TestEmergencyStopNotRemovedAutomatically(t *testing.T){
 p:=filepath.Join(t.TempDir(),"state.json")
 if err:=os.WriteFile(p+".stop",[]byte("STOP"),0600);err!=nil{t.Fatal(err)}
 for i:=0;i<3;i++{
  if enforceEmergencyStop(p)==nil{t.Fatal("stop cleared on repeated invocation")}
 }
 if _,err:=os.Stat(p+".stop");err!=nil{t.Fatal("stop marker missing")}
}
func TestEmergencyStopIsStatePathSpecific(t *testing.T){
 dir:=t.TempDir()
 a:=filepath.Join(dir,"a.state")
 b:=filepath.Join(dir,"b.state")
 if err:=os.WriteFile(a+".stop",[]byte("STOP"),0600);err!=nil{t.Fatal(err)}
 if enforceEmergencyStop(a)==nil{t.Fatal("state A stop ineffective")}
 if err:=enforceEmergencyStop(b);err!=nil{t.Fatal("unrelated state falsely stopped")}
}
func TestEmergencyStopEmptyPathFailsClosed(t *testing.T){
 if enforceEmergencyStop("")==nil{t.Fatal("accepted empty path")}
}
