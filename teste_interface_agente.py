"""Fluxos Streamlit com Gemini/n8n simulados; nenhum envio externo."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from agente_triagem import ErroTriagem, ResultadoTriagem
from integracao_n8n import ConfiguracaoN8N
from organizacoes import consultar_organizacoes

OFERTA = {"item": "pão", "quantidade": 25, "bairro": "Vila Mariana",
          "data_retirada": "2026-11-12", "horario_retirada": "09:00-10:00"}
MENSAGEM = "25 unidades de pão, Vila Mariana, retirada em 12/11/2026, das 9h às 10h."


def triagem(pendente=False):
    oferta = {**OFERTA, "quantidade": None} if pendente else deepcopy(OFERTA)
    return ResultadoTriagem(
        status="aguardando_dados" if pendente else "pronta_para_revisao",
        oferta=oferta, pendencias=["quantidade"] if pendente else [],
        perguntas=["Qual é a quantidade exata em unidades inteiras positivas?"] if pendente else [],
        consulta=None if pendente else consultar_organizacoes(oferta),
        ferramentas=["extrair_oferta"] if pendente else ["extrair_oferta", "consultar_organizacoes"],
    )


class TesteInterfaceAgente(unittest.TestCase):
    def setUp(self):
        self.agente = self.enterContext(patch("agente_triagem.executar_triagem", return_value=triagem()))
        self.envio = self.enterContext(patch("integracao_n8n.enviar_oferta"))
        self.enterContext(patch("integracao_n8n.ler_configuracao", return_value=ConfiguracaoN8N(
            "https://exemplo.invalid/webhook/ofertas", "token-ficticio")))
        self.consulta = self.enterContext(patch("organizacoes.consultar_organizacoes", wraps=consultar_organizacoes))
        self.app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=10).run()
        self.assertEqual(len(self.app.exception), 0)

    def clicar(self, rotulo):
        next(b for b in self.app.button if b.label == rotulo).click().run()
        self.assertEqual(len(self.app.exception), 0)

    def analisar(self):
        self.app.text_area(key="mensagem").set_value(MENSAGEM)
        self.clicar("Analisar mensagem")

    def tem_botao(self, chave):
        return any(b.key == chave for b in self.app.button)

    def test_analise_nao_confirma_nem_registra_e_previa_aguarda_revisao(self):
        self.analisar()
        self.agente.assert_called_once_with(MENSAGEM)
        self.assertIsNone(self.app.session_state["resumo"])
        self.assertIsNone(self.app.session_state["consulta"])
        self.assertFalse(self.tem_botao("registrar_oferta"))
        self.clicar("Confirmar revisão")
        self.assertEqual(self.app.session_state["consulta"]["oferta"], OFERTA)
        self.assertTrue(self.tem_botao("registrar_oferta"))
        self.envio.assert_not_called()
        self.consulta.assert_not_called()  # Reaproveita a prévia da mesma oferta.

    def test_pendencia_e_complemento_manual_exigem_consulta_da_versao_corrigida(self):
        self.agente.return_value = triagem(pendente=True)
        self.analisar()
        self.assertTrue(any("quantidade exata" in m.value for m in self.app.markdown))
        self.clicar("Confirmar revisão")
        self.assertFalse(self.tem_botao("registrar_oferta"))
        self.app.text_input(key="rev_quantidade").set_value("25")
        self.clicar("Confirmar revisão")
        self.assertIsNone(self.app.session_state["consulta"])
        self.clicar("Consultar organizações")
        self.consulta.assert_called_once_with(OFERTA)
        self.envio.assert_not_called()

    def test_correcao_descarta_previa_e_payload_usa_novo_resultado(self):
        self.analisar()
        self.app.text_input(key="rev_quantidade").set_value("60")
        self.clicar("Confirmar revisão")
        self.assertIsNone(self.app.session_state["consulta"])
        self.clicar("Consultar organizações")
        self.assertFalse(any(r["compativel"] for r in self.app.session_state["consulta"]["resultados"]))
        self.clicar("Registrar oferta")
        payload = self.envio.call_args.args[0]
        self.assertEqual(payload["quantidade"], 60)
        self.assertEqual(payload["consulta"]["status"], "sem_compativeis")

    def test_edicao_apos_confirmacao_bloqueia_registro_ate_nova_confirmacao(self):
        self.analisar()
        self.clicar("Confirmar revisão")
        self.app.text_input(key="rev_bairro").set_value("Moema").run()
        self.assertIsNone(self.app.session_state["consulta"])
        self.assertFalse(self.tem_botao("registrar_oferta"))
        self.envio.assert_not_called()

    def test_mudanca_de_mensagem_e_falha_limpam_resultados_anteriores(self):
        self.analisar()
        self.clicar("Confirmar revisão")
        self.app.text_area(key="mensagem").set_value("outra oferta").run()
        self.assertFalse(self.tem_botao("registrar_oferta"))
        self.agente.side_effect = ErroTriagem("Gemini — HTTP 503. Indisponível.")
        self.clicar("Analisar mensagem")
        self.assertIsNone(self.app.session_state["oferta"])
        self.assertIsNone(self.app.session_state["triagem"])
        self.assertIsNone(self.app.session_state["previa_consulta"])
        self.assertIsNone(self.app.session_state["consulta"])
        self.assertEqual(self.app.text_area(key="mensagem").value, "outra oferta")
        self.envio.assert_not_called()

    def test_registro_so_apos_clique_e_repeticao_fica_desabilitada(self):
        self.analisar()
        self.clicar("Confirmar revisão")
        ident = self.app.session_state["registro_id"]
        self.envio.assert_not_called()
        self.clicar("Registrar oferta")
        self.envio.assert_called_once()
        self.assertEqual(self.envio.call_args.args[0]["oferta_id"], ident)
        self.assertTrue(self.app.button(key="registrar_oferta").disabled)
        self.app.run()
        self.envio.assert_called_once()


if __name__ == "__main__":
    unittest.main()
