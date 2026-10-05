"""Reviewed 4.3 gameplay overlay; do not regenerate country history or artwork."""
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from hoi4_script import parse, one, scalar, entries, walk, replace

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod'
PLAN = ROOT / 'design/balance-4.3.json'


def spec():
    return json.loads(PLAN.read_text(encoding='utf-8'))


def emit(rows):
    return ' '.join((r.key + ' ' + (r.operator or '=') + ' ' if r.key else '') +
                    ('{ ' + emit(r.value) + ' }' if isinstance(r.value, list) else r.value) for r in rows)


def save(path, text, bom=False):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + '\n', encoding='utf-8-sig' if bom else 'utf-8', newline='\n')


def exclusion_pairs():
    return {frozenset((p['a'], p['b'])) for p in spec()['removed_exclusions']}


def filter_graph(fields, fid):
    result = copy.deepcopy(fields)
    pairs = exclusion_pairs()
    for row in result:
        if row.key == 'mutually_exclusive':
            row.value = [v for v in row.value if v.key != 'focus' or frozenset((fid, v.value)) not in pairs]
    return [r for r in result if r.key != 'mutually_exclusive' or r.value]


def research_ready(factory_count, slots):
    return slots >= 5 or factory_count >= spec()['research_factories'][str(slots + 1)]


def research_trigger(data):
    cases = ['amount_research_slots > 4']
    for target, factories in data['research_factories'].items():
        current = int(target) - 1
        cases.append(f'AND = {{ amount_research_slots > {current-1} amount_research_slots < {current+1} num_of_factories > {factories-1} }}')
    return 'OR = { ' + ' '.join(cases) + ' }'


def island_building(states, kind):
    cap = 5 if kind == 'infrastructure' else 20
    chain = []
    for i, state in enumerate(states):
        limit = f'owns_state = {state} {state} = {{ is_fully_controlled_by = PREV {kind} < {cap} }}'
        slot = 'add_extra_state_shared_building_slots = 1 ' if kind in ['arms_factory', 'industrial_complex'] else ''
        chain.append(('if' if i == 0 else 'else_if') + ' = { limit = { ' + limit + ' } ' +
                     str(state) + ' = { ' + slot + 'add_building_construction = { type = ' + kind + ' level = 1 instant_build = yes } } }')
    return ' '.join(chain) + ' else = { add_political_power = 40 }'


def resource_helper(kind):
    candidates = []
    for path in sorted((MOD / 'history/states').glob('*.txt')):
        state = one(parse(path.read_text(encoding='utf-8-sig')), 'state').value
        resources = scalar(state, 'resources', [])
        amount = scalar(resources, kind, '0')
        if float(amount) > 0:
            candidates.append(int(scalar(state, 'id')))
    chain = []
    for i, sid in enumerate(candidates):
        chain.append(('if' if i == 0 else 'else_if') + f' = {{ limit = {{ owns_state = {sid} {sid} = {{ sofzh_unification_french_state = yes is_fully_controlled_by = PREV }} }} {sid} = {{ add_resource = {{ type = {kind} amount = 4 }} }} }}')
    if not candidates:
        return 'add_political_power = 40'
    return ' '.join(chain) + ' else = { add_political_power = 40 }'


