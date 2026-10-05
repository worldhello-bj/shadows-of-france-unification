"""Curate different native illustrations; never create tinted copies or badges.

The draft is a review aid. Individual overrides and rejected candidates are
recorded separately, and chosen source artwork is copied into the repository.
"""
import argparse,collections,hashlib,json,math,re,struct,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from unique_focus_art import ROOT,PLAN,read,save,sha
from hoi4_script import parse,entries,scalar

GAME=Path('D:/steam/steamapps/common/Hearts of Iron IV')
SELECTION=ROOT/'design/native-focus-art-selection.json'
TERMS={
 'diplomacy':'treaty agreement alliance diplomatic diplomacy conference relations cooperation trade friendship concession negotiation political_pressure peace international mission pact invitation military_deal scientific_exchange intelligence_exchange licence license',
 'unification':'unity unification union liberation free independence national consolidation federation resistance sovereignty defend annex reclaim reunification integration territory claim political_pressure border fatherland population peace civil',
 'workers':'worker workers labor labour union communist communism socialist socialism revolution red peasant collective collectivization strike proletariat syndicalist commune',
 'civilian_industry':'industry industrial factory manufacture production workshop investment economic economy reconstruction works industrialization public_works experts employment corporatism corporation infrastructure',
 'militia':'militia paramilitary volunteer blackshirts guard police carabinieri corps reserve infantry armed soldier rifle legion brigade',
 'empire':'empire imperial emperor eagle crown monarchy monarch king throne glory imperialism court royal order power regency',
 'fighter':'fighter aircraft aviation airforce pilot aerial airplane plane flight jet sky air_school aeronautica',
 'parliament':'parliament parliamentary assembly council election democratic democracy government representation cabinet congress civil constitution federation',
 'army':'army military infantry soldier force armed troops training drill academy doctrine command defensive defense mobilization legion brigade',
 'propaganda':'propaganda press media newspaper printing public culture cultural popular rally support nationalism national_education mobilization information resistance',
 'security':'security intelligence counterintelligence secret espionage spy spies operative infiltration surveillance sabotage conspiracy agency purge police national_security',
 'battleship':'battleship dreadnought heavy_fleet big_guns large_navy ship navy naval',
 'equality':'equality equal enfranchise suffrage rights vote reform legal justice freedom liberty democracy liberation emancipation constitution civil socialist women',
 'republic':'republic republican democratic democracy government election freedom liberty liberation council constitution popular',
 'crown':'crown monarchy monarch king royal regency throne emperor court dynasty nobility aristocracy',
 'currency':'currency bank banking money monetary finance financial credit gold capital devaluation economy trade market tariff stockpile_currency price',
 'social_welfare':'welfare social housing medical hospital employment education health population healthcare immigration pension refugee poor poverty',
 'military_industry':'arms armament weapon military_industry military_factory ammunition gun artillery production manufacture tank_assembly',
 'bomber':'bomber bombing bomb strategic tactical cas close_air aircraft',
 'constitution':'constitution law legal justice court parliament democracy reform election judicial administration judges vote',
 'science':'science scientific research university technology technical scientists nuclear laboratory institute innovation rocket weapon',
 'agriculture':'agriculture agricultural farm farmer farmland grain food peasant rural land_reclamation land_redistribution',
 'naval_base':'naval_base dockyard shipyard port harbor harbour naval_infrastructure naval_industry navy',
 'corsica':'island coastal mountain self independence sovereign home autonomy militia local reconstruction resist',
 'fortification':'fort fortify fortress fortification defense defensive bastion wall bunker stronghold',
 'submarine':'submarine undersea wolf_pack sub torpedo',
 'fuel':'fuel oil refinery refining rubber petroleum',
 'landing':'landing invasion naval_invasion marine amphibious fleet coast naval',
 'logistics':'logistics supply network transport depot army_supply truck rail infrastructure',
 'roads':'road roads infrastructure transport construction public_works highway',
 'special_forces':'special_forces elite commando marine paratrooper corps veteran airborne',
 'destroyer':'destroyer escort small_ship navy naval',
 'communications':'communication radio telephone phone radar electronic signal cryptologic',
 'church':'church catholic pope bishop faith spiritual religion religious clerical theologian concordat',
 'infantry':'infantry soldier rifle small_arms troops military armed legion brigade training',
 'paris':'france french paris civic capital marianne liberate resistance republic',
 'carrier':'carrier air_carrier aircraft_carrier naval_air aviation',
 'naval_air':'naval_bomber naval_air aviation naval aircraft air_carrier carrier',
 'engineering':'engineer engineering machinery mechanics technical motor industry research production',
 'railway':'railway railroad rail train transport supply_line infrastructure',
 'motorized':'motor motorized motor_cycle truck vehicle mechanized transport armored',
 'armor':'armor armored tank tankette mechanized tracked panzer heavy_tank',
 'mountain':'mountain alpine hill winter mountaineer alpin',
 'cruiser':'cruiser navy light_cruiser ship naval',
 'steel':'steel metal mill mining ore resource extraction coal iron industry',
 'power':'power energy hydroelectric electrification dam turbine electricity',
 'artillery':'artillery gun cannon battery ordnance anti_tank self_propelled',
 'coast_defense':'coast coastal defense fortify naval_mine mine_warfare bunker port harbor',
}
# These names imply a map, flag, foreign emblem or geographically specific pact.
# More visual exclusions are added to the checked-in selection after review.
EXCLUDE='befriend_ attack_ invade_ puppet annex_ map_ flags flag_ continent america africa asia chinese japanese japan manchur indonesia baltic pacific scandina balkan nordic norse turk hejaz arab islam templar comintern teutonic swastika lebensraum deutsch pan_slavic colonies commonwealth hindu buddh pakistan india_ indian_ siberian arctic lithuanian mongolia antarctic croatia habesha ethiopian suez brazil chile mapuche romania bulgaria hungar habsburg ottoman carlist iberian iberia spanish polish westminster korea china australian australia_ indochina malaya nippon pan_german danubian catalonia norwegian danish swedish finnish icelandic union_jack chilean argentine portuguese lithuania latvia estonia tajik uzbek philippine siamese finno_russian african soviet_republic northern_territory reich britain british philipino new_zealand'.split()
GENERAL='council parliament law justice treaty diplomacy agreement alliance friendship reform constitution republic democratic socialist workers unions labor civil political peace campaign propaganda cooperation international invest industry economy production army naval aircraft fighter bomber training factory rail road artillery tank monarch king crown trade research university education welfare security intelligence espionage operative administration credit currency finance bank reconstruction infrastructure grain farming housing hospital clergy catholic church religion tradition press equality freedom liberation independence autonomy sovereign consolidation unity integration military weapons science militia guard corps veteran peasants revolutionary revolution defense defensive fortress fortification border power energy resource mining oil fuel supply logistics motorized mechanized armament ammunition marine mountain paratroop radio communication aerial aviation royal emperor empire court resistance nationalism public popular mobilization mobilize work economy economic air_ fleet cruiser submarine carrier destroyer artillery cannon gun aeronautic navy medics conspiracy equality propaganda rights vote elections tyrann queen inheritance throne mediterra civil servants settle science self_ manpower secret service support_democracy support_communism support_fascism devalue currency money monetary social peasants volunteer'.split()

