"""Fail releases that reuse focus art, even through alias sprites or copies."""
import json,hashlib,collections
from PIL import Image
from validate import ROOT,MOD
from hoi4_script import parse,one,entries,scalar
from unique_focus_art import shape

def audit(check,gfx):
    data=json.loads((ROOT/'design/unique-focus-art.json').read_text(encoding='utf-8'))
    assets={a['id']:a for a in data['assets']};check(len(assets)==473,'One exclusive illustration for every retained major focus')
    source_hashes=[];pixel_hashes=[];sprites=[];textures=[]
    for country in ['paris','corsica']:
        tree=one(parse((MOD/f'common/national_focus/sofzh_{country}.txt').read_text(encoding='utf-8')),'focus_tree')
        for n in entries(tree.value,'focus'):
            fid=scalar(n.value,'id');a=assets[fid];sprite=scalar(n.value,'icon');sprites.append(sprite)
            check(sprite=='GFX_sof_focus_unique_'+a['key'],'Focus uses its own sprite: '+fid)
            check(sprite in gfx,'Exclusive focus sprite registered: '+fid)
            if sprite not in gfx:continue
            texture=scalar(gfx[sprite].value,'texturefile').strip('"');textures.append(texture)
            check(texture=='gfx/interface/sof_focus_unique/'+a['key']+'.dds','Focus uses its own native texture: '+fid)
            source=ROOT/a['source'];check(source.is_file(),'Exclusive source exists: '+fid)
            if not source.is_file():continue
            source_hash=hashlib.sha256(source.read_bytes()).hexdigest();source_hashes.append(source_hash)
            check(source_hash==a.get('source_sha256'),'Exclusive source provenance: '+fid)
            im=Image.open(source);check(im.mode=='RGBA' and im.getchannel('A').getextrema()[0]==0 and im.getchannel('A').getextrema()[1]>=250,'Exclusive source alpha: '+fid)
            native=Image.open(MOD/texture);check(native.mode=='RGBA' and native.size==(96,96),'Exclusive native focus size and mode: '+fid)
            alpha=native.getchannel('A').getextrema()
            check(native.getpixel((0,0))[3]==0 and alpha[0]==0 and alpha[1]>=250,'Exclusive native transparent padding: '+fid)
            pixel_hashes.append(hashlib.sha256(native.tobytes()).hexdigest())
    for label,values in [('sprite',sprites),('texture',textures),('source image content',source_hashes),('native-resolution pixels',pixel_hashes)]:
        duplicates={k:v for k,v in collections.Counter(values).items() if v>1}
        check(len(values)==473 and not duplicates,'No reused focus '+label+': '+str(duplicates))
    review_path=ROOT/'design/unique-focus-art-review.json'
    check(review_path.is_file(),'Current exclusive focus art has a recorded visual review')
    if review_path.is_file():
        review=json.loads(review_path.read_text(encoding='utf-8'))
        expected_source={a['id']:a['source_sha256'] for a in data['assets']}
        expected_pixels={a['id']:hashlib.sha256(Image.open(ROOT/'art/focus/unique/exports'/(a['key']+'.png')).tobytes()).hexdigest() for a in data['assets']}
        check(review.get('visual_review_complete') is True and review.get('source_sha256')==expected_source and review.get('native_pixel_sha256')==expected_pixels,'Visual review covers exactly the current 473 source and native images')
    for file,expected in data['semantic_baseline']['semantic_sha256'].items():
        if (ROOT/'design/balance-4.3.json').is_file():
            balance=json.loads((ROOT/'design/balance-4.3.json').read_text(encoding='utf-8'))
            if file in balance['changed_files']:
                recorded=balance['changed_files'][file]
                check(recorded['before_semantic_sha256']==expected,'Balance overlay starts from the original reviewed gameplay: '+file)
                expected=recorded['after_semantic_sha256']
        current=shape(parse((ROOT/file).read_text(encoding='utf-8-sig')))
        actual=hashlib.sha256(json.dumps(current,ensure_ascii=False).encode('utf-8')).hexdigest()
        check(actual==expected,'Exclusive art and explicitly reviewed gameplay changes match: '+file)
