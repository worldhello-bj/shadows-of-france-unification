"""Audit the real shared graph, numeric budgets and one-time old-save reconciliation."""
from pathlib import Path
from copy import deepcopy
import re,json,itertools
from hoi4_script import parse,entries,one,scalar,walk
ROOT=Path(__file__).resolve().parents[1];MOD=ROOT/'mod'

class Runner:
 def __init__(self):
  self.effects={n.key:n.value for p in (MOD/'common/scripted_effects').glob('*.txt') for n in parse(p.read_text(encoding='utf-8-sig')) if isinstance(n.value,list)}
 def cond(self,rows,c):
  result=[]
  for n in rows:
   k,v=n.key,n.value
   if k=='NOT':r=not self.cond(v,c)
   elif k=='OR':r=any(self.cond([a],c) for a in v)
   elif k in ['AND','limit']:r=self.cond(v,c)
   elif k=='has_idea':r=v in c['ideas']
   elif k=='has_country_flag':r=v in c['flags']
   elif k=='has_completed_focus':r=v in c['completed']
   elif k=='has_focus_tree':r=v==c['tree']
   elif k=='original_tag':r=v==c['tag']
   elif k=='sof_mrs_red_public_allowed':r=(not c['red'])==(v=='yes')
   elif k=='has_dlc':r=v.strip('"') in c['dlc']
   elif k=='has_tech':r=v in c['tech']
   elif k in ['num_of_factories','amount_research_slots','num_of_controlled_states']:
    a=c[{'num_of_factories':'factories','amount_research_slots':'slots','num_of_controlled_states':'states'}[k]];b=float(v)
    r={'=':a==b,'>':a>b,'<':a<b,'>=':a>=b,'<=':a<=b,'!=':a!=b}[n.operator]
   elif k=='always':r=v=='yes'
   else:raise AssertionError('Unmodelled generic condition: '+str(k))
   result.append(r)
  return all(result)
 def execute(self,rows,c):
  matched=False
  for n in rows:
   k,v=n.key,n.value
   if k=='if':
    matched=self.cond(one(v,'limit').value,c)
    if matched:self.execute([a for a in v if a.key!='limit'],c)
   elif k=='else_if':
    if not matched and self.cond(one(v,'limit').value,c):self.execute([a for a in v if a.key!='limit'],c);matched=True
   elif k=='else':
    if not matched:self.execute(v,c)
    matched=True
   elif k=='hidden_effect':self.execute(v,c)
   elif k=='add_ideas':c['ideas'].add(v)
   elif k=='remove_ideas':c['ideas'].discard(v)
   elif k=='swap_ideas':c['ideas'].discard(scalar(v,'remove_idea'));c['ideas'].add(scalar(v,'add_idea'))
   elif k=='set_country_flag':c['flags'].add(v)
   elif k=='add_research_slot':c['slots']+=int(v)
   elif k=='add_war_support':c['war_support']+=float(v)
   elif k in self.effects:self.execute(self.effects[k],c)
   else:raise AssertionError('Unmodelled generic effect: '+str(k))
 def effect(self,name,c):self.execute(self.effects[name],c)

def state(**kwargs):
 c=dict(ideas=set(),flags=set(),completed=set(),tree='sof_generic',tag='LIL',red=False,dlc=set(),tech=set(),factories=0,slots=2,states=1,war_support=.5);c.update(kwargs);return c

