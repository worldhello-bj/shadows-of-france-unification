"""Export the current source tree to a local installable directory."""
import argparse
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'source-release')
    args = parser.parse_args()
    destination = args.output.resolve()
    source = (ROOT / 'mod').resolve()
    if destination == ROOT or destination == source or source in destination.parents:
        parser.error('Choose an output directory outside mod/ and separate from the repository root.')
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination / 'mod', dirs_exist_ok=True)
    for name in ('install.ps1', 'README.md', 'VERSION'):
        shutil.copy2(ROOT / name, destination / name)
    print(f'Exported source release: {destination}')

if __name__ == '__main__':
    main()
