import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
from services.legal_engine.rules.reflexos_proibidos import ReflexosProibidosRule

def _ctx(nome, reflexos):
    return ContextoJuridico(numero_processo='0001234-56.2024.5.03.0001', data_admissao='01/03/2020',
        data_demissao='15/01/2025', verbas_deferidas=[VerbaContexto(nome=nome, reflexos=reflexos)])
def _erro(alertas, rid): return any(a.get('nivel')=='ERRO' and a.get('regra_id')==rid for a in alertas if isinstance(a,dict))
def _nerros(alertas, rid): return sum(1 for a in alertas if isinstance(a,dict) and a.get('nivel')=='ERRO' and a.get('regra_id')==rid)

class TestDSROJ394:
    def setup_method(self): self.r = ReflexosProibidosRule()
    def test_id(self): assert self.r.id == 'OJ_394_SDI1_TST_REFLEXOS_PROIBIDOS'
    def test_prioridade(self): assert self.r.prioridade == 30
    def test_dsr_ferias_erro(self): assert _erro(self.r.aplicar(_ctx('DSR',['Ferias'])).alertas, self.r.id)
    def test_dsr_13_erro(self): assert _erro(self.r.aplicar(_ctx('DSR',['13 Salario'])).alertas, self.r.id)
    def test_dsr_fgts_erro(self): assert _erro(self.r.aplicar(_ctx('DSR',['FGTS'])).alertas, self.r.id)
    def test_dsr_3_proibidos_3_erros(self): assert _nerros(self.r.aplicar(_ctx('DSR',['Ferias','13 Salario','FGTS'])).alertas, self.r.id)==3
    def test_dsr_sem_reflexos_ok(self): assert not _erro(self.r.aplicar(_ctx('DSR',[])).alertas, self.r.id)
    def test_mensagem_oj394(self): assert any('OJ 394' in a.get('mensagem','') for a in self.r.aplicar(_ctx('DSR',['Ferias'])).alertas)
    def test_registrada(self): assert self.r.id in self.r.aplicar(_ctx('DSR',['Ferias'])).regras_aplicadas

class TestMultas:
    def setup_method(self): self.r = ReflexosProibidosRule()
    def test_467_ferias(self): assert _erro(self.r.aplicar(_ctx('Multa art. 467',['Ferias'])).alertas, self.r.id)
    def test_477_dsr(self): assert _erro(self.r.aplicar(_ctx('Multa art. 477',['DSR'])).alertas, self.r.id)
    def test_dano_moral_fgts(self): assert _erro(self.r.aplicar(_ctx('Dano Moral',['FGTS'])).alertas, self.r.id)
    def test_dano_material_aviso(self): assert _erro(self.r.aplicar(_ctx('Dano Material',['Aviso Previo'])).alertas, self.r.id)
    def test_aviso_em_si_mesmo(self): assert _erro(self.r.aplicar(_ctx('Aviso Previo',['Aviso Previo'])).alertas, self.r.id)

class TestPermitidos:
    def setup_method(self): self.r = ReflexosProibidosRule()
    def test_he_dsr_ok(self): assert not _erro(self.r.aplicar(_ctx('Horas Extras',['DSR'])).alertas, self.r.id)
    def test_sem_verbas_ok(self):
        ctx = ContextoJuridico(numero_processo='x', data_admissao='01/03/2020')
        assert self.r.aplicar(ctx).alertas == []
    def test_sem_reflexos_ok(self): assert not _erro(self.r.aplicar(_ctx('DSR',[])).alertas, self.r.id)

class TestCanon:
    def setup_method(self): self.r = ReflexosProibidosRule()
    def test_dsr_minusculo(self): assert _erro(self.r.aplicar(_ctx('dsr',['Ferias'])).alertas, self.r.id)
    def test_descanso_semanal(self): assert _erro(self.r.aplicar(_ctx('Descanso Semanal Remunerado',['Ferias'])).alertas, self.r.id)
