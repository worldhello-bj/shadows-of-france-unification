"""Exercise actual balance scripts, including old-save and research boundaries."""
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from hoi4_script import parse, one, entries, scalar, walk

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod'


class Runner:
    def __init__(self, effects):
        self.effects = effects

    def matches(self, rows, c):
        values = []
        for row in rows:
            if row.key in ['AND', 'OR', 'NOT']:
                v = self.matches(row.value, c) if row.key == 'AND' else any(self.matches([r], c) for r in row.value)
                if row.key == 'NOT':
                    v = not self.matches(row.value, c)
            elif row.key in ['has_country_flag', 'has_completed_focus']:
                v = row.value in c['flags' if row.key == 'has_country_flag' else 'completed']
            elif row.key == 'has_focus_tree':
                v = row.value == c['tree']
            elif row.key in ['amount_research_slots', 'num_of_factories']:
                a, b = c['slots' if row.key == 'amount_research_slots' else 'factories'], float(row.value)
                v = {'>': a > b, '<': a < b, '>=': a >= b, '<=': a <= b, '=': a == b}[row.operator]
            elif row.key == 'sof_balance_research_ready':
                v = self.matches(c['research_trigger'], c)
            else:
                raise AssertionError('Unknown balance guard: ' + str(row.key))
            values.append(v)
        return all(values)

    def execute(self, rows, c):
        taken = False
        for row in rows:
            if row.key in ['if', 'else_if', 'else']:
                if row.key == 'if':
                    taken = False
                if not taken and (row.key == 'else' or self.matches(one(row.value, 'limit').value, c)):
                    self.execute([r for r in row.value if r.key != 'limit'], c)
                    taken = True
            elif row.key == 'set_country_flag':
                c['flags'].add(row.value)
            elif row.key == 'add_to_variable':
                for v in row.value:
                    c['vars'][v.key] = c['vars'].get(v.key, 0) + float(v.value)
            elif row.key == 'clamp_variable':
                var = scalar(row.value, 'var')
                c['vars'][var] = max(float(scalar(row.value, 'min')), min(float(scalar(row.value, 'max')), c['vars'].get(var, 0)))
            elif row.key == 'add_research_slot':
                c['slots'] += int(row.value)
            elif row.key == 'add_political_power':
                c['pp'] += float(row.value)
            elif row.key in self.effects:
                self.execute(self.effects[row.key], c)
            else:
                raise AssertionError('Unknown balance effect: ' + str(row.key))


