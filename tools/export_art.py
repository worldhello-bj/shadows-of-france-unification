"""Technical resizing/export of committed generated masters; no creative edits."""
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'art/civilwar/source'
EXPORT=ROOT/'art/civilwar/exports'
NATIVE=ROOT/'mod/gfx/interface/sof_civilwar'

def main():
    EXPORT.mkdir(parents=True,exist_ok=True);NATIVE.mkdir(parents=True,exist_ok=True)
    for p in SOURCE.glob('*.png'):
        im=Image.open(p).convert('RGBA')
        if p.stem=='background':
            im.resize((510,500),Image.Resampling.LANCZOS).save(NATIVE/'panel.dds');continue
        assert im.getchannel('A').getextrema()==(0,255),p
        for size in [32,48,64,128]:
            small=im.resize((size,size),Image.Resampling.LANCZOS);small.save(EXPORT/f'{p.stem}-{size}.png')
            if size==32:small.save(NATIVE/f'decision_{p.stem}.dds')
        category=Image.new('RGBA',(52,40),(0,0,0,0))
        category.alpha_composite(im.resize((40,40),Image.Resampling.LANCZOS),(6,0));category.save(NATIVE/f'category_{p.stem}.dds')
    print('Exported native DDS and 32/48/64/128px review PNG files.')

if __name__=='__main__':main()
