"""Audit actual state scripts and exercise guarded resource migration."""
from pathlib import Path
from copy import deepcopy
import json,hashlib,math,collections
from hoi4_script import parse,one,entries,scalar,walk
ROOT=Path(__file__).resolve().parents[1];MOD=ROOT/'mod';FLAG='sof_economy_resources_450'

def sha(b):return hashlib.sha256(b).hexdigest()
def protected(rows):
 result=[]
 for n in rows:
  if n.key in ['resources','industrial_complex','arms_factory','dockyard','add_extra_state_shared_building_slots']:continue
  if n.key=='set_state_flag' and n.value==FLAG:continue
  value=protected(n.value) if isinstance(n.value,list) else n.value
  if n.key=='buildings' and value==[]:continue
  result.append((n.key,n.operator,value))
 return result
def signature(rows):return sha(json.dumps(protected(rows),ensure_ascii=False,separators=(',',':')).encode('utf-8'))

class Runner:
 def __init__(self):
  self.effects={n.key:n.value for n in parse((MOD/'common/scripted_effects/sof_economy_map_450.txt').read_text(encoding='utf-8-sig'))}
  self.current=one(parse((MOD/'common/scripted_triggers/sof_economy_map_450.txt').read_text(encoding='utf-8-sig')),'sof_economy_map_is_current').value
 def cond(self,rows,c,sid=None):
  result=[]
  for n in rows:
   k,v=n.key,n.value
   if k=='NOT':r=not self.cond(v,c,sid)
   elif k in ['AND','limit']:r=self.cond(v,c,sid)
   elif k=='OR':r=any(self.cond([a],c,sid) for a in v)
   elif k=='is_ai':r=c['ai']==(v=='yes')
   elif k=='has_state_flag':r=v in c['states'][sid]['flags']
   elif k=='has_global_flag':r=v in c['global_flags']
   elif k=='sof_economy_map_is_current':r=self.cond(self.current,c)==(v=='yes')
   elif k.isdigit():r=self.cond(v,c,int(k))
   else:raise AssertionError('Unmodelled condition: '+k)
   result.append(r)
  return all(result)
 def execute(self,rows,c,sid=None):
  for n in rows:
   k,v=n.key,n.value
   if k=='if':
    if self.cond(one(v,'limit').value,c,sid):self.execute([a for a in v if a.key!='limit'],c,sid)
   elif k.isdigit():self.execute(v,c,int(k))
   elif k=='add_resource':
    t=scalar(v,'type');c['states'][sid]['resources'][t]=c['states'][sid]['resources'].get(t,0)+int(scalar(v,'amount'))
   elif k=='set_state_flag':c['states'][sid]['flags'].add(v)
   elif k=='set_global_flag':c['global_flags'].add(v)
   elif k in self.effects and v=='yes':self.execute(self.effects[k],c,sid)
   else:raise AssertionError('Unmodelled effect: '+k)

