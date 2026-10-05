"""One independent illustration per focus; preserve generated alpha at export.

Generated assets use the built-in imagegen tool, one call per illustration.
Other assets are individually selected original-game illustrations, copied
with their provenance. This module exports native DDS and refuses missing,
reused, or byte-identical artwork.
"""
import argparse,collections,hashlib,json,shutil,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hoi4_script import parse,one,entries,scalar,replace

ROOT=Path(__file__).resolve().parent.parent;MOD=ROOT/'mod';ART=ROOT/'art/focus/unique'
PLAN=ROOT/'design/unique-focus-art.json'

STYLE='Use case: stylized-concept. Asset: ONE independent production national-focus icon for a 1930s grand-strategy mod set in fragmented France. Style: classic HOI4 hand-painted realistic miniature metal icon, antique gold and bronze accents, steel-gray main objects, deep sculpted shadows, restrained muted navy or burgundy. Strong, focus-specific subject and silhouette, readable when reduced to 96px. Use sparse supporting ornament that suits this particular subject; avoid the identical full round laurel medallion on every icon. Centered on a square transparent canvas, outline fully visible and 12 percent clear transparent margin on ALL four sides. Actual transparent alpha in the background and openings. No words, letters, numerals, watermark, rectangular card, photographic scenery, foreign flags or foreign corporate logos. One coherent illustrated object composition; NOT a sprite sheet or collage.'

