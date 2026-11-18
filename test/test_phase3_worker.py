from scripts import refresh_discovery as worker


def test_worker_refreshes_only_due_enabled_sources(monkeypatch):
    monkeypatch.setattr(worker.SourceModel,'all',lambda:[
        {'id':1,'enabled':True,'next_refresh_at':'2000-01-01T00:00:00+00:00'},
        {'id':2,'enabled':False,'next_refresh_at':'2000-01-01T00:00:00+00:00'},
        {'id':3,'enabled':True,'next_refresh_at':'2099-01-01T00:00:00+00:00'}])
    def run(source_id):
        assert source_id==1
        return {'id':7}
    monkeypatch.setattr(worker,'run_source',run)
    assert worker.refresh_due()==[{'source_id':1,'ok':True,'run_id':7}]


def test_worker_isolates_source_failure(monkeypatch):
    monkeypatch.setattr(worker.SourceModel,'all',lambda:[{'id':1,'enabled':True}, {'id':2,'enabled':True}])
    def run(source_id):
        if source_id==1:
            raise RuntimeError('Provider not available')
        return {'id':8}
    monkeypatch.setattr(worker,'run_source',run)
    result=worker.refresh_due()
    assert result[0]['ok'] is False
    assert result[1]=={'source_id':2,'ok':True,'run_id':8}
