"""Testes sem rede ou chave; usa respostas simuladas e o cadastro local real."""
import unittest
from copy import deepcopy
from unittest.mock import Mock

import httpx
try:
    import httpx2
except ModuleNotFoundError:
    httpx2 = None
from google.genai import types

from agente_triagem import ErroTriagem, executar_triagem, identificar_pendencias
from extracao import ErroExtracao
from organizacoes import consultar_organizacoes

OFERTA = dict(item="pão", quantidade=25, bairro="Vila Mariana",
              data_retirada="2026-11-12", horario_retirada="09:00-10:00")


def resposta(*nomes, texto="Revisão necessária.", argumentos=None):
    partes = [types.Part(function_call=types.FunctionCall(
        name=nome, args=argumentos or {}, id=f"call_{i}"
    )) for i, nome in enumerate(nomes)]
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=partes or [types.Part.from_text(text=texto)])
    )])


class TesteAgente(unittest.TestCase):
    def rodar(self, respostas, oferta=None, consultor=None, mensagem="mensagem original"):
        cliente = Mock()
        cliente.models.generate_content.side_effect = respostas
        extrator = Mock(return_value=deepcopy(OFERTA if oferta is None else oferta))
        consulta = consultor if consultor is not None else Mock(return_value=[])
        resultado = executar_triagem(mensagem, client=cliente, modelo="modelo-teste",
                                    extrator=extrator, consultor=consulta)
        return resultado, cliente, extrator, consulta

    def test_oferta_completa_consulta_cadastro_real(self):
        resultado, _, extrator, _ = self.rodar([
            resposta("extrair_oferta"), resposta("consultar_organizacoes"), resposta()
        ], consultor=consultar_organizacoes)
        self.assertEqual(resultado.status, "pronta_para_revisao")
        self.assertEqual([o["id"] for o in resultado.consulta if o["compativel"]], ["org_demo_001"])
        self.assertFalse(resultado.registrado)
        self.assertTrue(resultado.exige_revisao_humana)
        extrator.assert_called_once_with("mensagem original")

    def test_sem_compatibilidade_e_resultado_valido(self):
        resultado, *_ = self.rodar([resposta("extrair_oferta"), resposta("consultar_organizacoes"), resposta()],
                                  oferta={**OFERTA, "quantidade": 60}, consultor=consultar_organizacoes)
        self.assertEqual(resultado.status, "pronta_para_revisao")
        self.assertFalse(any(o["compativel"] for o in resultado.consulta))

    def test_pendencia_bloqueia_consulta_mesmo_se_modelo_pedir(self):
        resultado, _, _, consultor = self.rodar([
            resposta("extrair_oferta"), resposta("consultar_organizacoes"), resposta()
        ], oferta={**OFERTA, "quantidade": None})
        consultor.assert_not_called()
        self.assertEqual(resultado.status, "aguardando_dados")
        self.assertEqual(resultado.pendencias, ["quantidade"])
        self.assertIn("quantidade exata", resultado.perguntas[0])
        self.assertIsNone(resultado.consulta)

    def test_validacao_independente_da_ia(self):
        for campo, valor in [("quantidade", True), ("quantidade", 0), ("quantidade", 1.5),
                             ("data_retirada", "2026-02-30"), ("data_retirada", "20261112"),
                             ("horario_retirada", "10:00-09:00"), ("horario_retirada", "09:00-09:00"),
                             ("horario_retirada", "25:00-26:00"), ("bairro", "  ")]:
            with self.subTest(campo=campo, valor=valor):
                self.assertIn(campo, identificar_pendencias({**OFERTA, campo: valor}))

    def test_ferramenta_de_escrita_recusada(self):
        with self.assertRaisesRegex(ErroTriagem, "não permitida"):
            self.rodar([resposta("registrar_oferta")])

    def test_modelo_nao_pode_trocar_oferta(self):
        with self.assertRaisesRegex(ErroTriagem, "argumentos não permitidos"):
            self.rodar([resposta("extrair_oferta", argumentos={"mensagem": "substituir dados"})])

    def test_falsa_confirmacao_em_texto_nao_e_aceita(self):
        resultado, *_ = self.rodar([resposta("extrair_oferta"), resposta(texto="Registrado! 999 organizações!")],
                                  oferta={**OFERTA, "bairro": None})
        self.assertFalse(resultado.registrado)
        self.assertIsNone(resultado.consulta)
        self.assertIsNone(resultado.oferta["bairro"])

    def test_oferta_completa_sem_consulta_nao_conclui(self):
        with self.assertRaisesRegex(ErroTriagem, "sem consultar"):
            self.rodar([resposta("extrair_oferta"), resposta()])

    def test_sem_extracao_nao_ha_resultado_oficial(self):
        with self.assertRaisesRegex(ErroTriagem, "não extraiu"):
            self.rodar([resposta(texto="Oferta confirmada!")])

    def test_consulta_antes_da_extracao_nao_executa(self):
        consultor = Mock(return_value=[])
        resultado, *_ = self.rodar([resposta("consultar_organizacoes"), resposta("extrair_oferta"), resposta()],
                                  consultor=consultor, oferta={**OFERTA, "quantidade": None})
        consultor.assert_not_called()
        self.assertIsNone(resultado.consulta)

    def test_repeticoes_usam_cache(self):
        _, _, extrator, consultor = self.rodar([
            resposta("extrair_oferta", "extrair_oferta"),
            resposta("consultar_organizacoes", "consultar_organizacoes"), resposta()
        ])
        extrator.assert_called_once()
        consultor.assert_called_once()

    def test_limite_impede_loop(self):
        with self.assertRaisesRegex(ErroTriagem, "limite"):
            self.rodar([resposta("extrair_oferta")] * 4)

    def test_limite_de_chamadas_paralelas(self):
        with self.assertRaisesRegex(ErroTriagem, "limite"):
            self.rodar([resposta(*(["extrair_oferta"] * 5))])

    def test_erro_de_conexao_sem_detalhes_sensiveis(self):
        with self.assertRaises(ErroTriagem) as contexto:
            self.rodar([httpx.ConnectError("segredo-nao-exibir")])
        self.assertNotIn("segredo-nao-exibir", str(contexto.exception))

    @unittest.skipIf(httpx2 is None, "httpx2 não é usado pelo SDK instalado")
    def test_conexao_httpx2_interrompida_na_orquestracao(self):
        with self.assertRaisesRegex(ErroTriagem, "conexão com o Gemini falhou") as contexto:
            self.rodar([httpx2.ConnectError("[WinError 10054] detalhe-privado")])
        self.assertNotIn("detalhe-privado", str(contexto.exception))

    @unittest.skipIf(httpx2 is None, "httpx2 não é usado pelo SDK instalado")
    def test_conexao_httpx2_interrompida_dentro_do_extrator(self):
        cliente = Mock()
        cliente.models.generate_content.return_value = resposta("extrair_oferta")
        with self.assertRaisesRegex(ErroTriagem, "conexão com o Gemini falhou"):
            executar_triagem("oferta", client=cliente, modelo="teste", extrator=Mock(
                side_effect=httpx2.ConnectError("[WinError 10054]")
            ))

    def test_falha_da_extracao_e_preservada_como_erro_seguro(self):
        cliente = Mock()
        cliente.models.generate_content.return_value = resposta("extrair_oferta")
        with self.assertRaisesRegex(ErroTriagem, "Limite atingido"):
            executar_triagem("oferta", client=cliente, modelo="teste",
                            extrator=Mock(side_effect=ErroExtracao("Limite atingido")))

    def test_conteudo_e_id_preservados_no_historico(self):
        primeira = resposta("extrair_oferta")
        primeira.candidates[0].content.parts[0].thought_signature = b"assinatura"
        historicos = []
        cliente = Mock()
        respostas = iter([primeira, resposta()])

        def gerar(**kwargs):
            historicos.append(deepcopy(kwargs["contents"]))
            return next(respostas)

        cliente.models.generate_content.side_effect = gerar
        executar_triagem("original", client=cliente, modelo="teste", extrator=lambda _: {**OFERTA, "bairro": None})
        self.assertEqual(historicos[1][1].parts[0].thought_signature, b"assinatura")
        self.assertEqual(historicos[1][2].parts[0].function_response.id, "call_0")

    def test_nova_execucao_nao_reutiliza_oferta_anterior(self):
        primeira, *_ = self.rodar([resposta("extrair_oferta"), resposta("consultar_organizacoes"), resposta()])
        segunda, *_ = self.rodar([resposta("extrair_oferta"), resposta()], oferta={**OFERTA, "bairro": None})
        self.assertEqual(primeira.oferta["bairro"], "Vila Mariana")
        self.assertIsNone(segunda.oferta["bairro"])

    def test_retorno_das_ferramentas_usa_papel_aceito_pelo_gemini(self):
        cliente = Mock()
        respostas = iter([resposta("extrair_oferta"), resposta("consultar_organizacoes"), resposta()])

        def gerar(**kwargs):
            for conteudo in kwargs["contents"]:
                self.assertIn(conteudo.role, {"user", "model"})
                if any(p.function_response is not None for p in conteudo.parts):
                    self.assertEqual(conteudo.role, "user")
            return next(respostas)

        cliente.models.generate_content.side_effect = gerar
        resultado = executar_triagem("oferta fictícia", client=cliente, modelo="teste",
                                     extrator=lambda _: OFERTA, consultor=lambda _: [])
        self.assertEqual(resultado.status, "pronta_para_revisao")

    def test_entrada_vazia_ou_extensa_nao_chama_api(self):
        cliente = Mock()
        for mensagem in ("  ", "a" * 8001):
            with self.assertRaises(ErroTriagem):
                executar_triagem(mensagem, client=cliente, modelo="teste")
        cliente.models.generate_content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
