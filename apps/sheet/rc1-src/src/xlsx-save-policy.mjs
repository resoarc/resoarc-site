/**
 * A valid XLSX ZIP is not proof of lossless round-tripping.
 * If the OOXML feature inventory shows that normal export removed content,
 * fail closed by default. A user may explicitly choose the simplified XLSX format and acknowledge the exact losses.
 */
export function decideNormalXlsxSave(audit,{acceptLoss=false}={}) {
  if (!audit) return {action:'allow',lost:[]};
  const lost=Array.isArray(audit.losses)?audit.losses.filter(x=>Number(x?.missing)>0):[];
  if (lost.length) return {action:acceptLoss?'confirm-loss':'block',lost};
  return {action:audit.hasRisks?'confirm':'allow',lost:[]};
}
