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
    from build_regional_manufacturers import build, totals
    check(build(check_only=True) == 20, 'Manufacturer script, localization and docs rebuild exactly from authored source')
    design = json.loads((ROOT / 'design/regional-manufacturers.json').read_text(encoding='utf-8'))
    companies = design['manufacturers']
    check(design['tier_count'] >= 8 and design['traits_per_company'] == 16, 'At least eight real vertical tiers with two growth paths')
    check(design['research_bonus'] == .15 and design['task_capacity'] == 3, 'Stronger initial research and native task capacity')
    tags = {p['tag'] for p in json.loads((ROOT / 'design/country-design.json').read_text(encoding='utf-8'))}
    check(len(companies) == 20 and {p['tag'] for p in companies} == tags, 'Every one of the 20 region representatives has a distinctive company')
    organizations = {r.key: r.value for r in parse((MOD / 'common/military_industrial_organization/organizations/sof_regional_manufacturers.txt').read_text(encoding='utf-8'))}
    idea_groups = one(parse((MOD / 'common/ideas/sof_regional_manufacturers.txt').read_text(encoding='utf-8')), 'ideas').value
    legacy = {r.key: (slot.key, r.value) for slot in idea_groups for r in slot.value if isinstance(r.value, list)}
    all_focus = {scalar(n.value, 'id') for p in (MOD / 'common/national_focus').glob('*.txt') for t in entries(parse(p.read_text(encoding='utf-8-sig')), 'focus_tree') for n in entries(t.value, 'focus')}
    for p in (MOD / 'common/national_focus').glob('*.txt'):
        all_focus.update(scalar(n.value, 'id') for n in entries(parse(p.read_text(encoding='utf-8-sig')), 'shared_focus'))
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
        check(len(entries(org, 'trait')) == 16 and len(entries(org, 'initial_trait')) == 1, 'Sixteen selectable traits plus initial regional craft: ' + key)
        positions = {(int(scalar(one(t.value, 'position').value, 'x')), int(scalar(one(t.value, 'position').value, 'y'))) for t in entries(org, 'trait')}
        check(positions == {(x, y) for x in [1,4] for y in range(8)}, 'Eight actual rows and two columns without visual overlap: ' + key)
        for r in walk(org):
            if r.key == 'icon': check(r.value in gfx, 'Native organization art resolves: ' + r.value)
            if r.key in ['name', 'text', 'tooltip']: check(r.value in loc, 'Regional organization player text resolves: ' + r.value)
        check('GFX_idea_' + scalar(idea, 'picture') in gfx, 'Legacy company logo resolves: ' + key)
        traits = entries(org, 'trait'); known = set(); depth = {}
        for trait in traits:
            token = scalar(trait.value, 'token')
            parents = []
            for parent in entries(trait.value, 'all_parents'):
                check(all(v.value in known for v in parent.value), 'Organization trait depends on an earlier level: ' + token)
                parents.extend(v.value for v in parent.value)
            depth[token] = 1 + max((depth[p] for p in parents), default=0)
            known.add(token)
        check(depth[key + '_trait_8'] == depth[key + '_trait_16'] == 8, 'Both final traits require eight actual successive unlocks: ' + key)
        check({key + '_trait_' + str(i) for i in range(1,5)} <= known, 'Previously selected four tokens survive the extension: ' + key)
        total = totals(row, design); full = total['equipment']; production = total['production']
        check(all(abs(v) <= (design['numeric_caps']['equipment_cost'] if k == 'build_cost_ic' else design['numeric_caps']['equipment']) + .000001 for k,v in full.items()) and all(abs(v) <= design['numeric_caps']['production'] + .000001 for v in production.values()), 'Stronger regional equipment and line bonuses stay within authored budgets: ' + key)
        main = next(iter(row['initial_equipment']))
        check(abs(full[main]) >= (.249999 if main == 'build_cost_ic' else .379999), 'Full growth delivers the requested strong regional specialization: ' + key)
        check(total['organization'] == {'military_industrial_organization_funds_gain': .5, 'military_industrial_organization_research_bonus': .05, 'military_industrial_organization_task_capacity': 1}, 'Full growth reaches 50 percent funds, 20 percent research and four tasks: ' + key)
        check(any(v < 0 if k != 'build_cost_ic' else v > 0 for k, v in row['initial_equipment'].items()), 'Initial specialization has a real performance or price tradeoff: ' + key)
        signature = (tuple(row['equipment']), tuple(sorted(full.items())), tuple(sorted(production.items())))
        check(signature not in signatures, 'A company has its own equipment/bonus combination: ' + key); signatures.add(signature)
        for aat in [False, True]:
            c = dict(original_tag=row['tag'], tag=row['tag'], aat=aat, completed=set(), owned={row['factory_state']}, controlled={row['factory_state']}, capitulated=False)
            check(matches(one(org, 'allowed').value, c) == aat and matches(one(idea, 'allowed').value, c) != aat, 'AAT and traditional designers are mutually isolated: ' + key + ' ' + str(aat))
            check(not matches(one(org, 'available').value, c), 'Unfinished real industry focus keeps company greyed out: ' + key)
            c['completed'] = {row['unlock'][0]}
            check(matches(one(org, 'available').value, c) and matches(one(idea, 'available').value, c), 'Completed actual focus and factory control unlock both representations: ' + key)
            for trait in entries(org, 'trait'):
                token = scalar(trait.value, 'token')
                suffix = int(token.rsplit('_', 1)[1])
                tier = suffix if suffix <= 8 else suffix - 8
                gates = entries(trait.value, 'available')
                if gates:
                    c['completed'] = {row['unlock'][0]}
                    check(not matches(gates[0].value, c), 'Late tier requires its actual industry milestone: ' + token)
                    field = 'specialize' if tier <= 5 else 'capstone'
                    c['completed'].add(row[field][0])
                    check(matches(gates[0].value, c), 'Industry milestone opens the correct later tier: ' + token)
            c['completed'] = {row['unlock'][0]}
            c['controlled'].clear()
            check(not matches(one(org, 'available').value, c) and matches(one(idea, 'cancel').value, c), 'Loss of factory disables organization and cancels appointed fallback: ' + key)
            c['controlled'] = set(c['owned']); c['original_tag'] = 'ZZZ'
            check(not matches(one(org, 'allowed').value, c) and not matches(one(idea, 'allowed').value, c), 'A conquering foreign country cannot obtain the origin-exclusive company: ' + key)
    for asset in design['native_art_assets']:
        check(asset['sprite'] in gfx, 'Company native art registered: ' + asset['sprite'])
        check(hashlib.sha256((ROOT / asset['destination']).read_bytes()).hexdigest() == asset['sha256'], 'Company artwork provenance preserved: ' + asset['sprite'])