def tokens(s):return set(re.findall('[a-z0-9]+',s.lower()))-{'gfx','focus','goal','generic','sof','sfp','sfc','fra','ita','the','of','to','and','a','in','with','our','for','on','de','del','della','di','dei'}
def score(a,c,original):
    name=c['sprite'].lower();at=tokens(a['id']);ct=tokens(name);value=0
    for term in TERMS[a['family']].split():
        if term in name:value+=11 if '_' in term else 7
    value+=sum(17+min(5,len(t)) for t in at & ct)
    if original.get(a['id'])==c['sprite']:value+=27
    if any(x in name for x in ['_fra_','_ita_','_generic_']):value+=2
    if 'shine' in name or 'uap' in name or 'alp' in name:value-=3
    if a['family'] in ['fighter','bomber','armor','artillery','submarine','carrier','naval_air','destroyer','cruiser','mountain','motorized']:
        if not any(term in name for term in TERMS[a['family']].split()):value-=500
    return value

def hungarian(weights):
    """Maximum-weight matching, one artwork per focus, using rectangular rows."""
    n=len(weights);m=len(weights[0]);assert n<=m
    u=[0]*(n+1);v=[0]*(m+1);p=[0]*(m+1);way=[0]*(m+1)
    for i in range(1,n+1):
        p[0]=i;j0=0;minv=[float('inf')]*(m+1);used=[False]*(m+1)
        while True:
            used[j0]=True;i0=p[j0];delta=float('inf');j1=0
            for j in range(1,m+1):
                if used[j]:continue
                cur=-weights[i0-1][j-1]-u[i0]-v[j]
                if cur<minv[j]:minv[j]=cur;way[j]=j0
                if minv[j]<delta:delta=minv[j];j1=j
            for j in range(m+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                else:minv[j]-=delta
            j0=j1
            if p[j0]==0:break
        while True:
            j1=way[j0];p[j0]=p[j1];j0=j1
            if j0==0:break
    result=[0]*n
    for j in range(1,m+1):
        if p[j]:result[p[j]-1]=j-1
    return result

def native_image(c):
    try:im=Image.open(c['source']).convert('RGBA')
    except NotImplementedError:
        raw=Path(c['source']).read_bytes()
        assert raw[:4]==b'DDS ' and raw[84:88]==b'DX10',c['sprite']
        height,width,pitch=struct.unpack_from('<III',raw,12)
        fmt=struct.unpack_from('<I',raw,128)[0]
        if fmt not in (87,88,90,91,92,93):raise
        stride=pitch if pitch>=width*4 else width*4
        mode='BGRA' if fmt in (87,90,91) else 'BGRX'
        im=Image.frombytes('RGBA' if mode=='BGRA' else 'RGB',(width,height),raw[148:148+stride*height],'raw',mode,stride,1).convert('RGBA')
    frames=int(c['frames'])
    if frames>1:im=im.crop((0,0,im.width//frames,im.height))
    assert im.getchannel('A').getextrema()==(0,255),c['sprite']
    return im

def fingerprint(im):
    p=list(im.convert('L').resize((9,8),Image.Resampling.LANCZOS).getdata())
    return sum((p[y*9+x]>p[y*9+x+1])<<(y*8+x) for y in range(8) for x in range(8))

def draft():
    data=json.loads(read(PLAN))
    active_file=ROOT/'dist/unique-local-generation-ids.json'
    generating=set(json.loads(read(active_file))) if active_file.exists() else set()
    pending=[a for a in data['assets'] if 'source_sha256' not in a and a['id'] not in generating]
    catalog=json.loads(read(ROOT/'dist/native-focus-art-catalog.json'));original={}
    records=json.loads(read(ROOT/'design/vanilla-major-remake.json'))['nodes'];donor={n['donor']:n['id'] for n in records}
    for fname in ['france.txt','italy.txt']:
        for tree in entries(parse(read(GAME/'common/national_focus'/fname)),'focus_tree'):
            for n in entries(tree.value,'focus'):
                fid=scalar(n.value,'id')
                if fid in donor:original[donor[fid]]=scalar(n.value,'icon')
    selection=json.loads(read(SELECTION)) if SELECTION.exists() else dict(rejected_sprites=[],overrides={})
    unique={};pixelset=set();silhouettes=[];pool=[]
    for c in catalog:
        name=c['sprite'].lower()
        origin=re.search(r'gfx_(?:focus|goal)_(?:focus_)?([a-z]{3})_',name)
        if origin and origin.group(1) not in ('fra','ita') and origin.group(1) not in ('gen','nav','air','arm'):
            if c['sprite'] not in selection.get('allowed_foreign_sprites',[]):continue
        if c['sprite'] in selection['rejected_sprites'] or any(t in name for t in EXCLUDE):continue
        if 'overlay' in name or any(t in name for t in ['_shine','_uap','_alp']):continue
        relevant=GENERAL+[term for family in TERMS.values() for term in family.split()]
        if not any(t in name for t in relevant):continue
        if c['sha256'] in unique:continue
        unique[c['sha256']]=c
        try:im=native_image(c)
        except (AssertionError,OSError,NotImplementedError):continue
        box=im.getchannel('A').getbbox()
        if not box or min(box[2]-box[0],box[3]-box[1])<45:continue
        digest=sha(im.tobytes())
        if digest in pixelset:continue
        fp=fingerprint(im)
        if any((fp^other).bit_count()<=4 for other in silhouettes):continue
        pixelset.add(digest);silhouettes.append(fp);pool.append(c)
    pending_ids={a['id'] for a in pending}
    overrides={fid:s for fid,s in selection['overrides'].items() if fid in pending_ids};by={c['sprite']:c for c in catalog}
    taken={by[s]['sha256'] for s in overrides.values()};pool=[c for c in pool if c['sha256'] not in taken]
    save(ROOT/'dist/native-focus-art-pool.json',pool)
    automatic=[a for a in pending if a['id'] not in overrides]
    weights=[[score(a,c,original) for c in pool] for a in automatic]
    assignments=hungarian(weights);chosen={a['id']:(pool[j],weights[i][j]) for i,(a,j) in enumerate(zip(automatic,assignments))}
    for fid,s in overrides.items():chosen[fid]=(by[s],score(next(a for a in pending if a['id']==fid),by[s],original))
    rows=[]
    for a in pending:
        c,match=chosen[a['id']];rows.append(dict(id=a['id'],title=a['title'],family=a['family'],candidate=c,semantic_score=match))
    selection.update(version=data['version'],scope='Native illustrations are exclusive within the 473 retained major focuses; existing other-country generic tree is preserved.',draft=rows,pool_size=len(pool),visual_review_complete=False)
    save(SELECTION,selection);contacts(rows)
    print(json.dumps(dict(native=len(rows),candidates=len(pool),low_score=sum(r['semantic_score']<12 for r in rows))))

def contacts(rows):
    out=ROOT/'dist/native-selection';out.mkdir(parents=True,exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
    for start in range(0,len(rows),56):
        selected=rows[start:start+56];im=Image.new('RGB',(1400,70+math.ceil(len(selected)/8)*152),'#1c2328');d=ImageDraw.Draw(im)
        d.text((15,15),f'原版候选审阅 {start+1}–{start+len(selected)}',font=font,fill='#e8d7ac')
        for i,r in enumerate(selected):
            x=10+i%8*173;y=50+i//8*152;icon=native_image(r['candidate']);icon.thumbnail((96,96));im.paste(icon,(x+34,y),icon)
            for j,label in enumerate([str(start+i+1)+' '+r['title'],r['candidate']['sprite'].replace('GFX_focus_','').replace('GFX_goal_','')]):
                text=label[:22];d.text((x,y+100+j*18),text,font=font,fill='#e8d7ac' if j==0 else '#99aebb')
        im.save(out/f'CANDIDATES-{start//56+1}.png')

def apply():
    data=json.loads(read(PLAN));selection=json.loads(read(SELECTION));assert selection['visual_review_complete'],'Review selected native illustrations before binding them'
    by={a['id']:a for a in data['assets']}
    for r in selection['draft']:
        a=by[r['id']]
        if 'source_sha256' in a:
            assert a.get('native_sprite'),'Never overwrite an independently generated illustration with native art'
            assert sha((ROOT/a['source']).read_bytes())==a['source_sha256'],'Existing native source changed outside the curation tool'
        c=r['candidate'];assert sha(Path(c['source']).read_bytes())==c['sha256'];dest=ROOT/a['source'];dest.parent.mkdir(parents=True,exist_ok=True);native_image(c).save(dest)
        a.update(source_sha256=sha(dest.read_bytes()),provenance='Exclusive native HOI4 illustration, selected by subject and visually reviewed',native_sprite=c['sprite'],native_texture=c['texture'],native_texture_sha256=c['sha256'],native_frame=0)
        # An unused generation prompt must not be misreported as provenance.
        if 'prompt' in a:a['unused_generation_prompt']=a.pop('prompt')
        a['selection_reason']=r.get('review_note',f'Native composition matched to {a["title"]}; individual subject and silhouette reviewed at 96px')
    data['art_policy']='Each of 473 focuses owns a different complete illustration. Independently generated art and individually selected native art are both used; no tint, badge or filename variants.'
    save(PLAN,data);print(json.dumps(dict(complete=sum('source_sha256' in a for a in data['assets']),native=len(selection['draft']))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['draft','apply']);args=p.parse_args();globals()[args.command]()
