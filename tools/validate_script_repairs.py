"""Audit parser balance, engine API aliases and project/raid dependency closure."""
import hashlib
import json
from itertools import product
from pathlib import Path

from hoi4_script import TOKENS, parse, walk, one, entries, scalar
from build_script_repairs import repaired

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod'
REF = ROOT / 'references/script-repairs-4.5.1'


def before_documented_api_fix(relative, current):
    """Retain historical art/balance baselines while accepting only the exact R2 fix."""
    if relative != 'mod/common/national_focus/sofzh_corsica.txt' or not (ROOT / 'design/script-repairs-4.5.1.json').is_file():
        return current
    spec = json.loads((ROOT / 'design/script-repairs-4.5.1.json').read_text(encoding='utf-8'))
    row = next(r for r in spec['files'] if r['relative'] == relative)
    original = (REF / relative).read_bytes()
    assert hashlib.sha256(original).hexdigest() == row['previous_sha256']
    assert hashlib.sha256(current).hexdigest() == row['sha256']
    assert original.count(b'add_army_experience = 20') == 1
    assert current == original.replace(b'add_army_experience = 20', b'army_experience = 20')
    return original


def balanced(text):
    depth = 0
    for token in TOKENS.finditer(text):
        if token[0] == '{':
            depth += 1
        elif token[0] == '}':
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def audit(check):
    spec = json.loads((ROOT / 'design/script-repairs-4.5.1.json').read_text(encoding='utf-8'))
    helper_catalog = json.loads((REF / 'native-helper-names.json').read_text(encoding='utf-8'))
    native_helpers = set().union(*map(set, helper_catalog.values()))
    api = {kind: set(json.loads((REF / ('native-'+kind+'.json')).read_text(encoding='utf-8'))['names'])
           for kind in ['effects', 'triggers']}
    check({'army_experience', 'create_equipment_variant'} <= api['effects'], 'Effects confirmed by installed engine documentation')
    check('amount_research_slots' in api['triggers'], 'Research-slot condition confirmed by installed engine documentation')
    definitions = {}
    for kind in ['scripted_effects', 'scripted_triggers']:
        for path in (MOD / 'common' / kind).glob('*.txt'):
            for entry in parse(path.read_text(encoding='utf-8-sig')):
                if entry.key:
                    definitions[entry.key] = entry
    for path in MOD.rglob('*'):
        if path.suffix not in {'.txt', '.gui', '.gfx'}:
            continue
        text = path.read_text(encoding='utf-8-sig')
        check(balanced(text), 'Balanced script: '+path.relative_to(MOD).as_posix())
        tokens = {t[0] for t in TOKENS.finditer(text) if not t[0].startswith('#')}
        for old in ['add_army_experience', 'num_research_slots']:
            check(old not in tokens, 'Supported engine API: '+old+' in '+path.relative_to(MOD).as_posix())
    for folder in ['common/special_projects', 'common/raids']:
        for path in (MOD / folder).rglob('*.txt'):
            for n in walk(parse(path.read_text(encoding='utf-8-sig'))):
                if n.key in native_helpers or (n.key and n.key.startswith(('SP_create_', 'sof_sp_'))):
                    check(n.key in definitions, 'Project/raid helper resolves: '+n.key)
    for name in spec['helpers']:
        check(name in definitions, 'Portable helper defined: '+name)
        if name not in definitions:
            continue
        body = list(walk(definitions[name].value))
        check(any(n.key == 'create_equipment_variant' for n in body), 'Helper creates usable blueprint: '+name)
        check(not any(n.key in native_helpers - set(definitions) for n in body), 'Helper dependency closure: '+name)
        check(not any(n.key in {'original_tag', 'design_team', 'country_event', 'news_event', 'has_completed_focus'}
                      for n in body), 'Helper independent of donor campaigns: '+name)
    for row in spec['files']:
        path = ROOT / row['relative']
        check(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'],
              'Reviewed repair hash: '+row['relative'])
        if row['relative'].endswith('/sof_special_projects_451.txt'):
            regenerated = (REF / 'portable-helpers.txt').read_bytes()
        else:
            regenerated = repaired(row['relative'], (REF / row['relative']).read_bytes())
        check(hashlib.sha256(regenerated).hexdigest() == row['sha256'], 'Repair reproducible: '+row['relative'])
    for rel in ['design/country-design.json', 'design/vanilla-major-remake.json', 'tools/vanilla_local_policy.py']:
        text = (ROOT / rel).read_text(encoding='utf-8-sig')
        check('num_research_slots' not in text and 'add_army_experience' not in text,
              'Generator and design use engine API: '+rel)

    # Validate the caller's COUNTRY scope and DLC gates, plus production variant identity.
    cases = [('land_projects.txt', 'sp_land_military_engineering_vehicles', spec['helpers'][0], 'Gotterdammerung'),
             ('rocket_projects.txt', 'sp_rockets_rocket_engines', spec['helpers'][1], 'By Blood Alone'),
             ('naval_projects.txt', 'sp_naval_ice_carrier', spec['helpers'][2], 'Man the Guns')]
    for filename, _, helper, dlc in cases:
        text = (MOD / 'common/special_projects/projects' / filename).read_text(encoding='utf-8-sig')
        project = next(n for n in parse(text) if any(x.key == helper for x in walk(n.value)))
        country = one(one(project.value, 'project_output').value, 'country_effects')
        branch = next(n for n in entries(country.value, 'if') if any(x.key == helper for x in walk(n.value)))
        check(any(n.key == 'has_dlc' and n.value == '"'+dlc+'"' for n in walk(one(branch.value, 'limit').value)),
              'COUNTRY blueprint preserves DLC gate: '+helper)
        if helper == spec['helpers'][2]:
            production = next(n for n in walk(branch.value) if n.key == 'version_name')
            check(production.value == '"Habakkuk"', 'Production uses generated Habakkuk variant')
            names = [n.value for n in walk(definitions[helper].value) if n.key == 'name']
            check(len(names) == 9 and set(names) == {production.value}, 'All nine carrier technology cases create requested variant')
    nuclear = parse((MOD / 'common/raids/nuclear_raids.txt').read_text(encoding='utf-8-sig'))
    original = parse((REF / 'mod/common/raids/nuclear_raids.txt').read_text(encoding='utf-8-sig'))
    # All native raid effects except original-country story callbacks are identical.
    excluded = {'bathe_in_hellfire_nuclear', 'bathe_in_hellfire_thermonuclear', 'PHI_cobalt_sea_achievement'}
    def normalized(rows):
        return [(n.key, n.operator, normalized(n.value) if isinstance(n.value, list) else n.value)
                for n in rows if n.key not in excluded]
    check(normalized(nuclear) == normalized(original), 'Nuclear damage, units, costs and outcomes preserved exactly')

    # Evaluate every generic technology branch using the actual parsed helper.
    # This proves the fixture's blueprint selection, not execution inside HOI4.
    def selected_variant(rows, techs, radar=False):
        chosen = None
        for entry in rows:
            if entry.key == 'create_equipment_variant':
                return entry.value
            if entry.key in {'if', 'else_if', 'else'}:
                conditions = entries(entry.value, 'limit')
                eligible = all((n.key == 'has_tech' and n.value in techs) or
                               (n.key == 'is_special_project_completed' and radar)
                               for n in conditions[0].value) if conditions else True
                if chosen is None and eligible:
                    chosen = entry
        return selected_variant(chosen.value, techs, radar) if chosen else None
    carrier = definitions[spec['helpers'][2]].value
    for aa, radar, armor, prototype in product([False, True], repeat=4):
        techs = {key for key, active in [('antiair2', aa), ('cavity_magnatron', radar),
                                         ('improved_heavy_armor_scheme', armor)] if active}
        variant = selected_variant(carrier, techs, prototype)
        modules = one(variant, 'modules').value if variant else []
        check(variant is not None and scalar(variant, 'name') == '"Habakkuk"' and
              scalar(variant, 'type') == 'ship_hull_mega_carrier',
              'Carrier blueprint fixture: '+str((aa, radar, armor, prototype)))
        expected_radar = 'ship_radar_2' if radar else ('ship_radar_1' if aa and armor and prototype else 'empty')
        check(scalar(modules, 'fixed_ship_radar_slot') == expected_radar,
              'Carrier radar follows technology fixture: '+str((aa, radar, armor, prototype)))
    rocket = definitions[spec['helpers'][1]].value
    for advanced in [False, True]:
        variant = selected_variant(rocket, {'aa_lmg'} if advanced else set())
        modules = one(variant, 'modules').value if variant else []
        check(scalar(modules, 'fixed_main_weapon_slot') == ('light_mg_4x' if advanced else 'light_mg_2x') and
              scalar(modules, 'engine_type_slot') == 'rocket_engine_1',
              'Rocket blueprint follows weapons technology fixture: '+str(advanced))


if __name__ == '__main__':
    failures = []
    count = [0]
    def check(ok, description):
        count[0] += 1
        if not ok:
            failures.append(description)
    audit(check)
    print(json.dumps(dict(ok=not failures, checks=count[0], errors=failures, game_engine_verified=False)))
    raise SystemExit(bool(failures))
