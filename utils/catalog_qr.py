from io import BytesIO
import os,re
from urllib.parse import urlsplit
import qrcode
from qrcode.image.svg import SvgPathImage


def build_table_qr(token):
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{32}',token):raise ValueError('Token de mesa inválido')
    origin=os.getenv('SMARTRESTO_PUBLIC_ORIGIN','').rstrip('/')
    if origin:
        parts=urlsplit(origin)
        if parts.scheme!='https' or not parts.hostname or parts.username or parts.path or parts.query or parts.fragment:
            raise ValueError('Configura un origen público HTTPS válido para imprimir QR de producción')
    else:origin='http://127.0.0.1:5000'
    url=origin+'/catalog/qr/'+token
    image=qrcode.make(url,image_factory=SvgPathImage,box_size=10,border=4)
    stream=BytesIO();image.save(stream)
    return stream.getvalue(),url
