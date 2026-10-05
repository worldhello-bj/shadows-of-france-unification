"""Portable regional MIO/designer coverage, eligibility and equipment audits."""
import hashlib
import json
import re
from pathlib import Path
from hoi4_script import parse, one, scalar, entries, walk

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod'


def matches(rows, country):
    values = []
    for r in rows:
        if r.key in ['AND', 'OR', 'NOT', 'FROM', 'custom_trigger_tooltip']:
            body = [v for v in r.value if v.key != 'tooltip']
            value = any(matches([v], country) for v in body) if r.key == 'OR' else matches(body, country)
            if r.key == 'NOT': value = not value
        elif r.key in ['original_tag', 'tag']:
            value = country[r.key] == r.value
        elif r.key == 'has_dlc':
            value = country['aat']
        elif r.key == 'has_capitulated':
            value = country['capitulated'] == (r.value == 'yes')
        elif r.key == 'has_completed_focus':
            value = r.value in country['completed']
        elif r.key and r.key.isdigit():
            value = int(r.key) in country['owned'] and int(r.key) in country['controlled']
        elif r.key in ['is_owned_by', 'is_fully_controlled_by']:
            value = True  # Literal state eligibility is evaluated at the outer state block.
        else:
            raise AssertionError('Unknown manufacturer guard: ' + str(r.key))
        values.append(value)
    return all(values)


def audit(check, gfx):
    from build_regional_manufacturers import build
    check(build(check_only=True) == 20, 'Manufacturer script, localization and docs rebuild exactly from authored source')
    design = json.loads((ROOT / 'design/regional-manufacturers.json').read_text(encoding='utf-8'))
    companies = design['manufacturers']
    tags = {p['tag'] for p in json.loads((ROOT / 'design/country-design.json').read_text(encoding='utf-8'))}
    check(len(companies) == 20 and {p['tag'] for p in companies} == tags, 'Every one of the 20 region representatives has a distinctive company')
    organizations = {r.key: r.value for r in parse((MOD / 'common/military_industrial_organization/organizations/sof_regional_manufacturers.txt').read_text(encoding='utf-8'))}
    idea_groups = one(parse((MOD / 'common/ideas/sof_regional_manufacturers.txt').read_text(encoding='utf-8')), 'ideas').value
    legacy = {r.key: (slot.key, r.value) for slot in idea_groups for r in slot.value if isinstance(r.value, list)}
    all_focus = {scalar(n.value, 'id') for p in (MOD / 'common/national_focus').glob('*.txt') for t in entries(parse(p.read_text(encoding='utf-8-sig')), 'focus_tree') for n in entries(t.value, 'focus')}
    states = {int(scalar(one(parse(p.read_text(encoding='utf-8-sig')), 'state').value, 'id')) for p in (MOD / 'history/states').glob('*.txt')}
    loc_file = MOD / 'localisation/simp_chinese/replace/sof_regional_manufacturers_l_simp_chinese.yml'
    check(loc_file.read_bytes().startswith(b'\xef\xbb\xbf'), 'Manufacturer Chinese localization has the required UTF-8 BOM')
    loc = dict(re.findall(r'(?m)^\s+([^\s:]+):\d*\s+"(.*)"', loc_file.read_text(encoding='utf-8-sig')))
    signatures = set()
    for row in companies:
        key = row['id']; org = organizations[key]; slot, idea = legacy[key + '_legacy']
        check(slot == row['legacy_slot'], 'Regional fallback uses the real native exclusive designer slot: ' + key)
        check(row['factory_state'] in states, 'Physical factory site exists: ' + key)
        check(set(row['unlock'] + row['specialize'] + row['capstone']) <= all_focus, 'Existing active and legacy focus milestones resolve: ' + key)
        check(len(entries(org, 'trait')) == 4 and len(entries(org, 'initial_trait')) == 1, 'Four-level organization plus initial regional craft: ' + key)
        for r in walk(org):
            if r.key == 'icon': check(r.value in gfx, 'Native organization art resolves: ' + r.value)
            if r.key in ['name', 'text', 'tooltip']: check(r.value in loc, 'Regional organization player text resolves: ' + r.value)
        check('GFX_idea_' + scalar(idea, 'picture') in gfx, 'Legacy company logo resolves: ' + key)
        traits = entries(org, 'trait'); known = set()
        for trait in traits:
            token = scalar(trait.value, 'token')
            for parent in entries(trait.value, 'any_parent'):
                check(all(v.value in known for v in parent.value), 'Organization trait depends on an earlier level: ' + token)
            known.add(token)
        full = dict(row['initial_equipment']); production = dict(row['initial_production'])
        for trait in row['traits']:
            for target, values in [(full, trait.get('equipment', {})), (production, trait.get('production', {}))]:
                for k, v in values.items(): target[k] = target.get(k, 0) + v
        check(all(abs(v) <= .120001 for v in full.values()) and all(abs(v) <= .060001 for v in production.values()), 'Regional bonuses stay on equipment/lines within authored caps: ' + key)
        check(any(v < 0 if k != 'build_cost_ic' else v > 0 for k, v in row['initial_equipment'].items()), 'Initial specialization has a real performance or price tradeoff: ' + key)
        signature = (tuple(row['equipment']), tuple(sorted(full.items())), tuple(sorted(production.items())))
        check(signature not in signatures, 'A company has its own equipment/bonus combination: ' + key); signatures.add(signature)
        for aat in [False, True]:
            c = dict(original_tag=row['tag'], tag=row['tag'], aat=aat, completed=set(), owned={row['factory_state']}, controlled={row['factory_state']}, capitulated=False)
            check(matches(one(org, 'allowed').value, c) == aat and matches(one(idea, 'allowed').value, c) != aat, 'AAT and traditional designers are mutually isolated: ' + key + ' ' + str(aat))
            check(not matches(one(org, 'available').value, c), 'Unfinished real industry focus keeps company greyed out: ' + key)
            c['completed'] = {row['unlock'][0]}
            check(matches(one(org, 'available').value, c) and matches(one(idea, 'available').value, c), 'Completed actual focus and factory control unlock both representations: ' + key)
            c['controlled'].clear()
            check(not matches(one(org, 'available').value, c) and matches(one(idea, 'cancel').value, c), 'Loss of factory disables organization and cancels appointed fallback: ' + key)
            c['controlled'] = set(c['owned']); c['original_tag'] = 'ZZZ'
            check(not matches(one(org, 'allowed').value, c) and not matches(one(idea, 'allowed').value, c), 'A conquering foreign country cannot obtain the origin-exclusive company: ' + key)
    for asset in design['native_art_assets']:
        check(asset['sprite'] in gfx, 'Company native art registered: ' + asset['sprite'])
        check(hashlib.sha256((ROOT / asset['destination']).read_bytes()).hexdigest() == asset['sha256'], 'Company artwork provenance preserved: ' + asset['sprite'])
