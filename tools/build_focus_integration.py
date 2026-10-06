"""Integrate the existing transplants with local cabinet and politics controls."""
import json
import re
import copy
from pathlib import Path
from hoi4_script import parse, one, entries, scalar, walk, replace
from vanilla_historical import LEADERS, SLOTS, char_id, idea_id

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod'
ISLAND_TAGS = ('AJC', 'BST', 'CLV', 'COR', 'SRT')


def owned_character(source, tag=None):
    return char_id(source)+(('_'+tag.lower()) if source.startswith('ITA_') and tag else '')


def emit(rows):
    return ' '.join((r.key+' '+(r.operator or '=')+' { '+emit(r.value)+' }' if isinstance(r.value, list)
                     else (r.key+' '+(r.operator or '=')+' '+r.value if r.key else r.value)) for r in rows)


def save(relative, text):
    p = MOD / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8', newline='\n')


def build():
    meta = json.loads((ROOT/'design/historical-cabinet.json').read_text(encoding='utf-8'))
    members = {p['id']:p for p in meta['members']}
    relative = 'common/ideas/sofzh_cabinet.txt'
    text = (MOD/relative).read_text(encoding='utf-8-sig')
    changes = []
    for cat in one(parse(text), 'ideas').value:
        if not cat.key.startswith('sofzh_cabinet_'):
            continue
        for node in cat.value:
            if not isinstance(node.value, list):
                continue
            for on_add in entries(node.value, 'on_add'):
                if not entries(on_add.value, 'hidden_effect'):
                    changes.append((on_add.start, on_add.end, 'on_add = { hidden_effect = { '+emit(on_add.value)+' } }'))
            if node.key in members:
                p = members[node.key]
                prefix = 'SFP_' if p['source'].startswith('FRA_') else 'SFC_'
                tree = 'sofzh_paris' if prefix=='SFP_' else 'sofzh_corsica'
                ready = 'has_focus_tree = '+tree+' OR = { '+' '.join('has_completed_focus = '+prefix+f for f in p['focuses'])+' } '
                if p['governments']:
                    ready += 'OR = { '+' '.join('has_government = '+g for g in p['governments'])+' } '
                ready += ' '.join('NOT = { has_completed_focus = '+prefix+f+' }' for f in p['retired'])
                visible = one(node.value, 'visible')
                changes.append((visible.start, visible.end, 'visible = { sofzh_cabinet_country = yes OR = { has_idea = '+node.key+' AND = { '+ready+' } } }'))
    save(relative, replace(text, changes))

    relative = 'common/characters/sof_vanilla_historical.txt'
    text = (MOD/relative).read_text(encoding='utf-8-sig')
    # Earlier text replacement substituted a shorter GFX token inside its suffix variant.
    text = re.sub(r'"(GFX_sof_van_[^"]+)"(_civilian|_small)', r'"\1\2"', text)
    changes = []
    for node in one(parse(text), 'characters').value:
        if not isinstance(node.value, list):
            continue
        for field in entries(node.value, 'can_be_captured'):
            changes.append((field.start, field.end, ''))
        for role in entries(node.value, 'country_leader'):
            for field in entries(role.value, 'can_be_captured'):
                changes.append((field.start, field.end, ''))
        if not entries(node.value, 'country_leader'):
            ideology = next(v[1] for v in LEADERS.values() if char_id(v[0])==node.key)
            changes.append((node.end-1, node.end-1, ' country_leader = { ideology = '+ideology+' expire = "1965.1.1.1" } '))
    save(relative, replace(text, changes))

    text = (MOD/relative).read_text(encoding='utf-8-sig')
    chars = one(parse(text), 'characters')
    defined = {n.key for n in chars.value}
    clones = []
    for node in chars.value:
        if not node.key.startswith('sof_hist_character_ita_') or node.key.endswith(tuple('_'+t.lower() for t in ISLAND_TAGS)):
            continue
        for tag in ISLAND_TAGS:
            cid = node.key+'_'+tag.lower()
            if cid not in defined:
                clone = copy.deepcopy(node);clone.key = cid
                clones.append(emit([clone]))
    if clones:
        save(relative, text[:chars.end-1]+'\n'+'\n'.join(clones)+'\n'+text[chars.end-1:])

    relative = 'common/scripted_effects/sof_vanilla_major.txt'
    text = (MOD/relative).read_text(encoding='utf-8-sig')
    rows = parse(text)
    changes = []
    repairs = []
    existing = {n.key for n in rows}
    for old, (source, ideology, gov) in LEADERS.items():
        name = 'sof_hist_complete_'+old.lower()
        cid = char_id(source)
        pid = idea_id(source)
        node = one(rows, name)
        recruit = f'if = {{ limit = {{ NOT = {{ has_character = {cid} }} }} recruit_character = {cid} }}'
        leadership = f'set_politics = {{ ruling_party = {gov} elections_allowed = '+('yes' if gov=='democratic' else 'no')+' } '
        leadership += f'if = {{ limit = {{ {cid} = {{ has_ideology = {ideology} }} }} remove_country_leader_role = {{ character = {cid} ideology = {ideology} }} }} '
        leadership += f'add_country_leader_role = {{ character = {cid} promote_leader = yes country_leader = {{ ideology = {ideology} expire = "1965.1.1.1" }} }}'
        extra = ''
        if old=='ITA_the_italian_republic':
            king = char_id('ITA_vittorio_emanuele_iii')
            extra = f'if = {{ limit = {{ has_character = {king} }} retire_character = {king} }} remove_ideas = {idea_id("ITA_vittorio_emanuele_iii")} '
        appointment = 'add_ideas = '+pid if pid in members else ''
        body = ('custom_effect_tooltip = '+name+'_tt hidden_effect = { '+recruit+
                f' if = {{ limit = {{ has_character = {cid} }} '+leadership+' '+extra+f' set_country_flag = {name}_done }} }} '+
                f'if = {{ limit = {{ has_character = {cid} }} {appointment} }}')
        if source.startswith('ITA_'):
            dispatch = []
            for index, tag in enumerate(ISLAND_TAGS):
                # Scope every historical Italian token, including the king's retirement.
                scoped = re.sub(r'sof_hist_character_ita_[a-z0-9_]+', lambda m: m[0]+'_'+tag.lower(), body)
                dispatch.append(('if' if index==0 else 'else_if')+' = { limit = { original_tag = '+tag+' } '+scoped+' }')
            body = 'custom_effect_tooltip = '+name+'_tt hidden_effect = { '+' '.join(dispatch)+' }'
            if pid in members:
                body += ' show_ideas_tooltip = '+pid
        changes.append((node.start, node.end, name+' = { '+body+' }'))
    for old, (source, ideology, gov) in LEADERS.items():
        for tag in ISLAND_TAGS if source.startswith('ITA_') else (None,):
            cid = owned_character(source, tag)
            fid = ('SFP_' if old.startswith('FRA_') else 'SFC_')+old[4:]
            tree = 'sofzh_paris' if old.startswith('FRA_') else 'sofzh_corsica'
            gate = 'original_tag = '+tag+' ' if tag else ''
            repairs.append(f'if = {{ limit = {{ {gate}has_focus_tree = {tree} has_government = {gov} has_completed_focus = {fid} NOT = {{ has_character = {cid} }} }} recruit_character = {cid} if = {{ limit = {{ has_character = {cid} }} if = {{ limit = {{ {cid} = {{ has_ideology = {ideology} }} }} remove_country_leader_role = {{ character = {cid} ideology = {ideology} }} }} add_country_leader_role = {{ character = {cid} promote_leader = yes country_leader = {{ ideology = {ideology} expire = "1965.1.1.1" }} }} }} }}')
    repair_body = 'sof_hist_repair_roles_460 = { '+' '.join(repairs)+' }'
    if 'sof_hist_repair_roles_460' not in existing:
        suffix = '\n'+repair_body+'\n'
    else:
        node = one(rows, 'sof_hist_repair_roles_460')
        changes.append((node.start, node.end, repair_body))
        suffix = ''
    save(relative, replace(text, changes)+suffix)
    relative = 'common/on_actions/sof20_startup.txt'
    text = (MOD/relative).read_text(encoding='utf-8-sig')
    if 'sof_hist_repair_roles_460' not in text:
        text = text.replace('sof_hist_setup = yes', 'sof_hist_setup = yes sof_hist_repair_roles_460 = yes')
    save(relative, text)

    relative = 'localisation/simp_chinese/replace/sof_vanilla_major_l_simp_chinese.yml'
    path = MOD/relative
    text = path.read_text(encoding='utf-8-sig')
    names = dict(re.findall(r'(?m)^ ([^ :]+):\d* "((?:[^"\\]|\\.)*)"', text))
    for p in members.values():
        key = p['id']+'_desc'
        value = f'历史内阁 · {SLOTS[p["slot"]]}\\n任命：125政治点数；替换同职务现任，调整冷却90天。'
        text = re.sub(r'(?m)^ '+re.escape(key)+r':\d* ".*"$', lambda _: ' '+key+':0 "'+value+'"', text)
    governments = dict(democratic='民主', communism='社会主义', fascism='法西斯', neutrality='中立')
    for old, (source, _, gov) in LEADERS.items():
        key = 'sof_hist_complete_'+old.lower()+'_tt'
        if key in names:
            continue
        value = '政府领袖：§Y'+names.get(char_id(source), source)+'§!；执政方向：'+governments[gov]+'。'
        if idea_id(source) in members:
            value += '免费任命为行政首席，同职务替换。'
        text += ' '+key+':0 "'+value+'"\n'
    path.write_bytes(text.encode('utf-8-sig'))
    print(json.dumps(dict(ok=True, historical_members=len(members), leader_routes=len(LEADERS), renderer='native', game_engine_verified=False)))


if __name__ == '__main__':
    build()
