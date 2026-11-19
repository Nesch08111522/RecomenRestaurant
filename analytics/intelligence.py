"""Evidence-based commercial metrics and a bounded seasonal baseline, in PEN cents."""
from collections import Counter,defaultdict
from datetime import date,datetime,timedelta
from statistics import mean,pstdev
from zoneinfo import ZoneInfo
LIMA=ZoneInfo('America/Lima')

def paid(o):return o.get('state')=='Entregado' and o.get('paid') is True and not o.get('refunded')
def day(o):return str(o.get('created') or o.get('day') or '')[:10]


def service_metrics(sessions,queue_rows,tables_count,start,end):
    """Rotación y espera con sesiones y turnos registrados; sin inventar ocupación."""
    first,last=start.isoformat(),end.isoformat();days=(end-start).days+1
    closed=[];durations=[]
    for session in sessions:
        closed_at=str(session.get('closed_at') or '')[:10]
        if session.get('status')!='Finalizada' or not first<=closed_at<=last:continue
        try:
            opened=datetime.fromisoformat(session['opened_at']);ended=datetime.fromisoformat(session['closed_at'])
        except (KeyError,ValueError):continue
        minutes=(ended-opened).total_seconds()/60
        if 1<=minutes<=600:
            closed.append(session);durations.append(minutes)
    waits=[];no_shows=0
    for row in queue_rows:
        created=str(row.get('created_at') or '')[:10]
        if not first<=created<=last:continue
        if row.get('status')=='No se presentó':no_shows+=1
        stamp=row.get('seated_at') or row.get('called_at')
        if not stamp:continue
        try:waits.append(max(0,(datetime.fromisoformat(stamp)-datetime.fromisoformat(row['created_at'])).total_seconds()/60))
        except (KeyError,ValueError):pass
    return {'sessions':len(closed),'average_minutes':round(mean(durations),1) if durations else None,
            'median_minutes':round(sorted(durations)[len(durations)//2],1) if durations else None,
            'rotation_per_table_day':round(len(closed)/max(1,tables_count)/days,2) if tables_count else None,
            'wait_samples':len(waits),'median_wait_minutes':round(sorted(waits)[len(waits)//2],1) if waits else None,
            'no_shows':no_shows,'tables':tables_count,
            'method':'Sesiones de mesa cerradas y turnos registrados en el período. La ocupación en vivo se consulta en Flow.'}


def report(orders,products,start,end):
    first_day,last_day=start.isoformat(),end.isoformat()
    eligible=[o for o in orders if paid(o) and day(o)<=last_day]
    selected=[o for o in eligible if first_day<=day(o)<=last_day]
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
    order_days=Counter()
    history=[]
    for o in eligible:
        try: stamp=date.fromisoformat(day(o))
        except ValueError: continue
        history.append(stamp);order_days[stamp]+=1
    earliest=min(history) if history else end
    forecast=[]
    if len(eligible)>=10 and history and (end-min(history)).days>=28:
        for i in range(1,8):
            target=end+timedelta(days=i);samples=[]
            for week in range(1,9):
                comparable=target-timedelta(days=7*week)
                if earliest<=comparable<=end:samples.append(order_days[comparable])
            if len(samples)>=4:
                forecast.append({'day':target.isoformat(),'orders':round(mean(samples),1),'low':max(0,round(mean(samples)-pstdev(samples),1)),'high':round(mean(samples)+pstdev(samples),1),'sample_days':len(samples)})
    return {'income':income,'orders':len(selected),'average_ticket':round(income/len(selected)) if selected else None,'known_costs':costs,'cost_coverage':round(costed/total_units*100,1) if total_units else None,'margin':income-costs if total_units and costed==total_units else None,'previous_income':previous,'income_change':round((income-previous)/previous*100,1) if previous else None,'customers':len(customers),'new_customers':sum(first[uid]>=start.isoformat() for uid in customers),'frequent_customers':sum(n>1 for n in customers.values()),'inactive_customers':len(all_ids-set(customers)),'top_products':quantities.most_common(8),'least_products':sorted(((name,quantities[name]) for name in names),key=lambda x:(x[1],x[0]))[:8],'daily':[( (start+timedelta(days=i)).isoformat(),daily[(start+timedelta(days=i)).isoformat()]) for i in range(duration)],'hours':sorted(hours.items()),'forecast':forecast,'forecast_method':'Media histórica del mismo día de semana, hasta ocho semanas; intervalo descriptivo, no garantía.' if forecast else 'Datos insuficientes: se requieren diez compras completadas y al menos cuatro semanas comparables.','missing_metrics':['Ocupación, rotación y espera: requieren sesiones de mesa y cola instrumentadas.','Merma: requiere un registro de movimientos de desperdicio.']}
