"""Build local, replaceable, optimized GLB food representations (not photogrammetry).
Build-only dependencies: numpy, Pillow, trimesh==4.6.13. Not needed by Flask at runtime.
"""
from pathlib import Path
import math, json
from collections import defaultdict
import numpy as np
from PIL import Image, ImageFilter
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'static/models/auth';OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(14335)
PALETTE={'ceramic':('#e5ded0',.25),'dark':('#282c27',.3),'meat':('#764022',.39),'rice':('#f5ecd9',.63),'fries':('#d6a744',.45),'tomato':('#b83e27',.34),'onion':('#c490ae',.48),'fish':('#f1e1d1',.32),'potato':('#e88728',.54),'corn':('#efdfbd',.5),'leaf':('#477d30',.54),'yellow':('#dcbd49',.44),'avocado':('#87a650',.6),'coffee':('#5e301a',.27),'caramel':('#a86425',.24),'flan':('#ebcf9a',.37)}

def texture(key):
    color=PALETTE[key][0]; rgb=np.array([int(color[i:i+2],16) for i in (1,3,5)],dtype=float)
    low=Image.fromarray(rng.integers(65,200,(32,32),dtype=np.uint8)).resize((256,256),Image.Resampling.BICUBIC)
    fine=rng.normal(0,3,(256,256))
    factor=np.asarray(low)/255*.30+.83+fine/255
    return Image.fromarray(np.clip(factor[:,:,None]*rgb,0,255).astype(np.uint8),'RGB')
MATS={key:PBRMaterial(name=key,baseColorTexture=texture(key),baseColorFactor=[255,255,255,255],metallicFactor=0,roughnessFactor=value[1],doubleSided=False) for key,value in PALETTE.items()}

def sphere(scale=(1,1,1)):
    m=trimesh.creation.icosphere(subdivisions=2,radius=1)
    m.vertices*=np.array(scale);return m

def jitter(mesh,amount=.07):
    mesh=mesh.copy();mesh.vertices*=rng.uniform(1-amount,1+amount,(len(mesh.vertices),1));return mesh

def positioned(mesh,pos=(0,0,0),scale=(1,1,1),angle=0):
    m=mesh.copy();m.vertices*=np.array(scale);m.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));m.apply_translation(pos);return m

def plate(dark=False):
    profile=np.array([[0,.03],[.88,.03],[1.14,.075],[1.4,.16],[1.44,.15],[1.44,.10],[1.23,.015],[.8,-.025],[0,-.025]])
    return trimesh.creation.revolve(profile,sections=80)

