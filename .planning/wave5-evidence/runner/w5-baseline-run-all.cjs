const fs = require('fs')
const {run}=require('/tmp/w5-baseline-harness.cjs')
const {P,ORDER}=require('/tmp/w5-baseline-core-runner.cjs')
const destination=process.env.W5_REPORT || '/tmp/w5-baseline-all-results.json'
;(async()=>{
 const results=[]
 for(const phase of ORDER){
  const result=await run(phase,P[phase]);results.push(result)
  fs.writeFileSync(destination,JSON.stringify(results,null,2))
  if(result.fatal){process.exitCode=1;break}
  const failures=result.checks.filter(c=>!c.ok)
  if(failures.length){
   process.exitCode=1
   // Preserve baseline #430 failure while collecting independent later flows; all other failed prerequisites stop.
   if(failures.some(c=>!c.name.startsWith('c7 repeat approver: bob cannot approve again')))break
  }
 }
})().catch(error=>{console.error(error);process.exitCode=1})
