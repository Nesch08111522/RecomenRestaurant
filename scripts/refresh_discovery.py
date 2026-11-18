"""Worker de aplicación. Ejecutar: python -m scripts.refresh_discovery.

Windows Task Scheduler/cron es dueño de la cadencia; no hay bucles persistentes
ni hilos dentro del servidor Flask. Respeta enabled y next_refresh_at por fuente.
"""
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1]/'.env',override=False)

from logic.business_radar import now
from models.discovery import SourceModel,run_source

logger=logging.getLogger('smartresto.discovery.worker')


def refresh_due():
    sources=[source for source in SourceModel.all()
             if source.get('enabled') and source.get('next_refresh_at','')<=now()]
    results=[]
    for source in sources[:20]:
        try:
            run=run_source(source['id'])
            results.append({'source_id':source['id'],'ok':True,'run_id':run['id']})
        except Exception as error:
            logger.warning('Fuente %s no actualizada: %s',source['id'],type(error).__name__)
            results.append({'source_id':source['id'],'ok':False,'error_type':type(error).__name__})
    return results


def main():
    logging.basicConfig(level=logging.INFO)
    results=refresh_due()
    print('Radar: %s fuentes vencidas; %s actualizadas; %s pendientes.' %
          (len(results),sum(row['ok'] for row in results),sum(not row['ok'] for row in results)))
    return 1 if any(not row['ok'] for row in results) else 0


if __name__=='__main__':
    raise SystemExit(main())
