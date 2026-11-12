import re
import json
from copy import deepcopy
from uuid import uuid4
import base64
from html import escape
from datetime import timedelta, datetime, timezone
from datetime import date
from pathlib import Path

import streamlit as st

from agente_triagem import ErroTriagem, executar_triagem
from painel_indicadores import exibir_painel
from organizacoes import consultar_organizacoes
from integracao_n8n import (
    ErroRegistro, enviar_oferta, ler_configuracao, montar_payload, validar_configuracao,
)


PASTA = Path(__file__).resolve().parent
ILUSTRACOES = PASTA / "brand" / "exportacoes"

CAMPOS = (
    ("item", "Item"),
    ("quantidade", "Quantidade"),
    ("bairro", "Bairro"),
    ("data_retirada", "Data de retirada"),
    ("horario_retirada", "Horário de retirada"),
)

CHAVES_REVISAO = {
    "item": "rev_item",
    "quantidade": "rev_quantidade",
    "bairro": "rev_bairro",
    "data_retirada": "rev_data",
    "horario_retirada": "rev_horario",
}

PADRAO_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PADRAO_HORARIO = re.compile(
    r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$"
)


def juntar_nomes(nomes: list[str]) -> str:
    if not nomes:
        return "nenhuma"
    if len(nomes) == 1:
        return nomes[0]
    return ", ".join(nomes[:-1]) + " e " + nomes[-1]


def nomes_pendentes(valores: dict[str, str | int | None]) -> list[str]:
    return [nome for campo, nome in CAMPOS if valores.get(campo) in (None, "")]


def validar_revisao(
    valores: dict[str, str],
) -> tuple[list[str], dict[str, str | int | None]]:
    erros: list[str] = []
    revisado: dict[str, str | int | None] = {}

    for campo, _nome in CAMPOS:
        revisado[campo] = valores.get(campo, "").strip() or None

    quantidade = revisado["quantidade"]
    if isinstance(quantidade, str):
        try:
            if re.fullmatch(r"[0-9]+", quantidade) is None:
                raise ValueError

            numero = int(quantidade)
            if numero < 1:
                raise ValueError

            revisado["quantidade"] = numero
        except ValueError:
            erros.append("Quantidade precisa ser um número inteiro positivo.")
            revisado["quantidade"] = None

    data_retirada = revisado["data_retirada"]
    if isinstance(data_retirada, str):
        try:
            if PADRAO_DATA.fullmatch(data_retirada) is None:
                raise ValueError

            date.fromisoformat(data_retirada)
        except ValueError:
            erros.append(
                "Data de retirada precisa ser uma data válida "
                "no formato AAAA-MM-DD."
            )

    horario = revisado["horario_retirada"]
    if isinstance(horario, str):
        correspondencia = PADRAO_HORARIO.fullmatch(horario)

        if correspondencia is None:
            erros.append(
                "Horário de retirada precisa ser um intervalo no formato "
                "HH:MM-HH:MM, com o fim depois do início."
            )
        else:
            inicio = (
                int(correspondencia.group(1)) * 60
                + int(correspondencia.group(2))
            )
            fim = (
                int(correspondencia.group(3)) * 60
                + int(correspondencia.group(4))
            )

            if fim <= inicio:
                erros.append(
                    "Horário de retirada precisa ser um intervalo no formato "
                    "HH:MM-HH:MM, com o fim depois do início."
                )

    return erros, revisado


def valor_exibicao(valor: str | int | None) -> str:
    if valor is None or valor == "":
        return "Não informado"
    return str(valor)


def ler_revisao() -> dict[str, str]:
    return {
        campo: str(st.session_state.get(chave, "") or "")
        for campo, chave in CHAVES_REVISAO.items()
    }


def reiniciar_revisao(oferta: dict[str, str | int | None]) -> None:
    for campo, chave in CHAVES_REVISAO.items():
        valor = oferta.get(campo)
        st.session_state[chave] = "" if valor is None else str(valor)
    st.session_state.resumo = None
    st.session_state.erros_revisao = []
    st.session_state.revisao_conferida = None
    st.session_state.registro_id = "oferta_" + uuid4().hex
    st.session_state.registro = None
    st.session_state.registro_alguma_vez = False


