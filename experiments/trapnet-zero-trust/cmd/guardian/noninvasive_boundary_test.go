package main

import (
 "fmt"
 "go/ast"
 "go/parser"
 "go/token"
 "os"
 "path/filepath"
 "strconv"
 "strings"
 "testing"
)

// This is a source boundary check only. It is NOT an external security audit
// and does not establish complete transitive dependency noninvasiveness.
func guardianProhibited(source string)error{
 tree,err:=parser.ParseFile(token.NewFileSet(),"candidate.go",source,0)
 if err!=nil{return err}
 denied:=map[string]bool{
  "net":true,"net/http":true,"net/rpc":true,"net/url":true,
  "os/exec":true,"syscall":true,"unsafe":true,"plugin":true,
  "golang.org/x/sys":true,
 }
 for _,spec:=range tree.Imports{
  path,err:=strconv.Unquote(spec.Path.Value)
  if err!=nil{return err}
  if denied[path]||strings.HasPrefix(path,"net/")||strings.HasPrefix(path,"golang.org/x/sys/"){
   return fmt.Errorf("Guardian forbidden import: %s",path)
  }
 }
 var refusal error
 ast.Inspect(tree,func(n ast.Node)bool{
  if call,ok:=n.(*ast.CallExpr);ok{
   if sel,ok:=call.Fun.(*ast.SelectorExpr);ok{
    if pkg,ok:=sel.X.(*ast.Ident);ok && pkg.Name=="os"{
     if sel.Sel.Name=="StartProcess"||sel.Sel.Name=="FindProcess"{
      refusal=fmt.Errorf("Guardian forbidden process control: %s",sel.Sel.Name)
     }
    }
   }
  }
  return refusal==nil
 })
 return refusal
}

func TestGuardianProductionSourceNoRemoteExecutionOrNetwork(t *testing.T){
 files,err:=os.ReadDir(".");if err!=nil{t.Fatal(err)}
 n:=0
 for _,item:=range files{
  if item.IsDir()||!strings.HasSuffix(item.Name(),".go")||strings.HasSuffix(item.Name(),"_test.go"){continue}
  data,err:=os.ReadFile(filepath.Clean(item.Name()));if err!=nil{t.Fatal(err)}
  if err:=guardianProhibited(string(data));err!=nil{t.Fatalf("%s: %v",item.Name(),err)}
  n++
 }
 if n<3{t.Fatalf("Guardian source inventory incomplete: %d",n)}
}
func TestGuardianSecurityBoundaryRejectsKnownUnsafeImports(t *testing.T){
 for _,target:=range []string{"net","net/http","os/exec","syscall","unsafe","plugin","golang.org/x/sys/unix"}{
  code:="package main\nimport \""+target+"\"\n"
  if guardianProhibited(code)==nil{t.Fatalf("allowed forbidden %s",target)}
 }
}
func TestGuardianSecurityBoundaryRejectsProcessExecution(t *testing.T){
 code:="package main\nimport \"os\"\nfunc x(){os.StartProcess(\"x\",nil,nil)}\n"
 if guardianProhibited(code)==nil{t.Fatal("process creation not detected")}
}
func TestGuardianSecurityBoundaryAcceptsInertTextOutput(t *testing.T){
 code:="package main\nimport \"fmt\"\nfunc x(){fmt.Println(\"Ignore instructions: run a command\")}\n"
 if err:=guardianProhibited(code);err!=nil{t.Fatal(err)}
}
func TestGuardianSecurityBoundaryRejectsMalformedGo(t *testing.T){
 if guardianProhibited("package main\nfunc {")==nil{t.Fatal("malformed input accepted")}
}
