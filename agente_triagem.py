"""Triagem experimental por function calling. Sem ferramentas de escrita."""
from __future__ import annotations

import os
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import httpx
try:
    import httpx2
except ModuleNotFoundError:
    httpx2 = None  # SDKs anteriores utilizam somente httpx.
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from extracao import ErroExtracao, extrair_oferta
from organizacoes import consultar_organizacoes

ERROS_CONEXAO = (httpx.HTTPError, TimeoutError, ConnectionError)
if httpx2 is not None:
    ERROS_CONEXAO += (httpx2.HTTPError,)

PASTA = Path(__file__).resolve().parent
CAMPOS = ("item", "quantidade", "bairro", "data_retirada", "horario_retirada")
PERGUNTAS = {
    "item": "Qual é o alimento? Informe apenas um alimento por oferta.",
    "quantidade": "Qual é a quantidade exata em unidades inteiras positivas?",
    "bairro": "Em qual bairro a retirada será feita?",
    "data_retirada": "Qual é a data completa da retirada (AAAA-MM-DD)?",
    "horario_retirada": "Qual é o intervalo de retirada, com início e fim (HH:MM-HH:MM)?",
}


class ErroTriagem(Exception):
    """Mensagem pública sem detalhes de credenciais ou respostas da API."""


def identificar_pendencias(oferta: dict) -> list[str]:
    pendentes = []
    for campo in CAMPOS:
        valor = oferta.get(campo)
        valido = True
        if campo in ("item", "bairro"):
            valido = isinstance(valor, str) and bool(valor.strip())
        elif campo == "quantidade":
            valido = type(valor) is int and valor > 0
        elif campo == "data_retirada":
            try:
                valido = (isinstance(valor, str)
                          and re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor) is not None
                          and date.fromisoformat(valor).isoformat() == valor)
            except ValueError:
                valido = False
        else:
            valido = (isinstance(valor, str) and re.fullmatch(
                r"(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d", valor
            ) is not None)
            if valido:
                inicio, fim = valor.split("-")
                valido = inicio < fim
        if not valido:
            pendentes.append(campo)
    return pendentes


@dataclass
class ResultadoTriagem:
    status: str
    oferta: dict
    pendencias: list[str]
    perguntas: list[str]
    consulta: list[dict] | None
    ferramentas: list[str]
    exige_revisao_humana: bool = True
    registrado: bool = False

    def para_dict(self) -> dict:
        return asdict(self)


def _declaracao(nome: str, descricao: str):
    return types.FunctionDeclaration(
        name=nome, description=descricao,
        parameters_json_schema={"type": "object", "properties": {}},
    )


def _configuracao(prompt: str, primeira: bool):
    return types.GenerateContentConfig(
        system_instruction=prompt,
        tools=[types.Tool(function_declarations=[
            _declaracao("extrair_oferta", "Extrai a mensagem original e identifica pendências. Sem argumentos."),
            _declaracao("consultar_organizacoes", "Consulta somente a oferta extraída, quando não há pendências. Prévia fictícia, sem registro."),
        ])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
            mode="ANY" if primeira else "AUTO",
            allowed_function_names=["extrair_oferta"] if primeira else None,
        )),
    )


