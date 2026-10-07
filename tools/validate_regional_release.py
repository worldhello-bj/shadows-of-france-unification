"""Fresh-start release topology checks for all twenty active regional countries."""
import json
from pathlib import Path
from hoi4_script import parse,entries,one,scalar,walk
R=Path(__file__).resolve().parents[1];M=R/'mod'
EXPECTED={t:'sof_region_'+t+'_1936' for t in 'MET STR ROU LYO BRD TOU NAN CFR DIJ BES TRS AMI CHL MOP POI'.split()}
EXPECTED.update(PRS='sofzh_paris',AJC='sofzh_corsica',REN='sof_brittany',MRS='sof_mrs_red',LIL='sof_lille_vanilla_pilot')
def audit():
 tests=[]
 def ck(v,m):tests.append((bool(v),m))
 trees={};shared={};global_ids={}
 for path in (M/'common/national_focus').glob('*.txt'):
  rows=parse(path.read_text(encoding='utf-8-sig'))
  for e in entries(rows,'shared_focus'):
   if isinstance(e.value,list):
    k=scalar(e.value,'id');ck(k not in shared,'Unique shared node '+k);shared[k]=e.value
    ck(k not in global_ids,'Globally unique focus ID '+k);global_ids[k]=path.name
  for e in entries(rows,'focus_tree'):
   tid=scalar(e.value,'id');ck(tid not in trees,'Unique tree '+tid);trees[tid]=e.value
   for n in entries(e.value,'focus'):
    k=scalar(n.value,'id');ck(k not in global_ids,'Globally unique focus ID '+k);global_ids[k]=path.name
 def trigger(rows,tag):
  for r in rows:
   k,v=r.key,r.value
   if k in ['add','factor']:continue
   if k in ['original_tag','tag']:ok=v==tag
   elif k=='always':ok=v=='yes'
   elif k=='NOT':ok=all(not trigger([x],tag) for x in v)
   elif k=='OR':ok=any(trigger([x],tag) for x in v)
   elif k=='AND':ok=trigger(v,tag)
   else:raise AssertionError('Selector requires explicit initial-state model: '+str(k))
   if not ok:return False
  return True
 def weight(tree,tag):
  c=one(tree,'country').value;v=float(scalar(c,'factor','0'))
  for mod in entries(c,'modifier'):
   if trigger(mod.value,tag):
    v+=float(scalar(mod.value,'add','0'));v*=float(scalar(mod.value,'factor','1'))
  return v
 summary={}
 for tag,tid in EXPECTED.items():
  ck(tid in trees,'Active dedicated tree exists '+tag)
  if tid not in trees:continue
  scores={k:weight(v,tag) for k,v in trees.items()};best=max(scores.values());winners=[k for k,v in scores.items() if v==best]
  ck(winners==[tid],'Exactly one intended selected tree '+tag+' '+str(winners))
  tree=trees[tid];nodes={scalar(n.value,'id'):n.value for n in entries(tree,'focus')};own=len(nodes)
  used={e.value for e in entries(tree,'shared_focus')};ck(used<=shared.keys(),'Shared roots resolve '+tag)
  while True:
   more={k for k,v in shared.items() if any(e.value in used for g in entries(v,'prerequisite') for e in entries(g.value,'focus'))}
   if more<=used:break
   used|=more
  nodes.update({k:shared[k] for k in used if k in shared});active=set(nodes);vis=set();stack=set()
  def visit(k):
   ck(k not in stack,'No active prerequisite cycle '+tag+k)
   if k in vis or k in stack:return
   stack.add(k)
   for group in entries(nodes[k],'prerequisite'):
    for e in entries(group.value,'focus'):
     ck(e.value in active,'Active prerequisite resolves '+tag+k+' '+str(e.value))
     if e.value in active:visit(e.value)
   stack.remove(k);vis.add(k)
  for k,v in nodes.items():
   visit(k)
   for group in entries(v,'mutually_exclusive'):
    for e in entries(group.value,'focus'):ck(e.value in active,'Active exclusion resolves '+tag+k)
   for e in entries(v,'relative_position_id'):ck(e.value in active,'Active layout anchor resolves '+tag+k)
  summary[tag]=dict(tree=tid,own_nodes=own,shared_nodes=len(nodes)-own,roots=sum(not entries(v,'prerequisite') for v in nodes.values()))
 # Runtime closure after retiring old trees: references must resolve, including AI.
 helpers={n.key for k in ['scripted_effects','scripted_triggers'] for p in (M/'common'/k).glob('*.txt') for n in parse(p.read_text(encoding='utf-8-sig'))}
 for folder in ['common/national_focus','common/scripted_triggers','common/scripted_effects','common/decisions','common/ai_strategy_plans','common/ideas','common/military_industrial_organization','events','history/countries']:
  for p in (M/folder).rglob('*.txt'):
   for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
    if n.key in ['has_completed_focus','complete_national_focus','focus'] and isinstance(n.value,str):
     ck(n.value in global_ids,'Live focus reference '+str(p.relative_to(M))+' '+n.value)
    if n.key in ['has_focus_tree','load_focus_tree'] and isinstance(n.value,str):
     ck(n.value in trees,'Live tree reference '+str(p.relative_to(M))+' '+n.value)
    ck(n.key!='num_of_owned_states','Native owned-state API '+str(p.relative_to(M)))
    if n.key and n.key.startswith(('sof_','sofzh_','sof20_')) and isinstance(n.value,str) and n.value in ['yes','no']:
     ck(n.key in helpers,'Custom gameplay helper resolves '+n.key+' '+str(p.relative_to(M)))
 for p in (M/'common/ai_strategy_plans').glob('*.txt'):
  for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
   if n.key=='ai_national_focuses':
    for f in n.value:ck(f.value in global_ids,'AI priority resolves '+str(f.value))
   if n.key=='focus_factors':
    for f in n.value:ck(f.key in global_ids,'AI focus factor resolves '+str(f.key))
 report=dict(ok=all(a for a,b in tests),checks=len(tests),errors=[b for a,b in tests if not a],regions=summary,engine_verified=False)
 return report
if __name__=='__main__':
 import sys;r=audit();print(json.dumps(r,ensure_ascii=False));sys.exit(not r['ok'])