SUBJECTS={
 'SFP_metropolitan_france':'A compact Parisian industrial city block seen from above, a large toothed cog behind the block and a single arched stone supply canal beneath it; tall narrow brick workshops, NOT a pair of chimneys factory emblem.',
 'SFP_industrial_expansion':'A tall 1930s lattice construction crane hoisting a steel factory roof truss, the diagonally suspended truss is the dominant foreground shape, with two short unfinished concrete walls at the base.',
 'SFP_algerie_france':'Loire valley development: a large turning watermill wheel above a stone river sluice and newly electrified mill workshop, with a single broad pale-gold river ribbon curving beneath.',
 'SFP_invest_in_the_colonies':'Local district investment: a period banker desk calculator and a rolled construction blueprint tied with burgundy ribbon, a cluster of three large bronze coins in front; no factory silhouette.',
}
SUBJECTS.update({
 'SFP_invest_in_west_africa':'Breton development: a rugged stone coastal workshop, a large Breton fishing net winch and a curved stone quay; the net winch dominates.',
 'SFP_invest_in_indochina':'Normandy development: a timber-frame rebuilding scaffold surrounding one half-built Norman house, a large carpenter plane in the foreground.',
 'SFP_invest_in_syria':'Champagne investment: a tall pressure vessel above a cellar arch and a broad row of vineyard leaves, with a riveted steel processing valve as the main object.',
 'SFP_colonial_industry':'A new regional brickworks: a squat kiln with a bold brick stack and a paddle-wheel furnace blower, viewed from low angle.',
 'SFP_global_integration':'Interconnected district economies: two different industrial workshops on either end of a large mechanical coupling shaft, the connecting coupling is dominant.',
 'SFP_industrial_collectivization':'Workers collective industry: three strong gloved worker hands turning the same immense machine control wheel, with one short factory beam behind.',
 'SFP_nationalize_key_industry':'A large antique state-ownership wax seal set on a steel turbine housing, with a folded official deed behind it, no letters on the deed.',
 'SFP_invest_in_our_weaker_allies':'Allied investment: a heavy capital toolbox passed from a large reinforced workshop to a smaller fragile one, visible spanner and support brace.',
 'SFC_develop_ethiopia':'Corsican island development: a Corsica-shaped bronze island relief with a masonry quarry derrick rising from its mountain ridge.',
 'SFC_develop_libya':'Mainland industrial foothold: a compact 1930s gantry above a new coastal freight warehouse, a single large cargo pallet foreground.',
 'SFC_develop_eritrea':'Balagne development: a terraced stone hillside workshop and olive press with a large screw press as dominant silhouette.',
 'SFC_develop_somaliland':'Sartene development: a steep slate stairway winding to a small mountain machine workshop, massive stone blocks foreground.',
 'SFC_industria_della_gomma_sintetica':'A thick loop of synthetic rubber hose around a chemical retort and a single black tire, muted charcoal rubber highlights.',
 'SFC_strengthen_northern_industry':'A massive steel reinforcing girder bridging two northern industrial halls, with a brass riveting hammer placed diagonally.',
 'SFC_modernize_the_mezzogiorno':'South Corsican modernization: an old stone workshop roof replaced by corrugated steel sheets held by a bold lifting clamp.',
 'SFC_new_industrialization_program':'An unfolded blueprint showing a distinctive sawtooth factory roof, a large dividers compass and concrete foundation footing at the bottom.',
 'SFC_redirect_alfa_romeo_production':'Workshop conversion: a bronze arrow-shaped conveyor carrying an automobile engine on one side and armored vehicle engine on the other, no corporate logos.',
 'SFC_increase_production':'A horizontal industrial belt press with three heavy machine parts emerging in a bold fan shape; the stamping ram dominates.',
 'SFC_keep_specialization':'Precision specialist industry: a large steel micrometer measuring a beautifully machined turbine blade, one tool rest behind.',
 'SFC_standardization':'Standard parts: a bold go/no-go plug gauge with three perfectly matching steel bolts arranged along a single measuring rail.',
 'SFC_specialization':'Specialized production: a turret lathe with a single intricate brass chuck and one thick cutting tool dominating the silhouette.',
 'SFC_improve_the_industries':'Industrial improvement: an antique pressure dial set atop an upgraded exposed piston cylinder and lubricating feed tube.',
 'SFC_new_corporations':'Corporate coordination: a triangle of three metal trade-guild seals joined by a sturdy brace around an industrial handshake, no wording.',
 'SFC_industrial_socialization':'Socialized industry: a heavy communal factory key supported by two worker palms above a low red-edged production bench.',
 'SFC_new_ricostruzione_industriale':'Industrial reconstruction institute: a broken stone industrial arch repaired with shiny steel braces and a large surveying plumb bob.',
 'SFC_production_lines':'One distinctive S-shaped conveyor assembly line carrying three unfinished machine housings beneath a strong overhead rail.',
 'SFC_planned_economy':'Planned economy: an immense mechanical slide rule crossing a production flowchart board and a solid brass scheduling wheel, no letters or numbers.',
 'SFP_invite_anti_fascist_emigrants':'A 1930s travel trunk with an open passport showing only a blank oval portrait, a welcoming bronze doorway key and folded refugee travel permit.',
 'SFP_reconnect_to_the_balkans':'Contact eastern French cities: a vintage telegraph key sending two bright metallic wires toward a Gothic city tower silhouette.',
 'SFP_loyalty_to_moscow':'Eastern allied cooperation: a paired rail-coupler locking together in front of two different fortified French town gates, no foreign symbols.',
 'SFP_review_foreign_policy':'A large brass magnifying lens poised above a round diplomatic compass and one torn obsolete agreement beneath, no text.',
 'SFP_support_the_finns':'Support northern French partners: a wooden aid sled loaded with one warm blanket roll and a large medical supply chest, a protective hand above.',
 'SFP_confirm_eastern_commitments':'An upright defensive pike and a heavy wax-sealed pledge leaning on a steel shield, a Gothic French eastern gate embossed faintly on the shield.',
 'SFP_strengthen_the_little_entente':'Three different French city-gate crests locked firmly into a triangular stone keystone construction, one bronze tightening clasp.',
 'SFP_invite_yugoslavia':'An Alsatian stork beside an open diplomatic invitation, a traditional half-timbered Alsace gateway rising behind, no letters.',
 'SFP_invite_romania':'A Burgundy wine-vine scroll encircling one open invitation envelope, a characteristic Burgundian square tile roof behind.',
 'SFP_join_the_ententes':'Two independently shaped diplomatic signet rings interlocking on a joined ribbon with a central metal bridge clasp.',
 'SFP_revive_the_franco_polish_alliance':'Paris-Metz revived alliance: a delicate Paris Eiffel silhouette joined to a stout Metz cathedral tower by one large renewed brass hinge.',
 'SFP_buy_time':'A tilted bronze hourglass with a fountain-pen nib wedged across the middle and a restrained curling diplomatic ribbon.',
 'SFP_go_with_britain':'Normandy cooperation: a tall stone lighthouse and a Parisian lamp connected by a broad bronze harbor chain link.',
 'SFP_concessions_to_italy':'Marseille consultation: two small opposing negotiation seats around a large maritime anchor-shaped conference table, no national flag.',
 'SFP_ratify_the_stresa_front':'Southern pact ratification: three bronze coastal city anchors fastened by a single thick burgundy ratification knot.',
 'SFP_franco_soviet_treaty':'Capital-eastern alliance: a Paris civic dome and a Gothic eastern bastion joined by a large embossed bilateral seal and a short rail line.',
 'SFP_diplomatic_freedom':'A proud dove breaking out through an open diplomatic iron cage, the cage door and escaping dove form a distinctive open silhouette.',
 'SFP_latin_entente':'Southern city alliance: a semicircular amphitheater of three city shields around a large olive sprig and clasped bronze bracelet.',
 'SFP_reach_out_to_spain':'Southwestern partners: a rolled route map passed over a wine barrel and a large fleur-de-lis stamped travel seal, no text.',
 'SFP_invite_portugal':'Invitation to Nantes: a folded blank invitation held within the prow of an antique Loire riverboat with a tall square mast.',
 'SFP_compensate_italy':'Marseille cooperation compensation: a massive maritime balance weighing a shipyard anchor against a large capital coin, with a small sealed offer behind.',
 'SFP_intervention_in_greece':'Mediterranean district cooperation: a large conch shell cradling an olive twig and a bronze maritime partnership ring.',
 'SFP_towards_a_new_europe':'Towards a new France: a splendid newly opened double civic gate and a bright rising bronze sun above an outline of mainland France.',
 'SFP_establish_spheres_of_influence':'A large brass geographical divider compass enclosing a globe in three wide concentric metallic influence rings.',
 'SFP_dominate_the_middle_east':'Dominating French east: a bold chess rook rising over a three-way stone bridge, the rook has restrained Gothic French geometry.',
 'SFP_woo_italy':'Courting Marseille: a small olive crown held out toward a large Marseille harbor wheel and a single white negotiation rose.',
 'SFP_join_germany':'Eastern entente: a horizontal heavy alliance chain fastens a winged Parisian civic crest to a fortified eastern French city shield.',
 'SFP_no_further_humiliations':'Rejecting humiliation: an unbent shining bronze diplomatic sword rises out of a broken kneeling manacle, no enemies depicted.',
 'SFC_anglo_italian_agreements':'Corsica-Normandy agreement: a Corsican mountain tower and a Norman stone abbey on either side of a broad folded accord, a large single copper clasp.',
 'SFC_seek_british_military_cooperation':'Seeking Normandy military cooperation: a naval telescope extends from a Corsican watchtower toward a Norman coastal beacon, two small military insignia on the barrel.',
 'SFC_anglo_italian_pact':'Normandy nonaggression: two crossed coastal defense sabers remain secured in their scabbards by one strong bronze peace band.',
 'SFC_invite_france_to_military_partnership':'Inviting Paris military partnership: a tall Corsican garrison drum and a Parisian ceremonial sword arranged around an open invitation scroll.',
 'SFC_franco_italian_pact':'Corsica-Paris nonaggression: a Corsican tower-shaped bronze padlock securing two lowered rifle bayonets, Paris fleur-de-lis relief on one handle.',
 'SFC_cooperate_with_moderates':'Moderate coalition: two differently gloved hands carefully balance one upright political scale, with a small olive leaf in the balanced center.',
 'SFC_iberian_protection':'Southwest security cooperation: a thick folded shield enfolds a Bordeaux wine-cluster civic crest and a small coastal watch lantern.',
 'SFC_foreign_affairs':'A 1930s diplomats leather dispatch case with a conspicuous brass latch, a compact world globe half revealed within the open case.',
 'SFC_potential_allies_in_the_balkans':'Potential southern allies: three separated empty treaty chairs beside a large open compass pointed toward a Provençal square tower.',
 'SFC_guarantee_austrian_independence':'Guaranteeing Alsace independence: a protective armored hand cradles a characteristic half-timbered Alsatian town gate beneath a large stork wing.',
 'SFC_negotiate_italian_claims':'Negotiating Corsican claims: a Corsica-shaped copper map surrounded by survey dividers and a single broad pointing diplomatic hand.',
 'SFC_ratify_the_stresa_front':'Ratifying capital pact: an oversized fountain pen stamps a bronze Paris dome-shaped ratification seal onto a curled treaty with no letters.',
 'SFC_joint_military_programs':'Joint military programs: three military calipers jointly measure a single tank track link above a shared engineering plan.',
 'SFC_pact_of_steel':'Eastern military pact: two massive riveted steel wrists lock in a clasp above a short Gothic arch and a compact French eastern city shield.',
 'SFC_german_military_cooperation':'Military cooperation with Metz: a Metz cathedral tower relief set within one large military rangefinder, a folded blank training map at the base.',
 'SFC_treaty_with_germany':'Metz cooperation agreement: a curved Gothic Metz gate signet pressing a deep seal into one blank dispatch sheet, with a brass hinge along the side.',
 'SFC_request_control_of_french_territories':'Negotiated mainland outposts: a large coastal harbor key passes from a diplomatic glove toward a small stone watchtower and miniature landing pier.',
 'SFC_befriend_japan':'Courting Nantes: a Nantes sailing-ship prow and Corsican granite tower joined by a single sturdy shipbuilders handshake.',
 'SFC_befriend_greece':'Corsican outreach to Marseille: a wide-spoked Marseille harbor pilot wheel tied to a mountain tower by a flowing white olive ribbon.',
 'SFC_befriend_turkey':'Courting Toulouse: a distinctive brick Toulouse civic tower beside a brass aviators compass and a single clasped negotiating glove.',
 'SFC_spanish_italian_alliance':'Bordeaux cooperation proposal: a Bordeaux stone bridge spanning a curled maritime treaty, one grape-cluster diplomatic seal at the center.',
 'SFC_befriend_portugal':'Bordeaux friendship: a single ornate bronze wine goblet and a Corsican olive branch resting across an open harbor invitation.',
 'SFC_military_cooperation':'Shared military training: two different infantry rifles placed side by side on a shared training rack and a strong instructor pointer.',
 'SFC_mafia_abroad':'Overseas mafia network: a shadowy 1930s felt hat over a discreet international shipping ledger and an antique coded brass locket, no text.',
 'SFC_peace_preservation':'Preserving peace: a large white dove perched atop a downward-pointing sheathed spear and a circular peace watch dial.',
 'SFC_reestablish_old_alliances':'Rebuilding old alliances: a once-broken ornate treaty clasp newly soldered together, with two aged curled alliance ribbons.',
 'SFC_military_agreements':'Military agreements: a thick blank contract pinned by a crossed cartridge belt buckle and a cleanly sheathed officer dagger.',
 'SFC_condemn_colonialism':'Rejecting mainland domination: a bronze Corsican civic fist pushing back a large imposed imperial stamp and breaking its heavy handle.',
 'SFC_negotiations_with_albania':'Negotiations with Marseille: an immense port conference bell between a Corsican mountain silhouette and Marseille cathedral dome.',
})
SUBJECTS.update({
 'SFP_split_belgium':'Picardy unification: a tall Picard brick belfry with a newly raised single bronze civic banner and one decisive crossed infantry bayonet at its base; no flags or text.',
 'SFP_bring_home_quebec':'Aquitaine unification: an Aquitaine stone town gate with an oversized returned city key and one curling vine at the foot; the long key dominates.',
 'SFP_expand_to_the_suez':'Advancing to the Rhone river mouth: a large river-lock wheel opens a heavy water gate beneath a small cargo barge prow; the water gate and wheel dominate.',
 'SFP_avenge_waterloo':'Northern campaign: a heavy French cavalry cuirass and single lowered lance stand above a breached small stone northern belfry gateway; the cuirass dominates.',
 'SFP_reorganize_the_dutch':'Reorganizing Picardy: a large civic surveyors square straightens a leaning brick administrative arch, with one small rolled blank regional charter.',
 'SFP_retribution_for_sedan':'Champagne campaign: a massive artillery shell beside a shattered slate-roof defensive blockhouse, with a tiny vine sprig at the base.',
 'SFP_disunite_germany':'Advancing into Lorraine: an immense armored gauntlet pushes aside a broken iron fortress gate, with a small Gothic eastern town tower behind.',
 'SFP_return_to_borodino':'Eastern French unification: a single tall steel bridge keystone bears a French fleur-de-lis relief, protected by one upright saber and a broad bronze rising sun.',
 'SFC_towards_a_greater_italy':'Corsican consolidation: a mountain civic tower is newly connected to a lower coastal tower by a large fresh brass hinge, the hinge dominates; no Italian symbols.',
 'SFC_balkan_ambition':'Ambitions on the southern French mainland: an enormous brass navigation dividers compass spans a Provençal harbor arch and a short coastal road segment.',
 'SFC_support_albanian_irredentism':'Savoy campaign: a stout Savoy mountain pass gate is protected by a huge infantry bayonet and one rough Alpine rock; no foreign flags or heraldic coats.',
 'SFC_italian_irredentism':'Corsican national consolidation: an open iron civic manacle is pulled apart by a strong Corsican granite fist with a small olive branch; no Italian emblems.',
 'SFC_demand_ticino':'Savoy regional campaign: a broad winding Alpine stone bridge and a prominently planted mountaineers ice axe, with a single bold mountain ridge behind.',
 'SFC_war_with_the_uk':'Normandy campaign: a massive coastal landing ramp unfolds toward a small Norman timber-framed shore house, with a single dominant lowered naval anchor.',
 'SFC_war_with_greece':'Languedoc campaign: an oversized medieval stone city gate with one forceful modern infantry rifle set diagonally across it and a small southern olive sprig.',
 'SFC_claims_on_turkey_bba':'Provence campaign: a tall rugged stone harbor bastion and a large commanding maritime signal lantern held out over one thick protective bronze shield.',
})