def executar_triagem(mensagem: str, *, client=None, modelo: str | None = None,
                     extrator=None, consultor=None) -> ResultadoTriagem:
    """Uma mensagem completa por execução; dependências injetáveis para testes.

    A fonte das ferramentas é o estado Python. O modelo não pode fornecer uma
    oferta alternativa nem confirmar uma revisão. Texto livre do modelo não é
    usado como resultado oficial. No máximo 4 chamadas ao modelo/4 ferramentas.
    """
    if not isinstance(mensagem, str) or not mensagem.strip():
        raise ErroTriagem("Digite a mensagem da oferta.")
    if len(mensagem) > 8000:
        raise ErroTriagem("Use uma mensagem de até 8.000 caracteres.")
    extrator = extrator or extrair_oferta
    consultor = consultor or consultar_organizacoes
    load_dotenv(PASTA / ".env")
    modelo = modelo or os.getenv("GEMINI_MODEL")
    if not modelo:
        raise ErroTriagem("Preencha GEMINI_MODEL no arquivo .env.")
    proprio = client is None
    if proprio:
        chave = os.getenv("GEMINI_API_KEY")
        if not chave:
            raise ErroTriagem("Preencha GEMINI_API_KEY no arquivo .env.")
        client = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=60000))
    oferta = None
    consulta = None
    ferramentas = []
    historico = [types.Content(role="user", parts=[types.Part.from_text(text=mensagem)])]
    try:
        prompt = (PASTA / "prompts" / "agente_v1.md").read_text(encoding="utf-8")
        for rodada in range(4):
            resposta = client.models.generate_content(
                model=modelo, contents=historico,
                config=_configuracao(prompt, primeira=rodada == 0),
            )
            if not resposta.candidates or not resposta.candidates[0].content:
                raise ErroTriagem("O agente não retornou uma resposta utilizável. Tente novamente.")
            conteudo = resposta.candidates[0].content
            chamadas = [parte.function_call for parte in (conteudo.parts or [])
                        if parte.function_call is not None]
            if not chamadas:
                if oferta is None:
                    raise ErroTriagem("O agente não extraiu a oferta. Tente novamente.")
                pendencias = identificar_pendencias(oferta)
                if not pendencias and consulta is None:
                    raise ErroTriagem("O agente encerrou sem consultar as organizações. Tente novamente.")
                return ResultadoTriagem(
                    status="aguardando_dados" if pendencias else "pronta_para_revisao",
                    oferta=deepcopy(oferta), pendencias=pendencias,
                    perguntas=[PERGUNTAS[c] for c in pendencias],
                    consulta=deepcopy(consulta), ferramentas=ferramentas.copy(),
                )
            if len(ferramentas) + len(chamadas) > 4:
                raise ErroTriagem("O agente atingiu o limite de ferramentas. Tente novamente.")
            # Preserva integralmente o conteúdo, incluindo assinaturas do modelo.
            historico.append(conteudo)
            retornos = []
            for chamada in chamadas:
                nome = chamada.name
                if nome not in {"extrair_oferta", "consultar_organizacoes"}:
                    raise ErroTriagem("O agente solicitou uma ferramenta não permitida.")
                if chamada.args:
                    raise ErroTriagem("O agente enviou argumentos não permitidos. Tente novamente.")
                ferramentas.append(nome)
                if nome == "extrair_oferta":
                    if oferta is None:
                        extraida = extrator(mensagem)
                        dados = extraida.model_dump() if hasattr(extraida, "model_dump") else extraida
                        if not isinstance(dados, dict):
                            raise ErroTriagem("Não foi possível validar a oferta extraída.")
                        oferta = {campo: deepcopy(dados.get(campo)) for campo in CAMPOS}
                    pendencias = identificar_pendencias(oferta)
                    retorno = {"oferta": oferta, "pendencias": pendencias,
                               "perguntas": [PERGUNTAS[c] for c in pendencias]}
                elif oferta is None:
                    retorno = {"erro": "Extraia a oferta antes de consultar."}
                elif identificar_pendencias(oferta):
                    retorno = {"erro": "Há pendências. Peça os dados e encerre.",
                               "pendencias": identificar_pendencias(oferta)}
                else:
                    if consulta is None:
                        consulta = consultor(deepcopy(oferta))
                    retorno = {"previa_ficticia": True, "resultados": consulta,
                               "exige_revisao_humana": True, "registrado": False}
                retorno = deepcopy(retorno)
                resposta_funcao = types.FunctionResponse(
                    name=nome, response=retorno, id=chamada.id,
                )
                retornos.append(types.Part(function_response=resposta_funcao))
            # Gemini recebe function_response em um Content de papel user.
            historico.append(types.Content(role="user", parts=retornos))
        raise ErroTriagem("O agente atingiu o limite de etapas. Tente novamente.")
    except ErroExtracao as erro:
        raise ErroTriagem(str(erro)) from None
    except errors.APIError as erro:
        # Exibe apenas o código numérico; nunca imprime corpo, headers ou chave.
        codigo = erro.code if type(erro.code) is int else None
        orientacoes = {
            400: "A API recusou os parâmetros da chamada ou um recurso solicitado pelo agente.",
            401: "A autenticação foi recusada.",
            403: "O acesso foi negado. Verifique a chave e as permissões do projeto.",
            404: "O modelo ou recurso solicitado não foi encontrado.",
            429: "O limite de uso ou a cota da API foi atingido.",
            500: "O Gemini apresentou uma falha interna.",
            503: "O Gemini está indisponível no momento.",
            504: "O Gemini excedeu o tempo de resposta.",
        }
        identificador = f"HTTP {codigo}" if codigo is not None else "código não informado"
        orientacao = orientacoes.get(codigo, "A API não concluiu a solicitação.")
        raise ErroTriagem(f"Gemini — {identificador}. {orientacao}") from None
    except ERROS_CONEXAO:
        raise ErroTriagem("A conexão com o Gemini falhou. Aguarde e tente novamente.") from None
    except (OSError, ValueError, TypeError, AttributeError):
        raise ErroTriagem("Não foi possível concluir a triagem. Confira os arquivos locais e tente novamente.") from None
    finally:
        if proprio:
            client.close()
