"""Adapt existing decisions without changing IDs, rewards or party popularity."""
from pathlib import Path
import hashlib, json, re
from build_ideology_panel import ROOT, MOD, PROFILES, build_loc
from hoi4_script import parse, one, entries, replace
from ideology_modifiers import bonuses

PASS = ROOT.parent.parent / 'zh_work/decision-adaptation-pass'
REF = ROOT / 'references/decision-adaptation'
LOC = 'localisation/simp_chinese/replace/sofzh_ideologies_l_simp_chinese.yml'
PANEL_LOC = 'localisation/simp_chinese/replace/sofzh_ideology_panel_l_simp_chinese.yml'
REPAIR = ['common/decisions/sofzh_occupation.txt', 'common/scripted_triggers/sofzh_occupation.txt',
          'common/decisions/sof_mrs_red.txt', 'common/national_focus/sof_mrs_red.txt', 'common/scripted_effects/sof_mrs_red.txt',
          'common/scripted_effects/sofzh_occupation.txt']
EXISTING = ['common/decisions/sofzh_ideologies.txt', LOC, PANEL_LOC] + REPAIR
NEW = ['common/scripted_triggers/sofzh_political_reforms.txt', 'common/scripted_localisation/sofzh_political_reforms.txt']
FILES = EXISTING + NEW
GROUPS = {'democratic': '共和主义', 'communism': '社会主义', 'fascism': '法西斯主义', 'neutrality': '非同盟'}


def inclusive_repair(text):
    """Use native < and >, preserving equality exactly, including floats."""
    changes = []
    def visit(rows):
        for row in rows:
            if row.key == 'check_variable' and isinstance(row.value, list) and len(row.value) == 1 and row.value[0].operator in ('>=', '<='):
                val = row.value[0]
                changes.append((row.start, row.end, f'NOT = {{ check_variable = {{ {val.key} {"<" if val.operator == ">=" else ">"} {val.value} }} }}'))
            elif isinstance(row.value, list):
                visit(row.value)
            elif row.operator in ('>=', '<='):
                changes.append((row.start, row.end, f'NOT = {{ {row.key} {"<" if row.operator == ">=" else ">"} {row.value} }}'))
    visit(parse(text))
    return replace(text, changes)


def write(rel, text, bom=False):
    path = MOD / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    reference = REF / rel
    if reference.exists():
        raw = reference.read_bytes()
        if raw.count(b'\r\n') == raw.count(b'\n') and b'\r\n' in raw:
            text = text.replace('\r\n', '\n').replace('\n', '\r\n')
    path.write_text(text, encoding='utf-8-sig' if bom else 'utf-8', newline='')


def patch_loc(text, values):
    for key, value in values.items():
        line = f' {key}:0 "{value}"'
        pattern = re.compile(r'^ ' + re.escape(key) + r':\d* ".*"$', re.M)
        assert len(pattern.findall(text)) == 1, key
        text = pattern.sub(lambda _: line, text)
    return text


