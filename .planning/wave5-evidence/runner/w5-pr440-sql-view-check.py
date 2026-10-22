import json,subprocess,os
from pathlib import Path
ids=json.loads(Path('/tmp/w5-baseline-ids.json').read_text());c=ids['catalogue']
cur_ids=','.join("'%s'"%a['id'] for a in c['active'])
def query(user, sql):
 cmd=['docker','exec','-e','PGPASSWORD='+os.environ['W5_DB_PASSWORD'],'gc-monkey-db','psql','-h','127.0.0.1','-U','app_user','-d','gene_curator_dev','-qAt','-v','ON_ERROR_STOP=1','-c',f"BEGIN; SET LOCAL app.current_user_id='{user}'; {sql}; ROLLBACK;"]
 return subprocess.check_output(cmd,text=True).strip().splitlines()
rows=query(c['userIds']['alice'],f"SELECT json_build_object('id',v.curation_id,'genetic',v.genetic_score,'experimental',v.experimental_score,'total',v.total_score,'stored_genetic',c.computed_scores->>'genetic_evidence_total','stored_experimental',c.computed_scores->>'experimental_evidence_total','stored_total',c.computed_scores->>'total_score') FROM active_curations_summary v JOIN curations c ON c.id=v.curation_id WHERE v.curation_id IN ({cur_ids}) ORDER BY v.curation_id")
values=[json.loads(r) for r in rows];assert len(values)==2,values
for v in values:
 for key in ['genetic','experimental','total']:
  assert v[key] is not None and float(v[key])==float(v['stored_'+key]),(key,v)
hidden=query(c['outsiderId'],f'SELECT count(*) FROM active_curations_summary WHERE curation_id IN ({cur_ids})');assert hidden==['0'],hidden
role=query(c['userIds']['alice'],"SELECT json_build_object('user',current_user,'superuser',rolsuper,'bypassrls',rolbypassrls) FROM pg_roles WHERE rolname=current_user");r=json.loads(role[0]);assert r=={'user':'app_user','superuser':False,'bypassrls':False},r
result={'passed':True,'role':r,'numeric_rows':values,'outsider_count':0}
Path('/tmp/w5-pr440-sql-view-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
