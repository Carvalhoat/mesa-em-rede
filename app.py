import re
from datetime import date
from pathlib import Path

import streamlit as st

from extracao import ErroExtracao, extrair_oferta


PASTA = Path(__file__).resolve().parent
LOGO = PASTA / "brand" / "logo-horizontal.png"

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


def garantir_estado() -> None:
    st.session_state.setdefault("mensagem_analisada", None)
    st.session_state.setdefault("oferta", None)
    st.session_state.setdefault("resumo", None)
    st.session_state.setdefault("erro", None)
    st.session_state.setdefault("erros_revisao", [])
    st.session_state.setdefault("revisao_conferida", None)


def aplicar_estilo() -> None:
    st.markdown(
        """
        <style>
        h1, h2, h3 { color: #234539; }
        .faixa-ficticia {
            border-left: 4px solid #AD4D35;
            background: #FFFFFF;
            color: #26332D;
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            margin: 0.25rem 0 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def analisar_mensagem(texto: str) -> None:
    try:
        with st.spinner("Analisando a mensagem..."):
            oferta = extrair_oferta(texto).model_dump()
    except ErroExtracao as erro:
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
    reiniciar_revisao(oferta)


def confirmar_revisao() -> None:
    informados = ler_revisao()
    erros, revisado = validar_revisao(informados)
    st.session_state.revisao_conferida = informados
    st.session_state.erros_revisao = erros
    if erros:
        st.session_state.resumo = None
        return
    st.session_state.resumo = revisado


def exibir_valores(valores: dict[str, str | int | None]) -> None:
    for campo, nome in CAMPOS:
        st.write(f"**{nome}:** {valor_exibicao(valores.get(campo))}")


def main() -> None:
    st.set_page_config(
        page_title="Triagem de excedentes",
        page_icon=str(LOGO),
        layout="centered",
    )
    aplicar_estilo()
    garantir_estado()

    st.image(str(LOGO), width=480)
    st.title("Triagem de excedentes")
    st.markdown(
        """
        <div class="faixa-ficticia">
        Esta demonstração usa dados fictícios.
        A revisão confirmada permanece apenas nesta sessão do navegador:
        ela não é gravada em arquivo nem enviada a outro sistema.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.text_area(
        "Mensagem do restaurante",
        key="mensagem",
        height=140,
    )

    if st.button("Analisar mensagem", type="primary"):
        texto = str(st.session_state.get("mensagem", "")).strip()
        if not texto:
            st.warning("Escreva a mensagem do restaurante antes de analisar.")
        else:
            analisar_mensagem(texto)

    if st.session_state.erro:
        st.error(st.session_state.erro)

    oferta = st.session_state.oferta
    if oferta is None:
        return

    texto_atual = str(st.session_state.get("mensagem", "")).strip()
    mensagem_mudou = texto_atual != st.session_state.mensagem_analisada

    st.subheader("Mensagem analisada")
    st.write(st.session_state.mensagem_analisada)

    st.subheader("Campos extraídos")
    exibir_valores(oferta)
    pendencias_extracao = nomes_pendentes(oferta)
    if pendencias_extracao:
        st.warning(
            "Pendências da extração: "
            + juntar_nomes(pendencias_extracao)
            + "."
        )
    else:
        st.success("A extração não deixou pendências.")

    st.subheader("Revisão")
    st.caption(
        "Ajuste o que precisar. Campos em branco continuam como informações "
        "ausentes e não são preenchidos automaticamente."
    )
    st.text_input("Item", key="rev_item")
    st.text_input(
        "Quantidade",
        key="rev_quantidade",
        help="Número inteiro positivo. Deixe em branco se a quantidade seguir ausente.",
    )
    st.text_input("Bairro", key="rev_bairro")
    st.text_input(
        "Data de retirada",
        key="rev_data",
        help="Formato AAAA-MM-DD. Deixe em branco se a data seguir ausente.",
    )
    st.text_input(
        "Horário de retirada",
        key="rev_horario",
        help="Intervalo HH:MM-HH:MM, em 24 horas. Deixe em branco se o horário seguir ausente.",
    )

    if mensagem_mudou:
        st.warning(
            "A mensagem foi alterada e exige uma nova análise. "
            "A confirmação fica bloqueada até que o texto atual seja analisado. "
            "O resultado anterior não vale para o texto novo."
        )
    elif st.button("Confirmar revisão"):
        confirmar_revisao()

    revisao_atual = ler_revisao()
    conferencia_atual = (
        st.session_state.revisao_conferida == revisao_atual
        and not mensagem_mudou
    )
    if conferencia_atual:
        for mensagem_erro in st.session_state.erros_revisao:
            st.error(mensagem_erro)

    resumo = st.session_state.resumo
    if (
        resumo is None
        or mensagem_mudou
        or st.session_state.revisao_conferida != revisao_atual
    ):
        if resumo is not None and not mensagem_mudou:
            st.info(
                "Os campos da revisão mudaram. "
                "Confirme novamente para atualizar o resumo desta sessão."
            )
        return

    st.subheader("Resumo revisado")
    exibir_valores(resumo)
    pendencias = nomes_pendentes(resumo)
    if pendencias:
        st.warning(
            "Ainda há pendências: " + juntar_nomes(pendencias) + "."
        )
    else:
        st.success("A revisão não tem pendências.")
    st.caption(
        "Este resumo existe somente nesta sessão. "
        "Atualizar ou fechar a página descarta a revisão."
    )


if __name__ == "__main__":
    main()
