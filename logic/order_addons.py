"""Resolve selected complements from server-owned catalog data only."""
from logic.market import MarketError


def resolve(dish, names, qty, restricted=False):
    if not isinstance(names, list) or len(names) > 20 or any(not isinstance(n, str) for n in names) or len(set(names)) != len(names):
        raise MarketError('Seleccion de adicionales invalida.')
    options = dish.get('addons') or []
    by_name = {a['name']: a for a in options}
    selected = []
    for name in names:
        option = by_name.get(name)
        if not option or option.get('is_available') is False:
            raise MarketError('El adicional ya no esta disponible.')
        price = option.get('price_cents')
        stock = option.get('stock')
        if type(price) is not int or price < 0 or type(stock) is not int or stock < qty:
            raise MarketError('El adicional no tiene precio o stock confirmado suficiente.')
        if restricted:
            raise MarketError('No hay declaraciones alimentarias verificadas para estos adicionales.')
        selected.append(dict(name=name, price_cents=price, quantity=qty))
    return selected
