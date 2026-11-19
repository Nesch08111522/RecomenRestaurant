"""Validate compact self-contained binary glTF files before exposing a dish preview."""
import json
import struct
from io import BytesIO
from PIL import Image
from logic.market import MarketError


def validate_glb(raw):
    if not 20 <= len(raw) <= 1500000:
        raise MarketError("El modelo GLB debe pesar hasta 1,5 MB.")
    magic, version, size = struct.unpack_from("<4sII",raw)
    if magic != b"glTF" or version != 2 or size != len(raw):
        raise MarketError("Selecciona un archivo GLB versión 2 válido.")
    offset, chunks = 12, []
    while offset < size:
        if offset+8 > size:
            raise MarketError("El archivo GLB está incompleto.")
        length, kind = struct.unpack_from("<I4s",raw,offset)
        offset += 8
        if length % 4 or offset+length > size:
            raise MarketError("El archivo GLB está incompleto.")
        chunks.append((kind,raw[offset:offset+length]))
        offset += length
    if not chunks or chunks[0][0] != b"JSON" or len(chunks)>2 or len(chunks)==2 and chunks[1][0]!=b"BIN\0":
        raise MarketError("Usa un GLB autocontenido.")
    try:
        data = json.loads(chunks[0][1])
        if data["asset"]["version"] != "2.0":
            raise ValueError
        if len(data.get("nodes",[]))>500 or len(data.get("meshes",[]))>200:
            raise ValueError
        def check(value):
            if isinstance(value,dict):
                if "uri" in value or "extensionsRequired" in value or "extensions" in value:
                    raise ValueError
                for item in value.values():
                    check(item)
            elif isinstance(value,list):
                for item in value:
                    check(item)
        check(data)
        buffers = data.get("buffers",[])
        if len(buffers)>1 or buffers and (len(chunks)!=2 or buffers[0]["byteLength"]>len(chunks[1][1])):
            raise ValueError
        for image in data.get('images',[]):
            if len(chunks)!=2 or image.get('mimeType') not in ('image/png','image/jpeg'):
                raise ValueError
            view=data['bufferViews'][image['bufferView']]
            start=view.get('byteOffset',0);length=view['byteLength']
            if view.get('buffer',0)!=0 or type(start)!=int or type(length)!=int or start<0 or length<=0 or start+length>len(chunks[1][1]):raise ValueError
            with Image.open(BytesIO(chunks[1][1][start:start+length])) as texture:
                if texture.width>4096 or texture.height>4096 or texture.width*texture.height>16000000:raise ValueError
                texture.verify()
    except (ValueError,KeyError,TypeError,RecursionError,IndexError,OSError,Image.DecompressionBombError):
        raise MarketError("Exporta un modelo optimizado con texturas incluidas y sin extensiones.") from None
    return raw
