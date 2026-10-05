"""Execute the emitted cabinet and migration scripts in a small state model.

This is a source-level regression runner, not an HOI4 engine emulator. Unknown
operations fail loudly; scenarios cover lock/unlock, replacement, regime and
war transitions, saved focus completions, and research alliance membership.
"""
import json,re,copy
from pathlib import Path
from PIL import Image
from hoi4_script import parse,one,scalar,entries,walk

ROOT=Path(__file__).resolve().parent.parent;MOD=ROOT/'mod'
def read(p):return p.read_text(encoding='utf-8-sig')

class State:
    def __init__(self,tree='sofzh_paris',gov='democratic',faction=None):
        self.tree=tree;self.gov=gov;self.faction=faction;self.focus=set();self.ideas=set();self.flags=set();self.pp=500
        self.war=False;self.subjects=0;self.groups=set();self.characters=set();self.roles={};self.leader=None
        self.variables={'SFC_army_org_factor':.27};self.dynamic={'SFC_regio_esercito_dynamic_modifier'}

class Runner:
    def __init__(self,ideas,triggers,effects,world):self.ideas=ideas;self.triggers=triggers;self.effects=effects;self.world=world
    def matches(self,rows,c,root=None,prev=None):
        root=root or c;values=[]
        for r in rows:
            k,v=r.key,r.value
            if k in ['AND','limit']:value=self.matches(v,c,root,prev)
            elif k=='OR':value=any(self.matches([x],c,root,prev) for x in v)
            elif k=='NOT':value=not self.matches(v,c,root,prev)
            elif k=='always':value=v=='yes'
            elif k=='sofzh_cabinet_country':value=True
            elif k=='custom_trigger_tooltip':value=self.matches([x for x in v if x.key!='tooltip'],c,root,prev)
            elif k in self.triggers:value=self.matches(self.triggers[k],c,root,prev)
            elif k=='has_focus_tree':value=c.tree==v
            elif k=='has_completed_focus':value=v in c.focus
            elif k=='has_government':value=c.gov==v
            elif k=='has_idea':value=v in c.ideas
            elif k=='has_country_flag':value=v in c.flags
            elif k=='has_character':value=v in c.characters
            elif k=='has_war':value=c.war==(v=='yes')
            elif k=='has_political_power':value=c.pp>float(v)
            elif k=='num_subjects':value=c.subjects<float(v)
            elif k=='is_in_tech_sharing_group':value=v in c.groups
            elif k=='any_other_country':value=any(self.matches(v,x,root,c) for x in self.world if x is not c)
            elif k=='is_in_faction_with':
                assert v in ['ROOT','PREV'],v
                target=root if v=='ROOT' else prev;assert target is not None
                value=c.faction is not None and c.faction==target.faction
            elif k.startswith('sof_hist_character_'):
                value=scalar(v,'has_ideology') in c.roles.get(k,set())
            else:raise AssertionError('Unsupported test guard '+str(k))
            values.append(value)
        return all(values)
    def add(self,pid,c):
        assert pid in self.ideas,pid
        c.ideas.add(pid)
        for r in entries(self.ideas[pid],'on_add'):self.execute(r.value,c)
    def execute(self,rows,c):
        branch=False
        for r in rows:
            k,v=r.key,r.value
            if k in ['if','else_if']:
                take=(not branch if k=='else_if' else True) and self.matches(one(v,'limit').value,c)
                if take:self.execute([x for x in v if x.key!='limit'],c)
                branch=(branch or take) if k=='else_if' else take
            elif k=='else':
                if not branch:self.execute(v,c)
            elif k in self.effects:self.execute(self.effects[k],c)
            elif k=='add_ideas':
                for pid in ([v] if isinstance(v,str) else [x.value for x in v]):self.add(pid,c)
            elif k=='remove_ideas':c.ideas.discard(v)
            elif k=='set_country_flag':c.flags.add(v if isinstance(v,str) else scalar(v,'flag'))
            elif k=='clr_country_flag':c.flags.discard(v)
            elif k=='recruit_character':c.characters.add(v)
            elif k=='set_politics':c.gov=scalar(v,'ruling_party')
            elif k=='add_country_leader_role':
                ch=scalar(v,'character');assert ch in c.characters,ch
                ideology=scalar(one(v,'country_leader').value,'ideology')
                assert ideology not in c.roles.get(ch,set()),'Duplicate leader role '+ch
                c.roles.setdefault(ch,set()).add(ideology);c.leader=ch
            elif k=='remove_country_leader_role':c.roles.setdefault(scalar(v,'character'),set()).discard(scalar(v,'ideology'))
            elif k=='retire_character':c.characters.discard(v);c.roles.pop(v,None)
            elif k=='add_to_tech_sharing_group':c.groups.add(v)
            elif k=='remove_from_tech_sharing_group':c.groups.discard(v)
            elif k=='custom_effect_tooltip':pass
            else:raise AssertionError('Unsupported test effect '+str(k))

