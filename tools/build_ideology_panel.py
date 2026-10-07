"""Build the native politics-tab sub-ideology chart from existing party data.

Use the game's native political pie renderer and four active representative rows.
The twelve subtypes remain in the read-only data adapter and route tooltips.
"""
from pathlib import Path
import hashlib
import json
import math
import re
from PIL import Image, ImageDraw, ImageFont
from hoi4_script import parse, one, entries, scalar, replace
from ideology_modifiers import bonuses

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / 'mod'
PASS = ROOT.parent.parent / 'zh_work/ideology-panel-pass'
PROFILES = [
    ('liberal', 'democratic', '自由共和主义', 'liberalism populism', '#4BA5E0'),
    ('conservative', 'democratic', '保守共和主义', 'conservatism', '#3266AC'),
    ('social', 'democratic', '社会共和主义', 'socialism', '#58CCD0'),
    ('revolutionary', 'communism', '革命社会主义', 'marxism anti_revisionism buddhist_socialism', '#D84A43'),
    ('vanguard', 'communism', '先锋社会主义', 'leninism stalinism', '#971F35'),
    ('communal', 'communism', '自由社会主义', 'anarchist_communism', '#EE8C78'),
    ('fascist', 'fascism', '法西斯主义', 'fascism_ideology emperor_fascism', '#C59A44'),
    ('national_socialist', 'fascism', '纳粹主义', 'nazism gen_nazism', '#7E622D'),
    ('corporatist', 'fascism', '法团主义', 'sof_corporatism falangism rexism', '#E4C679'),
    ('monarchist', 'neutrality', '君主主义', 'sof_monarchism', '#9776C3'),
    ('authoritarian', 'neutrality', '威权主义', 'despotism oligarchism japan_militarism_ideology', '#78868E'),
    ('regionalist', 'neutrality', '地方自治主义', 'sof_localism moderatism centrism anarchism', '#79AD71'),
]
DEFAULTS = {'democratic': 1, 'communism': 4, 'fascism': 7, 'neutrality': 12}
GUI_REL = 'interface/countrypoliticsview.gui'
SYNC_REL = 'common/scripted_effects/sofzh_ideologies.txt'
NEW_RELS = [
    'interface/sofzh_ideology_panel.gui', 'interface/sofzh_ideology_panel.gfx',
    'common/scripted_triggers/sofzh_ideology_panel.txt',
    'common/scripted_effects/sofzh_ideology_panel.txt',
    'common/scripted_guis/sofzh_ideology_panel.txt',
    'common/on_actions/sofzh_ideology_panel.txt',
    'localisation/simp_chinese/replace/sofzh_ideology_panel_l_simp_chinese.yml',
    'gfx/interface/sofzh_ideology_panel/swatches.dds',
    'gfx/interface/sofzh_ideology_panel/refresh.dds',
]


def write(rel, text, bom=False):
    path = MOD / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8-sig' if bom else 'utf-8'))


def aliases(values, trigger):
    return 'OR = { ' + ' '.join(f'{trigger} = {v}' for v in values.split()) + ' }'


def leaders_by_group():
    subtype_groups = {a: group for _, group, _, values, _ in PROFILES for a in values.split()}
    groups = {g: set() for g in DEFAULTS}
    for path in sorted((MOD / 'common/characters').glob('*.txt')):
        for container in entries(parse(path.read_text(encoding='utf-8-sig')), 'characters'):
            for character in container.value:
                if not isinstance(character.value, list):
                    continue
                for role in entries(character.value, 'country_leader'):
                    group = subtype_groups.get(scalar(role.value, 'ideology'))
                    if group:
                        groups[group].add(character.key)
    return {g: sorted(ids) for g, ids in groups.items()}


def build_triggers(leaders):
    lines = ['# Display-only classification of active party representatives.']
    for ident, group, _, values, _ in PROFILES:
        # PREV first returns to the owning country; inside that scope PREV is
        # the candidate character. The engine accepts a character scope here.
        # This also covers newly created and foreign party representatives.
        opposition = f'    any_character = {{ {aliases(values, "has_ideology")} PREV = {{ has_country_leader = {{ character = PREV ruling_only = no }} }} }}'
        lines.append(f'''sofzh_chart_party_{ident} = {{
 OR = {{
  AND = {{ has_government = {group} {aliases(values, 'has_country_leader_ideology')} }}
  AND = {{ NOT = {{ has_government = {group} }} OR = {{
{opposition}
  }} }}
 }}
}}
''')
    write(NEW_RELS[2], '\n'.join(lines))