def concise_pending():
    data=json.loads(read(PLAN));ids=set(json.loads(read(ROOT/'dist/unique-local-generation-ids.json')))
    pending=[]
    for a in data['assets']:
        if a['id'] not in ids or 'source_sha256' in a:continue
        assert a['id'] in SUBJECTS,a['id']
        a['earlier_unused_generation_prompt']=a['prompt']
        a['prompt']=STYLE+' Required dominant subject: '+SUBJECTS[a['id']]
        pending.append(a)
    save(PLAN,data);save(ROOT/'dist/unique-concise-pending.json',pending)
    print(json.dumps(dict(remaining=len(pending))))

def refresh_prompts():
    data=json.loads(read(PLAN))
    for a in data['assets']:
        if a['id'] in SUBJECTS and 'source_sha256' not in a and 'Required dominant subject:' not in a['prompt']:
            a['prompt']+=' Required dominant subject: '+SUBJECTS[a['id']]
    save(PLAN,data)

def read(p):return p.read_text(encoding='utf-8-sig')
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(data):return hashlib.sha256(data).hexdigest()
def shape(rows):return [(x.key,x.operator,shape(x.value) if isinstance(x.value,list) else x.value) for x in rows if x.key not in ['icon','picture']]

def plan():
    assert not PLAN.exists(),'Preserve the existing generation manifest; do not overwrite completed artwork or prompt provenance'
    remake=json.loads(read(ROOT/'design/vanilla-major-remake.json'));family=json.loads(read(ROOT/'design/focus-art-spec.json'));groups=collections.defaultdict(list)
    for n in remake['nodes']:groups[n['art']].append(n)
    # Each of the 48 existing independently generated masters may be used by
    # exactly ONE focus. All other nodes require a new standalone generation.
    assets=[];existing={a['key']:a for a in family['assets']}
    for n in remake['nodes']:
        key=n['id'].lower();siblings=groups[n['art']];a=dict(id=n['id'],key=key,tag=n['tag'],title=n['title'],family=n['art'],source=f'art/focus/unique/source/{key}.png')
        # motorway receives a newly requested bespoke illustration; retain the
        # old road master for a different applicable road focus instead.
        first=next((x for x in siblings if x['id']!='SFP_autoroutes'),siblings[0])
        if n['id']==first['id']:
            old=existing[n['art']];a.update(source=old['source'],source_sha256=old['source_sha256'],prompt=old['prompt'],provenance='Existing independently generated master, now exclusive to one focus')
        else:
            related='; '.join(x['title'] for x in siblings if x['id']!=n['id'])
            a['prompt']=STYLE+f' Target focus: {n["title"]} ({n["id"]}, an internal ID which must NEVER appear as lettering). Gameplay purpose: '+n['original_description'][:1800]+f' Local adapted title {n["title"]} is authoritative; treat any foreign place in the original purpose as the corresponding French local district. Design the dominant physical object specifically for this focus, rather than a generic {n["art"]} emblem. Related focuses will EACH have other independent illustrations: {related}. Make this focus distinguishable from those by its main subject, object arrangement, and silhouette, not merely a tint, small badge, number, or background. Do not draw an entire focus tree. Deliver this ONE icon only.'
            a['provenance']='Pending separate built-in imagegen call'
        assets.append(a)
    files=['mod/common/national_focus/sofzh_paris.txt','mod/common/national_focus/sofzh_corsica.txt','mod/common/ideas/sof_vanilla_major.txt','mod/common/dynamic_modifiers/sof_vanilla_major.txt','mod/common/decisions/sof_vanilla_major.txt','mod/common/decisions/categories/sof_vanilla_major.txt']
    baseline={p:sha(json.dumps(shape(parse(read(ROOT/p))),ensure_ascii=False).encode('utf-8')) for p in files}
    data=dict(version='4.2.0',scope='473 retained Paris/Corsica focuses; each has exclusive art and texture, gameplay preserved from 4.1.0',assets=assets,semantic_baseline=dict(source_commit='3120dbb9105c9c2e5a8bc341b195554dafa18517',semantic_sha256=baseline),game_engine_verified=False)
    save(PLAN,data);refresh_prompts();print(json.dumps(dict(total=len(assets),existing=sum('source_sha256' in a for a in assets),to_generate=sum('source_sha256' not in a for a in assets))))