def make(mode):
    groups=defaultdict(list)
    def add(key,mesh,pos=(0,0,0),scale=(1,1,1),angle=0):groups[key].append(positioned(mesh,pos,scale,angle))
    add('dark' if mode=='signature' else 'ceramic',plate())
    leaf=sphere((.13,.05,.008))
    if mode=='lomo':
        beef=jitter(sphere((.22,.11,.085)),.10)
        for i in range(30):
            a=rng.uniform(0,2*math.pi);r=rng.uniform(0,.65);add('meat',beef,(r*math.cos(a)-.18,r*math.sin(a),.20+rng.uniform(0,.2)),angle=a)
        fry=trimesh.creation.box([.36,.055,.045])
        for i in range(30):add('fries',fry,(rng.uniform(-.8,-.30),rng.uniform(-.7,.65),rng.uniform(.1,.25)),angle=rng.uniform(-1.7,1.7))
        rice=sphere((.033,.016,.014))
        add('rice',sphere((.40,.36,.22)),(.64,.20,.28))
        for i in range(90):
            a=rng.uniform(0,2*math.pi);r=rng.uniform(0,.35);add('rice',rice,(.64+r*math.cos(a),.2+r*math.sin(a),.39+.15*(1-r/.35)),angle=a)
        for i in range(8):add('tomato',sphere((.20,.09,.07)),(rng.uniform(-.65,.2),rng.uniform(-.65,.65),.4),angle=rng.uniform(0,6.2))
        for i in range(9):add('onion',sphere((.16,.035,.02)),(rng.uniform(-.6,.4),rng.uniform(-.5,.6),.42),angle=rng.uniform(0,6.2))
    elif mode=='ceviche':
        fish=jitter(trimesh.creation.box([.19,.15,.13]),.12)
        for i in range(38):
            a=rng.uniform(0,6.28);r=rng.uniform(0,.66);add('fish',fish,(r*math.cos(a),r*math.sin(a),.15+rng.uniform(0,.24)),angle=a)
        for i in range(5):add('potato',sphere((.18,.19,.09)),(.79,.3-i*.16,.17),angle=.2*i)
        for i in range(13):add('corn',sphere((.083,.071,.068)),(rng.uniform(-.95,-.58),rng.uniform(-.4,.4),.20+rng.uniform(0,.06)))
        onion=trimesh.creation.torus(major_radius=.35,minor_radius=.014,major_sections=44,minor_sections=6)
        for i in range(5):add('onion',onion,(rng.uniform(-.15,.18),rng.uniform(-.15,.18),.43+i*.03),scale=(1,.5,1),angle=rng.uniform(0,6))
        for i in range(4):add('tomato',trimesh.creation.torus(major_radius=.08,minor_radius=.019,major_sections=24,minor_sections=6),(rng.uniform(-.4,.4),rng.uniform(-.4,.4),.4))
    elif mode=='dessert':
        cup_profile=np.array([[0,.015],[.25,.015],[.31,.45],[.28,.47],[.25,.41],[.23,.05],[0,.05]])
        cup=trimesh.creation.revolve(cup_profile,sections=56)
        add('ceramic',cup,(-.45,.23,.08),scale=(1.35,1.35,1.35))
        handle=trimesh.creation.torus(major_radius=.14,minor_radius=.04,major_sections=40,minor_sections=8);handle.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));add('ceramic',handle,(-.01,.23,.44))
        add('coffee',trimesh.creation.cylinder(radius=.34,height=.025,sections=60),(-.45,.23,.65))
        add('caramel',trimesh.creation.torus(major_radius=.29,minor_radius=.028,major_sections=60,minor_sections=8),(-.45,.23,.68))
        flan=trimesh.creation.revolve(np.array([[0,0],[.37,0],[.30,.35],[0,.35]]),sections=64)
        add('flan',flan,(.49,-.3,.08))
        add('caramel',trimesh.creation.cylinder(radius=.3,height=.02,sections=56),(.49,-.3,.445))
    else:
        for key,z,h in [('yellow',.17,.22),('avocado',.34,.10),('fish',.43,.07),('yellow',.59,.23)]:
            add(key,trimesh.creation.cylinder(radius=.52,height=h,sections=60),(0,0,z))
        for i in range(10):add('tomato',sphere((.06,.07,.04)),(rng.uniform(-.37,.37),rng.uniform(-.35,.35),.75))
        for x in [-.17,.17]:
            add('rice',sphere((.14,.18,.11)),(x,0,.83));add('yellow',sphere((.095,.10,.03)),(x,0,.925))
    for i in range(12 if mode!='dessert' else 2):
        a=rng.uniform(0,6.28);r=rng.uniform(.1,.60);add('leaf',leaf,(r*math.cos(a),r*math.sin(a),.5 if mode!='signature' else 1.0),angle=a)
    scene=trimesh.Scene()
    for key,parts in groups.items():
        mesh=trimesh.util.concatenate(parts)
        # Texture coordinates follow each surface; PBR textures remain embedded in GLB.
        vertices=mesh.vertices
        uv=np.column_stack(((np.arctan2(vertices[:,1],vertices[:,0])+math.pi)/(2*math.pi),(vertices[:,2]*2)%1))
        mesh.visual=TextureVisuals(uv=uv,material=MATS[key])
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]))
        scene.add_geometry(mesh,geom_name=key,node_name=key)
    dest=OUT/f'{mode}.glb';dest.write_bytes(scene.export(file_type='glb'))
    print(mode,dest.stat().st_size,'bytes',sum(len(m.faces) for m in scene.geometry.values()),'triangles',len(scene.geometry),'draw groups')

for mode in ['lomo','ceviche','dessert','signature']:make(mode)
for name in ['lomo','ceviche','dessert','signature']:
    source=ROOT/'.work/auth-experience/assets'/f'{name}.png'
    if source.exists():
        im=Image.open(source);im.thumbnail((1100,825));im.save(ROOT/'static/images/auth'/f'{name}.webp',quality=88,method=6)
(OUT/'README.md').write_text('''# SmartResto — modelos gastronómicos locales\n\nCuatro GLB de geometría real, con materiales PBR y texturas incrustadas. Representaciones procedurales de referencia, no escaneos fotogramétricos ni reproducciones exactas de productos de los negocios.\n\nLa API prioriza el modelo GLB publicado del plato cuando existe; de lo contrario identifica claramente esta representación de referencia. Cada modelo es sustituible por un GLB profesional optimizado sin modificar formularios ni autenticación.\n\nConstrucción: `.work/auth-experience/build_models.py`; dependencia de compilación `trimesh==4.6.13`. Flask no necesita trimesh en producción.\n''',encoding='utf-8')