def balance_reward(fid, rows, data):
    rows = copy.deepcopy(rows)
    updates = [v for v in data['focus_variable_changes'] if v['id'] == fid]
    for row in walk(rows):
        if row.key == 'add_to_variable':
            for v in row.value:
                for change in updates:
                    if v.key == change['var']:
                        assert float(v.value) in [change['old'], change['new']], (fid, v.key)
                        v.value = format(change['new'], '.6g')
        if row.key == 'add_tech_bonus':
            bonus = entries(row.value, 'bonus')
            uses = entries(row.value, 'uses')
            specialist = fid.startswith('SFC_') and any(t in emit(row.value).lower() for t in data['corsica_specialist_tokens'])
            limit = .75 if specialist or fid in ['SFP_laissez_faire', 'SFP_surface_combat', 'SFP_improved_screen_ships'] else .5
            budget = 1.5 if specialist or fid == 'SFP_laissez_faire' else data['research_bonus_budget']
            if uses:
                uses[0].value = str(min(int(uses[0].value), 2))
            if bonus:
                count = int(uses[0].value) if uses else 1
                bonus[0].value = format(min(float(bonus[0].value), limit, budget / count), '.6g')
            for ahead in entries(row.value, 'ahead_reduction'):
                ahead.value = format(min(float(ahead.value), 1), '.6g')
        if row.key == 'add_doctrine_cost_reduction':
            for field in entries(row.value, 'cost_reduction'):
                field.value = format(min(float(field.value), data['doctrine_cap']), '.6g')
            for field in entries(row.value, 'uses'):
                field.value = str(min(int(field.value), 2))
    result = []
    for action in rows:
        body = list(walk([action]))
        if any(r.key == 'add_research_slot' for r in body):
            result.extend(parse('custom_effect_tooltip = sof_balance_research_slot_tt sof_balance_research_slot = yes'))
            continue
        resource = [r for r in body if r.key == 'add_resource']
        if resource:
            kind = scalar(resource[0].value, 'type')
            if kind == 'oil':
                result.extend(parse('add_fuel = 2500'))
                continue
            if kind in ['steel', 'aluminium', 'tungsten', 'chromium', 'rubber']:
                result.extend(parse('sof_balance_resource_' + kind + ' = yes'))
                continue
        if fid in data['naval_design_no_free_dockyards']:
            if any(r.key == 'type' and r.value == 'dockyard' for r in body) or any(r.key == 'add_extra_state_shared_building_slots' for r in body):
                continue
        text = emit([action])
        if 'air_facility' in text:
            text = text.replace('air_facility', 'air_base').replace('air_base < 20', 'air_base < 10')
        result.extend(parse(text))
    if fid == 'SFC_strengthen_northern_industry':
        result = parse(island_building(data['island_north_states'], 'arms_factory') +
                       ' add_tech_bonus = { name = sof_balance_northern_industry bonus = 0.5 uses = 1 category = industry }')
    elif fid == 'SFC_modernize_the_mezzogiorno':
        result = parse(island_building(data['island_south_states'], 'industrial_complex') + ' ' + island_building(data['island_south_states'], 'infrastructure'))
    if fid == 'SFP_france_undividable' and not any(r.key == 'remove_ideas' and r.value == 'sof_van_prs_fra_expanded_citizenship' for r in result):
        result.extend(parse('remove_ideas = sof_van_prs_fra_expanded_citizenship'))
    if fid.startswith('SFC_') and any(r.key == 'add_to_variable' for r in walk(result)) and not any(r.key == 'sof_balance_clamp' for r in walk(result)):
        result.extend(parse('hidden_effect = { sof_balance_clamp = yes }'))
    return result


