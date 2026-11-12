from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest
from agente_triagem import ResultadoTriagem


class TesteInterfacePainel(unittest.TestCase):
    def setUp(self):
        self.agente = self.enterContext(patch("agente_triagem.executar_triagem"))
        self.envio = self.enterContext(patch("integracao_n8n.enviar_oferta"))
        self.app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=10).run()
        self.app.radio(key="pagina").set_value("Painel de indicadores").run()

    def test_sem_arquivo_nao_mostra_numeros_inventados(self):
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.metric), 0)
        self.agente.assert_not_called()
        self.envio.assert_not_called()

    def test_csv_importado_alimenta_indicadores_sem_chamadas_externas(self):
        dados = (Path(__file__).parent / "data" / "ofertas_exemplo.csv").read_bytes()
        arquivo = SimpleNamespace(name="ofertas.csv", getvalue=lambda: dados)
        with patch("streamlit.file_uploader", return_value=arquivo):
            self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual([m.value for m in self.app.metric], ["5", "2", "1", "66,7%"])
        self.agente.assert_not_called()
        self.envio.assert_not_called()

    def test_exemplo_esta_identificado_e_filtros_atualizam_indicadores(self):
        self.app.radio(key="painel_fonte").set_value("Exemplo fictício").run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual([m.value for m in self.app.metric], ["5", "2", "1", "66,7%"])
        self.assertTrue(any("independente da sua planilha" in w.value for w in self.app.warning))
        self.app.selectbox[0].set_value("Todas").run()
        self.assertEqual([m.value for m in self.app.metric], ["6", "3", "1", "75,0%"])
        self.app.multiselect[0].set_value(["Moema"]).run()
        self.assertEqual([m.value for m in self.app.metric], ["2", "0", "0", "—"])
        self.agente.assert_not_called()
        self.envio.assert_not_called()

    def test_recorte_vazio_e_retorno_para_triagem(self):
        self.app.radio(key="painel_fonte").set_value("Exemplo fictício").run()
        self.app.multiselect[0].set_value([]).run()
        self.assertEqual(self.app.metric[0].value, "0")
        self.assertTrue(any("Nenhuma oferta" in w.value for w in self.app.warning))
        self.app.radio(key="pagina").set_value("Triagem da oferta").run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.text_area), 1)
        self.agente.assert_not_called()
        self.envio.assert_not_called()

    def test_navegacao_preserva_mensagem_e_correcao_em_andamento(self):
        self.agente.return_value = ResultadoTriagem(
            status="pronta_para_revisao",
            oferta={"item": "pão", "quantidade": 25, "bairro": "Vila Mariana",
                    "data_retirada": "2026-11-12", "horario_retirada": "09:00-10:00"},
            pendencias=[], perguntas=[], consulta=[], ferramentas=["extrair_oferta", "consultar_organizacoes"],
        )
        self.app.radio(key="pagina").set_value("Triagem da oferta").run()
        self.app.text_area(key="mensagem").set_value("mensagem fictícia")
        next(b for b in self.app.button if b.label == "Analisar mensagem").click().run()
        self.app.text_input(key="rev_quantidade").set_value("60").run()
        ident = self.app.session_state["registro_id"]
        self.app.radio(key="pagina").set_value("Painel de indicadores").run()
        self.app.radio(key="painel_fonte").set_value("Exemplo fictício").run()
        self.app.radio(key="pagina").set_value("Triagem da oferta").run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.text_area(key="mensagem").value, "mensagem fictícia")
        self.assertEqual(self.app.text_input(key="rev_quantidade").value, "60")
        self.assertEqual(self.app.session_state["registro_id"], ident)
        self.assertIsNone(self.app.session_state["resumo"])
        self.agente.assert_called_once()
        self.envio.assert_not_called()


if __name__ == "__main__":
    unittest.main()
