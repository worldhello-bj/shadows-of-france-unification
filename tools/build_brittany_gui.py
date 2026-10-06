"""Native council window: generated paintings with authored readable controls.

The preview uses the same DDS assets and authored element rectangles as the GUI.
Its sample state is illustrative; it is not an engine screenshot.
"""
from pathlib import Path
import hashlib
import json
import math
from PIL import Image,ImageDraw,ImageFont
from brittany_art import load_art

COLORS=['#d4b572','#a7b8ca','#c78173','#77b3af','#aeaa7a','#a5ba84']
SHORT=['沙托','勒梅斯特','巴翁','勒戈尔热','特雷曼坦','唐吉－普里让']
DEMAND=['市政与透明预算','收支审计与自治','劳工与技术教育','港口与共和制度','市镇自治与教育','农业合作与救济']
FONT='C:/Windows/Fonts/msyh.ttc'
TABS=[('members','议员协商'),('bills','法案进程'),('forces','军事纲领'),('funds','委员基金')]
HEADER_SHIFT=98
HEIGHT=622+HEADER_SHIFT
PAGE_HEIGHT=589+HEADER_SHIFT


def seat_positions(delegates):
    dots=[]
    for radius,count in [(48,14),(70,22),(92,28),(114,36)]:
        for i in range(count):
            angle=math.pi+(i+.5)*math.pi/count
            dots.append((angle,round(146+radius*math.cos(angle))-5,round(211+radius*math.sin(angle))-5))
    dots.sort()
    owners=[key for key,_,seats,_,_,_ in delegates for _ in range(seats)]
    return [(key,x,y) for key,(_,x,y) in zip(owners,dots)]


