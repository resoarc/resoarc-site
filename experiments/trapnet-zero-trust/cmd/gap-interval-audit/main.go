// gap-interval-audit is an offline, read-only cryptographic binding check.
// It never sends an event, accesses the HUB network, writes a checkpoint,
// validates independent Witness custody or authorizes public deployment.
package main

import (
    "bytes"
    "crypto/ed25519"
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "io"
    "os"
    "strings"
    "time"

    "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/outageproof"
    "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/protocol"
    "github.com/resoarc/resoarc-site/experiments/trapnet-zero-trust/receipt"
)

func readBounded(path string, max int) ([]byte,error) {
    if path=="" {return nil, errors.New("required private/local argument not supplied")}
    info,err:=os.Lstat(path)
    if err!=nil || !info.Mode().IsRegular() || info.Size()<1 || info.Size()>int64(max) {
        return nil,errors.New("unsafe or oversized evidence input")
    }
    raw,err:=os.ReadFile(path)
    if err!=nil || len(raw)==0 || len(raw)>max {return nil,errors.New("evidence read failed")}
    return raw,nil
}

func decodeCanonical(path string,max int, out any)error {
    raw,err:=readBounded(path,max);if err!=nil{return err}
    d:=json.NewDecoder(bytes.NewReader(raw))
    d.DisallowUnknownFields()
    if err:=d.Decode(out);err!=nil{return errors.New("malformed signed evidence JSON")}
    if err:=d.Decode(new(any));err!=io.EOF{return errors.New("signed evidence contains trailing data")}
    encoded,err:=json.Marshal(out);if err!=nil{return err}
    compact:=new(bytes.Buffer)
    if err:=json.Compact(compact,raw);err!=nil{return errors.New("bad JSON body")}
    // Strict canonical Go field encoding also rejects unknown/duplicate keys.
    if !bytes.Equal(encoded,compact.Bytes()){
        return errors.New("signed evidence must use canonical nonduplicated JSON")
    }
    return nil
}

func publicKey(path string)(ed25519.PublicKey,error){
    raw,err:=readBounded(path,256)
    if err!=nil{return nil,err}
    return protocol.PublicFromHex(strings.TrimSpace(string(raw)))
}

func run(argv []string) error {
    f:=flag.NewFlagSet("gap-interval-audit",flag.ContinueOnError)
    f.SetOutput(io.Discard)
    signedReportPath:=f.String("report","","exact signed Sensor recovery-gap report JSON")
    receiptPath:=f.String("hub-receipt","","exact signed HUB receipt JSON")
    attestationPath:=f.String("operator-interval","","separately signed operator interval JSON")
    manifestPath:=f.String("source-manifest","","fixed redacted evidence manifest to hash")
    sensorPubPath:=f.String("sensor-pub","","pinned Sensor Ed25519 PUBLIC key file")
    hubPubPath:=f.String("hub-pub","","pinned HUB Ed25519 PUBLIC key file")
    operatorPubPath:=f.String("operator-pub","","pinned operator Ed25519 PUBLIC key file")
    if err:=f.Parse(argv);err!=nil{return errors.New("invalid CLI options")}
    if f.NArg()!=0{return errors.New("unexpected CLI arguments")}
    var report protocol.SignedReport
    var ack receipt.Signed
    var att outageproof.SignedInterval
    if err:=decodeCanonical(*signedReportPath,8192,&report);err!=nil{return err}
    if err:=decodeCanonical(*receiptPath,receipt.MaxBytes,&ack);err!=nil{return err}
    if err:=decodeCanonical(*attestationPath,4096,&att);err!=nil{return err}
    source,err:=readBounded(*manifestPath,outageproof.MaxSourceBytes)
    if err!=nil{return err}
    sensorPub,err:=publicKey(*sensorPubPath);if err!=nil{return err}
    hubPub,err:=publicKey(*hubPubPath);if err!=nil{return err}
    operatorPub,err:=publicKey(*operatorPubPath);if err!=nil{return err}
    if err:=outageproof.Verify(att,report,ack,source,sensorPub,hubPub,operatorPub,time.Now().UTC());err!=nil{return err}
    return nil
}

func main(){
    result:=map[string]any{
        "schema":"trapnet.outage-interval-offline-audit.v063",
        "formal_release":"HOLD","interval_observation_truth_verified":false,
        "independent_witness_verified":false,
        "sensor_allowlist_revocation_verified":false,
        "public_traffic_modified":false,
        "cryptographic_binding_verified":false,
        "status":"HOLD",
    }
    err:=run(os.Args[1:])
    if err==nil{
        result["cryptographic_binding_verified"]=true
        result["status"]="BINDING_VERIFIED_RELEASE_HOLD"
    }else{
        result["failure_code"]="offline_input_or_signature_invalid"
    }
    data,e:=json.Marshal(result);if e!=nil{fmt.Println("{}");os.Exit(3)}
    fmt.Println(string(data))
    if err!=nil{os.Exit(2)}
}
