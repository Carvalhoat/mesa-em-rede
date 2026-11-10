import json
import re
import unicodedata
from datetime import date
from pathlib import Path


PASTA = Path(__file__).resolve().parent

PADRAO_INTERVALO = re.compile(
    r"([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)"
)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.casefold())
    sem_acentos = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(sem_acentos.split())


def minutos(horario: str) -> int:
    horas, minuto = horario.split(":")
    return int(horas) * 60 + int(minuto)


def formatar_horario(valor: int) -> str:
    return f"{valor // 60:02d}:{valor % 60:02d}"


def consultar_organizacoes(oferta: dict) -> list[dict]:
    campos = (
        "item",
        "quantidade",
        "bairro",
        "data_retirada",
        "horario_retirada",
    )

    pendentes = [
        campo
        for campo in campos
        if oferta.get(campo) is None
        or oferta.get(campo) == ""
    ]

    if pendentes:
        raise ValueError(
            "Complete a revisão antes da consulta. "
            "Campos pendentes: " + ", ".join(pendentes)
        )

    quantidade = oferta["quantidade"]
    if type(quantidade) is not int or quantidade < 1:
        raise ValueError("A quantidade deve ser um inteiro positivo.")

    try:
        dia_retirada = date.fromisoformat(oferta["data_retirada"])
    except (ValueError, TypeError):
        raise ValueError(
            "Informe uma data válida no formato AAAA-MM-DD."
        ) from None

    intervalo = oferta["horario_retirada"]
    if (
        not isinstance(intervalo, str)
        or PADRAO_INTERVALO.fullmatch(intervalo) is None
    ):
        raise ValueError("Informe o intervalo no formato HH:MM-HH:MM.")

    inicio_texto, fim_texto = intervalo.split("-")
    inicio_oferta = minutos(inicio_texto)
    fim_oferta = minutos(fim_texto)

    if fim_oferta <= inicio_oferta:
        raise ValueError(
            "O fim da retirada deve ser posterior ao início."
        )

    item = normalizar(oferta["item"])
    bairro = normalizar(oferta["bairro"])

    organizacoes = json.loads(
        (PASTA / "data" / "organizacoes.json").read_text(
            encoding="utf-8"
        )
    )

    resultados = []

    for organizacao in organizacoes:
        motivos = []
        impedimentos = []

        alimentos = {
            normalizar(alimento)
            for alimento in organizacao["alimentos_aceitos"]
        }
        bairros = {
            normalizar(regiao)
            for regiao in organizacao["bairros_atendidos"]
        }

        if item in alimentos:
            motivos.append("Aceita o alimento informado.")
        else:
            impedimentos.append("Alimento fora do cadastro de recebimento.")

        if bairro in bairros:
            motivos.append("Atende ao bairro da oferta.")
        else:
            impedimentos.append("Bairro fora da região atendida.")

        capacidade = organizacao["capacidade_por_oferta_unidades"]
        if quantidade <= capacidade:
            motivos.append(
                f"Recebe até {capacidade} unidades por oferta."
            )
        else:
            impedimentos.append(
                f"Capacidade insuficiente: recebe até "
                f"{capacidade} unidades por oferta."
            )

        dia_compativel = (
            dia_retirada.weekday() in organizacao["dias_semana"]
        )

        inicio_comum = max(
            inicio_oferta,
            minutos(organizacao["horario_inicio"]),
        )
        fim_comum = min(
            fim_oferta,
            minutos(organizacao["horario_fim"]),
        )

        janela_compativel = None

        if not dia_compativel:
            impedimentos.append("Não atende no dia da retirada.")
        elif inicio_comum >= fim_comum:
            impedimentos.append("Não há intervalo de retirada em comum.")
        else:
            janela_compativel = (
                f"{formatar_horario(inicio_comum)}-"
                f"{formatar_horario(fim_comum)}"
            )
            motivos.append(
                f"Disponível no dia, das "
                f"{formatar_horario(inicio_comum)} às "
                f"{formatar_horario(fim_comum)}."
            )

        resultados.append(
            {
                "id": organizacao["id"],
                "nome": organizacao["nome"],
                "compativel": not impedimentos,
                "motivos": motivos,
                "impedimentos": impedimentos,
                "janela_compativel": janela_compativel,
            }
        )

    return resultados
    