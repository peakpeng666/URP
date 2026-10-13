"""Additional independent full archive/selection binding; no candidate AST/exec.

This supplements, never replaces, the accepted receipt/journal terminal audit.
"""
import argparse,copy,hashlib,importlib.util,json,pathlib
from fractions import Fraction
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parent.parent
HERE=pathlib.Path(__file__).resolve().parent

def need(ok,why):
    if not ok:raise ValueError(why)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def textsha(v):return hashlib.sha256(v.encode()).hexdigest()
def fraction(v):return Fraction(v['numerator'],v['denominator'])
def rational(v):return {'numerator':v.numerator,'denominator':v.denominator}
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def derive(original,rows,observations):
    """Rows and observations are separately authenticated/receipt-verified inputs."""
    fixed={x['id']:x for x in original['generation']};archive=copy.deepcopy(original['archive']);by_id={x['id']:x for x in archive};states={}
    need(len(rows)==len(observations)==60,'sixty observations required')
    need([r['slot_id'] for r in rows]==[x['id'] for x in original['generation'] if x['phase']==1],'exact frozen phase-one roster')
    for row,obs in zip(rows,observations):
        sid=row['slot_id'];slot=fixed[sid];pack=row['pack'];candidate=obs['extraction']['candidate']
        need(obs['slot_id']==sid and pack['slot_id']==sid and pack['arm']==slot['arm'] and pack['order']==slot['order'] and pack['phase']==1,'immutable slot/pack binding')
        if candidate is None:
            need(obs['extraction']['unique'] is False and not obs['scores'],'unadmitted scores');states[sid]=('generation_failed',obs['extraction']['reason']);continue
        need(candidate['code_sha256']==textsha(candidate['code']) and candidate['description_sha256']==textsha(candidate['description']),'verified candidate exact content hashes')
        need(candidate['pair_sha256']==digest({'description':candidate['description'],'code':candidate['code']}),'verified pair hash')
        scores=obs['scores'];eligible=len(scores)==5 and [x['instance_index'] for x in scores]==list(range(5)) and all(x['outcome']=='ok' for x in scores)
        fitness=gap=None
        if eligible:
            fitness=rational(sum((Fraction(s['L1'],s['used_bins']) for s in scores),Fraction())/5)
            gap=rational(100*Fraction(sum(s['used_bins']-s['L1'] for s in scores),sum(s['L1'] for s in scores)))
        parents=list(pack['parents'])
        initial=[sid] if slot['arm']=='IID_TC' else sorted({line for parent in parents for line in by_id[parent]['initial_lineages']})
        expected={**copy.deepcopy(candidate),'id':sid,'arm':slot['arm'],'phase':1,'order':slot['order'],'tie_priority':slot['tie_priority'],'eligible':eligible,'fitness':fitness,'report_gap':gap,'parents':parents,'joint_duplicate_of':None,'code_duplicate_of':None,'initial_lineages':initial}
        archive.append(expected);by_id[sid]=expected;states[sid]=('eligible',None) if eligible else ('evaluation_failed','incomplete_or_failed_design_panel')
    archive.sort(key=lambda x:x['order']);seen_joint={};seen_code={}
    for c in archive:
        j=(c['arm'],c['joint_identity']);k=(c['arm'],c['code_identity'])
        c['joint_duplicate_of']=seen_joint.get(j);c['code_duplicate_of']=seen_code.get(k);seen_joint.setdefault(j,c['id']);seen_code.setdefault(k,c['id'])
    need([c for c in archive if c['phase']==0]==original['archive'],'historical P0 archive preservation')
    snapshots=copy.deepcopy(original['snapshots']);current=[]
    for arm in ('EOH_TC','IID_TC'):
        if arm=='EOH_TC':
            old=next(s for s in original['snapshots'] if s['phase']==0 and s['arm']==arm)
            pool=[by_id[i] for i in old['survivor_ids']]+[c for c in archive if c['arm']==arm and c['phase']==1 and c['eligible']];capacity=6
        else:pool=[c for c in archive if c['arm']==arm and c['eligible']];capacity=1
        unique={};dups={}
        for c in sorted(pool,key=lambda x:x['order']):
            if c['joint_identity'] in unique:dups[c['id']]=unique[c['joint_identity']]['id']
            else:unique[c['joint_identity']]=c
        ranked=sorted(unique.values(),key=lambda c:(-fraction(c['fitness']),c['tie_priority'],c['id']));survivors=ranked[:capacity];ids=[c['id'] for c in survivors]
        decisions={'eligible_ids':[c['id'] for c in sorted(pool,key=lambda c:c['order'])],'ranked_ids':[c['id'] for c in ranked],'duplicates':dups,'reasons':{c['id']:('exact_joint_duplicate' if c['id'] in dups else 'retained' if c['id'] in ids else 'outside_capacity') for c in pool}}
        snap={'name':'P1','arm':arm,'phase':1,'survivor_ids':ids,'members':[{k:copy.deepcopy(c[k]) for k in ('id','pair_sha256','code_identity','joint_identity','fitness','report_gap','tie_priority','initial_lineages')} for c in survivors],'decisions':decisions,'failed_offspring':[{'id':s['id'],'state':states[s['id']][0],'reason':states[s['id']][1]} for s in original['generation'] if s['phase']==1 and s['arm']==arm and states[s['id']][0]!='eligible'],'population_size':len(ids),'underfilled':len(ids)<capacity,'distinct_code_count':len({c['code_identity'] for c in survivors}),'behavior_diversity':'unknown_without_assignment_evidence','active_initial_lineages':sorted({line for c in survivors for line in c['initial_lineages']})}
        snap['sha256']=digest(snap);snapshots.append(snap);current.append(snap)
    return archive,snapshots,states

