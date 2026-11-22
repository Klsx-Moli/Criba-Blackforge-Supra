from copy import deepcopy
import pytest
from criba.invention_acceptance import (
    errores_entrada_interpretada, exigir_entrada_interpretada, propuestas_para_supra,
)

PROTOCOL = {k: 'source declaration' for k in ('metrica', 'baseline', 'umbral', 'condicion_fracaso',
 'alternativa_explicativa', 'resultado_favorable_mecanismo', 'resultado_favorable_alternativa')}
ENTRY = {'estado_interpretacion':'PROPUESTA', 'candidate_id':'c1', 'hipotesis':'h',
         'mecanismo':'m', 'prueba_concreta':'p', 'prueba':PROTOCOL,
         'interpretacion_error':'', 'critica':{'evaluation_status':'CRITIQUED'}}

def test_legitimate_minimal_archival_and_strict_supra():
    exigir_entrada_interpretada(ENTRY, para_supra=True)
    exigir_entrada_interpretada({k:v for k,v in ENTRY.items() if k != 'prueba'})

@pytest.mark.parametrize('field,value', [
 ('estado_interpretacion','PENDIENTE_INTERPRETACION'),('estado_interpretacion','UNKNOWN'),
 ('estado_interpretacion',None),('estado_interpretacion',True),
 ('hipotesis',''),('mecanismo',None),('mecanismo',0),
 ('interpretacion_error','timeout'),('interpretacion_error',None),
 ('interprete_result',{'estado':'PENDIENTE_INTERPRETACION', 'error':''}),
 ('interprete_result',{'estado':'PROPUESTA', 'error':'timeout'}),
 ('interprete_result','fake'),
])
def test_archival_conflict_fails(field,value):
    row = deepcopy(ENTRY)
    row[field] = value
    with pytest.raises(ValueError):
        exigir_entrada_interpretada(row)

@pytest.mark.parametrize('field,value', [('candidate_id',''),('candidate_id','  '),
 ('candidate_id',None),('candidate_id',' c1 '),('prueba_concreta',''),('prueba_concreta',True),
 ('prueba',None),('prueba',{}),('prueba',True),('critica',{'evaluation_status':'REJECTED'})])
def test_supra_needs_declared_fields(field,value):
    row = deepcopy(ENTRY)
    row[field] = value
    with pytest.raises(ValueError):
        exigir_entrada_interpretada(row,para_supra=True)

@pytest.mark.parametrize('field',list(PROTOCOL))
def test_supra_missing_each_protocol_obligation_fails(field):
    row = deepcopy(ENTRY)
    row["prueba"].pop(field)
    with pytest.raises(ValueError,match="prueba_sin:"+field):
        exigir_entrada_interpretada(row,para_supra=True)

@pytest.mark.parametrize('extra', [None,[],False,42,{},'PENDIENTE'])
def test_non_object_does_not_crash(extra):
    assert errores_entrada_interpretada(extra,para_supra=True)

@pytest.mark.parametrize('field',list(PROTOCOL))
def test_protocol_whitespace_and_type_fails(field):
    for value in ('', '  ', [], 0, None, False):
        row = deepcopy(ENTRY)
        row["prueba"][field] = value
        with pytest.raises(ValueError):
            exigir_entrada_interpretada(row, para_supra=True)

def test_archival_does_not_require_supra_specific_proof():
    row={'estado_interpretacion':'PROPUESTA','hipotesis':'h','mecanismo':'m'}
    assert errores_entrada_interpretada(row) == []
    assert errores_entrada_interpretada(row,para_supra=True)


def test_preflight_batch_rejects_bad_before_any_io():
    ready = deepcopy(ENTRY)
    wrong = deepcopy(ENTRY)
    wrong['prueba'].pop('metrica')
    with pytest.raises(ValueError,match='entrada 2'):
        propuestas_para_supra([ready,{'estado_interpretacion':'PENDIENTE_INTERPRETACION'},wrong])
    assert propuestas_para_supra([{'estado_interpretacion':'PENDIENTE_INTERPRETACION'},ready])==[ready]
    assert propuestas_para_supra([{'estado_interpretacion':'PENDIENTE_INTERPRETACION'}])==[]

@pytest.mark.parametrize('value',[None,{},False,0,'bad'])
def test_malformed_batch_fails(value):
    with pytest.raises(ValueError):
        propuestas_para_supra(value)

@pytest.mark.parametrize('entry',[None,False,0,[],'unexpected'])
def test_malformed_entry_fails(entry):
    with pytest.raises(ValueError):
        propuestas_para_supra([entry])

@pytest.mark.parametrize('state',['UNKNOWN',None,'ERROR','ABSTENER',True,0])
def test_bad_state_not_silently_skipped(state):
    with pytest.raises(ValueError):
        propuestas_para_supra([{'estado_interpretacion':state}])

def test_duplicate_candidate_id_blocks_second_send():
    a = deepcopy(ENTRY)
    b = deepcopy(ENTRY)
    b['mecanismo'] = 'different mechanism'
    with pytest.raises(ValueError,match='candidate_id repetido'):
        propuestas_para_supra([a,b])

def test_nested_result_missing_error_is_not_proof():
    a = deepcopy(ENTRY)
    a['interprete_result'] = {'estado':'PROPUESTA'}
    with pytest.raises(ValueError):
        exigir_entrada_interpretada(a)

@pytest.mark.parametrize('state', ['UNKNOWN', None, 'ERROR', 'ABSTENER'])
def test_fully_formed_wrong_state_never_reaches_supra(state):
    candidate = deepcopy(ENTRY)
    candidate['estado_interpretacion'] = state
    with pytest.raises(ValueError):
        propuestas_para_supra([candidate])
