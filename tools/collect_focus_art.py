"""Copy built-in imagegen results into the project without altering masters."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--key');parser.add_argument('--path',type=Path);args=parser.parse_args()
    receipts=json.loads((ROOT/'dist/focus-art-generation-current.json').read_text(encoding='utf-8'))
    specpath=ROOT/'design/focus-art-spec.json';spec=json.loads(specpath.read_text(encoding='utf-8'))
    if args.key:
        assert args.path and args.path.is_file() and args.key in {a['key'] for a in spec['assets']}
        receipts[args.key]=str(args.path)
        (ROOT/'dist/focus-art-generation-current.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for asset in spec['assets']:
        if asset['key'] not in receipts:continue
        path=ROOT/'art/focus/source'/(asset['key']+'.png');path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.png.tmp');shutil.copyfile(receipts[asset['key']],temporary);temporary.replace(path)
        asset['source']=path.relative_to(ROOT).as_posix();asset['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    temporary=specpath.with_suffix('.json.tmp');temporary.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(specpath)
    print(json.dumps({'saved':sum('source_sha256' in x for x in spec['assets']),'total':len(spec['assets'])}))

if __name__=='__main__':main()
