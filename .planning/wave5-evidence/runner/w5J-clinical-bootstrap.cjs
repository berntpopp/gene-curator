const {api,ids,saveIds,run}=require('/tmp/w5-baseline-harness.cjs');
const must=(r,s)=>{if(r.status>=300)throw Error(s+': '+r.status+' '+JSON.stringify(r.data).slice(0,500));return r.data};
(async()=>{
const c=ids().core;const all=must(await api('admin','GET','/schemas/curation-schemas?active_only=false'),'schemas');
const source=all.find(x=>x.id===c.curationSchemaId);const [v]=must(await api('admin','GET',`/schemas/curation-schemas/${source.id}/versions`),'versions');
const out={};
for(const type of ['new','old']){
const [preVersion]=must(await api('admin','GET',`/schemas/curation-schemas/${c.precurationSchemaId}/versions`),'pre versions');
const preSchema=must(await api('admin','POST',`/schemas/curation-schemas/${c.precurationSchemaId}/versions/${preVersion.id}/derive`,{name:`W5 J Clinical pre ${type} ${Date.now()}`,version:'w5e.1'}),'derive unique pre');must(await api('admin','PUT',`/schemas/curation-schemas/${preSchema.id}`,{is_active:true}),'activate pre');
const stock=all.find(x=>x.name==='ClinGen Gene-Disease Validity SOP'&&x.version==='11.0');const stockVersions=must(await api('admin','GET',`/schemas/curation-schemas/${stock.id}/versions`),'stock versions');
const s=type==='new'?stock:must(await api('admin','POST',`/schemas/curation-schemas/${stock.id}/versions/${stockVersions.at(-1).id}/derive`,{name:`W5 J old ClinGen pin ${Date.now()}`,version:'w5j.old'}),'derive old stock version');
if(type==='old')must(await api('admin','PUT',`/schemas/curation-schemas/${s.id}`,{is_active:true}),'activate old copy');
const [ver]=must(await api('admin','GET',`/schemas/curation-schemas/${s.id}/versions`),'clinical versions');const point_model=ver.snapshot.scoring_configuration.point_model;
const pair=must(await api('admin','POST','/schemas/workflow-pairs',{name:`W5 J Clinical ${type} ${Date.now()}`,version:'1',precuration_schema_id:preSchema.id,curation_schema_id:s.id,is_active:true}),'pair');
const scope=must(await api('admin','POST','/scopes/',{name:`w5e-${type}-${Date.now()}`,display_name:`W5 J Clinical ${type}`,is_public:false,default_workflow_pair_id:pair.id}),'scope');
const m=must(await api('admin','POST',`/scopes/${scope.id}/invitations`,{user_id:c.userIds.alice,role:'curator'}),'invite');must(await api('alice','POST',`/scopes/${scope.id}/invitations/${m.id}/accept`),'accept');
must(await api('admin','POST','/gene-assignments/',{scope_id:scope.id,gene_id:c.genes.PKD1.id,assigned_curator_id:c.userIds.alice}),'assignment');
const evidence={disease_name:`W5 clinical ${type} disease`,genetic_evidence:{},experimental_evidence:{},replicated_over_time:false};
const reviewer=must(await api('admin','POST',`/scopes/${scope.id}/invitations`,{user_id:c.userIds.bob,role:'reviewer'}),'reviewer invite');must(await api('bob','POST',`/scopes/${scope.id}/invitations/${reviewer.id}/accept`),'reviewer accept');
const pre=must(await api('alice','POST','/precurations/',{scope_id:scope.id,gene_id:c.genes.PKD1.id,precuration_schema_id:preSchema.id,evidence_data:{disease_name:evidence.disease_name,mode_of_inheritance:'AD',entity_confirmed:false,curator_notes:'Fixture precuration'}}),'precuration');
const {clickAndCapture,queueAction}=require('/tmp/w5-baseline-core-runner.cjs');
const setup=await run(`candidateE-${type}-precuration-fixture`,async({as,settle,check,shot,UI})=>{
const a=await as('alice');await a.goto(`${UI}/scopes/${scope.id}/precurations/${pre.id}`);await settle(a,800);const response=await clickAndCapture(a,a.getByRole('button',{name:/Submit for review/i}),'/precurations');check('Fixture precuration submitted through UI',response?.status()<300);await settle(a,700);
const b=await as('bob');const approved=await queueAction(b,{gene:'PKD1',stage:'Precuration',action:'Approve',notes:'Fixture approved independently',shotName:`candidateE-${type}-fixture-approval`,shot,check,settle});check('Fixture precuration approved through UI',approved.ok,approved.detail);
});if(setup.fatal||setup.checks.some(x=>!x.ok))throw Error(JSON.stringify(setup));
const list=must(await api('alice','GET',`/curations/?scope_id=${scope.id}`),'created curations');const created=(list.curations||list.items||list).find(x=>x.gene_id===c.genes.PKD1.id);if(!created)throw Error('No auto-created curation');
const loaded=must(await api('alice','GET',`/curations/${created.id}`),'loaded curation');
const cur=must(await api('alice','PATCH',`/curations/${created.id}/draft`,{evidence_data:evidence,lock_version:loaded.lock_version}),'fixture evidence');
out[type]={schemaId:s.id,versionId:ver.id,scopeId:scope.id,curationId:cur.id,point_model,storedScores:cur.computed_scores};
}
saveIds({clinical:out});console.log(JSON.stringify(out,null,2));
})().catch(e=>{console.error(e);process.exit(1)});