def build():
    PASS.mkdir(parents=True, exist_ok=True)
    for rel in EXISTING:
        target = REF / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((MOD / rel).read_bytes())
    rows = one(parse((MOD / EXISTING[0]).read_text(encoding='utf-8-sig')), 'sofzh_political_direction_category').value
    changes = []
    triggers = ['# Country scope. Engine cost checks political power before the effect.\nsofzh_reform_common = { sofzh_politics_eligible = yes sof_mrs_red_public_allowed = yes has_capitulated = no NOT = { has_country_flag = sofzh_political_reform_cooldown } }']
    scripted = []
    loc = {}
    extra = {
        'sofzh_reform_status_red': '§R红色马赛使用专属政治国策与协调决议，通用路线改革不可用。§!',
        'sofzh_reform_status_current': '§Y已采用此路线，无需重复支付政治点数。§!',
        'sofzh_reform_status_cooldown': '§R改革处于180天共用冷却期内。§!',
        'sofzh_reform_status_capitulated': '§R投降期间无法改革。§!',
        'sofzh_reform_status_ready': '§G可改革：消耗35政治点数，随后进入180天共用冷却。§!',
    }
    for ident, group, title, aliases, _ in PROFILES:
        decision = one(rows, 'sofzh_adopt_' + ident)
        key = 'sofzh_can_adopt_' + ident
        subtype = aliases.split()[0]
        triggers.append(f'{key} = {{ sofzh_reform_common = yes has_government = {group} NOT = {{ sofzh_politics_{ident} = yes }} }}')
        replacement = {
            'visible': 'visible = { sofzh_politics_eligible = yes }',
            'available': f'available = {{ {key} = yes }}',
            'complete_effect': f'''complete_effect = {{
            custom_effect_tooltip = sofzh_adopt_{ident}_tt
            hidden_effect = {{
                if = {{ limit = {{ {key} = yes }}
                    set_country_leader_ideology = {subtype}
                    set_country_flag = {{ flag = sofzh_political_reform_cooldown days = 180 }}
                    sofzh_sync_ideology = yes
                }}
            }}
        }}''',
        }
        for field, value in replacement.items():
            row = one(decision.value, field)
            changes.append((row.start, row.end, value))
        name = 'GetSofzhReformName' + ''.join(w.title() for w in ident.split('_'))
        status = 'GetSofzhReformStatus' + ''.join(w.title() for w in ident.split('_'))
        normal = f'sofzh_reform_name_{ident}'
        current = f'sofzh_reform_current_{ident}'
        wrong = f'sofzh_reform_group_{ident}'
        extra[normal] = f'{GROUPS[group]} · 确立{title}'
        extra[current] = f'§Y{GROUPS[group]} · {title}（当前）§!'
        extra[wrong] = f'§R需由{GROUPS[group]}阵营执政；此决议不会更换执政阵营。§!'
        scripted.append(f'defined_text = {{ name = {name} text = {{ trigger = {{ sofzh_politics_{ident} = yes }} localization_key = {current} }} text = {{ localization_key = {normal} }} }}')
        checks = [('sof_mrs_red_active = yes', 'red'), (f'NOT = {{ has_government = {group} }}', 'group'),
                  (f'sofzh_politics_{ident} = yes', 'current'), ('has_country_flag = sofzh_political_reform_cooldown', 'cooldown'), ('has_capitulated = yes', 'capitulated')]
        cases = ' '.join(f'text = {{ trigger = {{ {test} }} localization_key = {wrong if kind == "group" else "sofzh_reform_status_" + kind} }}' for test, kind in checks)
        scripted.append(f'defined_text = {{ name = {status} {cases} text = {{ localization_key = sofzh_reform_status_ready }} }}')
        effects = bonuses(MOD, ident)
        loc['sofzh_adopt_' + ident] = f'[{name}]'
        loc['sofzh_adopt_' + ident + '_desc'] = f'$' + subtype + f'_desc$\\n所属大类：{GROUPS[group]}\\n[{status}]\\n\\n通用路线效果（同时只生效一条）：\\n{effects}\\n\\n改革仅调整当前执政领袖的细分路线，不更换人物或执政阵营，也不改变党派支持率。成功后立即更新政治光谱。'
        loc['sofzh_adopt_' + ident + '_tt'] = f'采用{title}，替换原通用路线加成。\\n{effects}\\n立即更新政治光谱；180天后可再次改革。红色马赛使用专属政治机制。'
    loc['sofzh_political_direction_category_desc'] = '展示十二种细分政治路线；仅可在当前执政阵营内部改革。黄色标记为当前路线，悬停查看限制与效果。改革消耗35政治点数，所有路线共用180天冷却。红色马赛通过专属政治国策与协调决议管理组织路线。'
    write(EXISTING[0], replace((MOD / EXISTING[0]).read_text(encoding='utf-8-sig'), changes))
    write(LOC, patch_loc((MOD / LOC).read_text(encoding='utf-8-sig'), loc), True)
    write(NEW[0], '\n'.join(triggers) + '\n')
    write(NEW[1], '\n'.join(scripted) + '\n')
    # Keep new helper strings in the existing localization file: no extra package dependency.
    text = (MOD / LOC).read_text(encoding='utf-8-sig')
    for key, value in extra.items():
        if re.search(r'^ ' + re.escape(key) + r':', text, re.M):
            text = patch_loc(text, {key: value})
        else:
            text += f' {key}:0 "{value}"\n'
    write(LOC, text, True)
    for rel in REPAIR:
        write(rel, inclusive_repair((MOD / rel).read_text(encoding='utf-8-sig')))
    build_loc()
    data = dict(format=1, profiles=12, cost=35, cooldown_days=180, files=FILES,
                source_before={rel: hashlib.sha256((REF / rel).read_bytes()).hexdigest() for rel in EXISTING},
                game_engine_verified=False)
    (ROOT / 'design/decision-adaptation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(ok=True, profiles=12, files=len(FILES), game_engine_verified=False)))


if __name__ == '__main__':
    build()
