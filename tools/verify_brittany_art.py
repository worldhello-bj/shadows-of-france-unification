"""Check actual artwork bindings and preserve pre-art gameplay semantics."""
from pathlib import Path
import hashlib
import json
from PIL import Image
from hoi4_script import parse, entries, scalar, walk
from brittany_art import ROOT, ROUTES, ROLES


def structure(rows, skip=()):
    result=[]
    for r in rows:
        if r.key in skip:continue
        value=structure(r.value,skip) if isinstance(r.value,list) else r.value
        # A later syntax repair spells inclusive gates as native NOT < / NOT >.
        # Canonicalise that exact equivalence, without modifying frozen inputs.
        if r.operator in ('>=','<='):
            result.append(('NOT','=',[(r.key,'<' if r.operator=='>=' else '>',value)]))
        else:result.append((r.key,r.operator,value))
    return result


def main():
    mod=ROOT/'mod';baseline=ROOT/'references/brittany-art-before-20261006/mod'
    spec=json.loads((ROOT/'design/brittany-focus.json').read_text(encoding='utf-8'))
    originals=json.loads((ROOT/'art/brittany/generation-prompts.json').read_text(encoding='utf-8'))['assets']
    checks=[]
    def check(ok,label):checks.append(dict(ok=bool(ok),description=label))
    check(len(originals)==21 and len({r['key'] for r in originals})==21,'All 21 requested originals preserved')
    for r in originals:
        p=ROOT/r['file'];im=Image.open(p).convert('RGBA')
        check(hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],'Reviewed PNG original hash: '+r['key'])
        if r['transparent']:
            alpha=im.getchannel('A')
            check(alpha.getextrema()==(0,255),'Genuine alpha: '+r['key'])
            check(all(alpha.getpixel(pos)==0 for pos in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]),'Transparent outer corners: '+r['key'])
    sprites={}
    for path in (mod/'interface').glob('sof_brittany*.gfx'):
        for group in entries(parse(path.read_text(encoding='utf-8')),'spriteTypes'):
            for item in group.value:
                name=scalar(item.value,'name').strip('"')
                check(name not in sprites,'Unique Brittany sprite: '+name);sprites[name]=item.value
                texture=scalar(item.value,'texturefile').strip('"')
                check(texture in spec['files'],'Texture in package manifest: '+texture)
                with Image.open(mod/texture) as im:
                    frames=int(scalar(item.value,'noOfFrames','1'))
                    check(im.width%frames==0 and im.width>0 and im.height>0,'Native frame dimensions: '+name)
    for route in ROUTES:
        for role in ROLES:
            key=route+'_'+role;p=mod/'gfx/interface/sof_brt/military'/(key+'.dds')
            im=Image.open(p).convert('RGBA')
            check(im.size==(192,96) and im.getchannel('A').getextrema()==(0,255),'Readable transparent focus sheet: '+key)
    for row in walk(parse((mod/'common/ideas/sof_brittany.txt').read_text(encoding='utf-8'))):
        if row.key=='picture':check('GFX_idea_'+row.value in sprites,'Spirit sprite resolves: '+row.value)
    for rel in ['events/sof_brittany.txt','events/sof_brittany_hometowns.txt']:
        for row in walk(parse((mod/rel).read_text(encoding='utf-8'))):
            if row.key=='picture':check(row.value in sprites,'Event illustration resolves: '+row.value)
    for key in ['parliament','home_loss','home_recovery']:
        check(Image.open(mod/'gfx/event_pictures'/('sof_brt_'+key+'.dds')).size==(430,150),'Native event picture size: '+key)
    for rel in ['common/ideas/sof_brittany.txt','events/sof_brittany.txt','events/sof_brittany_hometowns.txt']:
        check(structure(parse((mod/rel).read_text(encoding='utf-8')),['picture'])==structure(parse((baseline/rel).read_text(encoding='utf-8')),['picture']),'Gameplay unchanged under visual replacements: '+rel)
    allowed={'common/ideas/sof_brittany.txt','events/sof_brittany.txt','events/sof_brittany_hometowns.txt',
             'interface/sof_brittany_council.gui','interface/sof_brittany_council.gfx',
             'localisation/simp_chinese/replace/sof_brittany_council_l_simp_chinese.yml'}
    for old in baseline.rglob('*'):
        if not old.is_file():continue
        rel=old.relative_to(baseline).as_posix()
        if rel not in allowed and not rel.endswith('.dds'):
            same=old.read_bytes()==(mod/rel).read_bytes()
            if not same and rel in ['common/scripted_effects/sof_brittany.txt','common/scripted_guis/sof_brittany_council.txt']:
                same=structure(parse(old.read_text(encoding='utf-8')))==structure(parse((mod/rel).read_text(encoding='utf-8')))
            check(same,'Other gameplay file unchanged or equivalent native inclusive gate: '+rel)
    layout=json.loads((ROOT/'design/brittany-gui-layout.json').read_text(encoding='utf-8'))
    for item in layout['texts']:
        check(item['x']>=0 and item['y']>=0 and item['x']+item['width']<=layout['width'] and item['y']+item['height']<=layout['height'],'Text bounds: '+item['name'])
    for item in layout['icons']:
        rows=sprites['GFX_sof_brt_ui_'+item['asset']];texture=scalar(rows,'texturefile').strip('"')
        im=Image.open(mod/texture);frames=int(scalar(rows,'noOfFrames','1'))
        check(item['x']>=0 and item['y']>=0 and item['x']+im.width//frames<=layout['width'] and item['y']+im.height<=layout['height'],'Icon bounds: '+item['name'])
    changed=[]
    for rel in spec['files']:
        old=baseline/rel
        if not old.exists() or old.read_bytes()!=(mod/rel).read_bytes():changed.append(rel)
    report=dict(ok=all(r['ok'] for r in checks),checks=len(checks),errors=[r['description'] for r in checks if not r['ok']],originals=21,transparent_originals=16,military_badges=15,event_pictures=3,runtime_changes=len(changed),files=changed,gameplay_preserved=True,game_engine_verified=False,visual_qa='Authored texture/layout previews, not engine screenshots')
    path=ROOT/'docs/reports/brittany/art-verification.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False))
    assert report['ok'],report['errors']


if __name__=='__main__':main()
