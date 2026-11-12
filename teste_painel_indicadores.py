import csv
import io
from datetime import date
from pathlib import Path
import unittest

from painel_indicadores import COLUNAS, ErroPainel, calcular_indicadores, filtrar_ofertas, ler_ofertas_csv

EXEMPLO = Path(__file__).parent / "data" / "ofertas_exemplo.csv"


class TestePainel(unittest.TestCase):
    def setUp(self):
        self.conteudo = EXEMPLO.read_bytes()
        self.ofertas = ler_ofertas_csv(self.conteudo)

    def csv_alterado(self, campo, valor, *, duplicar=False):
        linhas = list(csv.DictReader(io.StringIO(self.conteudo.decode("utf-8-sig"))))
        linhas[0][campo] = valor
        if duplicar:
            linhas.append(linhas[0].copy())
        texto = io.StringIO(newline="")
        escritor = csv.DictWriter(texto, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(linhas)
        return texto.getvalue().encode("utf-8")

    def test_taxa_exclui_pendentes_e_erros(self):
        recorte = filtrar_ofertas(self.ofertas, date(2026,11,1), date(2026,11,30))
        indicadores = calcular_indicadores(recorte)
        self.assertEqual(indicadores["total"], 5)
        self.assertEqual(indicadores["concluidas"], 3)
        self.assertEqual(indicadores["com_compativeis"], 2)
        self.assertEqual(indicadores["sem_compativeis"], 1)
        self.assertEqual(indicadores["nao_consultadas"], 1)
        self.assertEqual(indicadores["erros"], 1)
        self.assertAlmostEqual(indicadores["taxa_compatibilidade"], 200/3)

    def test_canceladas_sao_incluidas_somente_quando_solicitadas(self):
        todas = filtrar_ofertas(self.ofertas, date.min, date.max, status_oferta="Todas")
        self.assertEqual(calcular_indicadores(todas)["total"], 6)
        self.assertEqual(calcular_indicadores(todas)["taxa_compatibilidade"], 75)

    def test_periodo_e_por_registro_e_limites_sao_inclusivos(self):
        recorte = filtrar_ofertas(self.ofertas, date(2026,11,12), date(2026,11,12))
        self.assertEqual({o["oferta_id"] for o in recorte}, {"painel_demo_003", "painel_demo_004"})

    def test_filtros_combinados_e_selecao_vazia(self):
        recorte = filtrar_ofertas(self.ofertas, date.min, date.max, bairros=["Moema"], alimentos=["arroz"])
        self.assertEqual(len(recorte), 1)
        self.assertEqual(filtrar_ofertas(self.ofertas, date.min, date.max, bairros=[]), [])

    def test_sem_consultas_concluidas_nao_apresenta_zero_por_cento(self):
        pendentes = [o for o in self.ofertas if o["status_consulta"] in {"erro", "nao_consultada"}]
        self.assertIsNone(calcular_indicadores(pendentes)["taxa_compatibilidade"])
        self.assertIsNone(calcular_indicadores([])["taxa_compatibilidade"])

    def test_graficos_contam_ofertas_e_nao_somam_quantidades(self):
        indicadores = calcular_indicadores(self.ofertas)
        self.assertEqual(indicadores["por_alimento"]["pão"], 3)
        self.assertEqual(indicadores["por_bairro"]["Vila Mariana"], 4)

    def test_identificadores_repetidos_bloqueiam_contagem(self):
        with self.assertRaisesRegex(ErroPainel, "repetido"):
            ler_ofertas_csv(self.csv_alterado("item", "pão", duplicar=True))

    def test_dados_inconsistentes_nao_sao_ignorados_silenciosamente(self):
        for campo, valor in [("oferta_id", ""), ("dados_ficticios", "não"),
                             ("status_oferta", "entregue"), ("status_consulta", "desconhecido"),
                             ("quantidade", "1.5"), ("registrado_em", "31/02/2026"),
                             ("total_organizacoes_compativeis", "0"), ("bairro", "")]:
            with self.subTest(campo=campo), self.assertRaises(ErroPainel):
                ler_ofertas_csv(self.csv_alterado(campo, valor))

    def test_arquivo_com_aba_errada_e_grande_demais_sao_rejeitados(self):
        for conteudo in (b"nome,capacidade\nA,10\n", b"a" * (2*1024*1024+1)):
            with self.assertRaises(ErroPainel):
                ler_ofertas_csv(conteudo)

    def test_cabecalho_valido_sem_registros_e_linhas_vazias(self):
        cabecalho = ",".join(COLUNAS) + "\n" + ","*15 + "\n"
        self.assertEqual(ler_ofertas_csv(cabecalho.encode()), [])

    def test_colunas_vazias_adicionais_da_planilha_nao_bloqueiam_importacao(self):
        linhas = list(csv.reader(io.StringIO(self.conteudo.decode("utf-8-sig"))))
        texto = io.StringIO(newline="")
        escritor = csv.writer(texto)
        escritor.writerows([linha + [""]*10 for linha in linhas])
        self.assertEqual(len(ler_ofertas_csv(texto.getvalue().encode())), 6)

    def test_exportacao_ponto_virgula_cp1252_e_bairro_com_virgula(self):
        texto = io.StringIO(newline="")
        escritor = csv.DictWriter(texto, fieldnames=COLUNAS, delimiter=";")
        escritor.writeheader()
        linha = {k: self.ofertas[0][k] for k in COLUNAS}
        linha["bairro"] = "Bairro, com vírgula"
        linha["registrado_em"] = "11/11/2026 10:00:00"
        escritor.writerow(linha)
        self.assertEqual(ler_ofertas_csv(texto.getvalue().encode("cp1252"))[0]["bairro"], "Bairro, com vírgula")


if __name__ == "__main__":
    unittest.main()
