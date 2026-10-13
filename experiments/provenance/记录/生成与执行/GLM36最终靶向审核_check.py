import json,pathlib,hashlib,collections,statistics,time
start=time.process_time();root=pathlib.Path(__file__).parent;p=root/'source';s=json.loads((p/'summary.json').read_text());a=json.loads((p/'evaluation/assessment.json').read_text());m=json.loads((p/'RECORDS_HANDOFF_MANIFEST.json').read_text())
errs=[]
for f,rec in m['files'].items():
 b=(p/f).read_bytes()
 if len(b)!=rec['bytes'] or hashlib.sha256(b).hexdigest()!=rec['sha256']:errs.append(f)
assert not errs,errs
contexts=collections.defaultdict(set)
for t in s['tasks']:
 reqs=list((p/'raw'/t['task_id']).glob('*.request.json'));assert len(reqs)==1
 d=json.loads(reqs[0].read_text());assert (d['model'],d['reasoning_effort'],d['max_tokens'],d['temperature'],d['top_p'])==(t['model'],t['reasoning_effort'],64000,.7,.9);assert not d.get('tools')
 contexts[t['question_id']].add(json.dumps(d['messages'],sort_keys=True,ensure_ascii=False));assert t['cli_starts_recorded']==1
assert len(contexts)==6 and all(len(v)==1 for v in contexts.values())
score={}
for r in a['results']:
 if r['evaluation_status']=='complete':
  assert len(r['cases'])==3 and all(c['checker_status']=='passed' for c in r['cases'])
  score[r['task_id']]=(sum(c['used_bins'] for c in r['cases'])/sum(c['L1'] for c in r['cases'])-1)*100
assert len(score)==30
for r in s['paired_tables']['rows']:
 if r['task_id'] in score: assert abs(r['public_3x1000_gap_percent']-score[r['task_id']])<1e-5
pairs=[]
for q in sorted(contexts):
 aa=next(t for t in s['tasks'] if t['question_id']==q and t['model']=='glm-5.3' and t['reasoning_effort']=='max');bb=next(t for t in s['tasks'] if t['question_id']==q and t['model']=='glm-5.3-flash' and t['reasoning_effort']=='high');pairs.append({'question':q,'gap_delta_pp':score[aa['task_id']]-score[bb['task_id']],'wall_delta_s':aa['wall_seconds']-bb['wall_seconds']})
res={'status':'PASS_targeted_record_review','manifest_files':len(m['files']),'request_records':36,'identical_context_questions':6,'terminal_counts':dict(collections.Counter(t['outcome'] for t in s['tasks'])),'admission_counts':dict(collections.Counter(t['code_admission'] for t in s['tasks'])),'scored_candidates':len(score),'recorded_passed_cases':90,'pairs':pairs,'mean_gap_delta_pp':statistics.mean(x['gap_delta_pp'] for x in pairs),'mean_wall_delta_s':statistics.mean(x['wall_delta_s'] for x in pairs),'review_cpu_s':time.process_time()-start,'scope':'Independent archive hashes, actual request bodies, recorded score arithmetic. No model calls, no candidate execution rerun, no proof of provider internal HTTP count or billing; not a full sandbox audit.'}
(root/'REVIEW.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,ensure_ascii=False,indent=2))