def audit(check,loc=None,gfx=None):
 d=json.loads((ROOT/'design/generic-focus-4.4.json').read_text(encoding='utf-8'));source=(MOD/'common/national_focus/sof_mrs_shared_generic.txt').read_text(encoding='utf-8-sig')
 nodes={scalar(n.value,'id'):n.value for n in entries(parse(source),'shared_focus')};check(set(nodes)==set(d['focuses']),'Generic: exactly 153 stable shared IDs')
 occupied=set();active=set();done=set()
 def visit(i):
  check(i not in active,'Generic: no prerequisite cycle '+i)
  if i in active or i in done:return
  active.add(i)
  for group in entries(nodes[i],'prerequisite'):
   for n in entries(group.value,'focus'):
    check(n.value in nodes,'Generic: prerequisite resolves '+n.value)
    if n.value in nodes:visit(n.value)
  active.remove(i);done.add(i)
 for i,n in nodes.items():
  visit(i);p=d['focuses'][i];xy=(int(scalar(n,'x')),int(scalar(n,'y')))
  check(xy==(p['x'],p['y']),'Generic: configured grid '+i);check(xy not in occupied,'Generic: no node overlap '+i);occupied.add(xy)
  check(not entries(n,'relative_position_id'),'Generic: unambiguous absolute coordinates '+i)
  offsets=entries(n,'offset');check(len(offsets)==1 and scalar(offsets[0].value,'x')=='80','Generic: Marseille reserved offset '+i)
  check(int(scalar(n,'cost'))*7==p['cost']*7,'Generic: focus duration '+i)
  check(not entries(n,'mutually_exclusive'),'Generic: no artificial generic mutual exclusion '+i)
  if gfx:check(scalar(n,'icon') in gfx,'Generic: existing artwork resolves '+i)
  for group in entries(n,'prerequisite'):
   for dep in entries(group.value,'focus'):
    if dep.value in nodes:check(int(scalar(nodes[dep.value],'y'))<xy[1],'Generic: prerequisite is above node '+i+' '+dep.value)
 root=one(parse((MOD/'common/national_focus/SoF_generic.txt').read_text(encoding='utf-8-sig')),'focus_tree').value
 roots=[n.value for n in entries(root,'shared_focus')];reachable=set(roots)
 while True:
  before=len(reachable)
  for i,n in nodes.items():
   if any(a.value in reachable for b in entries(n,'prerequisite') for a in entries(b.value,'focus')):reachable.add(i)
  if len(reachable)==before:break
 check(set(nodes)<=reachable,'Generic: all nodes reach the eight original shared roots')
 check(len(entries(root,'shortcut'))==9,'Generic: nine native shortcuts')
 runner=Runner();peers={k:'sofzh_specialist_'+k for k in ['administration','civil_industry','mil_industry','engineering']}
 for k in ['infantry','recruitment','staff','special_forces','motorized','armor','artillery','air_defence','air_support','naval_air','dockyards','surface_navy','submarines','carrier','landing','fuel','recovery']:peers[k]='sofzh_dedicated_'+k
 families={m[1] for k in runner.effects if (m:=re.fullmatch(r'sof_generic_upgrade_(.+)_[1-6]',k))}
 for family in families:
  cap=6 if family=='administration' else 3;peer=peers.get(family)
  for current,target in itertools.product(range(cap+1),range(1,cap+1)):
   c=state(ideas={'sofzh_reward_'+family+'_'+str(current)} if current else set());runner.effect(f'sof_generic_upgrade_{family}_{target}',c)
   check(c['ideas']=={'sofzh_reward_'+family+'_'+str(max(current,target))},f'Generic: upgrade never stacks or downgrades {family} {current}>{target}')
  if peer:
   for generic,other,target in itertools.product(range(cap+1),range(1,4),range(1,cap+1)):
    ideas={peer+'_'+str(other)}
    if generic:ideas.add('sofzh_reward_'+family+'_'+str(generic))
    c=state(ideas=ideas);runner.effect(f'sof_generic_upgrade_{family}_{target}',c);rank=max(generic,other,target)
    expected=('sofzh_reward_'+family if rank>3 else peer)+'_'+str(rank)
    check(c['ideas']=={expected},f'Generic: counterpart reconciliation {family} g{generic}/p{other}>{target}')
 # Research decisions exercise actual reward guards and each integer boundary.
 for short,p in d['research_slots'].items():
  node=nodes['SOF_GENERIC_'+short]
  for tag,slots,factories in itertools.product(['LIL','MRS'],range(2,7),[p['factories']-1,p['factories'],p['factories']+1]):
   c=state(tag=tag,slots=slots,factories=factories);runner.execute(one(node,'completion_reward').value,c);cap=min(p['cap'],4) if tag=='MRS' else p['cap']
   check(c['slots']==slots+int(factories>=p['factories'] and slots<cap),f'Generic: slot boundary {short}/{tag}/{slots}/{factories}')
   check(any(i.startswith('sofzh_reward_research_') for i in c['ideas']),'Generic: capped research focus still has permanent reward')
 for j,short in enumerate(['arrondissement','department','province','region','state','nation'],1):
  c=state(completed={'SOF_GENERIC_'+short},ideas={'sofzh_reward_administration_1','sofzh_reward_administration_3'});runner.effect('sof_generic_migrate_440',c)
  # Preserve highest prior benefit if an edited save owns a higher tier than its focus history.
  check(c['ideas']=={'sofzh_reward_administration_'+str(max(j,3))},'Generic: old-save administration rank '+str(j));snap=deepcopy(c);runner.effect('sof_generic_migrate_440',c);check(c==snap,'Generic: migration is idempotent '+str(j))
 c=state(tree='sofzh_paris',ideas={'sofzh_dedicated_armor_3'});before=deepcopy(c);runner.effect('sof_generic_migrate_440',c);check(c==before,'Generic: unrelated major saves are untouched')
 guarded=json.loads((ROOT/'design/marseille-reward-guards.json').read_text(encoding='utf-8'))['guarded_effects']
 for name in guarded:check(any(n.key=='sof_mrs_red_public_allowed' for n in walk(runner.effects[name])),'Generic: Marseille guard preserved '+name)
 c=state(tag='MRS',tree='sof_mrs_red',red=True);runner.effect('sofzh_reward_sof_generic_basic_industry',c);check(not c['ideas'],'Generic: red Marseille cannot stack generic industrial spirits')
 c=state(tag='MRS',tree='sof_mrs_red',red=True);runner.effect('sofzh_reward_sof_generic_250_naval_bombers',c)
 check(any(k.startswith('sofzh_reward_naval_air_') for k in c['ideas']),'Generic: Marseille permitted naval aviation support remains available')
 # Verify all modified fields against the authoring design, rather than golden counts.
 ideas=one(one(parse((MOD/'common/ideas/sofzh_rewards.txt').read_text(encoding='utf-8-sig')),'ideas').value,'country').value
 for family,series in d['modifier_series'].items():
  for j in range(len(next(iter(series.values())))):
   row=one(ideas,'sofzh_reward_'+family+'_'+str(j+1));values={n.key:float(n.value) for n in one(row.value,'modifier').value}
   check(values=={k:v[j] for k,v in series.items()},'Generic: exact numeric series '+family+str(j+1))
 for family,series in d['equipment_cost_series'].items():
  for j,value in enumerate(series,1):
   row=one(ideas,'sofzh_reward_'+family+'_'+str(j));check(all(float(n.value)==value for n in walk(row.value) if n.key=='build_cost_ic'),'Generic: bounded equipment discount '+family+str(j))
 check(abs(d['modifier_series']['mil_industry']['industrial_capacity_factory'][-1]+d['legacy_modifiers']['fra_generic_military_industrial_complex']['industrial_capacity_factory']-.30)<1e-8,'Generic: 30% base industrial output budget')
 check(abs(-.25-.12+d['equipment_cost_series']['armor'][-1])<=.50,'Generic: 47% armor cost discount incl eight-tier MIO')
 check(d['modifier_series']['surface_navy']['navy_fuel_consumption_factor'][-1]+d['modifier_series']['submarines']['navy_fuel_consumption_factor'][-1]+d['modifier_series']['fuel']['navy_fuel_consumption_factor'][-1]>-.25,'Generic: naval fuel reductions remain above -25% combined')
 # Scope protection is checked against installed/published byte manifests by the packager.

def main():
 errors=[];count=0
 def check(ok,msg):
  nonlocal count;count+=1
  if not ok:errors.append(msg)
 audit(check);report=dict(ok=not errors,checks=count,errors=errors,game_engine_verified=False,scope='Actual Clausewitz scripts in a small condition/effect harness; not game/save/UI execution')
 print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if report['ok'] else 1)
if __name__=='__main__':main()
