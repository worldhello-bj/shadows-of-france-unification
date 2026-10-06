"""Execute bounded fixtures of the actual decision scripts; no engine claims."""
import argparse, hashlib, json, re
from copy import deepcopy
from build_decision_adaptation import ROOT, MOD, REF, PASS, PROFILES, EXISTING, NEW, LOC, REPAIR, inclusive_repair
from hoi4_script import parse, one, entries, scalar, walk
from validate_marseille_red import Scripts, World, shape
from validate_ideology_panel import Fixture
from ideology_modifiers import bonuses


class ReformWorld(World):
    def test(self, row, ctx):
        if row.key == 'has_country_leader_ideology':
            return ctx['cur']['ideology'] == row.value
        if row.key == 'compliance':
            return self.compare(ctx['cur']['compliance'], float(row.value), row.operator)
        return super().test(row, ctx)

    def execute(self, rows, ctx):
        for row in rows:
            if row.key == 'hidden_effect':
                self.execute(row.value, ctx)
            elif row.key == 'set_country_leader_ideology':
                ctx['cur']['ideology'] = row.value
            elif row.key == 'sofzh_refresh_ideology_chart':
                c = ctx['cur']
                f = Fixture(c['support'], c['government'], c['ideology']).run()
                c['chart'] = f.variables
            else:
                super().execute([row], ctx)

    def select(self, decision):
        c = self.countries['MRS']; ctx = self.ctx()
        if not self.cond(one(decision, 'visible').value, ctx) or not self.cond(one(decision, 'available').value, ctx) or c['political_power'] < float(scalar(decision, 'cost')):
            return False
        c['political_power'] -= float(scalar(decision, 'cost'))
        self.execute(one(decision, 'complete_effect').value, ctx)
        return True


