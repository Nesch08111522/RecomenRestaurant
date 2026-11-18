from app import create_app


def test_discovery_responses_are_not_cached():
    app=create_app({'TESTING':True,'SECRET_KEY':'x'*32,'WTF_CSRF_ENABLED':False})
    client=app.test_client()
    response=client.get('/admin/api/discovery/candidates')
    assert response.status_code==401
    assert response.headers.get('Cache-Control')=='no-store'
    invalid=client.post('/api/discovery/invitations/preview',json={'token':''})
    assert invalid.status_code==400
    assert invalid.headers.get('Cache-Control')=='no-store'
    assert invalid.headers.get('Referrer-Policy')=='no-referrer'