def collect(key,path):
    data=json.loads(read(PLAN));asset=next(a for a in data['assets'] if a['key']==key)
    assert path.is_file(),path
    im=Image.open(path);assert im.mode=='RGBA' and im.getchannel('A').getextrema()[0]==0 and im.getchannel('A').getextrema()[1]>=250,path
    dest=ROOT/asset['source'];dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.resolve()!=path.resolve():shutil.copyfile(path,dest)
    asset['source_sha256']=sha(dest.read_bytes());asset['provenance']='Separate built-in imagegen call';save(PLAN,data)
    print(json.dumps(dict(saved=key,complete=sum('source_sha256' in a for a in data['assets']),total=len(data['assets']))))

def export():
    data=json.loads(read(PLAN));assets=data['assets'];assert len(assets)==473
    assert all('source_sha256' in a for a in assets),'Not every focus has independent art yet'
    assert len({a['source_sha256'] for a in assets})==473,'Reused or identical source images'
    native=MOD/'gfx/interface/sof_focus_unique';native.mkdir(parents=True,exist_ok=True);(ART/'exports').mkdir(parents=True,exist_ok=True)
    sprites=[];hashes=[]
    for a in assets:
        source=ROOT/a['source'];assert sha(source.read_bytes())==a['source_sha256'],source
        im=Image.open(source).convert('RGBA');alpha=im.getchannel('A').getextrema();assert alpha[0]==0 and alpha[1]>=250
        fitted=im.copy();fitted.thumbnail((86,86),Image.Resampling.LANCZOS);result=Image.new('RGBA',(96,96));result.alpha_composite(fitted,((96-fitted.width)//2,(96-fitted.height)//2))
        png=ART/'exports'/(a['key']+'.png');dds=native/(a['key']+'.dds');result.save(png);result.save(dds);hashes.append(sha(result.tobytes()))
        sprites.append(f'spriteType = {{ name = "GFX_sof_focus_unique_{a["key"]}" texturefile = "gfx/interface/sof_focus_unique/{a["key"]}.dds" noOfFrames = 1 }}')
    assert len(set(hashes))==473,'Duplicate native-resolution pixels'
    (MOD/'interface/sof_focus_unique.gfx').write_text('spriteTypes = {\n'+'\n'.join(sprites)+'\n}\n',encoding='utf-8',newline='\n')
    return data

def apply():
    data=export();assets={a['id']:a for a in data['assets']};remake=json.loads(read(ROOT/'design/vanilla-major-remake.json'));records={n['id']:n for n in remake['nodes']}
    for country in ['paris','corsica']:
        p=MOD/f'common/national_focus/sofzh_{country}.txt';text=read(p);changes=[]
        for n in entries(one(parse(text),'focus_tree').value,'focus'):
            fid=scalar(n.value,'id');a=assets[fid];icon=one(n.value,'icon');changes.append((icon.start,icon.end,'icon = GFX_sof_focus_unique_'+a['key']));records[fid]['art']=a['key'];records[fid]['art_source']=a['source']
        p.write_text(replace(text,changes),encoding='utf-8',newline='\n')
    remake['version']=data['version'];remake['art_style']='Exclusive illustration for every retained focus, generated and curated native artwork';save(ROOT/'design/vanilla-major-remake.json',remake)
    bindings=json.loads(read(ROOT/'design/focus-art-bindings.json'))
    for b in bindings['bindings']:
        if b['role']=='focus':b.update(art=assets[b['id']]['key'],exclusive=True)
    bindings['version']=data['version'];bindings['unique_focus_assets']=len(assets)
    bindings['family_assets']=48;bindings['assets']=48+len(assets)
    bindings['usage']=dict(collections.Counter(b['art'] for b in bindings['bindings']))
    bindings['focus_usage']={a['key']:1 for a in data['assets']}
    save(ROOT/'design/focus-art-bindings.json',bindings)
    contacts(data);print(json.dumps(dict(ok=True,focuses=len(assets),distinct_source_images=len(assets),distinct_native_pixel_images=len(assets))))

def contacts(data):
    out=ROOT/'docs/previews'/data['version'];out.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
    for tag in ['PRS','AJC']:
        nodes=[a for a in data['assets'] if a['tag']==tag]
        for start in range(0,len(nodes),64):
            selected=nodes[start:start+64];im=Image.new('RGB',(1200,70+((len(selected)+7)//8)*140),'#1c2328');d=ImageDraw.Draw(im)
            d.text((20,18),f'{tag} · 独立国策图标 {start+1}–{start+len(selected)} · 96像素',font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21),fill='#e9d5a5')
            for i,a in enumerate(selected):
                x=18+i%8*149;y=65+i//8*140;icon=Image.open(ART/'exports'/(a['key']+'.png'));im.paste(icon,(x+24,y),icon)
                title=a['title'];lines=[title[j:j+10] for j in range(0,min(len(title),20),10)]
                for j,line in enumerate(lines):d.text((x+73,y+98+j*17),line,font=font,anchor='mt',fill='#d7cbb0')
            im.save(out/f'{tag}-ICONS-{start//64+1}.png')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['plan','collect','apply','refresh','concise']);parser.add_argument('--key');parser.add_argument('--path',type=Path);args=parser.parse_args()
    if args.command=='plan':plan()
    elif args.command=='collect':collect(args.key,args.path)
    elif args.command=='refresh':refresh_prompts()
    elif args.command=='concise':concise_pending()
    else:apply()