def audit(check,gfx):
    meta=json.loads(read(ROOT/'design/historical-cabinet.json'));members=meta['members']
    cabinets=one(parse(read(MOD/'common/ideas/sofzh_cabinet.txt')),'ideas').value
    ideas={r.key:r.value for cat in cabinets for r in cat.value if isinstance(r.value,list)}
    ideas.update({r.key:r.value for r in one(one(parse(read(MOD/'common/ideas/sof_vanilla_major.txt')),'ideas').value,'country').value})
    triggers={r.key:r.value for r in parse(read(MOD/'common/scripted_triggers/sofzh_cabinet.txt'))}
    effects={r.key:r.value for r in parse(read(MOD/'common/scripted_effects/sof_vanilla_major.txt'))}
    nodes={scalar(r.value,'id'):r.value for tree in ['paris','corsica'] for r in entries(one(parse(read(MOD/f'common/national_focus/sofzh_{tree}.txt')),'focus_tree').value,'focus')}
    characters={r.key:r.value for r in one(parse(read(MOD/'common/characters/sof_vanilla_historical.txt')),'characters').value}
    check(len(members)==40,'40 historical cabinet members')
    check(len([x for x in cabinets if x.key.startswith('sofzh_cabinet_')])==8,'Existing eight political cabinet slots')
    loc={}
    for p in (MOD/'localisation/simp_chinese').rglob('*.yml'):loc.update(re.findall(r'(?m)^\s+([^\s:]+):\d*\s+"((?:[^"\\]|\\.)*)"',read(p)))
    for p in members:
        pid=p['id'];source=p['source'];tree='sofzh_paris' if source.startswith('FRA_') else 'sofzh_corsica';pre='SFP_' if source.startswith('FRA_') else 'SFC_'
        slot=p['slot'];same=[r.key for r in one(cabinets,'sofzh_cabinet_'+slot).value if isinstance(r.value,list)];body=ideas[pid]
        check(pid in same and pid+'_available' in triggers,'Historical slot and hiring guard: '+pid)
        check(all(pre+x in nodes for x in p['focuses']+p['retired']),'Historical unlocking focuses exist: '+pid)
        check(pid in loc and pid+'_desc' in loc and pid+'_unlock_tt' in loc,'Historical Chinese name and guidance: '+pid)
        check('GFX_idea_'+scalar(body,'picture') in gfx,'Historical portrait sprite: '+pid)
        check(Image.open(MOD/p['portrait']).size==(65,67),'Native advisor portrait dimensions: '+pid)
        check(bool(one(body,'modifier').value),'Historical member has numerical bonuses: '+pid)
        c=State(tree,(p['governments'] or ['democratic'])[0]);run=Runner(ideas,triggers,effects,[c])
        available=one(body,'available').value
        check(not run.matches(available,c),'Locked before completed focus: '+pid)
        c.focus.add(pre+p['focuses'][0]);check(run.matches(available,c),'Unlocked by qualifying focus: '+pid)
        c.pp=0;check(not run.matches(available,c),'Hiring requires actual political power: '+pid);c.pp=500
        # Exercise both legacy generic -> historical and historical -> generic.
        generic=f'sofzh_minister_{slot}_1';other='sof20_terrain_mountain';c.ideas.add(generic);c.ideas.add(other)
        run.add(pid,c);check(c.ideas&set(same)=={pid} and other in c.ideas,'Replacement preserves terrain and one member per slot: '+pid)
        check(not run.matches(available,c),'Current appointment cannot be hired again: '+pid)
        check(not run.matches(one(body,'cancel').value,c),'Appointed member survives hiring cooldown: '+pid)
        c.flags.discard('sofzh_cabinet_'+slot+'_cooldown');run.add(generic,c)
        check(c.ideas&set(same)=={generic},'Generic replacement removes historical payload: '+pid)
        if p['governments']:
            c.gov=next(g for g in ['democratic','communism','fascism','neutrality'] if g not in p['governments'])
            check(not run.matches(available,c) and run.matches(one(body,'cancel').value,c),'Wrong regime prevents and cancels appointment: '+pid)
            c.gov=p['governments'][0]
        for f in p['retired']:
            c.focus.add(pre+f);check(not run.matches(available,c) and run.matches(one(body,'cancel').value,c),'Disbanding or retirement locks the member: '+pid)
        for f in p['focuses']:
            reward=one(nodes[pre+f],'completion_reward').value
            check(any(r.key=='custom_effect_tooltip' and r.value==pid+'_unlock_tt' for r in reward),'Focus displays historical unlock: '+pre+f+' '+pid)
    # Actual native leader nodes, one-time upgrade of a 4.0 save, repeat pulse.
    from vanilla_historical import LEADERS,char_id,idea_id
    for old,(source,ideology,gov) in LEADERS.items():
        fid=('SFP_' if old.startswith('FRA_') else 'SFC_')+old[4:];effect='sof_hist_complete_'+old.lower()
        check(char_id(source) in characters,'Migrated leader defined: '+old)
        check(effect in effects and any(r.key==effect for r in one(nodes[fid],'completion_reward').value),'Leader effect wired to real focus: '+old)
        c=State('sofzh_paris' if old.startswith('FRA_') else 'sofzh_corsica');c.focus.add(fid);c.ideas={'sof_van_prs_fra_political_violence','sof20_terrain_mountain'}
        before=copy.deepcopy((c.variables,c.dynamic));run=Runner(ideas,triggers,effects,[c]);run.execute(effects['sof_hist_setup'],c)
        check(c.leader==char_id(source) and c.gov==gov,'Old completed focus receives historical leader: '+old)
        if idea_id(source) in ideas:check(idea_id(source) in c.ideas and c.pp==500,'Leader focus appoints chief without charging PP: '+old)
        check(before==(c.variables,c.dynamic) and 'sof20_terrain_mountain' in c.ideas,'Upgrade preserves earned variables and terrain: '+old)
        check('sof_van_prs_fra_political_violence' not in c.ideas,'Upgrade removes empty donor event marker: '+old)
        snapshot=copy.deepcopy(c.__dict__);run.execute(effects['sof_hist_setup'],c);check(snapshot==c.__dict__,'Historical upgrade runs once: '+old)
        run.execute(effects[effect],c);check(c.leader==char_id(source),'Explicit repeat appointment has no duplicate role: '+old)
    for pid in meta['repaired_empty_spirits']:check(any(float(r.value)!=0 for r in one(ideas[pid],'modifier').value),'Previously empty spirit now changes combat: '+pid)
    for old in meta['campaign_spirits']:
        pid='sof_van_cor_'+old.lower();body=ideas[pid];c=State('sofzh_corsica');run=Runner(ideas,triggers,effects,[c]);run.add(pid,c)
        check(not run.matches(one(body,'cancel').value,c),'Campaign bonus survives peaceful preparation: '+pid)
        c.war=True;run.execute(effects['sof_van_reward_sync'],c);check(not run.matches(one(body,'cancel').value,c),'Campaign bonus survives fighting: '+pid)
        c.war=False;check(run.matches(one(body,'cancel').value,c),'Campaign bonus cancels after peace: '+pid)
        run.add(pid,c);check(not run.matches(one(body,'cancel').value,c),'Later campaign can rearm the bonus: '+pid)
        c.flags.add('sofzh_unification_complete');check(run.matches(one(body,'cancel').value,c),'Campaign bonus cancels after unification: '+pid)
    for pid in ['sof_van_cor_ita_italian_confederation_leader','sof_van_cor_ita_italian_confederation_leader_improved']:
        c=State();run=Runner(ideas,triggers,effects,[c]);check(run.matches(one(ideas[pid],'cancel').value,c),'Confederation bonus requires subjects: '+pid);c.subjects=1;check(not run.matches(one(ideas[pid],'cancel').value,c),'Confederation bonus kept with a subject: '+pid)
    host=State('sofzh_corsica',faction='A');peer=State('sof_generic',faction='A');stranger=State('sof_generic',faction='B')
    host.focus.add('SFC_scientific_cooperation');run=Runner(ideas,triggers,effects,[host,peer,stranger]);group='sof_van_scientific_cooperation';spirit='sof_van_cor_ita_scientific_cooperation_ns'
    check(run.matches(triggers['sof_van_science_partner'],peer,root=stranger),'Global startup root cannot prevent a real ally joining research')
    check(not run.matches(triggers['sof_van_science_partner'],stranger,root=host),'Global startup root cannot enroll an unrelated country')
    host.focus.clear();host.flags.add('sof_van_science_host')
    check(run.matches(triggers['sof_van_science_partner'],host) and run.matches(triggers['sof_van_science_partner'],peer),'Cooperation is effective during the focus completion effect, before completion is recorded')
    host.focus.add('SFC_scientific_cooperation')
    for c in [host,peer,stranger]:run.execute(effects['sof_van_reward_sync'],c)
    check(all(group in c.groups and spirit in c.ideas for c in [host,peer]) and group not in stranger.groups,'Research host and actual allies enter group; strangers excluded')
    check(run.matches(one(ideas[spirit],'do_effect').value,peer),'Scientific spirit is effective inside its sharing group')
    peer.groups.add('unrelated_group');peer.ideas.add('sof20_terrain_mountain');peer.faction='B';run.execute(effects['sof_van_reward_sync'],peer)
    check(group not in peer.groups and spirit not in peer.ideas and 'unrelated_group' in peer.groups and 'sof20_terrain_mountain' in peer.ideas,'Leaving alliance removes only this research membership and spirit')
    peer.faction='A';run.execute(effects['sof_van_reward_sync'],peer);check(group in peer.groups and spirit in peer.ideas,'Rejoining alliance restores research cooperation')
    peer.faction=None;host.faction=None;run.execute(effects['sof_van_reward_sync'],peer);run.execute(effects['sof_van_reward_sync'],host)
    check(group in host.groups and group not in peer.groups,'Faction dissolution leaves the scientific host and removes former allies')
    # No historical feature mutates the old generic tree or its reward payload.
    reward=one(nodes['SFC_aid_for_the_spanish_republic'],'completion_reward').value
    check(not any(r.key=='add_manpower' and float(r.value)<0 for r in walk(reward)),'Removed foreign volunteer event cannot consume 10,000 men without delivery')
    refs=read(MOD/'common/on_actions/sof20_startup.txt')
    check('sof_hist_setup = yes' in refs and refs.count('sof_van_reward_sync = yes')==2,'Startup and weekly pulses migrate and synchronize rewards')