def audit(check, gfx):
    data = json.loads((ROOT / 'design/balance-4.3.json').read_text(encoding='utf-8'))
    effects = {r.key: r.value for r in parse((MOD / 'common/scripted_effects/sof_balance_430.txt').read_text(encoding='utf-8'))}
    trigger = one(parse((MOD / 'common/scripted_triggers/sof_balance_430.txt').read_text(encoding='utf-8')), 'sof_balance_research_ready').value
    current = {}
    for country in ['paris', 'corsica']:
        rel = f'mod/common/national_focus/sofzh_{country}.txt'
        current.update({scalar(n.value, 'id'): n.value for n in entries(one(parse((ROOT / rel).read_text(encoding='utf-8')), 'focus_tree').value, 'focus')})
    pairs = {frozenset((p['a'], p['b'])) for p in data['removed_exclusions']}
    check(len(pairs) == 28, '28 explicit compatible mutual-exclusion pairs')
    for pair in pairs:
        a, b = tuple(pair)
        for x, y in [(a, b), (b, a)]:
            check(not any(v.key == 'focus' and v.value == y for r in entries(current[x], 'mutually_exclusive') for v in r.value), 'Compatible focuses both remain playable: ' + x + ' / ' + y)
    for a, b in [('SFP_france_first', 'SFP_join_germany'), ('SFP_form_the_popular_front', 'SFP_revive_the_national_bloc'), ('SFC_increase_production', 'SFC_keep_specialization'), ('SFC_specialization', 'SFC_standardization')]:
        check(any(v.value == b for r in entries(current[a], 'mutually_exclusive') for v in r.value), 'Actual political or production choice stays exclusive: ' + a)
    ideas = {r.key: r.value for r in one(one(parse((MOD / 'common/ideas/sof_vanilla_major.txt').read_text(encoding='utf-8')), 'ideas').value, 'country').value}
    for rule in data['idea_changes']:
        actual = float(scalar(one(ideas[rule['id']], 'modifier').value, rule['key']))
        check(actual == rule['new'], 'Authored spirit balance applied: ' + rule['id'] + ' ' + rule['key'])
    for rule in data['focus_variable_changes']:
        found = [float(v.value) for r in walk(one(current[rule['id']], 'completion_reward').value) if r.key == 'add_to_variable' for v in r.value if v.key == rule['var']]
        check(found == [rule['new']], 'Exact focus increment balanced: ' + rule['id'] + ' ' + rule['var'])
    runner = Runner(effects)
    def country():
        return dict(tree='sofzh_corsica', flags={'sof_van_major_initialized'}, completed=set(), vars={}, slots=2, factories=5, pp=0, research_trigger=trigger)
    for rule in data['focus_variable_changes']:
        c = country(); c['completed'] = {rule['id']}; c['vars'][rule['var']] = rule['old']
        runner.execute(effects['sof_balance_setup_430'], c)
        check(abs(c['vars'][rule['var']] - rule['new']) < 1e-8, 'Old completed focus receives the numeric difference once: ' + rule['id'] + ' ' + rule['var'])
        before = copy.deepcopy(c); runner.execute(effects['sof_balance_setup_430'], c)
        check(c == before, 'Repeated migration never repeats a numeric correction: ' + rule['id'] + ' ' + rule['var'])
    c = country(); runner.execute(effects['sof_balance_setup_430'], c)
    check(all(v == 0 for v in c['vars'].values()), 'Fresh game gets no invented completed-focus compensation')
    for var, cap in data['variable_caps'].items():
        for old, expected in [(100, cap['max']), (-100, cap['min'])]:
            c = country(); c['vars'][var] = old; runner.execute(effects['sof_balance_clamp'], c)
            check(c['vars'][var] == expected, 'Actual clamp enforces its authored boundary: ' + var + ' ' + str(old))
    for slots, required in [(2, 6), (3, 10), (4, 20)]:
        for factories in [required - 1, required]:
            c = country(); c.update(slots=slots, factories=factories)
            ready = runner.matches(trigger, c); runner.execute(effects['sof_balance_research_slot'], c)
            check(ready == (factories >= required) and c['slots'] == slots + int(factories >= required), 'Research condition and completion both enforce actual industrial capacity: ' + str((slots, factories)))
    c = country(); c.update(slots=5, factories=0); runner.execute(effects['sof_balance_research_slot'], c)
    check(c['slots'] == 5 and c['pp'] == 75, 'Existing five-slot saves keep slots and receive the stated capped reward')
    for fid, fields in current.items():
        reward = one(fields, 'completion_reward').value
        if any(r.key == 'sof_balance_research_slot' for r in walk(reward)):
            check(any(r.key == 'sof_balance_research_ready' for r in walk(one(fields, 'available').value)), 'Research focus checks capacity before starting: ' + fid)
        for row in walk(reward):
            if row.key == 'add_tech_bonus':
                check(float(scalar(row.value, 'bonus', '0')) <= .75 and int(scalar(row.value, 'uses', '1')) <= 2, 'Research bonus stays within reviewed per-category budget: ' + fid)
            if row.key == 'add_doctrine_cost_reduction':
                check(float(scalar(row.value, 'cost_reduction', '0')) <= .4, 'Doctrine discount cap: ' + fid)
    for rel, hashes in data['changed_files'].items():
        from validate_script_repairs import before_documented_api_fix
        reviewed = before_documented_api_fix(rel, (ROOT / rel).read_bytes())
        check(hashlib.sha256(reviewed).hexdigest() == hashes['after_sha256'], 'Approved gameplay artifact has not drifted: ' + rel)
    on = parse((MOD / 'common/on_actions/sof_balance_430.txt').read_text(encoding='utf-8'))
    check(sum(r.key == 'sof_balance_setup_430' for r in walk(on)) == 2, 'Migration is wired to real startup and weekly actions')
