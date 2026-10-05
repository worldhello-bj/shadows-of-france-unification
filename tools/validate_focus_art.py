"""Check generated alpha, runtime bindings and unchanged gameplay structure."""
import hashlib,json
from PIL import Image
from validate import ROOT,MOD
from hoi4_script import parse,one,scalar,entries

def shape(rows):
    return [(x.key,x.operator,shape(x.value) if isinstance(x.value,list) else x.value) for x in rows if x.key not in ['icon','picture']]

def audit(check,gfx):
    spec=json.loads((ROOT/'design/focus-art-spec.json').read_text(encoding='utf-8'))
    binding=json.loads((ROOT/'design/focus-art-bindings.json').read_text(encoding='utf-8'))
    keys={a['key'] for a in spec['assets']}
    check(len(keys)==48,'48 individually generated focus icon masters')
    for asset in spec['assets']:
        path=ROOT/asset['source'];im=Image.open(path)
        check(hashlib.sha256(path.read_bytes()).hexdigest()==asset['source_sha256'],'Generated master preserved: '+asset['key'])
        check(im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255),'Generated master has real alpha: '+asset['key'])
        for role,size in [('focus',(96,96)),('idea',(64,64)),('decision',(32,32)),('category',(52,40))]:
            texture='gfx/interface/sof_focus/'+role+'_'+asset['key']+'.dds';im=Image.open(MOD/texture)
            check(im.size==size and im.mode=='RGBA','Native dimensions and alpha mode: '+texture)
            check(im.getchannel('A').getextrema()==(0,255) and im.getpixel((0,0))[3]==0,'Transparent native edges: '+texture)
    expected={b['id']:b for b in binding['bindings']}
    check(sum(b['role']=='focus' for b in expected.values())==473,'All 473 retained focus nodes have new art')
    for name in ['paris','corsica']:
        tree=one(parse((MOD/'common/national_focus'/f'sofzh_{name}.txt').read_text(encoding='utf-8')),'focus_tree').value
        for n in entries(tree,'focus'):
            fid=scalar(n.value,'id');sprite='GFX_sof_focus_'+expected[fid]['art']
            check(scalar(n.value,'icon')==sprite and sprite in gfx,'New local art binding: '+fid)
    ideas=entries(one(parse((MOD/'common/ideas/sof_vanilla_major.txt').read_text()),'ideas').value,'country')[0].value
    for n in ideas:
        sprite='GFX_idea_'+scalar(n.value,'picture');check(sprite in gfx and scalar(n.value,'picture')=='sof_focus_'+expected[n.key]['art'],'New local idea art: '+n.key)
    for n in parse((MOD/'common/dynamic_modifiers/sof_vanilla_major.txt').read_text()):
        sprite=scalar(n.value,'icon');check(sprite=='GFX_idea_sof_focus_'+expected[n.key]['art'] and sprite in gfx,'New local military-module art: '+n.key)
    for relative,category in [('common/decisions/sof_vanilla_major.txt',False),('common/decisions/categories/sof_vanilla_major.txt',True)]:
        rows=parse((MOD/relative).read_text());nodes=rows if category else one(rows,'sof_van_native_policies').value
        for n in nodes:
            icon=scalar(n.value,'icon');sprite='GFX_decision_'+('category_' if category else '')+icon
            check(icon=='sof_focus_'+expected[n.key]['art'] and sprite in gfx,'New local policy art: '+n.key)
    baseline=json.loads((ROOT/'design/focus-art-behavior-baseline.json').read_text(encoding='utf-8'))
    # This baseline proves the art-only 4.0.2 release. 4.1.0 deliberately
    # changes rewards and is checked by its cabinet/lifecycle scenarios.
    for relative,sha in (baseline['semantic_sha256'].items() if (ROOT/'VERSION').read_text().strip()=='4.0.2' else []):
        current=shape(parse((ROOT/relative).read_text(encoding='utf-8-sig')))
        actual=hashlib.sha256(json.dumps(current,ensure_ascii=False).encode('utf-8')).hexdigest()
        check(actual==sha,'Art update preserves text, layout, triggers and effects: '+relative)