def audit(check):
    data = json.loads((ROOT / 'design/decision-adaptation.json').read_text(encoding='utf-8'))
    s = Scripts()
    decisions = one(parse((MOD / EXISTING[0]).read_text(encoding='utf-8-sig')), 'sofzh_political_direction_category').value
    old = one(parse((REF / EXISTING[0]).read_text(encoding='utf-8-sig')), 'sofzh_political_direction_category').value
    check(len(decisions) == 12 and {r.key for r in decisions} == {r.key for r in old}, 'Retain all twelve decision IDs')
    for rel, digest in data['source_before'].items():
        check(hashlib.sha256((REF / rel).read_bytes()).hexdigest() == digest, 'Stable adaptation baseline: ' + rel)
    for rel in REPAIR:
        before = (REF / rel).read_bytes().decode('utf-8-sig')
        after = (MOD / rel).read_bytes().decode('utf-8-sig')
        check(after == inclusive_repair(before), 'Only equivalent inclusive comparisons changed: ' + rel)
    for root in ['common/decisions', 'common/scripted_triggers', 'common/scripted_effects']:
        for path in (MOD / root).rglob('*.txt'):
            check(not any(r.operator in ('>=', '<=') for r in walk(parse(path.read_text(encoding='utf-8-sig')))), 'Native comparison syntax: ' + path.name)
    loc_text = (MOD / LOC).read_text(encoding='utf-8-sig')
    loc = dict(re.findall(r'^ ([^ :]+):\d* "(.*)"$', loc_text, re.M))
    texts = {scalar(r.value, 'name'): entries(r.value, 'text') for r in parse((MOD / NEW[1]).read_text(encoding='utf-8-sig'))}
    def label(name, w):
        for row in texts[name]:
            trigger = entries(row.value, 'trigger')
            if not trigger or w.cond(trigger[0].value, w.ctx()):
                return scalar(row.value, 'localization_key')
        raise AssertionError(name)
    def scenario(group, alias, pp=100):
        w = ReformWorld(s)
        c = w.countries['MRS']
        c.update(government=group, ideology=alias, political_power=pp, support=(30, 35, 15, 20), leader='leader-identity', traits=['retained-trait'])
        return w, c
    cases = 0
    for ident, group, title, aliases, _ in PROFILES:
        decision = one(decisions, 'sofzh_adopt_' + ident).value
        original = one(old, 'sofzh_adopt_' + ident).value
        check(shape([r for r in decision if r.key not in ('visible', 'available', 'complete_effect')]) == shape([r for r in original if r.key not in ('visible', 'available', 'complete_effect')]), 'Preserve price, icon and AI: ' + ident)
        check(bonuses(MOD, ident) in loc['sofzh_adopt_' + ident + '_desc'], 'Description matches four actual modifiers: ' + ident)
        check('$sofzh_adopt_' + ident + '_desc$' not in (MOD / EXISTING[2]).read_text(encoding='utf-8-sig'), 'Chart tooltip independent of reform status: ' + ident)
        helper = 'GetSofzhReformStatus' + ''.join(v.title() for v in ident.split('_'))
        for alias in aliases.split():
            w, c = scenario(group, alias)
            before = deepcopy(c)
            check(not w.select(decision) and c == before, 'Active alias cannot repeat or pay: ' + alias)
            check(label(helper, w) == 'sofzh_reform_status_current', 'Current label: ' + alias)
            cases += 1
        # Switch from another profile inside this party with exactly enough PP.
        other = next(p for p in PROFILES if p[1] == group and p[0] != ident)
        w, c = scenario(group, other[3].split()[0], 35)
        c['ideas']['sofzh_ideology_' + other[0]] = None
        for row in decisions:
            check(w.cond(one(row.value, 'visible').value, w.ctx()), 'All profiles visible: ' + row.key)
        check(w.select(decision), '35 PP boundary accepts: ' + ident)
        check(c['political_power'] == 0 and c['ideology'] == aliases.split()[0], 'Charge once and apply canonical subtype: ' + ident)
        check(c['government'] == group and c['leader'] == 'leader-identity' and c['traits'] == ['retained-trait'] and c['support'] == (30, 35, 15, 20), 'Retain leader, traits, party and popularity: ' + ident)
        check(set(c['ideas']) == {'sofzh_ideology_' + ident}, 'Replace rather than stack generic spirits: ' + ident)
        check(c['chart']['sofzh_chart_' + ident] == dict(democratic=30, communism=35, fascism=15, neutrality=20)[group], 'Immediate chart refresh while paused: ' + ident)
        before = deepcopy(c); w.execute(one(decision, 'complete_effect').value, w.ctx())
        check(c == before, 'Repeated completion is guarded: ' + ident)
        other_decision = one(decisions, 'sofzh_adopt_' + other[0]).value
        c['political_power'] = 100
        w.day = 179
        check(not w.select(other_decision) and label('GetSofzhReformStatus' + ''.join(v.title() for v in other[0].split('_')), w) == 'sofzh_reform_status_cooldown', 'Shared cooldown blocks day 179: ' + ident)
        w.day = 180
        check(w.select(other_decision), 'Cooldown expires on day 180: ' + ident)
        w, c = scenario(group, other[3].split()[0], 34)
        check(not w.select(decision) and c['political_power'] == 34, '34 PP boundary blocks: ' + ident)
        w, c = scenario(group, other[3].split()[0])
        c['flags']['sofzh_political_reform_cooldown'] = (0, 180)
        other_party = next(p for p in PROFILES if p[1] != group)
        c['government'] = other_party[1]; c['ideology'] = 'unknown_legacy_subtype'
        blocked = next(p for p in PROFILES if p[1] == other_party[1] and p[0] not in ('liberal', 'revolutionary', 'fascist', 'regionalist'))
        party_decision = one(decisions, 'sofzh_adopt_' + blocked[0]).value
        w.day = 179
        check(not w.select(party_decision) and c['political_power'] == 100, 'Changing ruling party cannot evade shared cooldown: ' + ident)
        before = deepcopy(c)
        w.execute(one(decision, 'complete_effect').value, w.ctx())
        check(c == before, 'Stale completion after party change is guarded: ' + ident)
        for target_group in ('democratic', 'communism', 'fascism', 'neutrality'):
            if target_group == group: continue
            w, c = scenario(target_group, 'unknown_legacy_subtype')
            before = deepcopy(c)
            check(not w.select(decision) and c == before, 'Wrong ruling party blocks without payment: ' + ident + ' ' + target_group)
        w, c = scenario('communism', 'marxism')
        c['flags']['sof_mrs_red_government'] = (0, None)
        check(not w.select(decision) and c['political_power'] == 100 and not c['ideas'], 'Red Marseille blocks generic reforms: ' + ident)
        check(label(helper, w) == 'sofzh_reform_status_red', 'Red Marseille gets explicit explanation: ' + ident)
        w, c = scenario(group, other[3].split()[0]); c['has_capitulated'] = True
        check(not w.select(decision), 'Capitulation blocks reforms: ' + ident)
        w, c = scenario(group, other[3].split()[0]); c['cap'] = 1
        check(not w.select(decision), 'Non-French capital blocks reforms: ' + ident)
        cases += 11
    # Exact float/integer equality: no epsilon adjustments.
    for key, boundary in [('resistance', 35), ('resistance', 60), ('compliance', 60)]:
        rows = parse(inclusive_repair(f'{key} >= {boundary}'))
        for value in (boundary - .001, boundary, boundary + .001):
            w, c = scenario('democratic', 'liberalism')
            state = w.states[463]; state[key] = value
            check(w.cond(rows, w.ctx(463)) == (value >= boundary), f'Inclusive state boundary: {key} {value}')
    mrs = one(parse((MOD / 'common/decisions/sof_mrs_red.txt').read_text(encoding='utf-8-sig')), 'sof_mrs_red_politics').value
    academy = one(mrs, 'sof_mrs_red_engineering_slot').value
    for civ in range(14):
        for mil in range(14):
            w, c = scenario('communism', 'marxism')
            c['flags']['sof_mrs_red_government'] = (0, None)
            w.states[463].update(civ=civ, mil=mil)
            check(w.cond(one(academy, 'available').value, w.ctx()) == (civ + mil >= 12), f'Academy total factory threshold: {civ}+{mil}')
    for name, rows in texts.items():
        for row in rows:
            check(scalar(row.value, 'localization_key') in loc, 'Scripted localization resolves: ' + name)
    check((MOD / LOC).read_bytes().startswith(b'\xef\xbb\xbf'), 'Chinese localization retains BOM')
    return cases


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=str); args = parser.parse_args()
    errors = []; checks = 0
    def check(ok, message):
        nonlocal checks
        checks += 1
        if not ok: errors.append(message)
    cases = audit(check)
    report = dict(ok=not errors, checks=checks, cases=cases, errors=errors, game_engine_verified=False, scope='Actual-script decision and comparison fixtures; no HOI4 execution')
    if args.output:
        from pathlib import Path
        p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False)); raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__': main()