def build_effect():
    lines = ['# Native pie renderer; only four active party representatives are shown.',
             '# Only sofzh_chart_* display caches and temporary variables are written.',
             'sofzh_refresh_ideology_chart = {', ' if = { limit = { is_ai = no }']
    for ident, *_ in PROFILES:
        lines.append(f'  set_variable = {{ sofzh_chart_{ident} = 0 }}')
    lines += ['  set_variable = { sofzh_chart_total = 0 }',
              '  set_variable = { sofzh_chart_ruling = 0 }']
    for group, default in DEFAULTS.items():
        lines += [f'  set_variable = {{ sofzh_chart_{group}_frame = {default} }}']
        profiles = [(i, p) for i, p in enumerate(PROFILES, 1) if p[1] == group]
        for j, (i, p) in enumerate(profiles):
            lines.append(f'  {"if" if j == 0 else "else_if"} = {{ limit = {{ sofzh_chart_party_{p[0]} = yes }} set_variable = {{ sofzh_chart_{group}_frame = {i} }} }}')
        lines += [f'  set_variable = {{ sofzh_chart_{group}_pop = party_popularity_100@{group} }}',
                  f'  clamp_variable = {{ var = sofzh_chart_{group}_pop min = 0 max = 100 }}',
                  f'  add_to_variable = {{ sofzh_chart_total = sofzh_chart_{group}_pop }}',
                  f'  if = {{ limit = {{ has_government = {group} }} set_variable = {{ sofzh_chart_ruling = sofzh_chart_{group}_frame }} }}']
    lines += ['  clear_array = sofzh_chart_pie # discard old display-only segment cache',
              '  if = { limit = { check_variable = { var = sofzh_chart_total value = 0 compare = greater_than } }',
              ]
    for gi, group in enumerate(DEFAULTS):
        lines += [f'   divide_variable = {{ sofzh_chart_{group}_pop = sofzh_chart_total }}',
                  f'   multiply_variable = {{ sofzh_chart_{group}_pop = 100 }}']
        for i, p in enumerate(PROFILES, 1):
            if p[1] == group:
                lines.append(f'   if = {{ limit = {{ check_variable = {{ var = sofzh_chart_{group}_frame value = {i} compare = equals }} }} set_variable = {{ sofzh_chart_{p[0]} = sofzh_chart_{group}_pop }} }}')
    lines += ['  }', '  add_to_variable = { sofzh_chart_dirty = 1 }', ' }', '}', '']
    write(NEW_RELS[3], '\n'.join(lines))
    write(NEW_RELS[5], '''on_actions = {
 on_startup = { effect = { every_country = { limit = { is_ai = no } sofzh_refresh_ideology_chart = yes } } }
 on_daily = { effect = { if = { limit = { is_ai = no } sofzh_refresh_ideology_chart = yes } } }
}
''')


def build_gui():
    return build_compact_gui()


def build_compact_gui():
    lines = ['guiTypes = { containerWindowType = {',
             ' name = "sofzh_ideology_panel" position = { x = 175 y = 140 }',
             ' size = { width = 365 height = 144 } clipping = yes',
             ' instantTextboxType = { name = "sofzh_chart_title" position = { x = 5 y = 0 } font = "hoi_16mbs" text = "sofzh_chart_title" maxWidth = 310 maxHeight = 18 fixedsize = yes pdx_tooltip = "sofzh_chart_summary_tt" }',
             ' buttonType = { name = "sofzh_chart_refresh" position = { x = 342 y = 0 } quadTextureSprite = "GFX_sofzh_chart_refresh" buttonFont = "Main_14" buttonText = "" pdx_tooltip = "sofzh_chart_refresh_tt" }',
             ' instantTextboxType = { name = "sofzh_chart_no_data" position = { x = 5 y = 100 } font = "hoi_16mbs" text = "sofzh_chart_no_data" maxWidth = 110 maxHeight = 18 fixedsize = yes }',
             ' containerWindowType = { name = "sofzh_chart_legend" position = { x = 122 y = 20 } size = { width = 242 height = 96 } scale = 1 clipping = yes']
    visible = []
    for i, (ident, group, _, _, _) in enumerate(PROFILES, 1):
        gi = list(DEFAULTS).index(group)
        y = 4 + gi * 22
        tip = f'sofzh_chart_{ident}_tt'
        lines += [f' iconType = {{ name = "sofzh_chart_swatch_{ident}" spriteType = "GFX_sofzh_chart_swatch" position = {{ x = 0 y = {y + 3} }} frame = {gi + 1} pdx_tooltip = "{tip}" }}',
                  f' instantTextboxType = {{ name = "sofzh_chart_name_{ident}" position = {{ x = 17 y = {y} }} font = "hoi_16mbs" text = "sofzh_chart_name_{ident}" maxWidth = 155 maxHeight = 18 fixedsize = yes pdx_tooltip = "{tip}" }}',
                  f' instantTextboxType = {{ name = "sofzh_chart_value_{ident}" position = {{ x = 179 y = {y} }} font = "hoi_16mbs" text = "sofzh_chart_value_{ident}" maxWidth = 48 maxHeight = 18 fixedsize = yes format = right pdx_tooltip = "{tip}" }}',
                  f' instantTextboxType = {{ name = "sofzh_chart_ruling_{ident}" position = {{ x = 229 y = {y} }} font = "hoi_16mbs" text = "sofzh_chart_ruling_marker" maxWidth = 12 maxHeight = 18 fixedsize = yes pdx_tooltip = "sofzh_chart_ruling_tt" }}']
        condition = f'check_variable = {{ var = sofzh_chart_{group}_frame value = {i} compare = equals }}'
        for kind in ['swatch', 'name', 'value']:
            visible.append(f'   sofzh_chart_{kind}_{ident}_visible = {{ {condition} }}')
        visible.append(f'   sofzh_chart_ruling_{ident}_visible = {{ {condition} check_variable = {{ var = sofzh_chart_ruling value = {i} compare = equals }} }}')
    lines += [' }', '} }', '']
    write(NEW_RELS[0], '\n'.join(lines))
    write(NEW_RELS[4], '''scripted_gui = { sofzh_ideology_panel_gui = {
 context_type = player_context window_name = "sofzh_ideology_panel"
 parent_window_token = politics_tab
 visible = { always = yes } ai_enabled = { always = no }
 dirty = sofzh_chart_dirty
 effects = { sofzh_chart_refresh_click = { sofzh_refresh_ideology_chart = yes } }
 properties = { }
 triggers = {
   sofzh_chart_no_data_visible = { check_variable = { var = sofzh_chart_total value = 0 compare = equals } }
'''+'\n'.join(visible)+'\n }\n} }\n')




