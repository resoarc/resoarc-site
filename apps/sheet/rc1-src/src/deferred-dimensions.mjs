// Apply delayed XLSX dimensions only to the import generation that requested them.
// Errors and unavailable sheet IDs must never fail silently.
export function scheduleDimensionUpdate({
  getEngine, isCurrent, method, dimensions, options, onExhausted, onSettled,
  intervalMs=50, maxAttempts=200, schedule=setTimeout,
}) {
  if(!['setColumnWidth','setRowHeight'].includes(method))throw Error('Unsupported dimension update');
  if(!Number.isInteger(maxAttempts)||maxAttempts<1)throw Error('Invalid retry limit');
  let attempts=0;
  const retry=()=>{
    if(!isCurrent()){onSettled?.({status:"cancelled",method,sheetId:options?.id,attempts});return;}
    try {
      const engine=getEngine();
      if(engine && engine.getAllSheets?.().some(s=>s.id===options?.id) && typeof engine[method]==='function'){
        engine[method](dimensions,options);
        onSettled?.({status:"applied",method,sheetId:options?.id,attempts:attempts+1});
        return;
      }
    }catch{ /* Mounting engines can temporarily reject dimension updates. */ }
    if(++attempts<maxAttempts)schedule(retry,intervalMs);
    else {onExhausted?.({method,sheetId:options?.id,attempts});onSettled?.({status:"exhausted",method,sheetId:options?.id,attempts});}
  };
  schedule(retry,intervalMs);
}
