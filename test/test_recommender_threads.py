from concurrent.futures import ThreadPoolExecutor
from logic.recommender import RecommenderEngine

def test_parallel_requests_initialize_logic_and_isolate_diets(caplog):
    engine=RecommenderEngine()
    def check(index):
        compatible,_=engine.evaluate({'id':1,'rating':4.8,'dietary_restrictions':['vegano'] if index%2 else []},{'id':1,'restrictions':['vegano']})
        return compatible
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(check,range(12)))
    assert results==[bool(i%2) for i in range(12)]
    assert not any('Error insertando' in record.message for record in caplog.records)
