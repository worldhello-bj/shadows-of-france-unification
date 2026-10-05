"""Portable audits for the checked-in playable source, without a game install."""
import argparse,hashlib,json,re
from pathlib import Path
from PIL import Image
from hoi4_script import parse,one,scalar,entries,walk

ROOT=Path(__file__).resolve().parent.parent
MOD=ROOT/'mod'

def norm(rows):
    return [(r.key,r.operator,norm(r.value) if isinstance(r.value,list) else r.value) for r in rows]

def validate():
    checks=0;errors=[]
    def check(ok,description):
        nonlocal checks
        checks+=1
        if not ok:errors.append(description)
    version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
    check(bool(re.fullmatch(r'\d+\.\d+\.\d+',version)),'VERSION must be x.y.z')
    descriptor=(MOD/'descriptor.mod').read_text(encoding='utf-8-sig')
    check(f'version="{version}"' in descriptor,'Descriptor and VERSION must agree')
    check(not re.search(r'(?m)^(remote_file_id|dependencies|archive)=',descriptor),'Source descriptor must be independent of local publication metadata')
    loc={};duplicates=[]
    for p in (MOD/'localisation/simp_chinese').rglob('*.yml'):
        check(p.read_bytes().startswith(b'\xef\xbb\xbf'),'Chinese localization BOM: '+str(p.relative_to(ROOT)))
        for key,value in re.findall(r'(?m)^ ([^\s:]+):\d* "((?:[^"\\]|\\.)*)"',p.read_text(encoding='utf-8-sig')):
            if key.startswith('sof_cw_') or key.startswith('SOF20_'):
                if key in loc:duplicates.append(key)
                loc[key]=value
    check(not duplicates,'Duplicate new localization keys: '+str(duplicates))
    profiles=json.loads((ROOT/'design/country-design.json').read_text(encoding='utf-8'))
    remake=version.startswith('4.')
    expected_major={r['tag']:r['nodes'] for r in json.loads((ROOT/'design/vanilla-major-remake.json').read_text(encoding='utf-8'))['donors']} if remake else {}
    selected={p['tag']:p for p in profiles if not remake or p['tag'] in ['PRS','AJC']};check(len(selected)==(2 if remake else 20),'Representative country scope')
    all_ids=set();focus_counts={}
    for p in (MOD/'common/national_focus').glob('*.txt'):
        rows=parse(p.read_text(encoding='utf-8-sig'))
        for tree in entries(rows,'focus_tree'):
            fid=scalar(tree.value,'id');foci=entries(tree.value,'focus')
            # Tree ID is used in the design evidence, including Paris/Corsica.
            targets=[tag for tag,profile in selected.items() if profile.get('tree_id')==fid or (p.name==f'sof20_{tag}.txt')]
            if not targets:
                if fid in ['sofzh_paris','SOF_PRS','sof_paris']:targets=['PRS']
                if fid in ['sofzh_corsica','SOF_COR','sof_corsica']:targets=['AJC']
            if not targets:continue
            tag=targets[0];focus_counts[tag]=len(foci);ids={scalar(f.value,'id') for f in foci}
            check(len(ids)==len(foci),'Focus IDs unique in '+tag)
            check(not (ids&all_ids),'Focus IDs unique between selected countries: '+tag);all_ids|=ids
            for f in foci:
                ident=scalar(f.value,'id')
                # New focuses require Chinese titles; inherited Paris/Corsica
                # keys are in the full localization tree and checked below.
                if ident.startswith('SOF20_'):check(ident in loc,'Focus localized: '+ident)
                for prerequisite in entries(f.value,'prerequisite'):
                    for r in entries(prerequisite.value,'focus'):check(r.value in ids,'Prerequisite resolves: '+ident+' -> '+r.value)
                for mutual in entries(f.value,'mutually_exclusive'):
                    for r in entries(mutual.value,'focus'):check(r.value in ids,'Mutual exclusion resolves: '+ident+' -> '+r.value)
    check(len(focus_counts)==(2 if remake else 20),'All active bespoke trees resolved: '+str(focus_counts))
    check(sum(focus_counts.values())==(sum(expected_major.values()) if remake else 1408),'Expected active bespoke focus count')
    for tag,profile in selected.items():
        if tag in focus_counts:check(focus_counts[tag]==(expected_major[tag] if remake else profile['quota']),'Country focus quota: '+tag)
    gfx={}
    for p in (MOD/'interface').rglob('*.gfx'):
        for group in parse(p.read_text(encoding='utf-8-sig')):
            if not isinstance(group.value,list):continue
            for entry in group.value:
                if isinstance(entry.value,list) and scalar(entry.value,'name'):
                    name=scalar(entry.value,'name').strip('"');gfx[name]=entry
    artkeys=['campaign','register','rebuild','accord','sweep','guerrilla','civil','supply','pact','specialty','offer']
    for key in artkeys:
        for kind,size in [('decision',(32,32)),('category',(52,40))]:
            name='GFX_decision_'+('category_' if kind=='category' else '')+'sof_cw_'+key
            check(name in gfx,'Art sprite registered: '+name)
            if name not in gfx:continue
            rows=gfx[name].value;tex=MOD/scalar(rows,'texturefile').strip('"')
            check(tex.is_file(),'Art texture exists: '+str(tex.relative_to(ROOT)))
            if not tex.is_file():continue
            im=Image.open(tex).convert('RGBA');a=im.getchannel('A')
            check(im.size==size,'Native art size: '+name)
            check(a.getextrema()==(0,255),'Native art alpha: '+name)
            check(scalar(rows,'noOfFrames')=='1','Single-frame decision art: '+name)
    decisions=categories=0
    for rel in ['common/decisions/sofzh_unification.txt','common/decisions/sofzh_occupation.txt','common/decisions/sof20_regions.txt',
                'common/decisions/categories/sofzh_unification.txt','common/decisions/categories/sofzh_occupation.txt','common/decisions/categories/sof20_regions.txt']:
        rows=parse((MOD/rel).read_text(encoding='utf-8-sig'))
        for icon in [r.value for r in walk(rows) if r.key=='icon']:
            cat='/categories/' in rel;name='GFX_decision_'+('category_' if cat else '')+icon
            check(name in gfx,'Decision icon resolves: '+rel+' -> '+name)
            if cat:categories+=1
            else:decisions+=1
    check(decisions==132 and categories==21,'132 painted decisions and 21 categories')
    main=one(one(parse((MOD/'common/decisions/sofzh_unification.txt').read_text(encoding='utf-8-sig')),'sofzh_unification_campaign_category').value,'sofzh_unification_border_campaign').value
    check(scalar(main,'cost')=='25' and scalar(main,'days_re_enable')=='45','Border campaign fee/cooldown')
    check(scalar(one(main,'available').value,'has_country_flag')=='sofzh_unification_war_ready','Campaign still requires authorization')
    effect=one(parse((MOD/'common/scripted_effects/sof_civilwar_gui.txt').read_text(encoding='utf-8-sig')),'sof_cw_refresh').value
    forbidden={'add_core_of','create_wargoal','add_political_power','add_manpower','add_equipment_to_stockpile','add_ideas','set_technology'}
    check(not any(r.key in forbidden for r in walk(effect)),'GUI refresh remains read-only')
    groups=one(parse((MOD/'interface/sof_civilwar.gui').read_text(encoding='utf-8')),'guiTypes').value
    containers={scalar(r.value,'name').strip('"'):r.value for r in entries(groups,'containerWindowType')}
    window=containers['sof_cw_decision_window'];size=one(window,'size').value
    check((scalar(size,'width'),scalar(size,'height'))==('510','500'),'Native panel dimensions')
    local_functions={scalar(r.value,'name') for r in parse((MOD/'common/scripted_localisation/sof_civilwar_gui.txt').read_text(encoding='utf-8'))}
    for value in loc.values():
        for function in re.findall(r'\[(GetSofCw\w+)\]',value):check(function in local_functions,'GUI dynamic text resolves: '+function)
    for r in walk(window):
        if r.key in ['spriteType','quadTextureSprite']:
            name=r.value.strip('"');check(name in gfx or name=='GFX_flag_small','GUI custom sprite resolves: '+name)
        if r.key in ['text','buttonText','pdx_tooltip'] and r.value!='""':check(r.value.strip('"') in loc,'GUI text resolves: '+r.value)
    for p in (MOD/'common/technologies').glob('sof20*.txt'):parse(p.read_text(encoding='utf-8-sig'))
    for p in (ROOT/'art/civilwar/source').glob('*.png'):
        im=Image.open(p)
        if p.stem!='background':check(im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255),'Master transparent: '+p.name)
    if remake:
        from validate_vanilla import audit
        audit(check,loc,gfx)
    if version.startswith('4.'):
        from validate_focus_art import audit as audit_focus_art
        audit_focus_art(check,gfx)
    if version in ['4.1.0','4.2.0']:
        from validate_historical import audit as audit_historical
        audit_historical(check,gfx)
    report=dict(ok=not errors,version=version,checks=checks,errors=errors,countries=focus_counts,focus_total=sum(focus_counts.values()),
        decisions=decisions,categories=categories,game_engine_verified=False,scope='Portable source and art audits; no game, browser or savegame execution')
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args();report=validate()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if report['ok'] else 1)

if __name__=='__main__':main()