def derive_scores(original,observations):
    scores=copy.deepcopy(original['scores']);by_slot={}
    for score in scores:
        by_slot.setdefault(score.get('source_generation_slot'),[]).append(score)
    for obs in observations:
        target=by_slot[obs['slot_id']];need(len(target)==5 and [x['instance_index'] for x in target]==list(range(5)),'frozen score panel topology')
        candidate=obs['extraction']['candidate']
        if candidate is None:
            for score in target:score['reason']='generation_'+str(obs['extraction']['reason'])
            continue
        for score in target:score['reason']='missing_verified_observation'
        for verified in obs['scores']:
            score=target[verified['instance_index']];outcome=verified['outcome']
            score.update(state='verified' if outcome=='ok' else 'not_run' if outcome=='not_run' else 'failed',reason=None if outcome=='ok' else outcome,used_bins=verified['used_bins'],L1=verified['L1'],code_hash=candidate['code_sha256'],runtime_hash=verified['evidence']['runtime_sha256'],evidence=copy.deepcopy(verified))
    return scores

def verify_binding(original,ledger,rows,observations):
    for field in ('generation','scores'):
        expected=[x['id'] for x in original[field]];actual=[x['id'] for x in ledger[field]]
        need(len(expected)==len(set(expected)) and actual==expected,'exact unique full '+field+' ID sequence')
    archive,snapshots,states=derive(original,rows,observations)
    need(ledger['scores']==derive_scores(original,observations),'full score ledger differs from verified observations and frozen topology')
    need(ledger['archive']==archive,'full archive differs from receipt-verified source/identity and fixed metadata')
    need(ledger['snapshots']==snapshots,'complete snapshot differs from independently rebuilt archive')
    fixed={x['id']:x for x in original['generation']};rowmap={r['slot_id']:r for r in rows};obsmap={o['slot_id']:o for o in observations}
    for slot in ledger['generation']:
        if slot['phase']!=1:need(slot==fixed[slot['id']],'non-phase-one generation changed');continue
        row=rowmap[slot['id']];obs=obsmap[slot['id']]
        need(type(slot['logical_requests_observed']) is int and slot['logical_requests_observed']==1,'each phase-one slot has exactly one logical request')
        for key in ('id','arm','phase','order','operator','tie_priority'):need(slot[key]==fixed[slot['id']][key],'frozen generation metadata '+key)
        need(slot['parents']==row['pack']['parents'],'frozen parent IDs')
        need((slot['state'],slot['reason'])==states[slot['id']],'state derived from verified observation')
        need(slot['capture']==obs['capture'] and slot['extraction']=={k:v for k,v in obs['extraction'].items() if k!='candidate'},'observation binding')
    old_scores={x['id']:x for x in original['scores']};phase1ids=set(rowmap)
    for score in ledger['scores']:
        if score.get('source_generation_slot') not in phase1ids:need(score==old_scores[score['id']],'non-phase-one score changed')
    need(ledger['summary']['winners']=={'EOH_TC':None,'IID_TC':None},'phase-two winner summary must remain unset')
    need(ledger['summary']['halt_reason'] is None,'scheduler internal halt')
    return {'status':'passed','exact_generation_ID_sequence':132,'exact_score_ID_sequence':780,'archive_rows':len(archive),'historical_archive_rows_preserved':len(original['archive']),'full_archive_rebuilt_from_verified_candidates':True,'full_P1_snapshots_rebuilt':True,'P1_survivors':{s['arm']:s['survivor_ids'] for s in snapshots if s['phase']==1},'P1_best_ids':{s['arm']:(s['survivor_ids'][0] if s['survivor_ids'] else None) for s in snapshots if s['phase']==1},'P1_snapshot_sha256':{s['arm']:s['sha256'] for s in snapshots if s['phase']==1},'phase2_winners_unset':True,'candidate_AST_or_execution_calls':0}

