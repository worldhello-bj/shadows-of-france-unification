"""Export preserved image_gen originals to native game texture sizes.

Only size/format conversion and sprite-sheet assembly occur here. The original
paintings, colour and alpha are kept; no content retouch or synthetic portraits.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / 'art/brittany/generated-v1'
ROUTES = ['service', 'defence', 'offence']
ROLES = ['command', 'land', 'air', 'sea', 'supply']


def load_art(key, size):
    path = ORIGINALS / (key + '.png')
    assert path.is_file(), ('Missing reviewed generated original', key)
    with Image.open(path) as image:
        return image.convert('RGBA').resize(size, Image.Resampling.LANCZOS)


def badge_sheet(key):
    badge = load_art(key, (96, 96))
    sheet = Image.new('RGBA', (192, 96))
    # Both native frames retain the same painting. Game state overlays remain
    # responsible for locked/completed status; no image recolouring is applied.
    sheet.paste(badge, (0, 0)); sheet.paste(badge, (96, 0))
    return sheet


def spirit_source(key):
    if key in ['committee_economy', 'production', 'civic_bureau'] or any(s in key for s in ['budget', 'logistic', 'repair', 'arsenal', 'supply', 'workshop', 'industry']):
        return 'service_supply'
    if any(s in key for s in ['naval', 'port', 'escort', 'marine', 'dock', 'convoy', 'sea']):
        return 'service_sea'
    if any(s in key for s in ['air', 'watch', 'aviation', 'radar']):
        return 'service_air'
    if any(s in key for s in ['science', 'research', 'staff', 'school', 'education']):
        return 'service_command'
    if key.startswith('defence'):
        return 'defence_command'
    if key.startswith('offence') or key == 'expedition':
        return 'offence_command'
    if any(s in key for s in ['army', 'home', 'infantry', 'reserve', 'garrison', 'militia', 'wartime']):
        return 'service_land'
    return 'seal'


def spirit_picture(key):
    return 'sof_brt_spirit_' + spirit_source(key)


def build_art(mod, root):
    files = []; sprites = ['spriteTypes = {']; exports = []
    def export(key, rel, name, size):
        path = mod / rel; path.parent.mkdir(parents=True, exist_ok=True)
        load_art(key, size).save(path)
        files.append(rel)
        sprites.append(f'spriteType = {{ name = "{name}" texturefile = "{rel}" }}')
        exports.append(dict(source='art/brittany/generated-v1/'+key+'.png', path=rel,
                            size=list(size), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for key in ['parliament', 'home_loss', 'home_recovery']:
        export(key, 'gfx/event_pictures/sof_brt_'+key+'.dds', 'GFX_sof_brt_event_'+key, (430, 150))
    for key in [r+'_'+s for r in ROUTES for s in ROLES] + ['seal']:
        export(key, 'gfx/interface/sof_brt/spirits/'+key+'.dds', 'GFX_idea_sof_brt_spirit_'+key, (64, 64))
    sprites.append('}')
    rel = 'interface/sof_brittany_art.gfx'
    (mod/rel).write_text('\n'.join(sprites)+'\n', encoding='utf-8', newline='\n'); files.append(rel)
    report = dict(format=1, tool='built-in image_gen', original_count=21, exports=exports,
                  method='Native size/format conversion only; PNG originals and generated alpha preserved',
                  portraits='Historical politician placeholders retained; these paintings do not claim real likenesses')
    (root/'design/brittany-art.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return files