def garantir_estado() -> None:
    st.session_state.setdefault("mensagem_analisada", None)
    st.session_state.setdefault("oferta", None)
    st.session_state.setdefault("resumo", None)
    st.session_state.setdefault("erro", None)
    st.session_state.setdefault("erros_revisao", [])
    st.session_state.setdefault("revisao_conferida", None)
    st.session_state.setdefault("consulta", None)
    st.session_state.setdefault("triagem", None)
    st.session_state.setdefault("previa_consulta", None)
    st.session_state.setdefault("registro_id", None)
    st.session_state.setdefault("registro", None)
    st.session_state.setdefault("registro_alguma_vez", False)


def analisar_mensagem(texto: str) -> None:
    st.session_state.consulta = None
    st.session_state.triagem = None
    st.session_state.previa_consulta = None
    try:
        with st.spinner("O agente está organizando a oferta e verificando pendências..."):
            triagem = executar_triagem(texto)
            oferta = triagem.oferta
    except ErroTriagem as erro:
        st.session_state.oferta = None
        st.session_state.mensagem_analisada = None
        st.session_state.resumo = None
        st.session_state.erros_revisao = []
        st.session_state.revisao_conferida = None
        st.session_state.erro = str(erro)
        return
    except Exception:
        st.session_state.oferta = None
        st.session_state.mensagem_analisada = None
        st.session_state.resumo = None
        st.session_state.erros_revisao = []
        st.session_state.revisao_conferida = None
        st.session_state.erro = (
            "Não foi possível concluir a análise. "
            "Tente novamente. O texto digitado foi mantido."
        )
        return

    st.session_state.erro = None
    st.session_state.mensagem_analisada = texto
    st.session_state.oferta = oferta
    st.session_state.triagem = triagem.para_dict()
    if triagem.consulta is not None:
        st.session_state.previa_consulta = {
            "oferta": deepcopy(oferta),
            "mensagem": texto,
            "resultados": deepcopy(triagem.consulta),
            "realizada_em": datetime.now(timezone.utc).isoformat(),
        }
    reiniciar_revisao(oferta)


def confirmar_revisao() -> None:
    st.session_state.consulta = None
    informados = ler_revisao()
    erros, revisado = validar_revisao(informados)
    st.session_state.revisao_conferida = informados
    st.session_state.erros_revisao = erros
    if erros:
        st.session_state.resumo = None
        return
    st.session_state.resumo = revisado
    previa = st.session_state.previa_consulta
    if (
        not nomes_pendentes(revisado)
        and previa is not None
        and previa["oferta"] == revisado
        and previa["mensagem"] == st.session_state.mensagem_analisada
    ):
        st.session_state.consulta = deepcopy(previa)


