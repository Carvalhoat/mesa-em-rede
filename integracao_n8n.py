"""Envio explícito de ofertas fictícias revisadas ao webhook autenticado."""

import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class ConfiguracaoN8N:
    url: str
    token: str


class ErroRegistro(Exception):
    def __init__(self, mensagem: str, *, incerto: bool = False):
        super().__init__(mensagem)
        self.incerto = incerto


def ler_configuracao(pasta: Path) -> ConfiguracaoN8N:
    """Lê o arquivo explicitamente, sem imprimir segredos nem alterar o ambiente."""
    arquivo = pasta / ".env"
    valores = dotenv_values(arquivo, interpolate=False) if arquivo.is_file() else {}
    url = str(valores.get("N8N_WEBHOOK_URL") or os.getenv("N8N_WEBHOOK_URL", "")).strip()
    token = str(valores.get("N8N_WEBHOOK_TOKEN") or os.getenv("N8N_WEBHOOK_TOKEN", "")).strip()
    return ConfiguracaoN8N(url, token)


def validar_configuracao(config: ConfiguracaoN8N) -> None:
    if not config.url or not config.token:
        raise ErroRegistro("Configure N8N_WEBHOOK_URL e N8N_WEBHOOK_TOKEN no .env para habilitar o registro.")
    try:
        url = urllib.parse.urlsplit(config.url)
        porta = url.port
    except ValueError:
        raise ErroRegistro("Confira o endereço configurado para o webhook.") from None
    if (
        url.scheme != "https" or not url.hostname or not url.path.strip("/")
        or url.username or url.password or url.query or url.fragment
        or porta not in (None, 443)
        or any(c.isspace() for c in config.url)
    ):
        raise ErroRegistro("Use a URL HTTPS do webhook, sem senha, parâmetros ou fragmentos no endereço.")
    if any(c in config.token for c in "\r\n"):
        raise ErroRegistro("Confira o token do webhook: ele deve ocupar uma única linha.")


def montar_payload(oferta_id: str, oferta: dict, consulta: dict | None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", oferta_id):
        raise ErroRegistro("Identificador da oferta inválido.")
    for campo in ("item", "bairro"):
        if not isinstance(oferta.get(campo), str) or not oferta[campo].strip() or len(oferta[campo].strip()) > 150:
            raise ErroRegistro("Item e bairro precisam estar preenchidos com até 150 caracteres.")
    quantidade = oferta.get("quantidade")
    if type(quantidade) is not int or not 0 < quantidade <= 9007199254740991:
        raise ErroRegistro("Quantidade precisa ser um número inteiro positivo válido para a integração.")
    try:
        data = oferta["data_retirada"]
        if not isinstance(data, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
            raise ValueError
        if date.fromisoformat(data) < date(1900, 3, 1):
            raise ValueError
    except (KeyError, ValueError, TypeError):
        raise ErroRegistro("Confira a data de retirada antes de registrar.") from None
    horario = oferta.get("horario_retirada")
    if not isinstance(horario, str) or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d", horario):
        raise ErroRegistro("Confira o intervalo de retirada antes de registrar.")
    inicio, fim = horario.split("-")
    if fim <= inicio:
        raise ErroRegistro("O fim da retirada precisa ser posterior ao início.")

    resultado_consulta = {"status": "nao_consultada"}
    if consulta is not None:
        if consulta.get("oferta") != oferta:
            raise ErroRegistro("Consulte novamente: o resultado anterior não corresponde à oferta revisada.")
        resultados = consulta.get("resultados")
        if not isinstance(resultados, list):
            raise ErroRegistro("Resultado da consulta inválido. Consulte novamente.")
        ids = []
        conhecidos = {"org_demo_001", "org_demo_002", "org_demo_003"}
        for resultado in resultados:
            if not isinstance(resultado, dict) or type(resultado.get("compativel")) is not bool:
                raise ErroRegistro("Resultado da consulta inválido. Consulte novamente.")
            if resultado["compativel"]:
                ident = resultado.get("id")
                if not isinstance(ident, str) or ident not in conhecidos or ident in ids:
                    raise ErroRegistro("Confira os identificadores do cadastro de demonstração.")
                ids.append(ident)
        instante = consulta.get("realizada_em")
        try:
            momento = datetime.fromisoformat(instante)
            if momento.tzinfo is None or momento.utcoffset() is None:
                raise ValueError
        except (TypeError, ValueError):
            raise ErroRegistro("Consulte novamente para atualizar a data do resultado.") from None
        resultado_consulta = {
            "status": "com_compativeis" if ids else "sem_compativeis",
            "organizacoes_compativeis_ids": ids,
            "realizada_em": instante,
        }
    return {
        "oferta_id": oferta_id,
        "restaurante_id": "rest_demo_001",
        "revisao_confirmada": True,
        "dados_ficticios": True,
        "item": oferta["item"].strip(),
        "quantidade": quantidade,
        "unidade": "unidades",
        "bairro": oferta["bairro"].strip(),
        "data_retirada": data,
        "horario_retirada": horario,
        "consulta": resultado_consulta,
    }


class _SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Não encaminhar o token para outro endereço por redirecionamento.
        return None


def enviar_oferta(payload: dict, config: ConfiguracaoN8N) -> None:
    validar_configuracao(config)
    requisicao = urllib.request.Request(
        config.url,
        data=json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Mesa-Token": config.token},
        method="POST",
    )
    cliente = urllib.request.build_opener(_SemRedirecionamento())
    try:
        with cliente.open(requisicao, timeout=60) as resposta:
            corpo = resposta.read(65537)
            status_http = resposta.status
    except urllib.error.HTTPError as erro:
        codigo = erro.code
        erro.close()
        if codigo == 422:
            raise ErroRegistro("O n8n recusou a oferta. Confira os campos revisados e a configuração do fluxo.") from None
        if codigo in (401, 403):
            raise ErroRegistro("O n8n recusou a autenticação. Confira o token no .env e na credencial Header Auth.") from None
        if codigo == 404:
            raise ErroRegistro("Webhook indisponível. Na URL de teste, clique em Execute workflow antes de registrar. Na URL de produção, confira se o fluxo foi publicado.") from None
        if 300 <= codigo < 400:
            raise ErroRegistro("O webhook tentou redirecionar a chamada. Confira o endereço configurado.") from None
        raise ErroRegistro("O n8n não confirmou o registro. Confira a execução e a planilha antes de tentar novamente.", incerto=True) from None
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
        raise ErroRegistro("A conexão terminou sem confirmação. Confira a execução no n8n e a planilha. Uma nova tentativa usará o mesmo identificador.", incerto=True) from None
    try:
        if len(corpo) > 65536 or status_http != 200:
            raise ValueError
        retorno = json.loads(corpo.decode("utf-8"))
        if not isinstance(retorno, dict) or retorno.get("status") != "registro_ok" or retorno.get("registrado") is not True:
            raise ValueError
    except (ValueError, UnicodeError):
        raise ErroRegistro("A resposta não confirmou a gravação. Confira o último bloco do n8n e a planilha antes de reenviar.", incerto=True) from None
