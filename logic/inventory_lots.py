"""Inventory batches, including persisted single-batch records."""
from decimal import Decimal, ROUND_HALF_UP
from logic.market import MarketError


def batches(ingredient):
    return ingredient.get('lots', [ingredient])


def ordered(ingredient, day):
    return sorted((lot for lot in batches(ingredient) if lot['expires'] >= day and lot['quantity'] > 0),
                  key=lambda lot: (lot['expires'], lot.get('received_at', ''), lot['lot'])
                  if ingredient.get('rotation', 'FEFO') == 'FEFO' else (lot.get('received_at', ''), lot['lot']))


def quantity(ingredient, day):
    return sum(lot['quantity'] for lot in ordered(ingredient, day)) if ingredient else 0


def consume(ingredient, amount, day):
    if amount > quantity(ingredient, day):
        raise MarketError('Stock vigente insuficiente.')
    usage, cost = [], Decimal(0)
    for lot in ordered(ingredient, day):
        used = min(amount, lot['quantity'])
        if used:
            lot['quantity'] -= used
            amount -= used
            usage.append({'lot': lot['lot'], 'amount': used})
            cost += Decimal(used * lot['cost']) / lot['basis']
    sync(ingredient)
    return usage, cost


def sync(ingredient):
    if 'lots' in ingredient:
        ingredient['quantity'] = sum(lot['quantity'] for lot in ingredient['lots'])
        if ingredient['lots']:
            first = min(ingredient['lots'], key=lambda lot: (lot['expires'], lot.get('received_at', ''), lot['lot']))
            for field in ('expires', 'cost', 'basis', 'lot'):
                ingredient[field] = first[field]


def restore(ingredient, allocations):
    by_id = {lot['lot']: lot for lot in batches(ingredient)}
    for allocation in allocations:
        if allocation['lot'] not in by_id:
            raise MarketError('Falta el lote original: no se puede restaurar el inventario.')
        by_id[allocation['lot']]['quantity'] += allocation['amount']
    sync(ingredient)


def cost(recipe, pantry):
    total = Decimal(0)
    for name, amount in recipe.items():
        ingredient = pantry.get(name)
        if not ingredient:
            return None
        # Quote the actual FEFO/FIFO mix without modifying live inventory.
        remaining = amount
        for lot in sorted(batches(ingredient), key=lambda lot: (lot['expires'], lot.get('received_at', ''), lot['lot'])
                          if ingredient.get('rotation', 'FEFO') == 'FEFO' else (lot.get('received_at', ''), lot['lot'])):
            used = min(remaining, lot['quantity'])
            total += Decimal(used * lot['cost']) / lot['basis']
            remaining -= used
        if remaining:
            return None
    return int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))