def build_textures():
    folder = MOD / 'gfx/interface/sofzh_ideology_panel'
    folder.mkdir(parents=True, exist_ok=True)
    groups = one(parse((MOD/'common/ideologies/00_ideologies.txt').read_text(encoding='utf-8-sig')), 'ideologies').value
    colors = [tuple(int(n.value) for n in one(one(groups, group).value, 'color').value) for group in DEFAULTS]
    swatches = Image.new('RGBA', (12 * 4, 12))
    for i, color in enumerate(colors):
        d = ImageDraw.Draw(swatches)
        d.rounded_rectangle((i * 12 + 1, 1, i * 12 + 10, 10), radius=1, fill=color, outline='#E1DACA')
    swatches.save(folder / 'swatches.dds')
    refresh = Image.new('RGBA', (18 * 3, 18))
    d = ImageDraw.Draw(refresh)
    for i, color in enumerate(('#343B40', '#48545B', '#23292D')):
        x = i * 18
        d.rounded_rectangle((x, 0, x + 17, 17), 2, fill=color, outline='#7B7F78')
        d.arc((x + 4, 4, x + 13, 13), 50, 325, fill='#DDD6B8', width=1)
        d.polygon(((x + 12, 3), (x + 14, 7), (x + 10, 7)), fill='#DDD6B8')
    refresh.save(folder / 'refresh.dds')
    if 'gfx/interface/sofzh_ideology_panel/refresh.dds' not in NEW_RELS:
        NEW_RELS.append('gfx/interface/sofzh_ideology_panel/refresh.dds')
    lines = ['spriteTypes = {']
    for name, file, frames in [('swatch', 'swatches', 4), ('refresh', 'refresh', 3)]:
        lines.append(f' spriteType = {{ name = "GFX_sofzh_chart_{name}" texturefile = "gfx/interface/sofzh_ideology_panel/{file}.dds" noOfFrames = {frames} }}')
    lines += ['}', '']
    write(NEW_RELS[1], '\n'.join(lines))


def build_loc():
    rows = [('sofzh_chart_title', '政治光谱'),
            ('sofzh_chart_no_data', '暂无支持率数据'),
            ('sofzh_chart_refresh', '刷新显示'),
            ('sofzh_chart_refresh_tt', '更新党派路线与支持率显示。不会消耗政治点数或改变政体。支持率每天自动更新；暂停时可点此刷新。'),
            ('sofzh_chart_ruling_marker', '§Y◆§!'),
            ('sofzh_chart_ruling_tt', '§Y当前执政路线§!')]
    groups = {'democratic': '共和主义', 'communism': '社会主义', 'fascism': '法西斯主义', 'neutrality': '非同盟'}
    summary = '§Y政治路线与政党支持率§!\\n'
    for ident, group, title, aliases, _ in PROFILES:
        rows += [(f'sofzh_chart_name_{ident}', title),
                 (f'sofzh_chart_value_{ident}', f'[?sofzh_chart_{ident}|1]%'),
                 (f'sofzh_chart_{ident}_tt', f'§Y{title}§!\\n所属大类：{groups[group]}\\n党派支持率：§Y[?sofzh_chart_{ident}|1]%§!\\n\\n${aliases.split()[0]}_desc$\\n通用路线效果：\\n{bonuses(MOD, ident)}\\n\\n红色马赛采用专属政治机制，不叠加通用路线加成。此数值来自采用本路线的党派；没有采用本路线的党派时为0%。')]
    summary += '图表使用原版四类政党的真实支持率。右侧显示各党当前代表采用的细分路线，悬停可查看路线效果。\\n未采用的细分路线保留为0%，不平均分摊票数。\\n◆ 表示执政路线；暂停时可手动刷新。'
    rows.append(('sofzh_chart_summary_tt', summary))
    write(NEW_RELS[6], 'l_simp_chinese:\n' + ''.join(f' {k}:0 "{v}"\n' for k, v in rows), bom=True)


