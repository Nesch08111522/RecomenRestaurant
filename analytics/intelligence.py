"""Evidence-based commercial metrics and a bounded seasonal baseline, in PEN cents."""
from collections import Counter,defaultdict
from datetime import date,datetime,timedelta
from statistics import mean,pstdev
from zoneinfo import ZoneInfo
LIMA=ZoneInfo('America/Lima')

def paid(o):return o.get('state')=='Entregado' and o.get('paid') is True and not o.get('refunded')
def day(o):return str(o.get('created') or o.get('day') or '')[:10]
def report(orders,products,start,end):
    eligible=[o for o in orders if paid(o)]
    selected=[o for o in eligible if start.isoformat()<=day(o)<=end.isoformat()]
    income=sum(int(o.get('total',0)) for o in selected)
    lines=[line for o in selected for line in o.get('lines',[])]
    known=[l for l in lines if l.get('cost') is not None]
    costs=sum(int(l['cost'])*int(l.get('qty',0)) for l in known)
    quantities=Counter();daily=Counter();hours=Counter();customers=Counter();first={}
    for o in eligible:
        uid=str(o.get('uid'));first[uid]=min(first.get(uid,day(o)),day(o))
    for o in selected:
        daily[day(o)]+=int(o.get('total',0));customers[str(o.get('uid'))]+=1
        try:
            stamp=datetime.fromisoformat(o.get('created',''))
            hours[str((stamp.replace(tzinfo=LIMA) if stamp.tzinfo is None else stamp.astimezone(LIMA)).hour).zfill(2)+':00']+=1
        except ValueError:pass
        for l in o.get('lines',[]):quantities[str(l.get('name','Sin nombre'))]+=int(l.get('qty',0))
    duration=(end-start).days+1;previous_end=start-timedelta(days=1);previous_start=start-timedelta(days=duration)
    previous=sum(int(o.get('total',0)) for o in eligible if previous_start.isoformat()<=day(o)<=previous_end.isoformat())
    all_ids={str(o.get('uid')) for o in eligible if day(o)<=end.isoformat()}
    names={p.get('name') for p in products if p.get('name')}
    total_units=sum(int(l.get('qty',0)) for l in lines);costed=sum(int(l.get('qty',0)) for l in known)
    history=[date.fromisoformat(day(o)) for o in eligible if len(day(o))==10]
    forecast=[]
    if len(eligible)>=10 and history and (end-min(history)).days>=28:
        for i in range(1,8):
            target=end+timedelta(days=i);samples=[]
            for week in range(1,9):
                comparable=target-timedelta(days=7*week)
                if min(history)<=comparable<=end:samples.append(sum(1 for o in eligible if day(o)==comparable.isoformat()))
            if len(samples)>=4:
                forecast.append({'day':target.isoformat(),'orders':round(mean(samples),1),'low':max(0,round(mean(samples)-pstdev(samples),1)),'high':round(mean(samples)+pstdev(samples),1),'sample_days':len(samples)})
    return {'income':income,'orders':len(selected),'average_ticket':round(income/len(selected)) if selected else None,'known_costs':costs,'cost_coverage':round(costed/total_units*100,1) if total_units else None,'margin':income-costs if total_units and costed==total_units else None,'previous_income':previous,'income_change':round((income-previous)/previous*100,1) if previous else None,'customers':len(customers),'new_customers':sum(first[uid]>=start.isoformat() for uid in customers),'frequent_customers':sum(n>1 for n in customers.values()),'inactive_customers':len(all_ids-set(customers)),'top_products':quantities.most_common(8),'least_products':sorted(((name,quantities[name]) for name in names),key=lambda x:(x[1],x[0]))[:8],'daily':[( (start+timedelta(days=i)).isoformat(),daily[(start+timedelta(days=i)).isoformat()]) for i in range(duration)],'hours':sorted(hours.items()),'forecast':forecast,'forecast_method':'Media histórica del mismo día de semana, hasta ocho semanas; intervalo descriptivo, no garantía.' if forecast else 'Datos insuficientes: se requieren diez compras completadas y al menos cuatro semanas comparables.','missing_metrics':['Ocupación, rotación y espera: requieren sesiones de mesa y cola instrumentadas.','Merma: requiere un registro de movimientos de desperdicio.']}
