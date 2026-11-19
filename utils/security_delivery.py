"""Transactional security-code delivery. Never exposes codes or credentials to HTTP callers."""
import os, re, ssl, smtplib
from email.message import EmailMessage
import requests

class DeliveryUnavailable(RuntimeError): pass

def configured(channel):
    if channel not in ('email', 'sms'):
        return False
    if channel=='sms':
        return all(os.getenv(k,'').strip() for k in ('TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_FROM_NUMBER'))
    provider=os.getenv('SECURITY_EMAIL_PROVIDER','resend').strip()
    return bool(os.getenv('SECURITY_FROM_EMAIL','').strip()) and (bool(os.getenv('RESEND_API_KEY','').strip()) if provider=='resend' else provider=='smtp' and all(os.getenv(k,'').strip() for k in ('SMTP_HOST','SMTP_USERNAME','SMTP_PASSWORD')))

def send_code(channel, destination, code, delivery_id):
    if not configured(channel):raise DeliveryUnavailable('delivery_not_configured')
    body=f'Tu código de seguridad SmartResto es {code}. Vence en 10 minutos. No lo compartas. Si no solicitaste el cambio, ignora este mensaje.'
    try:
        if channel=='sms':
            sid=os.getenv('TWILIO_ACCOUNT_SID','').strip()
            if not re.fullmatch(r'AC[0-9a-fA-F]{32}',sid) or not re.fullmatch(r'\+[1-9]\d{7,14}',destination):raise DeliveryUnavailable('invalid_sms_configuration')
            response=requests.post(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json',auth=(sid,os.getenv('TWILIO_AUTH_TOKEN')),data={'To':destination,'From':os.getenv('TWILIO_FROM_NUMBER'),'Body':body},timeout=15,allow_redirects=False)
            if response.status_code!=201:raise DeliveryUnavailable('sms_rejected')
        elif os.getenv('SECURITY_EMAIL_PROVIDER','resend')=='smtp':
            message=EmailMessage();message['From']=os.getenv('SECURITY_FROM_EMAIL');message['To']=destination;message['Subject']='Código de seguridad SmartResto';message.set_content(body)
            port=int(os.getenv('SMTP_PORT','587'))
            if port==465:
                server=smtplib.SMTP_SSL(os.getenv('SMTP_HOST'),port,timeout=15,context=ssl.create_default_context())
            else:
                server=smtplib.SMTP(os.getenv('SMTP_HOST'),port,timeout=15);server.starttls(context=ssl.create_default_context())
            with server:
                server.login(os.getenv('SMTP_USERNAME'),os.getenv('SMTP_PASSWORD'));server.send_message(message)
        else:
            response=requests.post('https://api.resend.com/emails',headers={'Authorization':'Bearer '+os.getenv('RESEND_API_KEY','').strip(),'Idempotency-Key':delivery_id,'User-Agent':'SmartResto-Backend/1.0'},json={'from':os.getenv('SECURITY_FROM_EMAIL'),'to':[destination],'subject':'Código de seguridad SmartResto','text':body},timeout=15,allow_redirects=False)
            if response.status_code not in (200,201,202):raise DeliveryUnavailable('email_rejected')
    except DeliveryUnavailable:raise
    except Exception:raise DeliveryUnavailable('delivery_failed') from None
