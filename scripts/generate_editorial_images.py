"""Generate three reusable editorial images; never run during visitor requests."""
import base64, io, os, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from PIL import Image
from utils.llm_provider import settings
load_dotenv()
SCENES = {
 'home': 'Peruvian arroz con pato with rich green cilantro rice, tender duck, salsa criolla, handmade ivory ceramic plate, warm natural studio light, forest green background, appetizing premium food photography, no text, no logos, no people, entire plate visible, three quarter camera angle.',
 'offers': 'Peruvian anticuchos grilled skewers with golden potatoes, small bowl of creamy aji sauce, rustic ceramic serving platter, elegant deep burgundy background, commercial food photography with warm side light, no price tags, no text, no logos, entire platter visible.',
 'business': 'Fine dining Peruvian grilled trout with colorful Andean vegetables, refined matte black ceramic plate on deep forest background, elegant cinematic food photography, physically realistic materials, soft warm highlights, no text, no logos, full plate visible.'}
def generate(name):
    config=settings(); client=config.client()
    result=client.chat.completions.create(model=os.getenv('AI_IMAGE_MODEL','google/gemini-2.5-flash-image'),messages=[{'role':'user','content':SCENES[name]}],extra_body={'modalities':['image','text']},timeout=150)
    data=result.choices[0].message.model_dump()
    images=data.get('images') or []
    if not images: raise RuntimeError('Provider returned no image')
    url=images[0].get('image_url',{}).get('url','')
    if not url.startswith('data:image/') or ';base64,' not in url: raise RuntimeError('Expected inline image')
    raw=base64.b64decode(url.split(';base64,',1)[1],validate=True)
    if len(raw)>20_000_000: raise RuntimeError('Image too large')
    with Image.open(io.BytesIO(raw)) as im:
        im.thumbnail((1200,1200)); im.convert('RGB').save(Path('static/images/editorial')/(name+'.webp'),'WEBP',quality=86)
    print(name+': image saved',flush=True)
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={name:pool.submit(generate,name) for name in SCENES}
        for name, future in futures.items():
            try: future.result()
            except Exception as exc: print(name+': generation failed '+type(exc).__name__,flush=True)
