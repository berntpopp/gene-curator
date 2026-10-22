const fs=require('fs')
const {run,USERS}=require('/tmp/w5-baseline-harness.cjs')
const {detailAction,submitCuration,clickAndCapture,desc}=require('/tmp/w5-baseline-core-runner.cjs')
const UI='http://localhost:5190'
const browserRequest=(page,method,path,body)=>page.evaluate(async({method,path,body})=>{
 const response=await fetch(`http://localhost:8052/api/v1${path}`,{method,headers:{Authorization:`Bearer ${localStorage.getItem('access_token')}`,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined})
 return {status:response.status,data:await response.json()}
},{method,path,body})
run('pr441-review-narrow',async({as,check,shot,settle,ids,api,saveIds})=>{
 const core=ids().core
 const list=(await api('admin','GET',`/curations/?scope_id=${core.scopeId}`)).data
 const cur=(list.curations||list.items||list).find(x=>process.env.W5_REVIEW_CUR ? x.id===process.env.W5_REVIEW_CUR : x.gene_id===core.genes.PKD2.id && x.status==='in_review')
 const c={...core,curationId:cur.id}
 const bob=await as('bob')
 const first=await detailAction(bob,c,{action:'Approve',notes:'First independent vote for administrator work',shotName:'pr441-bob-first-vote',shot,settle})
 check('Bob first approval through UI succeeds',first.ok,first.detail)
 const meta=await browserRequest(bob,'GET',`/curations/${cur.id}`)
 check('Already-approved reviewer retains review capability with1 remaining',meta.status===200&&meta.data.can_review===true&&meta.data.has_approved===true&&meta.data.approvals_remaining===1,JSON.stringify({can_review:meta.data.can_review,has_approved:meta.data.has_approved,remaining:meta.data.approvals_remaining}))
 await bob.reload();await settle(bob)
 check('Already-approved UI hides Approve',await bob.getByRole('main').getByRole('button',{name:'Approve',exact:true}).count()===0)
 check('Already-approved UI retains Request changes',await bob.getByRole('main').getByRole('button',{name:'Request changes',exact:true}).isEnabled())
 check('Already-approved UI explains remaining approval', (await bob.locator('main').innerText()).includes('You approved; 1 more needed'))
 const comment=await browserRequest(bob,'POST',`/curations/${cur.id}/review-comments`,{item_path:'evidence_summary',kind:'query',body:'Already-approved reviewer can still discuss this evidence.'})
 check('Already-approved browser-origin comment succeeds',comment.status===201&&comment.data.author_id===c.userIds.bob,comment.status)
 const resolved=await browserRequest(bob,'PATCH',`/curations/${cur.id}/review-comments/${comment.data.id}`,{status:'resolved'})
 check('Already-approved reviewer can resolve own comment',resolved.status===200&&resolved.data.status==='resolved',resolved.status)
 await shot(bob,'pr441-repeat-approve-hidden-actions-retained')
 const requested=await detailAction(bob,c,{action:'Request changes',notes:'Already-approved reviewer requests an evidence clarification.',shotName:'pr441-approved-reviewer-requests-changes',shot,settle})
 check('Already-approved reviewer Request changes UI succeeds',requested.ok,requested.detail)
 const after=(await api('admin','GET',`/curations/${cur.id}`)).data
 check('Request changes returns item to draft',after.status==='draft'&&after.workflow_stage==='curation',`${after.status}/${after.workflow_stage}`)
 const admin=await as('admin')
 await admin.goto(`${UI}/scopes/${c.scopeId}/curations/${cur.id}/edit`);await settle(admin)
 await admin.getByRole('tab',{name:'Assessment'}).click()
 await admin.getByRole('textbox',{name:'Evidence Summary'}).fill('Clarified administrator evidence after approved-reviewer request.')
 const saved=await clickAndCapture(admin,admin.getByRole('button',{name:'Save draft'}),`/curations/${cur.id}`)
 check('Author saves revision through UI',saved&&saved.status()<300,await desc(saved))
 const {resp}=await submitCuration(admin,cur.id)
 check('Author resubmits through UI',resp&&resp.status()<300,await desc(resp))
 const reset=(await browserRequest(bob,'GET',`/curations/${cur.id}`)).data
 check('New round resets previous approval',reset.has_approved===false&&reset.approvals_remaining===2,JSON.stringify({has_approved:reset.has_approved,remaining:reset.approvals_remaining}))
 const reviewers={bob:c.userIds.bob}
 for(const who of ['dave','erin']){
  USERS[who]=`w5.${who}@genecurator.org`
  const users=(await api('admin','GET','/users/')).data
  const existing=users.find(u=>u.email===USERS[who])
  const u=existing?{status:200,data:existing}:await api('admin','POST','/users/',{email:USERS[who],name:`W5 ${who}`,role:'user',password:process.env.W5_TEST_PASSWORD,is_active:true})
  check(`Legacy fixture reviewer ${who} available`,u.status<300,u.status)
  reviewers[who]=u.data.id
  const access=await api(who,'GET',`/scopes/${c.scopeId}`)
  if(access.status!==200){
   const invite=await api('admin','POST',`/scopes/${c.scopeId}/invitations`,{user_id:u.data.id,role:'reviewer',notes:'Legacy retained-review API fixture'})
   check(`${who} invited`,invite.status===201,invite.status)
   const accepted=await api(who,'POST',`/scopes/${c.scopeId}/invitations/${invite.data.id}/accept`)
   check(`${who} accepted membership`,accepted.status===200,accepted.status)
  }else check(`${who} accepted membership available`,true)
 }
 const reviews={}
 for(const [who,user_id] of Object.entries(reviewers)){
  const current=await api(who,'GET','/workflow/reviews/my-assignments?status=pending')
  const pending=current.data.find(x=>x.item_id===cur.id)
  const assigned=pending?{status:200,data:pending}:await api('admin','POST',`/workflow/curation/${cur.id}/assign-reviewer`,{reviewer_id:user_id})
  check(`Legacy fixture has pending assignment for ${who}`,assigned.status===200&&Boolean(assigned.data.review_id),JSON.stringify(assigned.data).slice(0,200))
  if(!assigned.data.review_id)throw Error(`No pending review ID for ${who}`)
  reviews[who]=assigned.data.review_id
 }
 for(const who of ['bob','dave']){
  const vote=await api(who,'POST',`/workflow/reviews/${reviews[who]}/submit`,{decision:'approve',comments:'Legacy endpoint recorded approval with third review pending'})
  check(`Legacy ${who} submit records approval without activating`,vote.status===200&&vote.data.auto_transitioned===false,JSON.stringify(vote.data).slice(0,220))
 }
 const zero=await browserRequest(bob,'GET',`/curations/${cur.id}`)
 check('Legacy approvals reach0 needed while still in review',zero.status===200&&zero.data.status==='in_review'&&zero.data.has_approved===true&&zero.data.approvals_remaining===0,JSON.stringify({status:zero.data.status,has_approved:zero.data.has_approved,remaining:zero.data.approvals_remaining}))
 await bob.goto(`${UI}/scopes/${c.scopeId}/curations/${cur.id}`);await settle(bob)
 check('Already-approved zero-needed reviewer sees enabled Approve',await bob.getByRole('main').getByRole('button',{name:'Approve',exact:true}).isEnabled())
 await shot(bob,'pr441-zero-needed-approve-available')
 const activated=await detailAction(bob,c,{action:'Approve',notes:'Activate quorum recorded by legacy API',shotName:'pr441-zero-needed-activated',shot,settle})
 check('Zero-needed activation succeeds through actual UI',activated.ok,activated.detail)
 check('Zero-needed resulting curation is active',(await api('admin','GET',`/curations/${cur.id}`)).data.status==='active')
 saveIds({reviewNarrow:{curationId:cur.id,scopeId:c.scopeId,reviewers}})
}).then(result=>{const p=process.env.W5_NARROW_REPORT||'/tmp/w5-pr441-candidate-review-results.json';fs.writeFileSync(p,JSON.stringify(result,null,2));if(result.fatal||result.checks.some(c=>!c.ok))process.exitCode=1})