def patch_native():
    p = MOD / GUI_REL
    text = p.read_bytes().decode('utf-8-sig')
    root = next(r for r in one(parse(text), 'guiTypes').value if scalar(r.value, 'name') == '"countrypoliticsview"')
    changes = []
    for name in ('chart_explanation', 'political_pie_chart', 'pol_faction_icon'):
        node = next(r for r in root.value if isinstance(r.value, list) and scalar(r.value, 'name') == f'"{name}"')
        pos = one(node.value, 'position')
        desired = ('185', '167') if name == 'political_pie_chart' else ('-10000', '-10000')
        if (scalar(pos.value,'x'), scalar(pos.value,'y')) != desired:
            changes.append((pos.start, pos.end, f'position = {{ x = {desired[0]} y = {desired[1]} }}'))
    info = next(r for r in root.value if isinstance(r.value, list) and scalar(r.value, 'name') == '"ruling_party_info"')
    for name, y, height in [('ideology', 39, 18), ('elections', 60, 28)]:
        node = next(r for r in info.value if isinstance(r.value, list) and scalar(r.value, 'name') == f'"{name}"')
        for key, value in [('position', f'position = {{ x = 5 y = {y} }}'), ('font', 'font = "Main_14"'), ('maxWidth', 'maxWidth = 100'), ('maxHeight', f'maxHeight = {height}')]:
            target = one(node.value, key)
            changes.append((target.start, target.end, value))
    result = replace(text, changes)
    result = re.sub(r'(# replaced by twelve-route chart)(?: # replaced by twelve-route chart)+',r'\1',result)
    # Preserve the native file's newline convention and all unaffected bytes.
    p.write_bytes(result.encode('utf-8'))
    p = MOD / SYNC_REL
    text = p.read_bytes().decode('utf-8')
    node = one(parse(text), 'sofzh_sync_ideology')
    if not entries(node.value, 'sofzh_refresh_ideology_chart'):
        newline = '\r\n' if '\r\n' in text else '\n'
        text = text[:node.end - 1] + newline + ' sofzh_refresh_ideology_chart = yes' + newline + text[node.end - 1:]
        parse(text)
        p.write_bytes(text.encode('utf-8'))


def main():
    for name in ('segments.dds', 'disc.dds'):
        obsolete = MOD/'gfx/interface/sofzh_ideology_panel'/name
        assert obsolete.resolve().is_relative_to(MOD.resolve())
        obsolete.unlink(missing_ok=True)
    PASS.mkdir(parents=True, exist_ok=True)
    baseline = PASS / 'before'
    baseline.mkdir(exist_ok=True)
    before = {}
    for rel in [GUI_REL, SYNC_REL]:
        original = baseline / rel
        if not original.exists():
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes((MOD / rel).read_bytes())
        reference = ROOT / 'references/ideology-panel' / rel
        if not reference.exists():
            reference.parent.mkdir(parents=True, exist_ok=True)
            reference.write_bytes(original.read_bytes())
        before[rel] = hashlib.sha256(reference.read_bytes()).hexdigest()
    leaders = leaders_by_group()
    build_triggers(leaders)
    build_effect()
    build_gui()
    build_textures()
    build_loc()
    patch_native()
    data = dict(format=2,renderer='native political pie and four active profile rows',profiles=[dict(id=p[0],group=p[1],name=p[2],aliases=p[3].split(),color=p[4],frame=i) for i,p in enumerate(PROFILES,1)],
                defaults=DEFAULTS,known_party_leaders=leaders,files=NEW_RELS+[GUI_REL,SYNC_REL],
                source_before=before,display_only=True,game_engine_verified=False,
                support_basis='Each existing party contributes its actual support to its active representative\'s profile. Other profiles stay at zero; no fabricated split.')
    (ROOT / 'design/ideology-panel.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(ok=True,profiles=12,files=len(data['files']),known_leaders={g:len(v) for g,v in leaders.items()})))


if __name__ == '__main__':
    main()