def main():
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('--report-file-sha256',required=True);p.add_argument('--approval',required=True);p.add_argument('--approval-file-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    h=load(ROOT/'original132_phase1_preparation_20261005/phase1_numerical.py','phase1_binding_harness');core=load(HERE/'audit_terminal.py','prior_terminal_auditor')
    base=core.audit(h,1,a.report,a.report_file_sha256,a.approval,a.approval_file_sha256)
    before=core.snapshot(h)
    with patch('ast.parse',side_effect=AssertionError('candidate AST forbidden')),patch('subprocess.Popen',side_effect=AssertionError('process launch forbidden')):
        report=h.verify(h.read(a.report,a.report_file_sha256));plan=h.verify(h.read(h.STATE/'plan.json'));approval=h.read(a.approval,a.approval_file_sha256);trust=h.read(approval['receipt_trust_path'],approval['receipt_trust_file_sha256'])
        m=h.modules();_,rows=h.imported_rows(h.read(h.STATE/'handoff.json',plan['handoff_file_sha256']),m);panel,_=h.design_panel();freeze=h.verify(h.read(h.INPUTS/'freeze.json'));bridge=h.receipt_bridge(plan,trust,m) if plan['candidate_source_count'] else None;obs=[]
        for row in rows:
            bundle=h.verify(h.read(h.STATE/'bundles'/(row['claim']['claim_id']+'.json'))) if row['candidate'] else None
            obs.append(h.project(row,bundle,bridge,panel,freeze))
        original=h.verify(h.read(h.HERE/'history/scheduler-ledger.json'));ledger=h.verify(h.read(report['scheduler_ledger_path']));check=verify_binding(original,ledger,rows,obs)
    need(core.snapshot(h)==before,'source-binding audit mutated state')
    result={'schema':'phase1-strong-terminal-audit-v1','status':'passed','report_file_sha256':a.report_file_sha256,'report_sha256':report['sha256'],'plan_sha256':plan['sha256'],'ledger_sha256':ledger['sha256'],'base_receipt_audit':base,'source_selection_binding':check,'frozen_state_unchanged':True,'candidate_execution':0,'model_calls':0}
    with pathlib.Path(a.output).open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({'status':'passed','report_sha256':report['sha256'],'P1_survivors':check['P1_survivors'],'P1_best_ids':check['P1_best_ids']},sort_keys=True))
if __name__=='__main__':main()
