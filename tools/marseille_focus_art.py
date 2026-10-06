"""Export individually reviewed native illustrations and reject reused artwork."""
from pathlib import Path
from io import BytesIO
import argparse
import collections
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont
from hoi4_script import parse, entries, one, scalar

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod'
PLAN = ROOT / 'design/marseille-focus-art.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def shape(rows):
    return [(r.key, r.operator, shape(r.value) if isinstance(r.value, list) else r.value)
            for r in rows if r.key != 'icon']


def semantic_hash(text):
    return sha(json.dumps(shape(parse(text)), ensure_ascii=False).encode('utf-8'))


def fitted(im):
    """Compare visible content, excluding padding and invisible RGB values."""
    im = im.convert('RGBA')
    box = im.getchannel('A').getbbox()
    assert box, 'Empty focus illustration'
    im = im.crop(box)
    im.thumbnail((86, 86), Image.Resampling.LANCZOS)
    result = Image.new('RGBA', (96, 96))
    result.alpha_composite(im, ((96-im.width)//2, (96-im.height)//2))
    return result


def pixel_hash(im):
    return sha(fitted(im).tobytes())


def registry(mod):
    gfx = {}
    for path in (mod / 'interface').glob('*.gfx'):
        for group in entries(parse(path.read_text(encoding='utf-8-sig')), 'spriteTypes'):
            for row in group.value:
                if isinstance(row.value, list) and scalar(row.value, 'name'):
                    name = scalar(row.value, 'name').strip('"')
                    assert name not in gfx, 'Repeated sprite registration: ' + name
                    gfx[name] = row
    return gfx


def texture_image(mod, sprite):
    texture = scalar(sprite.value, 'texturefile').strip('"')
    im = Image.open(mod / texture).convert('RGBA')
    frames = int(scalar(sprite.value, 'noOfFrames', '1'))
    assert frames > 0 and im.width % frames == 0
    return texture, im.crop((0, 0, im.width//frames, im.height))


def export(put):
    data = json.loads(PLAN.read_text(encoding='utf-8'))
    assert data['visual_review_complete'] and len(data['assets']) == 52
    assert len({a['source_sha256'] for a in data['assets']}) == 52
    sprites = []
    for asset in data['assets']:
        source = ROOT / asset['source']
        assert sha(source.read_bytes()) == asset['source_sha256'], source
        image = fitted(Image.open(source))
        buffer = BytesIO()
        image.save(buffer, format='DDS')
        put(asset['texture'], buffer.getvalue())
        sprites.append('spriteType = { name = "' + asset['sprite'] + '" texturefile = "' +
                       asset['texture'] + '" noOfFrames = 1 }')
    put('interface/sof_mrs_red_focus.gfx', 'spriteTypes = {\n' + '\n'.join(sprites) + '\n}')


def audit(check, gfx=None, mod=MOD):
    data = json.loads(PLAN.read_text(encoding='utf-8'))
    assets = {a['id']: a for a in data['assets']}
    tree_text = (mod / 'common/national_focus/sof_mrs_red.txt').read_text(encoding='utf-8')
    tree = one(parse(tree_text), 'focus_tree').value
    nodes = entries(tree, 'focus')
    public = entries(parse((mod / 'common/national_focus/sof_mrs_shared_generic.txt')
                           .read_text(encoding='utf-8')), 'shared_focus')
    check(data['visual_review_complete'], 'Marseille artwork selection was reviewed individually')
    check(len(assets) == 52 and set(assets) == {scalar(n.value, 'id') for n in nodes},
          'Every new Marseille focus owns one reviewed illustration')
    check(len({a['native_texture_sha256'] for a in assets.values()}) == 52,
          '52 different original native artwork files')
    check(len({a['source_sha256'] for a in assets.values()}) == 52,
          '52 different source images, not sprite aliases')
    preserved = semantic_hash(tree_text) == data['gameplay_sha256']
    if not preserved and (ROOT/'design/decision-adaptation.json').is_file():
        from build_decision_adaptation import REF, inclusive_repair
        original = (REF/'common/national_focus/sof_mrs_red.txt').read_text(encoding='utf-8-sig')
        preserved = semantic_hash(original) == data['gameplay_sha256'] and tree_text == inclusive_repair(original)
    check(preserved,
          'Icon correction preserves all focus gameplay, layout and dependencies')
    gfx = registry(mod) if gfx is None else gfx
    sprites = []; textures = []; rendered = []; normalized = []
    for node in nodes + public:
        ident = scalar(node.value, 'id'); name = scalar(node.value, 'icon')
        sprites.append(name)
        check(name in gfx, 'Marseille focus sprite exists: ' + ident)
        if name not in gfx:
            continue
        texture, image = texture_image(mod, gfx[name])
        textures.append(texture)
        rendered.append(sha(image.tobytes())); normalized.append(pixel_hash(image))
        if ident in assets:
            asset = assets[ident]; source = ROOT / asset['source']
            check(name == asset['sprite'] and texture == asset['texture'],
                  'Marseille focus uses its own registered texture: ' + ident)
            check(sha(source.read_bytes()) == asset['source_sha256'],
                  'Reviewed source provenance preserved: ' + ident)
            check(image.size == (96, 96) and image.getchannel('A').getextrema() == (0, 255),
                  '96px Marseille icon has transparent background: ' + ident)
            check(image.getpixel((0, 0))[3] == 0 and
                  image.tobytes() == fitted(Image.open(source)).tobytes(),
                  'Exported DDS exactly matches reviewed artwork: ' + ident)
    for label, values in [('sprite names', sprites), ('texture paths', textures),
                          ('rendered pixels', rendered), ('visible normalized artwork', normalized)]:
        check(len(values) == 205 and len(set(values)) == 205,
              'Entire Marseille tree has 205 different ' + label)
    # The new illustrations also avoid the existing Paris/Corsica originals.
    major = json.loads((ROOT / 'design/unique-focus-art.json').read_text(encoding='utf-8'))
    reserved = {pixel_hash(Image.open(ROOT / a['source'])) for a in major['assets']}
    for asset in assets.values():
        check(pixel_hash(Image.open(ROOT / asset['source'])) not in reserved,
              'Marseille artwork does not repeat a retained major illustration: ' + asset['id'])


def contacts():
    data = json.loads(PLAN.read_text(encoding='utf-8'))
    assets = data['assets']; width = 1440; height = 95 + ((len(assets)+7)//8)*154
    canvas = Image.new('RGB', (width, height), '#172128'); draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 15)
    title = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 26)
    draw.text((25, 18), '红色马赛 · 52幅独立国策图标', font=title, fill='#f1d6a0')
    draw.text((25, 58), '实际DDS原尺寸预览 · 原版插画逐项筛选 · 完整树205项图像去重 · 非游戏截图',
              font=font, fill='#aabdc5')
    for i, asset in enumerate(assets):
        x = 12+(i%8)*178; y = 94+(i//8)*154
        im = Image.open(MOD/asset['texture']).convert('RGBA')
        canvas.paste(im, (x+41, y), im)
        label = asset['code']+' '+asset['title']
        for j in range(2):
            draw.text((x+89, y+99+j*20), label[j*10:(j+1)*10], font=font,
                      anchor='mt', fill='#e3d7bb')
    path = ROOT/'docs/MARSEILLE-ICONS-PREVIEW.png'; canvas.save(path)
    return path


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--installed', type=Path)
    args = parser.parse_args(); errors = []; checks = 0
    def check(ok, message):
        nonlocal checks
        checks += 1
        if not ok: errors.append(message)
    audit(check, mod=args.installed or MOD)
    report = dict(ok=not errors, checks=checks, errors=errors, new_icons=52,
                  total_tree_icons=205, duplicate_icons=0 if not errors else None,
                  game_engine_verified=False,
                  scope='Registered DDS content, source provenance and gameplay preservation')
    name = 'MARSEILLE-INSTALLED-ART-VERIFICATION.json' if args.installed else 'MARSEILLE-ART-VERIFICATION.json'
    (ROOT/'docs'/name).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if not args.installed and not errors: contacts()
    print(json.dumps(report, ensure_ascii=False)); raise SystemExit(0 if not errors else 1)


if __name__ == '__main__':
    main()
