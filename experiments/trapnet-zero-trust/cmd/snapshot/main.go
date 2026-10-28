// Local offline snapshot only: HUB must be fully stopped.
package main
import(
 "flag"
 "fmt"
 "log"
 "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/snapshot"
)
func main(){
 ledger:=flag.String("ledger","","path to STOPPED HUB ledger with matching .head")
 out:=flag.String("out","","new, nonexistent snapshot directory")
 flag.Parse()
 if *ledger==""||*out==""{log.Fatal("-ledger and -out are required")}
 head,err:=snapshot.Create(*ledger,*out)
 if err!=nil{log.Fatal("snapshot refused: ",err)}
 fmt.Printf("SNAPSHOT rows=%d digest=%s dir=%s\nTransfer both files OFF-HUB for witnessing; retain original ledger.\n",head.Rows,head.Digest,*out)
}