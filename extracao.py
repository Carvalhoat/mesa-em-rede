import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, ValidationError


class Oferta(BaseModel):
    item: str | None
    quantidade: int | None = Field(ge=1)
    bairro: str | None
    data_retirada: str | None
    horario_retirada: str | None


class ErroExtracao(Exception):
    """Falha de extração com texto seguro para exibir na interface."""


class ConfiguracaoAusente(ErroExtracao):
    pass


class IndisponibilidadeAPI(ErroExtracao):
    pass


class LimiteDeUsoAPI(ErroExtracao):
    pass


class FalhaAutenticacao(ErroExtracao):
    pass


class RespostaInvalida(ErroExtracao):
    pass


def _classificar_erro_api(erro: errors.APIError) -> ErroExtracao:
    codigo = erro.code or 0
    status = (erro.status or "").upper()

    if codigo == 429 or status == "RESOURCE_EXHAUSTED":
        return LimiteDeUsoAPI(
            "O limite de uso da API foi atingido. "
            "Aguarde um pouco e tente analisar novamente. "
            "O texto digitado foi mantido."
        )

    if codigo in (401, 403) or status in {"UNAUTHENTICATED", "PERMISSION_DENIED"}:
        return FalhaAutenticacao(
            "Não foi possível autenticar na API. "
            "Confira a configuração local e tente novamente. "
            "O texto digitado foi mantido."
        )

    if (
        codigo == 408
        or codigo >= 500
        or status in {"UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "ABORTED"}
    ):
        return IndisponibilidadeAPI(
            "A API está indisponível no momento. "
            "Aguarde e tente analisar novamente. "
            "O texto digitado foi mantido."
        )

    return ErroExtracao(
        "Não foi possível concluir a análise. "
        "Tente novamente. O texto digitado foi mantido."
    )


def extrair_oferta(mensagem: str) -> Oferta:
    pasta_projeto = Path(__file__).resolve().parent
    load_dotenv(pasta_projeto / ".env")

    chave = os.getenv("GEMINI_API_KEY")
    modelo = os.getenv("GEMINI_MODEL")

    if not chave or not modelo:
        raise ConfiguracaoAusente(
            "Preencha GEMINI_API_KEY e GEMINI_MODEL no arquivo .env."
        )

    prompt = (pasta_projeto / "prompts" / "extracao_v1.md").read_text(
        encoding="utf-8"
    )

    client = genai.Client(
        api_key=chave,
        http_options=types.HttpOptions(
            timeout=60000,
            retry_options=types.HttpRetryOptions(
                attempts=4,
                initial_delay=5,
                max_delay=30,
                exp_base=2,
            ),
        ),
    )

    try:
        resposta = client.models.generate_content(
            model=modelo,
            contents=mensagem,
            config=types.GenerateContentConfig(
                system_instruction=prompt,
                response_mime_type="application/json",
                response_schema=Oferta,
            ),
        )
    except errors.APIError as erro:
        raise _classificar_erro_api(erro) from None
    except (httpx.HTTPError, TimeoutError, ConnectionError):
        raise IndisponibilidadeAPI(
            "A API está indisponível no momento. "
            "Aguarde e tente analisar novamente. "
            "O texto digitado foi mantido."
        ) from None

    if not resposta.text:
        raise RespostaInvalida(
            "A API retornou uma resposta vazia. "
            "Tente analisar a mensagem outra vez. "
            "O texto digitado foi mantido."
        )

    try:
        return Oferta.model_validate_json(resposta.text)
    except ValidationError:
        raise RespostaInvalida(
            "A API respondeu em um formato que não pôde ser validado. "
            "Tente analisar a mensagem outra vez. "
            "O texto digitado foi mantido."
        ) from None