def audit(check,*_):
 d=json.loads((ROOT/'design/economy-map-4.5.json').read_text(encoding='utf-8'))
 ids={s['id'] for s in d['states']};types=d['types'];totals=collections.Counter();hist=collections.Counter();actual={}
 check(len(ids)==342 and len(types)==7,'Economy: exact French scope and seven resource types')
 logistic=one(parse((MOD/'common/scripted_triggers/sofzh_logistics.txt').read_text(encoding='utf-8-sig')),'sofzh_logistics_french_state').value
 check(ids=={int(n.value) for n in walk(logistic) if n.key=='state'},'Economy: use actual French map scope')
 for r in d['states']:
  text=(MOD/r['path']).read_text(encoding='utf-8-sig');rows=parse(text);s=one(rows,'state');h=one(s.value,'history').value
  check(int(scalar(s.value,'id'))==r['id'],'Economy: state path/id '+str(r['id']))
  check(signature(rows)==r['protected_ast_sha256'],'Economy: preserve population, infrastructure, ports, VPs and ownership '+str(r['id']))
  resource={n.key:int(n.value) for b in entries(s.value,'resources') for n in b.value}
  check(resource==r['resources'],'Economy: exact resource geography '+str(r['id']))
  check(set(resource)<=set(types) and all(n>0 for n in resource.values()),'Economy: valid positive resource entries '+str(r['id']))
  check(not r['impassable'] or not resource,'Economy: no deposits on unusable islands '+str(r['id']))
  check(len(resource)<=4,'Economy: regional specialization, no all-resource tiles '+str(r['id']))
  totals.update(resource);actual[r['id']]=resource
  buildings=entries(h,'buildings');b=buildings[0].value if buildings else []
  counts={t:int(scalar(b,t,'0')) for t in ['industrial_complex','arms_factory','dockyard']}
  slots=math.floor(d['category_slots'][scalar(s.value,'state_category')]*float(scalar(s.value,'buildings_max_level_factor','1')))
  count=sum(counts.values());hist[count]+=1
  check(slots==r['slots'] and count==(slots*4)//5,'Economy: 80% local slot budget '+str(r['id']))
  check(counts==r['factories'],'Economy: exact civil/military split '+str(r['id']))
  check(0<=count<=slots and slots*4-count*5<5,'Economy: integer rounding and spare capacity '+str(r['id']))
  check(not entries(h,'add_extra_state_shared_building_slots'),'Economy: remove compensating extra slots '+str(r['id']))
  check([n.value for n in entries(h,'set_state_flag')].count(FLAG)==1,'Economy: new campaign migration guard '+str(r['id']))
  check(not any(n.key in ['industrial_complex','arms_factory','dockyard'] for row in h if row.key and row.key.startswith('1936.') for n in walk(row.value) if isinstance(row.value,list)),'Economy: bookmark cannot restore five factories '+str(r['id']))
 check(dict(totals)==d['summary']['totals'],'Economy: all seven regional totals')
 check(totals['coal']>totals['steel']>totals['aluminium']>totals['rubber'],'Economy: French coal/steel advantage and scarce rubber')
 check(all(800<=totals[t]<=1600 for t in types),'Economy: every resource remains in the thousand-unit range')
 check(sum(not r for r in actual.values())==262,'Economy: 262 states have no strategic resource floor')
 check(len(hist)==7 and sum(k*v for k,v in hist.items())==810,'Economy: varied initial factory counts')
 check(sum(r['removed_compensation_slots'] for r in d['states'])==514,'Economy: remove only the documented 514 compensation slots')
 for rel,h in d['outside_france_sha256'].items():check(sha((MOD/rel).read_bytes())==h,'Economy: foreign state untouched '+rel)
 for rel in d['legacy_files'][:3]:
  rows=parse((MOD/rel).read_text(encoding='utf-8-sig'))
  check(not any(n.key=='add_resource' for n in walk(rows)),'Economy: deprecated supply cannot return '+rel)
 vp=parse((MOD/'common/scripted_effects/sofzh_resource_map.txt').read_text(encoding='utf-8-sig'))
 check(sum(n.key=='set_victory_points' for n in walk(vp))==851,'Economy: preserve all legacy town repair instructions')
 combined=parse((MOD/'common/scripted_effects/sofzh_combined_arms.txt').read_text(encoding='utf-8-sig'))
 check(any(n.key=='set_technology' for n in walk(combined)) and any(n.key=='add_building_construction' for n in walk(combined)),'Economy: keep original equipment/airport repair')
 check(sum(r['resources'].get('chromium',0) for r in d['states'] if r['region']=='AJC')==500,'Economy: Corsican chromium specialization')
 for required,typ in [([55,61,62,63,116,360],'coal'),([94,98,109],'steel'),([446],'aluminium'),([127],'oil'),([292],'tungsten')]:
  check(all(actual[s].get(typ,0)>0 for s in required),'Economy: preserve existing mining districts '+typ)
 for p in (MOD/'history/states').glob('*.txt'):
  rows=parse(p.read_text(encoding='utf-8-sig'))
  for n in walk(rows):
   if n.key=='victory_points':check(isinstance(n.value,list) and len(n.value)==2,'Economy: one province/value per victory point '+p.name)
 runner=Runner()
 migration=runner.effects['sof_economy_resources_migrate_450']
 forbidden={'add_building_construction','remove_building','add_extra_state_shared_building_slots','set_state_category','set_state_owner','set_state_controller','add_core_of','set_victory_points','set_technology','add_research_slot'}
 check(not any(n.key in forbidden for n in walk(migration)),'Economy: old-save migration never changes industry or territorial history')
 def campaign(ai=False,fresh=False):
  return dict(ai=ai,global_flags=set(),states={r['id']:dict(resources={t:(r['resources'] if fresh else r['previous_resources']).get(t,0) for t in types},flags={FLAG} if fresh else set(),factories=deepcopy(r['previous_factories']),extra_slots=r['removed_compensation_slots']) for r in d['states']})
 for scenario in ['ordinary','mining_rewards','partial','new_game','ai']:
  c=campaign(ai=scenario=='ai',fresh=scenario=='new_game');expected={}
  for r in d['states']:
   s=c['states'][r['id']];bonus={t:(r['id']%17+3 if scenario=='mining_rewards' else 0) for t in types}
   if scenario=='partial' and r['id']%2:
    s['resources']={t:r['resources'].get(t,0) for t in types};s['flags'].add(FLAG)
   for t in types:s['resources'][t]+=bonus[t]
   expected[r['id']]={t:(r['previous_resources'] if scenario=='ai' else r['resources']).get(t,0)+bonus[t] for t in types}
  old=deepcopy(c)
  runner.execute(migration,c)
  for r in d['states']:
   sid=r['id']
   check(c['states'][sid]['resources']==expected[sid],'Economy: actual-script migration '+scenario+'/'+str(sid))
   check(c['states'][sid]['factories']==old['states'][sid]['factories'] and c['states'][sid]['extra_slots']==old['states'][sid]['extra_slots'],'Economy: protect existing industry '+scenario+'/'+str(sid))
  stable=deepcopy(c);runner.execute(migration,c)
  check(c==stable,'Economy: migration is idempotent '+scenario)
  if scenario=='new_game':check(c==old,'Economy: new campaign never reissues resources')
 old=campaign();runner.execute(runner.effects['sof_economy_startup_450'],old)
 check(not runner.cond(runner.current,old) and FLAG not in old['global_flags'],'Economy: startup leaves old-save migration available')
 new=campaign(fresh=True);runner.execute(runner.effects['sof_economy_startup_450'],new)
 check(runner.cond(runner.current,new) and FLAG in new['global_flags'],'Economy: startup detects new campaign state markers')
 effects_by_state={int(n.key):n.value for n in walk(migration) if n.key and n.key.isdigit()}
 for r in d['states']:
  body=one(effects_by_state[r['id']],'if').value
  check(scalar(one(one(body,'limit').value,'NOT').value,'has_state_flag')==FLAG,'Economy: partial migration guard '+str(r['id']))
  delta={scalar(n.value,'type'):int(scalar(n.value,'amount')) for n in entries(body,'add_resource')}
  check(delta=={t:r['resources'].get(t,0)-r['previous_resources'].get(t,0) for t in types if r['resources'].get(t,0)!=r['previous_resources'].get(t,0)},'Economy: exact old-map delta '+str(r['id']))

def main():
 checks=0;errors=[]
 def check(ok,text):
  nonlocal checks
  checks+=1
  if not ok:errors.append(text)
 audit(check)
 report=dict(ok=not errors,checks=checks,errors=errors,game_engine_verified=False)
 print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if report['ok'] else 1)
if __name__=='__main__':main()