def apply():
    data = spec()
    records = json.loads((ROOT / 'design/vanilla-major-remake.json').read_text(encoding='utf-8'))
    by_id = {n['id']: n for n in records['nodes']}
    changed = []
    touched = []
    for country in ['paris', 'corsica']:
        rel = f'mod/common/national_focus/sofzh_{country}.txt'
        text = (ROOT / rel).read_text(encoding='utf-8-sig')
        edits = []
        for node in entries(one(parse(text), 'focus_tree').value, 'focus'):
            fid = scalar(node.value, 'id')
            for mutex in entries(node.value, 'mutually_exclusive'):
                kept = filter_graph([mutex], fid)
                edits.append((mutex.start, mutex.end, emit(kept)))
            reward = one(node.value, 'completion_reward')
            new_reward = balance_reward(fid, reward.value, data)
            note_key = fid + '_balance_note_tt'
            if (any(fid in (p['a'], p['b']) for p in data['removed_exclusions']) or
                any(r.key == 'sof_balance_research_slot' for r in new_reward) or
                fid in ['SFC_strengthen_northern_industry', 'SFC_modernize_the_mezzogiorno', 'SFC_oil_in_tripoli']):
                if not any(r.key == 'custom_effect_tooltip' and r.value == note_key for r in new_reward):
                    new_reward.extend(parse('custom_effect_tooltip = ' + note_key))
            edits.append((reward.start, reward.end, 'completion_reward = { ' + emit(new_reward) + ' }'))
            if any(r.key == 'sof_balance_research_slot' for r in new_reward):
                available = one(node.value, 'available')
                if not any(r.key == 'sof_balance_research_ready' for r in walk(available.value)):
                    edits.append((available.end - 1, available.end - 1, ' custom_trigger_tooltip = { tooltip = sof_balance_research_requirements_tt sof_balance_research_ready = yes } '))
            by_id[fid]['actions'] = [emit([r]) for r in new_reward]
        save(rel, replace(text, edits))
        touched.append(rel)
    rel = 'mod/common/ideas/sof_vanilla_major.txt'
    text = (ROOT / rel).read_text(encoding='utf-8-sig')
    ideas = {n.key: n for n in one(one(parse(text), 'ideas').value, 'country').value}
    edits = []
    for rule in data['idea_changes']:
        entry = one(one(ideas[rule['id']].value, 'modifier').value, rule['key'])
        assert float(entry.value) in [rule['old'], rule['new']], rule
        edits.append((entry.start, entry.end, rule['key'] + ' = ' + format(rule['new'], '.6g')))
    save(rel, replace(text, edits))
    touched.append(rel)
    clamp = ' '.join(f'clamp_variable = {{ var = {v} min = {c["min"]} max = {c["max"]} }}' for v, c in data['variable_caps'].items())
    corrections = ' '.join('if = { limit = { has_completed_focus = ' + c['id'] + ' } add_to_variable = { ' + c['var'] + ' = ' + format(c['new'] - c['old'], '.6g') + ' } }' for c in data['focus_variable_changes'])
    ready = research_trigger(data)
    effects = 'sof_balance_clamp = { ' + clamp + ' }\n'
    effects += 'sof_balance_setup_430 = { if = { limit = { has_focus_tree = sofzh_corsica has_country_flag = sof_van_major_initialized NOT = { has_country_flag = sof_balance_migrated_430 } } ' + corrections + ' sof_balance_clamp = yes set_country_flag = sof_balance_migrated_430 } }\n'
    effects += 'sof_balance_research_slot = { if = { limit = { amount_research_slots > 4 } add_political_power = 75 } else_if = { limit = { ' + ready + ' } add_research_slot = 1 } else = { add_political_power = 40 } }\n'
    for kind in ['steel', 'aluminium', 'tungsten', 'chromium', 'rubber']:
        effects += 'sof_balance_resource_' + kind + ' = { ' + resource_helper(kind) + ' }\n'
    save('mod/common/scripted_effects/sof_balance_430.txt', effects)
    save('mod/common/scripted_triggers/sof_balance_430.txt', 'sof_balance_research_ready = { ' + ready + ' }')
    save('mod/common/on_actions/sof_balance_430.txt', 'on_actions = { on_startup = { effect = { every_country = { sof_balance_setup_430 = yes } } } on_weekly = { effect = { sof_balance_setup_430 = yes } } }')
    loc = ['l_simp_chinese:', ' sof_balance_research_requirements_tt:0 "新增第3/4/5个科研槽，分别需要至少6/10/20家工厂。已有5槽可领取财政补助。"', ' sof_balance_research_slot_tt:0 "工业规模满足6/10/20家工厂时增加对应科研槽；已有5槽改为75政治点。完成时重新核验工业规模。"']
    for kind, label in [('steel', '钢铁'), ('aluminium', '铝'), ('tungsten', '钨'), ('chromium', '铬'), ('rubber', '橡胶')]:
        loc.append(f' sof_balance_resource_{kind}_tt:0 "在实际拥有并完整控制、原有{label}产出的法国地区增产4单位；没有合法厂址时改为40政治点。"')
    # Add compact player-facing notes without replacing the authored narrative.
    for fid in by_id:
        notes = []
        if any(fid in (p['a'], p['b']) for p in data['removed_exclusions']):
            notes.append('本项可以与原互斥的技术、建设或地区合作国策兼修；政治路线约束仍然保留。')
        if 'sof_balance_research_slot' in ' '.join(by_id[fid]['actions']):
            notes.append('新增第3、4、5科研槽分别需要6、10、20家工厂。')
        if fid in ['SFC_strengthen_northern_industry', 'SFC_modernize_the_mezzogiorno']:
            notes.append('建设仅落在实际拥有并完整控制的岛内北部或南部城市；无合法地点时按项目补助40政治点。')
        if fid == 'SFC_oil_in_tripoli':
            notes.append('增加2500燃料储备及炼油研究、建设能力，不在任意城市生成天然油矿。')
        if notes:
            loc.append(f' {fid}_balance_note_tt:0 "' + '\\n'.join(notes) + '"')
    save('mod/localisation/simp_chinese/replace/sof_balance_430_l_simp_chinese.yml', '\n'.join(loc), bom=True)
    # Record exact approved changes against the committed 4.2 baseline.
    from unique_focus_art import shape
    git = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]
    for rel in touched:
        before = subprocess.check_output(git + ['show', data['baseline_commit'] + ':' + rel], cwd=ROOT)
        after = (ROOT / rel).read_bytes()
        semantic = lambda raw: hashlib.sha256(json.dumps(shape(parse(raw.decode('utf-8-sig'))), ensure_ascii=False).encode('utf-8')).hexdigest()
        changed.append((rel, dict(before_sha256=hashlib.sha256(before).hexdigest(), after_sha256=hashlib.sha256(after).hexdigest(), before_semantic_sha256=semantic(before), after_semantic_sha256=semantic(after))))
    data['changed_files'] = dict(changed)
    records['version'] = data['version']
    records['balance_policy'] = 'design/balance-4.3.json'
    records['removed_exclusions'] = data['removed_exclusions']
    save('design/vanilla-major-remake.json', json.dumps(records, ensure_ascii=False, indent=2))
    save('design/balance-4.3.json', json.dumps(data, ensure_ascii=False, indent=2))
    save('VERSION', data['version'])
    descriptor = (MOD / 'descriptor.mod').read_text(encoding='utf-8-sig')
    save('mod/descriptor.mod', re.sub(r'(?m)^version="[^"]+"', 'version="' + data['version'] + '"', descriptor))
    print(json.dumps(dict(ok=True, version=data['version'], removed_exclusions=len(data['removed_exclusions']), spirit_fields=len(data['idea_changes']), caps=len(data['variable_caps'])), ensure_ascii=False))


if __name__ == '__main__':
    apply()