# Os personagens são arquivos locais aprovados no desenvolvimento da marca.
def imagem_personagem(nome: str, descricao: str, largura: int) -> None:
    caminho = ILUSTRACOES / nome
    if caminho.is_file():
        conteudo = base64.b64encode(caminho.read_bytes()).decode("ascii")
        st.markdown(
            f'<div class="personagem"><img src="data:image/png;base64,{conteudo}" '
            f'alt="{escape(descricao, quote=True)}" width="{largura}" /></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"Ilustração indisponível: {nome}")


def aplicar_estilo() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #FFF7EB; }
        .block-container { max-width: 1160px; padding-top: 5rem; padding-bottom: 2rem; }
        h1, h2, h3 { color: #234539; letter-spacing: -0.035em; }
        h1 { font-size: clamp(2.2rem, 4vw, 3.4rem) !important; line-height: 1.08 !important; }
        h2 { font-size: 1.65rem !important; }
        h3 { font-size: 1.2rem !important; }
        p { line-height: 1.65; }
        .marca { display: flex; align-items: center; gap: 12px; color: #234539; min-width: 0; flex: 1 1 320px; }
        .marca svg { display: block; flex: 0 0 44px; width: 44px; height: 44px; overflow: visible; }
        .marca > div { min-width: 0; }
        .marca-nome { font-weight: 800; font-size: 1.3rem; letter-spacing: -.04em; }
        .marca-sub { font-size: .7rem; color: #65766d; letter-spacing: .01em; overflow-wrap: anywhere; }
        .topo { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.6rem; gap: 16px; flex-wrap: wrap; width: 100%; box-sizing: border-box; }
        .selo { border: 1px solid #dcded2; color: #456052; border-radius: 30px; padding: 7px 13px; font-size: .75rem; flex: 0 1 auto; max-width: 100%; box-sizing: border-box; }
        .sobrelinha { color: #AD4D35; font-size: .72rem; font-weight: 800; letter-spacing: .12em; margin-bottom: .7rem; }
        .apoio { color: #53665c; max-width: 510px; font-size: 1rem; }
        .nota-demo { color: #53665c; font-size: .8rem; border-top: 1px solid #e7dfd0; padding: 12px 0; margin-bottom: 10px; }
        .etapas { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 5px 0 20px; }
        .etapa { display: flex; gap: 10px; align-items: center; border: 1px solid #e3dece; border-radius: 14px; padding: 13px; background: #ffffff88; }
        .etapa.ativa { background: #234539; border-color: #234539; color: white; }
        .etapa-num { width: 27px; height: 27px; flex: 0 0 27px; border-radius: 50%; border: 1px solid currentColor; display: grid; place-items: center; font-size: .8rem; }
        .etapa strong { display:block; font-size: .83rem; }
        .etapa small { font-size: .7rem; opacity: .8; }
        .etapa.futura { color: #6c776f; }
        .personagem { display: flex; align-items: center; justify-content: center; }
        .personagem img { max-width: 100%; height: auto; }
        div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 20px; }
        .st-key-entrada, .st-key-dados, .st-key-revisao, .st-key-resumo, .st-key-proximo { background: #FFFFFF; border-radius: 20px; }
        div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input { border-radius: 10px; }
        div.stButton > button { border-radius: 10px; min-height: 42px; font-weight: 650; }
        .rede { display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:10px; font-size:.73rem; color:#65766d; padding-top:24px; }
        .rede i { background:#AD4D35; width:6px; height:6px; border-radius:50%; display:inline-block; }
        @media (max-width: 640px) {
            .block-container { padding-top: 4.5rem; padding-left: 1rem; padding-right: 1rem; }
            .etapas { gap: 6px; }
            .etapa { flex-direction: column; align-items: flex-start; padding: 10px; gap: 7px; }
            .etapa strong { font-size: .72rem; }
            .etapa small { font-size: .65rem; }
            .selo { display:none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def carregar_exemplo() -> None:
    dia = (date.today() + timedelta(days=2)).strftime("%d/%m/%Y")
    st.session_state.mensagem = (
        "Temos 25 unidades de pão na Vila Mariana. "
        f"A retirada é dia {dia}, das 9h às 10h."
    )
    st.session_state.erro = None


def exibir_valores(valores: dict[str, str | int | None]) -> None:
    for campo, nome in CAMPOS:
        st.caption(nome)
        st.text(valor_exibicao(valores.get(campo)))


def exibir_registro(resumo: dict, consulta: dict | None) -> None:
    with st.container(border=True, key="registro"):
        st.subheader("4. Registre a oferta revisada")
        st.write("Salve esta oferta de demonstração na planilha do Mesa em Rede.")
        st.caption("O registro não confirma uma doação, não contata organizações e não reserva capacidade. Alterações só são enviadas ao clicar no botão abaixo.")
        if not st.session_state.registro_id:
            st.session_state.registro_id = "oferta_" + uuid4().hex
        try:
            payload = montar_payload(st.session_state.registro_id, resumo, consulta)
        except ErroRegistro as erro:
            st.warning(str(erro))
            return
        assinatura = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        registro = st.session_state.registro
        registro_atual = registro is not None and registro["assinatura"] == assinatura
        confirmado = registro_atual and registro["confirmado"]
        configuracao = None
        problema_config = None
        try:
            configuracao = ler_configuracao(PASTA)
            validar_configuracao(configuracao)
        except ErroRegistro as erro:
            problema_config = str(erro)
        except OSError:
            problema_config = "Não foi possível ler a configuração da integração. Confira o arquivo .env."
        if problema_config:
            st.info(problema_config)
        if consulta is None:
            st.caption("Esta oferta será salva como não consultada. Você poderá consultar organizações e atualizar o mesmo registro depois.")
        st.caption("Identificador desta oferta: " + st.session_state.registro_id)
        if st.session_state.registro_alguma_vez and not confirmado:
            st.info("Há uma versão desta oferta na planilha. O botão atualizará a mesma linha com os dados atuais, preservando a data do primeiro registro.")
        rotulo = "Oferta registrada" if confirmado else (
            "Tentar registro novamente" if registro_atual and registro.get("erro") else (
                "Atualizar oferta registrada" if st.session_state.registro_alguma_vez else "Registrar oferta"
            )
        )
        if st.button(rotulo, key="registrar_oferta", type="primary", disabled=bool(problema_config) or confirmado):
            estado = {"assinatura": assinatura, "confirmado": False, "erro": None, "incerto": False}
            st.session_state.registro = estado
            try:
                with st.spinner("Registrando a oferta na planilha..."):
                    enviar_oferta(payload, configuracao)
            except ErroRegistro as erro:
                estado["erro"] = str(erro)
                estado["incerto"] = erro.incerto
            else:
                estado["confirmado"] = True
                st.session_state.registro_alguma_vez = True
            st.rerun()
        registro = st.session_state.registro
        if registro is not None and registro["assinatura"] == assinatura:
            if registro["confirmado"]:
                st.success("Oferta registrada no Google Sheets. O registro continuará na planilha após fechar ou recarregar a aplicação.")
            elif registro.get("erro"):
                st.error(registro["erro"])
                if registro["incerto"]:
                    st.warning("Resultado pendente de conferência: a gravação pode ter ocorrido. Consulte o identificador acima no Sheets antes de reenviar.")
        st.caption("O identificador é mantido durante esta sessão. Uma nova análise inicia outra oferta; recarregar a página não recupera os registros anteriores na interface.")


def exibir_etapas(ativa: int, completa: bool) -> None:
    estados = (
        ("Informar excedente", "Mensagem do restaurante"),
        ("Revisar oferta", "Revisão concluída" if completa else "Conferência humana"),
        ("Consultar organizações", "Consulta concluída" if ativa == 2 else "Compatibilidade da oferta"),
    )
    partes = ['<div class="etapas">']
    for indice, (titulo, apoio) in enumerate(estados):
        classe = "ativa" if indice == ativa else ""
        if indice == 2 and not completa:
            classe = "futura"
        partes.append(
            f'<div class="etapa {classe}"><span class="etapa-num">{indice + 1}</span>'
            f'<div><strong>{titulo}</strong><small>{apoio}</small></div></div>'
        )
    partes.append("</div>")
    st.markdown("".join(partes), unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="Mesa em Rede · Triagem", page_icon="🍽️", layout="wide")
    aplicar_estilo()
    garantir_estado()
    # Mantém os campos da triagem quando seus widgets ficam fora da página.
    for chave in ("mensagem", *CHAVES_REVISAO.values()):
        if chave in st.session_state:
            st.session_state[chave] = st.session_state[chave]
    pagina = st.sidebar.radio("Navegação", ["Triagem da oferta", "Painel de indicadores"], key="pagina")
    if pagina == "Painel de indicadores":
        exibir_painel(PASTA)
        return

    # O símbolo é HTML/SVG estático, com fundo transparente.
    st.markdown(
        """
        <div class="topo"><div class="marca">
        <svg width="44" height="44" viewBox="0 0 80 80" aria-hidden="true">
          <g fill="none" stroke="#234539" stroke-width="2.7">
            <circle cx="40" cy="40" r="36"/><circle cx="40" cy="40" r="27"/>
            <path d="M18 55 L40 14 L62 55"/>
          </g>
          <g fill="#AD4D35"><circle cx="40" cy="14" r="4.5"/>
          <circle cx="18" cy="55" r="4.5"/><circle cx="62" cy="55" r="4.5"/></g>
        </svg>
        <div><div class="marca-nome">Mesa em Rede</div>
        <div class="marca-sub">Conectando excedentes alimentares a quem pode recebê-los.</div></div></div>
        <span class="selo">Protótipo · revisão humana</span></div>
        """,
        unsafe_allow_html=True,
    )

    texto, personagem = st.columns([2.5, 1], vertical_alignment="center")
    with texto:
        st.markdown('<div class="sobrelinha">DO EXCEDENTE À POSSIBILIDADE</div>', unsafe_allow_html=True)
        st.title("Um excedente pode encontrar uma nova mesa.")
        st.markdown(
            '<p class="apoio">Organize a oferta com apoio da IA e confira cada '
            'informação antes de seguir para o encaminhamento.</p>',
            unsafe_allow_html=True,
        )
    with personagem:
        imagem_personagem("pratinho-boas-vindas-final.png", "Pratinho acenando em boas-vindas", 210)
    st.markdown(
        '<div class="nota-demo">Demonstração com dados fictícios · '
        'A mensagem, os dados extraídos e a prévia da consulta fictícia são enviados '
        'ao Gemini durante a triagem. Ao clicar em Registrar oferta, '
        'os dados revisados são enviados ao n8n e salvos no Google Sheets. '
        'A mensagem original não é incluída nesse registro.</div>',
        unsafe_allow_html=True,
    )

    if (
        st.session_state.oferta is None
        or str(st.session_state.get("mensagem", "")).strip() != st.session_state.mensagem_analisada
        or st.session_state.revisao_conferida != ler_revisao()
    ):
        st.session_state.consulta = None

    etapas = st.empty()
    with st.container(border=True, key="entrada"):
        titulo, exemplo = st.columns([3, 1])
        with titulo:
            st.subheader("1. Conte o que está disponível")
        with exemplo:
            st.button("Usar exemplo", on_click=carregar_exemplo, use_container_width=True)
        st.caption("Informe alimento, quantidade, bairro, data e intervalo para retirada. O agente identifica pendências e, se os dados estiverem completos, prepara uma prévia de compatibilidade.")
        st.text_area(
            "Mensagem do restaurante", key="mensagem", height=125,
            placeholder="Ex.: temos 25 unidades de pão na Vila Mariana…",
        )
        if st.button("Analisar mensagem", type="primary"):
            atual = str(st.session_state.get("mensagem", "")).strip()
            if atual:
                analisar_mensagem(atual)
            else:
                st.warning("Escreva a mensagem do restaurante antes de analisar.")
        if st.session_state.erro:
            st.error(st.session_state.erro)

    oferta = st.session_state.oferta
    texto_atual = str(st.session_state.get("mensagem", "")).strip()
    mensagem_mudou = texto_atual != st.session_state.mensagem_analisada
    resumo_valido = (
        st.session_state.resumo is not None
        and not mensagem_mudou
        and st.session_state.revisao_conferida == ler_revisao()
    )
    completa = resumo_valido and not nomes_pendentes(st.session_state.resumo)

    if oferta is not None:
        if mensagem_mudou:
            st.warning("A mensagem mudou. Clique em Analisar mensagem para atualizar os dados. A confirmação está bloqueada.")
        triagem = st.session_state.triagem
        if triagem is not None and not mensagem_mudou:
            with st.container(border=True, key="triagem_agente"):
                st.subheader("Triagem do agente")
                st.caption("Resultado da mensagem analisada. Confira e complete os campos na revisão abaixo.")
                if triagem["perguntas"]:
                    st.info("O agente precisa de mais informações:")
                    for pergunta in triagem["perguntas"]:
                        st.write("• " + pergunta)
                elif st.session_state.previa_consulta is not None:
                    st.info("O agente preparou uma prévia de compatibilidade. Confirme a revisão para conferir o resultado.")
                st.caption("A triagem não confirma a revisão e não registra a oferta.")
                with st.expander("Como a triagem foi feita"):
                    nomes = {"extrair_oferta": "Extração dos dados e verificação de pendências",
                             "consultar_organizacoes": "Consulta ao cadastro fictício de organizações"}
                    for ferramenta in dict.fromkeys(triagem["ferramentas"]):
                        st.write("✓ " + nomes.get(ferramenta, "Etapa de triagem"))
        original, revisao = st.columns([1, 1.35], gap="large")
        with original:
            with st.container(border=True, key="dados"):
                st.subheader("O que a IA identificou")
                st.caption("Dados extraídos da mensagem analisada, antes das suas correções.")
                with st.expander("Ver mensagem analisada"):
                    st.text(st.session_state.mensagem_analisada)
                exibir_valores(oferta)
                pendentes = nomes_pendentes(oferta)
                if pendentes:
                    st.warning("Falta informar: " + juntar_nomes(pendentes) + ".")
                else:
                    st.success("Os cinco campos foram preenchidos pela extração.")
        with revisao:
            with st.container(border=True, key="revisao"):
                cabecalho, ilustra = st.columns([3, 1])
                with cabecalho:
                    st.subheader("2. Confira a oferta")
                    st.caption("Corrija o que precisar. Campos vazios continuam como pendências.")
                with ilustra:
                    imagem_personagem("pratinho-revisao-final.png", "Pratinho conferindo uma oferta", 95)
                st.text_input("Item", key="rev_item")
                quantidade, bairro = st.columns([1, 2])
                with quantidade:
                    st.text_input("Quantidade", key="rev_quantidade", help="Número inteiro positivo, em unidades.")
                with bairro:
                    st.text_input("Bairro", key="rev_bairro")
                data_col, hora_col = st.columns(2)
                with data_col:
                    st.text_input("Data de retirada", key="rev_data", help="Formato AAAA-MM-DD. Ex.: 2026-11-12.")
                with hora_col:
                    st.text_input("Horário de retirada", key="rev_horario", help="Formato HH:MM-HH:MM. Ex.: 09:00-10:00.")
                pendentes_revisao = nomes_pendentes({k: v.strip() for k, v in ler_revisao().items()})
                if pendentes_revisao:
                    st.caption("Complete quando possível: " + juntar_nomes(pendentes_revisao) + ".")
                if st.button("Confirmar revisão", type="primary", disabled=mensagem_mudou):
                    confirmar_revisao()
                conferencia_atual = (
                    st.session_state.revisao_conferida == ler_revisao()
                    and not mensagem_mudou
                )
                if conferencia_atual:
                    for erro in st.session_state.erros_revisao:
                        st.error(erro)

        resumo = st.session_state.resumo
        resumo_valido = (
            resumo is not None and not mensagem_mudou
            and st.session_state.revisao_conferida == ler_revisao()
        )
        completa = resumo_valido and not nomes_pendentes(resumo)
        if resumo_valido:
            with st.container(border=True, key="resumo"):
                info, ilustra = st.columns([3, 1], vertical_alignment="center")
                with info:
                    st.subheader("Oferta revisada" if completa else "Revisão com pendências")
                    st.caption("Resumo confirmado por você · disponível nesta sessão")
                    campos = st.columns(2)
                    with campos[0]:
                        for campo, rotulo in CAMPOS[:3]:
                            st.caption(rotulo)
                            st.text(valor_exibicao(resumo.get(campo)))
                    with campos[1]:
                        for campo, rotulo in CAMPOS[3:]:
                            st.caption(rotulo)
                            st.text(valor_exibicao(resumo.get(campo)))
                with ilustra:
                    imagem_personagem(
                        "pratinho-alimentos-final.png" if completa else "pratinho-revisao-final.png",
                        "Pratinho com uma caixa de alimentos" if completa else "Pratinho revisando dados pendentes", 160,
                    )
                if completa:
                    st.success("A revisão não tem pendências.")
                else:
                    st.warning("Ainda há pendências: " + juntar_nomes(nomes_pendentes(resumo)) + ".")
            if completa:
                with st.container(border=True, key="proximo"):
                    informacao, ilustra = st.columns([4, 1], vertical_alignment="center")
                    with informacao:
                        st.subheader("3. Encontre o próximo elo da rede")
                        st.write("Consulte organizações fictícias por alimento, bairro, capacidade e disponibilidade.")
                        st.caption("A consulta é uma sugestão para avaliação humana. Não envia mensagens nem reserva capacidade.")
                        previa = st.session_state.previa_consulta
                        if previa is not None and previa["oferta"] != resumo:
                            st.caption("Você alterou os dados da oferta. Consulte novamente para avaliar a versão revisada.")
                        if st.button("Consultar organizações", type="primary"):
                            st.session_state.consulta = None
                            try:
                                resultados = consultar_organizacoes(resumo)
                            except (ValueError, OSError, KeyError, TypeError):
                                st.error("Não foi possível consultar o cadastro. Confira data/organizacoes.json e os campos da oferta.")
                            else:
                                st.session_state.consulta = {
                                    "oferta": resumo.copy(),
                                    "mensagem": st.session_state.mensagem_analisada,
                                    "resultados": resultados,
                                    "realizada_em": datetime.now(timezone.utc).isoformat(),
                                }
                    with ilustra:
                        imagem_personagem("caminhao-retirada-final.png", "Ilustração de retirada de alimentos", 140)
                consulta = st.session_state.consulta
                consulta_atual = (
                    consulta is not None
                    and consulta["oferta"] == resumo
                    and consulta["mensagem"] == st.session_state.mensagem_analisada
                )
                if consulta_atual:
                    resultados = consulta["resultados"]
                    compativeis = [r for r in resultados if r["compativel"]]
                    st.subheader("Resultado da consulta")
                    st.caption(f"{len(compativeis)} de {len(resultados)} organizações com compatibilidade inicial. Dados de demonstração.")
                    st.caption("Capacidade por oferta. O cadastro não acompanha a soma de ofertas simultâneas.")
                    if not compativeis:
                        with st.container(border=True):
                            mensagem_vazia, ilustracao_vazia = st.columns([3, 1], vertical_alignment="center")
                            with mensagem_vazia:
                                st.markdown("**Ainda não encontramos uma organização compatível.**")
                                st.write("Nenhuma organização do cadastro atende a todos os critérios desta oferta. Consulte os motivos abaixo.")
                                st.caption("Confira se os dados da oferta estão corretos. A busca considera apenas as organizações fictícias cadastradas nesta demonstração.")
                            with ilustracao_vazia:
                                imagem_personagem(
                                    "pratinho-sem-compatibilidade-final.png",
                                    "Pratinho com expressão levemente triste porque não houve compatibilidade na consulta",
                                    150,
                                )
                    for resultado in compativeis:
                        with st.container(border=True):
                            st.subheader(resultado["nome"])
                            st.success("Compatibilidade inicial identificada")
                            for motivo in resultado["motivos"]:
                                st.write("✓ " + motivo)
                            st.caption("A organização ainda precisa confirmar interesse, condições de recebimento e retirada.")
                    outras = [r for r in resultados if not r["compativel"]]
                    if outras:
                        with st.expander("Por que as outras organizações não foram sugeridas?"):
                            for resultado in outras:
                                st.write("**" + resultado["nome"] + "**")
                                for motivo in resultado["impedimentos"]:
                                    st.write("• " + motivo)
                exibir_registro(resumo, consulta if consulta_atual else None)
        elif resumo is not None and not mensagem_mudou:
            st.info("Os campos da revisão mudaram. Confirme novamente para atualizar o resumo desta sessão.")

    consulta = st.session_state.consulta
    consulta_atual = (
        completa and consulta is not None
        and consulta["oferta"] == st.session_state.resumo
        and consulta["mensagem"] == st.session_state.mensagem_analisada
    )
    if not resumo_valido:
        st.session_state.consulta = None
    ativa = 0 if oferta is None or mensagem_mudou else 1
    if consulta_atual:
        ativa = 2
    with etapas.container():
        exibir_etapas(ativa, completa)
    st.markdown(
        '<div class="rede"><span>Restaurante</span><i></i><span>Triagem humana</span>'
        '<i></i><span>Organização receptora</span></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
