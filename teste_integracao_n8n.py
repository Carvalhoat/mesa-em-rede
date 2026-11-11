"""Testes sem rede, sem token real e sem chamadas ao Gemini ou ao n8n."""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from integracao_n8n import (
    ConfiguracaoN8N, ErroRegistro, _SemRedirecionamento,
    enviar_oferta, ler_configuracao, montar_payload, validar_configuracao,
)


class IntegracaoN8NTests(unittest.TestCase):
    def setUp(self):
        self.oferta = dict(item="pão", quantidade=25, bairro="Vila Mariana",
                           data_retirada="2026-11-12", horario_retirada="09:00-10:00")
        self.config = ConfiguracaoN8N("https://exemplo.app.n8n.cloud/webhook/mesa-em-rede/ofertas", "token_ficticio")

    def payload(self, consulta=None):
        return montar_payload("oferta_teste", self.oferta, consulta)

    def consulta(self, resultados):
        return dict(oferta=self.oferta.copy(), resultados=resultados,
                    realizada_em="2026-11-11T12:00:00+00:00")

    def executar_resposta(self, corpo, codigo=200):
        resposta = Mock()
        resposta.status = codigo
        resposta.read.return_value = corpo
        resposta.__enter__ = Mock(return_value=resposta)
        resposta.__exit__ = Mock(return_value=False)
        cliente = Mock()
        cliente.open.return_value = resposta
        with patch("integracao_n8n.urllib.request.build_opener", return_value=cliente):
            enviar_oferta(self.payload(), self.config)
        return cliente

    def test_payload_sem_consulta_nao_inclui_mensagem_ou_token(self):
        self.oferta["mensagem"] = "Não enviar"
        p = self.payload()
        self.assertEqual(p["consulta"], {"status": "nao_consultada"})
        self.assertNotIn("mensagem", p)
        self.assertNotIn("token", p)
        self.assertIs(p["revisao_confirmada"], True)
        self.assertIs(p["dados_ficticios"], True)

    def test_consulta_positiva_preserva_instante_original(self):
        c = self.consulta([dict(id="org_demo_001", compativel=True)])
        p = self.payload(c)
        self.assertEqual(p["consulta"]["status"], "com_compativeis")
        self.assertEqual(p["consulta"]["realizada_em"], c["realizada_em"])

    def test_consulta_sem_compativeis(self):
        c = self.consulta([dict(id="org_demo_001", compativel=False)])
        self.assertEqual(self.payload(c)["consulta"]["status"], "sem_compativeis")
        self.assertEqual(self.payload(c)["consulta"]["organizacoes_compativeis_ids"], [])

    def test_consulta_desatualizada_bloqueada(self):
        c = self.consulta([])
        c["oferta"]["quantidade"] = 60
        with self.assertRaises(ErroRegistro): self.payload(c)

    def test_quantidades_invalidas_bloqueadas(self):
        for valor in (0, -1, 2.5, True, "25", 9007199254740992):
            with self.subTest(valor=valor):
                self.oferta["quantidade"] = valor
                with self.assertRaises(ErroRegistro): self.payload()

    def test_data_e_horario_invalidos(self):
        for campo, valor in (("data_retirada", "2026-02-30"), ("horario_retirada", "10:00-09:00")):
            with self.subTest(campo=campo):
                dados = {**self.oferta, campo: valor}
                with self.assertRaises(ErroRegistro): montar_payload("teste", dados, None)

    def test_ids_desconhecidos_e_duplicados_bloqueados(self):
        for resultados in ([dict(id="desconhecido", compativel=True)], [dict(id="org_demo_001", compativel=True)] * 2):
            with self.assertRaises(ErroRegistro): self.payload(self.consulta(resultados))

    def test_url_e_token_invalidos(self):
        for url, token in (("http://exemplo.org/webhook", "x"), ("https://usuario:senha@exemplo.org/webhook", "x"), ("https://exemplo.org/webhook?token=x", "x"), (self.config.url, "x\ny"), ("", "")):
            with self.subTest(url=url):
                with self.assertRaises(ErroRegistro): validar_configuracao(ConfiguracaoN8N(url, token))

    def test_env_lido_sem_expor_ou_interpolar_token(self):
        with tempfile.TemporaryDirectory() as pasta:
            Path(pasta, ".env").write_text("N8N_WEBHOOK_URL=" + self.config.url + "\nN8N_WEBHOOK_TOKEN=abc${NAO_INTERPOLAR}\n")
            self.assertEqual(ler_configuracao(Path(pasta)).token, "abc${NAO_INTERPOLAR}")

    def test_sucesso_exige_confirmacao_e_envia_header(self):
        cliente = self.executar_resposta(b'{"status":"registro_ok","registrado":true}')
        req = cliente.open.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("X-mesa-token"), "token_ficticio")
        self.assertEqual(json.loads(req.data)["oferta_id"], "oferta_teste")

    def test_resposta_200_generica_nao_confirma(self):
        for corpo in (b'{}', b'{"status":"registro_ok","registrado":false}', b'nao-json'):
            with self.subTest(corpo=corpo):
                with self.assertRaises(ErroRegistro) as capturado: self.executar_resposta(corpo)
                self.assertTrue(capturado.exception.incerto)

    def test_http_422_401_404_e_500(self):
        for codigo in (422, 401, 403, 404, 500):
            erro = urllib.error.HTTPError(self.config.url, codigo, "erro", {}, io.BytesIO(b'token_ficticio'))
            with patch("integracao_n8n.urllib.request.build_opener") as abrir:
                abrir.return_value.open.side_effect = erro
                with self.assertRaises(ErroRegistro) as capturado: enviar_oferta(self.payload(), self.config)
                self.assertNotIn("token_ficticio", str(capturado.exception))
                self.assertEqual(capturado.exception.incerto, codigo == 500)

    def test_timeout_incerto_sem_reenvio_automatico(self):
        with patch("integracao_n8n.urllib.request.build_opener") as abrir:
            abrir.return_value.open.side_effect = TimeoutError()
            with self.assertRaises(ErroRegistro) as capturado: enviar_oferta(self.payload(), self.config)
            self.assertTrue(capturado.exception.incerto)
            self.assertEqual(abrir.return_value.open.call_count, 1)

    def test_redirecionamento_nao_encaminha_token(self):
        self.assertIsNone(_SemRedirecionamento().redirect_request(None, None, 302, "", {}, "https://outro.org"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
