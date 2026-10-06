"""Reproduce the bounded 4.5.1 repairs from reviewed source, without the game install."""
import hashlib
import json
from pathlib import Path

from hoi4_script import parse, walk, one, replace

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / 'references/script-repairs-4.5.1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def repaired(relative, raw):
    if relative in ['tools/vanilla_local_policy.py', 'design/vanilla-major-remake.json',
                    'mod/common/national_focus/sofzh_corsica.txt']:
        assert raw.count(b'add_army_experience = 20') == 1
        return raw.replace(b'add_army_experience = 20', b'army_experience = 20')
    if relative == 'design/country-design.json' or '/national_focus/sof20_' in relative:
        assert raw.count(b'num_research_slots < 5') == (18 if relative.startswith('design/') else 1)
        return raw.replace(b'num_research_slots < 5', b'amount_research_slots < 5')
    if relative == 'mod/common/autonomous_states/colony.txt':
        return raw + (b'\r\n' if b'\r\n' in raw else b'\n') + b'}\n'
    text = raw.decode('utf-8-sig')
    rows = parse(text)
    if relative.endswith('/air_projects.txt'):
        project = next(n for n in rows if any(x.key == 'GER_amerika_bomber_focke_wulf_completion_SP_effects'
                                             for x in walk(n.value)))
        donor = one(one(project.value, 'project_output').value, 'country_effects')
        changes = [(donor.start, donor.end,
                    '# Original German manufacturer bonus requires the removed German campaign.')]
    elif relative.endswith('/land_projects.txt'):
        project = one(rows, 'sp_land_flamethrower_tank')
        effects = one(one(project.value, 'project_output').value, 'country_effects')
        donor = one(effects.value, 'hidden_effect')
        changes = [(donor.start, donor.end,
                    '# Italian tankette-focus bonus removed; generic design bonuses and unlocks retained.')]
    elif relative.endswith('/nuclear_raids.txt'):
        names = {'bathe_in_hellfire_nuclear', 'bathe_in_hellfire_thermonuclear', 'PHI_cobalt_sea_achievement'}
        changes = [(n.start, n.end, '# Original-country story/achievement callback removed.')
                   for n in walk(rows) if n.key in names]
        assert len(changes) == 17
    else:
        names = {'SIA_raid_destroy_all_indochina_ports', 'is_literally_china',
                 'indonesia_increase_escalation_1_effect'}
        changes = [(raid.start, raid.end, '# Nonportable original-country raid removed: '+raid.key)
                   for raid in one(rows, 'types').value
                   if any(n.key in names for n in walk(raid.value))]
        assert changes, relative
    return replace(text, changes).encode('utf-8')


def build():
    spec = json.loads((ROOT / 'design/script-repairs-4.5.1.json').read_text(encoding='utf-8'))
    changed = 0
    for row in spec['files']:
        target = ROOT / row['relative']
        if target.is_file() and digest(target.read_bytes()) == row['sha256']:
            continue
        if row['relative'].endswith('/sof_special_projects_451.txt'):
            candidate = (REFERENCES / 'portable-helpers.txt').read_bytes()
        else:
            source = REFERENCES / row['relative']
            raw = source.read_bytes()
            assert digest(raw) == (row.get('native_sha256') or row['previous_sha256']), row['relative']
            candidate = repaired(row['relative'], raw)
        assert digest(candidate) == row['sha256'], row['relative']
        if target.exists():
            assert digest(target.read_bytes()) == row.get('previous_sha256'), \
                'Other changes in repair target: '+row['relative']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(candidate)
        changed += 1
    print(json.dumps(dict(ok=True, version='4.5.1', changed_files=changed)))


if __name__ == '__main__':
    build()
