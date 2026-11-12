"""Indicadores de ofertas fictícias importadas de CSV, sem acesso externo."""
import csv
import io
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

COLUNAS = (
    "oferta_id", "registrado_em", "restaurante_id", "item", "quantidade", "unidade",
    "bairro", "data_retirada", "horario_inicio", "horario_fim", "status_oferta",
    "status_consulta", "total_organizacoes_compativeis", "organizacoes_compativeis_ids",
    "consulta_realizada_em", "dados_ficticios",
)
STATUS_CONSULTA = {"com_compativeis", "sem_compativeis", "nao_consultada", "erro"}
LIMITE_BYTES = 2 * 1024 * 1024
LIMITE_OFERTAS = 10000


class ErroPainel(ValueError):
    pass


def _data_registro(texto: str) -> date:
    for formato in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except ValueError:
        raise ErroPainel("data de registro inválida; exporte as datas formatadas da planilha") from None


def ler_ofertas_csv(conteudo: bytes) -> list[dict]:
    if len(conteudo) > LIMITE_BYTES:
        raise ErroPainel("O CSV deve ter até 2 MB.")
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            texto = conteudo.decode("cp1252")
        except UnicodeDecodeError:
            raise ErroPainel("Exporte o CSV em UTF-8.") from None
    leitor = None
    for separador in (",", ";"):
        candidato = csv.reader(io.StringIO(texto), delimiter=separador, strict=True)
        try:
            cabecalho = [v.strip() for v in next(candidato)]
        except (StopIteration, csv.Error):
            continue
        if set(COLUNAS).issubset(cabecalho):
            nomes_preenchidos = [v for v in cabecalho if v]
            if len(nomes_preenchidos) != len(set(nomes_preenchidos)):
                raise ErroPainel("Há cabeçalhos repetidos no arquivo.")
            leitor = candidato
            break
    if leitor is None:
        raise ErroPainel("Arquivo incompatível. Exporte a aba ofertas com os 16 cabeçalhos originais.")
    ofertas = []
    conhecidos = set()
    try:
        for valores in leitor:
            numero_linha = leitor.line_num
            if not any(v.strip() for v in valores):
                continue
            if len(valores) != len(cabecalho):
                raise ErroPainel(f"Linha {numero_linha}: número de colunas diferente do cabeçalho.")
            linha = {k: v.strip() for k, v in zip(cabecalho, valores) if k in COLUNAS}
            ident = linha["oferta_id"]
            if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", ident) is None:
                raise ErroPainel(f"Linha {numero_linha}: identificador ausente ou inválido.")
            if ident in conhecidos:
                raise ErroPainel(f"Linha {numero_linha}: identificador repetido. Confira a planilha antes de calcular.")
            conhecidos.add(ident)
            if linha["dados_ficticios"].casefold() != "sim":
                raise ErroPainel(f"Linha {numero_linha}: esta versão aceita somente ofertas marcadas como fictícias.")
            if linha["status_oferta"] not in {"registrada", "cancelada"}:
                raise ErroPainel(f"Linha {numero_linha}: status da oferta desconhecido.")
            if linha["status_consulta"] not in STATUS_CONSULTA:
                raise ErroPainel(f"Linha {numero_linha}: status da consulta desconhecido.")
            if not linha["item"] or not linha["bairro"]:
                raise ErroPainel(f"Linha {numero_linha}: alimento e bairro precisam estar preenchidos.")
            if re.fullmatch(r"[0-9]+", linha["quantidade"]) is None or int(linha["quantidade"]) < 1:
                raise ErroPainel(f"Linha {numero_linha}: quantidade precisa ser um inteiro positivo.")
            try:
                linha["data_registro"] = _data_registro(linha["registrado_em"])
            except ErroPainel as erro:
                raise ErroPainel(f"Linha {numero_linha}: {erro}.") from None
            total = linha["total_organizacoes_compativeis"]
            status = linha["status_consulta"]
            if status in {"com_compativeis", "sem_compativeis"}:
                if re.fullmatch(r"[0-9]+", total) is None:
                    raise ErroPainel(f"Linha {numero_linha}: consulta concluída sem total válido.")
                if (status == "com_compativeis" and int(total) < 1) or (status == "sem_compativeis" and int(total) != 0):
                    raise ErroPainel(f"Linha {numero_linha}: total incompatível com o status da consulta.")
            elif total:
                raise ErroPainel(f"Linha {numero_linha}: consulta pendente ou com erro deve ter total em branco.")
            ofertas.append(linha)
            if len(ofertas) > LIMITE_OFERTAS:
                raise ErroPainel("O arquivo deve conter até 10.000 ofertas.")
    except csv.Error:
        raise ErroPainel("O CSV contém aspas ou linhas malformadas. Exporte novamente da planilha.") from None
    return ofertas


def filtrar_ofertas(ofertas: list[dict], inicio: date, fim: date, *, bairros=None,
                    alimentos=None, status_oferta="registrada") -> list[dict]:
    return [o for o in ofertas if inicio <= o["data_registro"] <= fim
            and (bairros is None or o["bairro"] in bairros)
            and (alimentos is None or o["item"] in alimentos)
            and (status_oferta == "Todas" or o["status_oferta"] == status_oferta)]


