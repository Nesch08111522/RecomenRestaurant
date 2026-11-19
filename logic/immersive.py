"""Validated measurements for a reviewed, rights-cleared dish representation."""
from decimal import Decimal,InvalidOperation
from logic.market import MarketError

def model_metadata(source):
    result={}
    for field,maximum in [('width_cm',150),('height_cm',150),('depth_cm',150),('portion_g',20000)]:
        raw=source.get(field)
        if raw not in (None,''):
            try:value=Decimal(str(raw))
            except InvalidOperation:raise MarketError('Indica medidas y porciones numéricas.') from None
            if not value.is_finite() or not 0<value<=maximum:raise MarketError('Las medidas o porciones están fuera del rango permitido.')
            result[field]=float(value)
    if any(k in result for k in ('width_cm','height_cm','depth_cm')) and not all(k in result for k in ('width_cm','height_cm','depth_cm')):
        raise MarketError('Completa ancho, alto y profundidad juntos, o deja las tres medidas vacías.')
    result['scale_verified']=False
    return result