def build_gui(mod,root,delegates,bills):
    from brittany_council_expansion import POOL, PRIMARY_TOWN, PROGRAMMES, programme_gate
    folder=mod/'gfx/interface/sof_brt/council';folder.mkdir(parents=True,exist_ok=True)
    assets={};gfx=['spriteTypes = {'];files=[]
    def asset(key,im,frames=1):
        rel='gfx/interface/sof_brt/council/'+key+'.dds';im.save(mod/rel)
        assets[key]=im;files.append(rel)
        gfx.append(f'spriteType = {{ name = "GFX_sof_brt_ui_{key}" texturefile = "{rel}" noOfFrames = {frames} }}')
    panel=Image.new('RGBA',(510,HEIGHT),'#182b32');d=ImageDraw.Draw(panel)
    for y in range(HEIGHT):
        c=tuple(int(v) for v in (24+y*.006,43+y*.01,50+y*.012));d.line((0,y,509,y),fill=c)
    # Fine ruled-paper and engraved border detail remain subordinate to text.
    for y in range(9,614+HEADER_SHIFT,4):d.line((10,y,499,y),fill='#1e3239')
    d.rectangle((2,2,507,619+HEADER_SHIFT),outline='#bca373',width=2);d.rectangle((7,7,502,614+HEADER_SHIFT),outline='#586765')
    for x,y in [(9,9),(487,9),(9,598+HEADER_SHIFT),(487,598+HEADER_SHIFT)]:
        d.line((x,y,x+13,y),fill='#cdb47c',width=2);d.line((x,y,x,y+13),fill='#cdb47c',width=2)
    for y in [69,224,276,317,589]:d.line((17,y+HEADER_SHIFT,492,y+HEADER_SHIFT),fill='#61716d')
    for x in [18,181,344]:
        d.rounded_rectangle((x,235+HEADER_SHIFT,x+147,270+HEADER_SHIFT),radius=3,fill='#293c43',outline='#7f806b')
    d.rounded_rectangle((295,83+HEADER_SHIFT,491,211+HEADER_SHIFT),radius=4,fill='#22373e',outline='#64726b')
    d.arc((26,86+HEADER_SHIFT,266,326+HEADER_SHIFT),180,360,fill='#655f50',width=1)
    d.arc((97,158+HEADER_SHIFT,195,256+HEADER_SHIFT),180,360,fill='#a89972',width=1)
    asset('panel',panel)
    asset('header_scene',load_art('parliament',(494,164)))
    asset('seal',load_art('seal',(45,45)))
    card=Image.new('RGBA',(231,78),'#23383f');d=ImageDraw.Draw(card)
    for y in range(1,77):
        shade=(39-y//9,60-y//9,65-y//10);d.line((1,y,229,y),fill=shade)
    d.rounded_rectangle((0,0,230,77),radius=3,outline='#a39772');d.line((10,31,220,31),fill='#556361')
    d.line((4,2,226,2),fill='#7b8270');d.line((4,75,226,75),fill='#12272e')
    asset('card',card)
    button=Image.new('RGBA',(294,26))
    for i,(bg,edge) in enumerate([('#334d55','#a68f61'),('#45616a','#d3b776'),('#23353c','#536267')]):
        d=ImageDraw.Draw(button);d.rounded_rectangle((i*98,0,i*98+97,25),radius=3,fill=bg,outline=edge)
        d.line((i*98+3,2,i*98+94,2),fill='#8d927e' if i!=2 else '#43595f')
        d.line((i*98+3,23,i*98+94,23),fill='#172b32')
    asset('button',button,3)
    tabs=Image.new('RGBA',(354,29))
    for i,(bg,edge) in enumerate([('#2c424a','#7c8272'),('#3e5860','#ccb279'),('#22363e','#52656a')]):
        ImageDraw.Draw(tabs).rounded_rectangle((i*118,0,i*118+117,28),radius=3,fill=bg,outline=edge)
    asset('tab',tabs,3)
    for i,(key,_,_,_,_,_) in enumerate(delegates):
        dot=Image.new('RGBA',(20,10));dd=ImageDraw.Draw(dot)
        for frame,c in enumerate(['#4b5d62',COLORS[i]]):
            dd.rounded_rectangle((frame*10+1,1,frame*10+8,8),radius=2,fill=c,outline='#172c34')
        asset('seat_'+key,dot,2)
    for key in ['defence','offence']:
        asset(key,load_art(key+'_command',(48,48)))
        asset(key+'_banner',load_art(key,(224,75)))
    fund_sources=dict(economy='service_supply',army='service_land',navy='service_sea',air='service_air',science='service_command',diplomacy='seal')
    for key,source in fund_sources.items():asset('fund_'+key,load_art(source,(28,28)))
    gfx.append('}')
    def write(rel,text,bom=False):
        p=mod/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8-sig' if bom else 'utf-8',newline='\n');files.append(rel)
    write('interface/sof_brittany_council.gfx','\n'.join(gfx)+'\n')
    gui=['guiTypes = { containerWindowType = { name = "sof_brt_council_window" position = { x = 0 y = 0 } size = { width = 510 height = '+str(HEIGHT)+' }']
    loc={};texts=[];icons=[];buttons=[]
    fixed={'sof_brt_background','sof_brt_header_scene','sof_brt_ermine_seal','sof_brt_ui_heading','sof_brt_ui_subtitle'}
    def icon(name,key,x,y,frame=None,tip=None,page=0):
        if name not in fixed:y+=HEADER_SHIFT
        gui.append(f'iconType = {{ name = "{name}" position = {{ x = {x} y = {y} }} spriteType = "GFX_sof_brt_ui_{key}" alwaystransparent = yes '+(f'frame = {frame} ' if frame else '')+(f'pdx_tooltip = "{tip}" ' if tip else '')+'}')
        icons.append(dict(name=name,asset=key,x=x,y=y,frame=frame or 1,page=page))
    def text(name,value,x,y,width,size=16,height=22,tip=None,page=0):
        if name not in fixed:y+=HEADER_SHIFT
        loc[name]=value
        font='hoi_24header' if size==24 else 'hoi_18mbs' if size==18 else 'hoi_16mbs'
        gui.append(f'instantTextBoxType = {{ name = "{name}" position = {{ x = {x} y = {y} }} font = "{font}" text = "{name}" maxWidth = {width} maxHeight = {height} format = left '+(f'pdx_tooltip = "{tip}" ' if tip else '')+'}')
        texts.append(dict(name=name,value=value,x=x,y=y,width=width,size=size,height=height,page=page))
    def button(name,value,x,y,key,tip=None,page=0):
        y+=HEADER_SHIFT
        loc[name]=value
        gui.append(f'buttonType = {{ name = "{name}" position = {{ x = {x} y = {y} }} quadTextureSprite = "GFX_sof_brt_ui_{key}" buttonText = "{name}" buttonFont = "hoi_16mbs" clicksound = decisions_ui_button '+(f'pdx_tooltip = "{tip}" ' if tip else '')+'}')
        buttons.append(dict(name=name,value=value,x=x,y=y,asset=key,page=page))
    icon('sof_brt_background','panel',0,0);icon('sof_brt_header_scene','header_scene',8,8);icon('sof_brt_ermine_seal','seal',447,16)
    text('sof_brt_ui_heading','布列塔尼地方议会',19,17,413,24,30)
    text('sof_brt_ui_subtitle','地方自治 · 责任内阁 · 战争授权',20,48,405)
    for i,(key,x,y) in enumerate(seat_positions(delegates)):icon('sof_brt_seat_'+str(i),'seat_'+key,x,y,tip='sof_brt_ui_support_tt')
    text('sof_brt_ui_chamber','100席地方代表',89,204,180)
    text('sof_brt_ui_support','支持  §Y[?sof_brt_support|0] / 100§!',309,95,176,24,30)
    text('sof_brt_ui_majority','[GetSofBrtMajority]',309,131,176)
    text('sof_brt_ui_isolation','[GetSofBrtIsolation]',309,160,177,16,40)
    text('sof_brt_ui_session','承诺180日 · 审议45日',309,190,176)
    for x,label in [(29,'普通法案  51席'),(192,'修法动员  66席'),(355,'战争授权  75席')]:text('sof_brt_ui_threshold_'+str(x),label,x,243,139)
    for i,(key,label) in enumerate(TABS):button('sof_brt_tab_'+key,label,18+118*i,284,'tab')
    triggers=[];effects=[];properties=[];scripted=[]
    for i,(key,label) in enumerate(TABS):
        effects.append(f'sof_brt_tab_{key}_click = {{ set_variable = {{ sof_brt_ui_tab = {i} }} }}')
        if i>0:triggers.append(f'sof_brt_page_{key}_visible = {{ check_variable = {{ sof_brt_ui_tab = {i} }} }}')
        else:triggers.append('sof_brt_page_members_visible = { NOT = { OR = { check_variable = { sof_brt_ui_tab = 1 } check_variable = { sof_brt_ui_tab = 2 } check_variable = { sof_brt_ui_tab = 3 } } } }')
        icon('sof_brt_active_tab_'+key,'tab',18+118*i,284,2)
        # Redraw the label over an always-transparent selected-tab plate.
        text('sof_brt_active_label_'+key,label,18+118*i+26,287,88)
        cond='check_variable = { sof_brt_ui_tab = '+str(i)+' }' if i else 'NOT = { OR = { check_variable = { sof_brt_ui_tab = 1 } check_variable = { sof_brt_ui_tab = 2 } check_variable = { sof_brt_ui_tab = 3 } } }'
        triggers.append(f'sof_brt_active_tab_{key}_visible = {{ {cond} }}')
        triggers.append(f'sof_brt_active_label_{key}_visible = {{ {cond} }}')
    gui.append('containerWindowType = { name = "sof_brt_page_members" position = { x = 0 y = 0 } size = { width = 510 height = '+str(PAGE_HEIGHT)+' }')
    for i,(key,name,seats,demand,cost,_) in enumerate(delegates):
        x=18+(i%2)*243;y=328+(i//2)*86
        icon('sof_brt_card_'+key,'card',x,y)
        icon('sof_brt_badge_'+key,'seat_'+key,x+10,y+12)
        text('sof_brt_name_'+key,f'[GetSofBrtName{key}] · {seats}席',x+28,y+6,199,18,25,'sof_brt_member_'+key+'_tt',1)
        text('sof_brt_demand_'+key,DEMAND[i],x+11,y+35,208,16,22,'sof_brt_member_'+key+'_tt',1)
        text('sof_brt_status_'+key,f'[GetSofBrtMember{key}]',x+11,y+57,113,16,21,page=1)
        button('sof_brt_lobby_'+key,f'协商 · {cost}',x+124,y+46,'button','sof_brt_member_'+key+'_tt',1)
        loc['sof_brt_member_'+key+'_tt']=f'[GetSofBrtFull{key}]：{demand}。[GetSofBrtHome{key}]。支付{cost}政治点，换取180日的{seats}席支持，同时承担公共支出承诺。须先完成对应听证。当前支持不能重复协商；家乡沦陷时须安排流亡代表或改任候补。'
        effects.append(f'sof_brt_lobby_{key}_click = {{ sof_brt_gui_lobby_{key} = yes }}')
        milestone=dict(chateau='P3',lemaistre='P4',bahon='P5',legorgeu='P6',tremintin='P7',prigent='P8')[key]
        triggers.append(f'sof_brt_lobby_{key}_click_enabled = {{ sof_brt_active = yes is_subject = no has_capitulated = no has_completed_focus = SOF_BRT_{milestone} NOT = {{ has_country_flag = sof_brt_pledge_{key} }} NOT = {{ has_country_flag = sof_brt_suspended_{key} }} NOT = {{ has_political_power < {cost} }} }}')
        scripted.append(f'defined_text = {{ name = GetSofBrtMember{key} text = {{ trigger = {{ has_country_flag = sof_brt_suspended_{key} }} localization_key = sof_brt_ui_suspended }} text = {{ trigger = {{ has_country_flag = sof_brt_pledge_{key} }} localization_key = sof_brt_ui_pledged }} text = {{ localization_key = sof_brt_ui_unpledged }} }}')
        reserve=next(p for p in POOL if p['slot']==key)
        for typename,primary,alternate in [('Name',SHORT[i],reserve['short']),('Full',name,reserve['name']),('Home','政治驻地：'+PRIMARY_TOWN[key],'政治驻地：'+reserve['town'])]:
            normal='sof_brt_identity_'+typename+'_'+key;replacement=normal+'_reserve'
            loc[normal]=primary;loc[replacement]=alternate
            scripted.append(f'defined_text = {{ name = GetSofBrt{typename}{key} text = {{ trigger = {{ has_country_flag = sof_brt_reserve_{key} }} localization_key = {replacement} }} text = {{ localization_key = {normal} }} }}')
        properties.append(f'sof_brt_badge_{key} = {{ frame = sof_brt_ui_{key} }}')
    gui.append('}')
    gui.append('containerWindowType = { name = "sof_brt_page_bills" position = { x = 0 y = 0 } size = { width = 510 height = '+str(PAGE_HEIGHT)+' }')
    for i,(key,(title,seats,pre,extra)) in enumerate(bills.items()):
        y=329+i*25
        text('sof_brt_bill_label_'+key,f'{title} · {seats}',26,y,318,16,22,'sof_brt_bill_'+key+'_tt',2)
        text('sof_brt_bill_state_'+key,f'[GetSofBrtBill{key}]',355,y,135,16,22,page=2)
        loc['sof_brt_bill_'+key+'_tt']=f'{title}须{seats}席，支付30政治点并审议45日。开始与结束均核验多数和政策条件。请在下方决议列表启动审议；未通过仅退回10政治点。'
        scripted.append(f'defined_text = {{ name = GetSofBrtBill{key} text = {{ trigger = {{ has_country_flag = sof_brt_law_{key} }} localization_key = sof_brt_ui_enacted }} text = {{ trigger = {{ has_country_flag = sof_brt_bill_{key} }} localization_key = sof_brt_ui_review }} text = {{ trigger = {{ {pre} }} localization_key = sof_brt_ui_wait_vote }} text = {{ localization_key = sof_brt_ui_locked }} }}')
    text('sof_brt_ui_bill_hint','在下方决议提出法案；结束审议时重新核验多数。',26,562,460,16,22,page=2)
    gui.append('}')
    gui.append('containerWindowType = { name = "sof_brt_page_forces" position = { x = 0 y = 0 } size = { width = 510 height = '+str(PAGE_HEIGHT)+' }')
    icon('sof_brt_defence_scene','defence_banner',24,328,page=3);icon('sof_brt_offence_scene','offence_banner',268,328,page=3)
    icon('sof_brt_shield','defence',30,414,page=3);icon('sof_brt_arrow','offence',274,414,page=3)
    text('sof_brt_ui_defence_title','孤立防御',90,414,153,18,26,page=3)
    text('sof_brt_ui_defence_state','[GetSofBrtDefence]',90,440,153,16,22,page=3)
    text('sof_brt_ui_offence_title','积极进攻',334,414,153,18,26,page=3)
    text('sof_brt_ui_offence_state','[GetSofBrtOffence]',334,440,153,16,22,page=3)
    text('sof_brt_ui_defence_body','市镇预备役 · 博卡日纵深\\n港口防空 · 渔港护航\\n本土防御 +16%\\n计划 -5% · 船坞建设 -5%',30,472,220,16,84,page=3)
    text('sof_brt_ui_offence_body','机动旅 · 海空登陆协同\\n攻击 +6% · 计划 +10%\\n本土防御 -4%\\n民用建设 -8%',274,472,220,16,84,page=3)
    text('sof_brt_ui_force_hint','两种纲领互斥；积极进攻仍须单独取得战争授权。',26,561,465,16,22,page=3)
    gui.append('}')
    gui.append('containerWindowType = { name = "sof_brt_page_funds" position = { x = 0 y = 0 } size = { width = 510 height = '+str(PAGE_HEIGHT)+' }')
    for i,(key,p) in enumerate(PROGRAMMES.items()):
        icon('sof_brt_fund_icon_'+key,'fund_'+key,27,333+i*33,page=4)
        text('sof_brt_fund_label_'+key,p['title'],65,337+i*33,286,16,22,'sof_brt_fund_'+key+'_tt',4)
        text('sof_brt_fund_state_'+key,'[GetSofBrtFund'+key+']',365,337+i*33,124,16,22,page=4)
        loc['sof_brt_fund_'+key+'_tt']='须51席、对应国策及委员会代表支持。拨款35政治点、持续180日。失去多数或必要支持时撤销。具体效果见下方委员会分类的专项决议。'
        scripted.append(f'defined_text = {{ name = GetSofBrtFund{key} text = {{ trigger = {{ has_idea = sof_brt_committee_{key} }} localization_key = sof_brt_ui_funded }} text = {{ trigger = {{ {programme_gate(p)} }} localization_key = sof_brt_ui_can_fund }} text = {{ localization_key = sof_brt_ui_no_fund }} }}')
    text('sof_brt_ui_fund_hint','专项35政治点 · 180日有效 · 失去多数即撤销\\n在下方“委员会与候补代表”分类拨款或改任。',26,545,465,16,40,page=4)
    gui.append('}')
    text('sof_brt_ui_footer','1930年代地方人物 · 席位与议会制度为架空设定',20,599,474,16,22)
    gui.append('} }')
    for i,(key,_,_) in enumerate(seat_positions(delegates)):properties.append(f'sof_brt_seat_{i} = {{ frame = sof_brt_ui_{key} }}')
    write('interface/sof_brittany_council.gui','\n'.join(gui)+'\n')
    write('common/scripted_guis/sof_brittany_council.txt','scripted_gui = { sof_brt_council_gui = { context_type = decision_category window_name = "sof_brt_council_window" ai_enabled = { always = no }\neffects = { '+'\n'.join(effects)+' }\ntriggers = { '+'\n'.join(triggers)+' }\nproperties = { '+'\n'.join(properties)+' } } }\n')
    scripted += [
      'defined_text = { name = GetSofBrtMajority text = { trigger = { check_variable = { sof_brt_support > 74 } } localization_key = sof_brt_ui_majority75 } text = { trigger = { sof_brt_supermajority = yes } localization_key = sof_brt_ui_majority66 } text = { trigger = { sof_brt_majority = yes } localization_key = sof_brt_ui_majority51 } text = { localization_key = sof_brt_ui_majority_low } }',
      'defined_text = { name = GetSofBrtIsolation text = { trigger = { has_country_flag = sof_brt_emergency_active } localization_key = sof_brt_ui_emergency } text = { trigger = { check_variable = { sof_brt_isolation = 3 } } localization_key = sof_brt_ui_stage3 } text = { trigger = { check_variable = { sof_brt_isolation = 2 } } localization_key = sof_brt_ui_stage2 } text = { trigger = { check_variable = { sof_brt_isolation = 1 } } localization_key = sof_brt_ui_stage1 } text = { localization_key = sof_brt_ui_stage0 } }',
      'defined_text = { name = GetSofBrtDefence text = { trigger = { has_completed_focus = SOF_BRT_F0 } localization_key = sof_brt_ui_selected } text = { trigger = { has_completed_focus = SOF_BRT_O0 } localization_key = sof_brt_ui_excluded } text = { localization_key = sof_brt_ui_undecided } }',
      'defined_text = { name = GetSofBrtOffence text = { trigger = { has_completed_focus = SOF_BRT_O0 } localization_key = sof_brt_ui_selected } text = { trigger = { has_completed_focus = SOF_BRT_F0 } localization_key = sof_brt_ui_excluded } text = { localization_key = sof_brt_ui_undecided } }',
    ]
    loc.update(sof_brt_ui_pledged='§G承诺有效§!',sof_brt_ui_unpledged='§g尚未支持§!',sof_brt_ui_enacted='§G已通过§!',sof_brt_ui_review='§Y审议中 · 45日§!',sof_brt_ui_wait_vote='§Y待表决§!',sof_brt_ui_locked='§g尚未解锁§!',sof_brt_ui_selected='§G已确立纲领§!',sof_brt_ui_excluded='§R路线互斥§!',sof_brt_ui_undecided='§Y尚未选择§!',sof_brt_ui_majority75='具备战争法案多数',sof_brt_ui_majority66='具备修法与动员多数',sof_brt_ui_majority51='具备普通法案多数',sof_brt_ui_majority_low='§Y尚未形成多数§!',sof_brt_ui_emergency='§Y紧急自卫动员§!',sof_brt_ui_stage3='孤立阶段 3 · 地方优先',sof_brt_ui_stage2='孤立阶段 2 · 武装中立',sof_brt_ui_stage1='孤立阶段 1 · 有限介入',sof_brt_ui_stage0='孤立限制已解除',sof_brt_ui_support_tt='六个党团合计100席。彩色席位表示有效支持，灰色席位尚未支持。协商承诺持续180日，到期重新计票。多数只是票数条件，不会自动授予法案或宣战权。')
    loc['sof_brt_ui_suspended']='§R驻地授权中断§!'
    loc.update(sof_brt_ui_funded='§G拨款有效§!',sof_brt_ui_can_fund='§Y可以拨款§!',sof_brt_ui_no_fund='§g缺乏授权§!')
    write('common/scripted_localisation/sof_brittany_council.txt','\n'.join(scripted)+'\n')
    write('localisation/simp_chinese/replace/sof_brittany_council_l_simp_chinese.yml','l_simp_chinese:\n'+'\n'.join(f' {k}:0 "{v}"' for k,v in loc.items())+'\n',True)
    # Render exact authored coordinates and textures for three representative views.
    out=root/'docs/previews/brittany';out.mkdir(parents=True,exist_ok=True)
    for page,(_,title) in enumerate(TABS,1):
        im=panel.copy();dd=ImageDraw.Draw(im)
        active={'chateau','lemaistre','legorgeu','tremintin'}
        for item in icons:
            if item.get('page') and item['page']!=page:continue
            key=item['asset']
            if key=='panel':continue
            if key=='tab':continue
            if key=='card' and page!=1:continue
            if key in ['defence','offence'] and page!=3:continue
            tex=assets[key]
            if key.startswith('seat_'):
                owner=key.removeprefix('seat_');frame=1 if owner in active else 0
                tex=tex.crop((frame*10,0,frame*10+10,10))
                if item['name'].startswith('sof_brt_badge_') and page!=1:continue
            im.alpha_composite(tex,(item['x'],item['y']))
        for item in buttons:
            if item['page'] and item['page']!=page:continue
            tex=assets[item['asset']];width=98 if item['asset']=='button' else 118
            im.alpha_composite(tex.crop((0,0,width,tex.height)),(item['x'],item['y']))
            font=ImageFont.truetype(FONT,14);length=dd.textlength(item['value'],font=font)
            dd.text((item['x']+(width-length)/2,item['y']+3),item['value'],font=font,fill='#e8e0c9')
        tab_tex=assets['tab'].crop((118,0,236,29));im.alpha_composite(tab_tex,(18+118*(page-1),284+HEADER_SHIFT))
        for item in texts:
            if item['page'] and item['page']!=page:continue
            if item['name'].startswith('sof_brt_active_label_') and item['name']!='sof_brt_active_label_'+TABS[page-1][0]:continue
            value=item['value'].replace('[?sof_brt_support|0]','70')
            for j,(key,_,_,_,_,_) in enumerate(delegates):value=value.replace('[GetSofBrtName'+key+']',SHORT[j])
            if value.startswith('[GetSofBrtMember'):value='承诺有效' if any(k in value for k in active) else '尚未支持'
            elif value.startswith('[GetSofBrtBill'):value='待表决'
            elif value.startswith('[GetSofBrtFund'):value='拨款有效'
            else:value=value.replace('[GetSofBrtMajority]','具备修法与动员多数').replace('[GetSofBrtIsolation]','孤立阶段 2 · 武装中立').replace('[GetSofBrtDefence]','已确立纲领').replace('[GetSofBrtOffence]','路线互斥')
            import re
            value=re.sub(r'§.','',value).replace('\\n','\n')
            font=ImageFont.truetype(FONT,item['size']-2)
            dd.multiline_text((item['x'],item['y']),value,font=font,fill='#e0dfd0',spacing=5)
        canvas=Image.new('RGB',(550,686+HEADER_SHIFT),'#0d2028');canvas.paste(im,(20,20),im)
        ImageDraw.Draw(canvas).text((20,652+HEADER_SHIFT),f'{title} · 实际DDS与控件布局预览，示例状态非游戏截图',font=ImageFont.truetype(FONT,13),fill='#a9b9b5')
        canvas.save(out/('COUNCIL-'+str(page)+'.png'))
    report=dict(width=510,height=HEIGHT,seats=100,tabs=4,files=files,assets=[dict(path=f,sha256=hashlib.sha256((mod/f).read_bytes()).hexdigest()) for f in files if f.endswith('.dds')],seat_allocation=[dict(key=k,count=s) for k,_,s,_,_,_ in delegates],engine_verified=False)
    (root/'design/brittany-gui-layout.json').write_text(json.dumps(dict(texts=texts,icons=icons,buttons=buttons,**report),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report