def calcular_indicadores(ofertas: list[dict]) -> dict:
    contagem = Counter(o["status_consulta"] for o in ofertas)
    concluidas = contagem["com_compativeis"] + contagem["sem_compativeis"]
    return {
        "total": len(ofertas), "com_compativeis": contagem["com_compativeis"],
        "sem_compativeis": contagem["sem_compativeis"],
        "nao_consultadas": contagem["nao_consultada"], "erros": contagem["erro"],
        "concluidas": concluidas,
        "taxa_compatibilidade": 100 * contagem["com_compativeis"] / concluidas if concluidas else None,
        "por_alimento": dict(sorted(Counter(o["item"] for o in ofertas).items())),
        "por_bairro": dict(sorted(Counter(o["bairro"] for o in ofertas).items())),
    }


def exibir_painel(pasta: Path) -> None:
    import streamlit as st

    st.title("Ofertas em números")
    st.write("Acompanhe os registros e a compatibilidade inicial da demonstração.")
    st.caption("Fonte: arquivo CSV importado. Sem atualização automática com a planilha; nenhum dado deste painel é enviado ao Gemini ou ao n8n.")
    with st.expander("Como exportar a planilha"):
        st.write("No Google Sheets, abra a aba ofertas. Vá em Arquivo → Fazer download → Valores separados por vírgulas (.csv, página atual). Importe o arquivo abaixo.")
        st.caption("O registro de uma oferta no aplicativo não atualiza este arquivo. Exporte e importe novamente para ver novos registros.")
    fonte = st.radio("Fonte do painel", ["Importar CSV", "Exemplo fictício"], horizontal=True, key="painel_fonte")
    if fonte == "Importar CSV":
        arquivo = st.file_uploader("CSV da aba ofertas", type=["csv"], key="painel_csv")
        if arquivo is None:
            st.info("Importe o CSV para visualizar os indicadores ou escolha Exemplo fictício para conhecer o painel.")
            return
        conteudo = arquivo.getvalue()
        st.caption("Fonte selecionada: " + arquivo.name)
    else:
        st.warning("Exemplo fictício independente da sua planilha. Estes números servem apenas para demonstrar o painel.")
        try:
            conteudo = (pasta / "data" / "ofertas_exemplo.csv").read_bytes()
        except OSError:
            st.error("Não foi possível abrir data/ofertas_exemplo.csv.")
            return
    try:
        ofertas = ler_ofertas_csv(conteudo)
    except ErroPainel as erro:
        st.error(str(erro))
        return
    if not ofertas:
        st.info("O arquivo tem cabeçalhos válidos, mas ainda não contém ofertas.")
        return
    datas = [o["data_registro"] for o in ofertas]
    st.subheader("Escolha o recorte")
    c1, c2 = st.columns(2)
    with c1:
        periodo = st.date_input("Período de registro", value=(min(datas), max(datas)),
                                min_value=min(datas), max_value=max(datas), format="DD/MM/YYYY")
        bairros = st.multiselect("Bairros", sorted({o["bairro"] for o in ofertas}),
                                 default=sorted({o["bairro"] for o in ofertas}))
    with c2:
        status = st.selectbox("Situação da oferta", ["registrada", "cancelada", "Todas"])
        alimentos = st.multiselect("Alimentos", sorted({o["item"] for o in ofertas}),
                                   default=sorted({o["item"] for o in ofertas}))
    if len(periodo) != 2:
        st.info("Selecione o início e o fim do período de registro.")
        return
    recorte = filtrar_ofertas(ofertas, *periodo, bairros=bairros, alimentos=alimentos, status_oferta=status)
    indicadores = calcular_indicadores(recorte)
    st.caption(f"{len(recorte)} de {len(ofertas)} ofertas no arquivo · período baseado no primeiro registro, não na data de retirada.")
    colunas = st.columns(4)
    taxa = indicadores["taxa_compatibilidade"]
    for coluna, rotulo, valor in zip(colunas,
            ["Ofertas no recorte", "Com compatibilidade", "Sem compatibilidade", "Taxa de compatibilidade"],
            [indicadores["total"], indicadores["com_compativeis"], indicadores["sem_compativeis"],
             f"{taxa:.1f}%".replace(".", ",") if taxa is not None else "—"]):
        coluna.metric(rotulo, valor)
    st.caption(f"Taxa = ofertas com compatibilidade ÷ consultas concluídas ({indicadores['concluidas']}). "
               f"Não consultadas: {indicadores['nao_consultadas']} · Com erro: {indicadores['erros']}. "
               "Sem consultas concluídas, a taxa não é calculada.")
    st.info("São registros de ofertas fictícias e sugestões iniciais. Estes números não representam doações, alimentos entregues ou pessoas atendidas.")
    if not recorte:
        st.warning("Nenhuma oferta corresponde aos filtros selecionados.")
        return
    esquerda, direita = st.columns(2)
    for coluna, titulo, chave, categoria in (
        (esquerda, "Ofertas por alimento", "por_alimento", "Alimento"),
        (direita, "Ofertas por bairro", "por_bairro", "Bairro"),
    ):
        with coluna:
            st.subheader(titulo)
            st.bar_chart([{categoria: k, "Ofertas": v} for k, v in indicadores[chave].items()],
                         x=categoria, y="Ofertas", color="#234539", horizontal=True)
    st.caption("Os gráficos contam ofertas; quantidades de alimentos diferentes não são somadas.")
    with st.expander("Conferir os registros do recorte"):
        st.dataframe([{k: o[k] for k in ("oferta_id", "registrado_em", "item", "quantidade", "unidade",
                       "bairro", "status_oferta", "status_consulta")} for o in recorte], hide_index=True,
                     width="stretch")
