import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class Oferta(BaseModel):
    item: str | None
    quantidade: int | None = Field(ge=1)
    bairro: str | None
    data_retirada: str | None
    horario_retirada: str | None


def main() -> None:
    pasta_projeto = Path(__file__).resolve().parent
    load_dotenv(pasta_projeto / ".env")

    chave = os.getenv("GEMINI_API_KEY")
    modelo = os.getenv("GEMINI_MODEL")

    if not chave or not modelo:
        raise SystemExit(
            "Preencha GEMINI_API_KEY e GEMINI_MODEL no arquivo .env."
        )

    prompt = (
        pasta_projeto / "prompts" / "extracao_v1.md"
    ).read_text(encoding="utf-8")

    exemplos = json.loads(
        (pasta_projeto / "data" / "exemplos.json").read_text(
            encoding="utf-8"
        )
    )

    client = genai.Client(api_key=chave)
    total_aprovados = 0

    for caso in exemplos:
        print(f"\nAnalisando: {caso['id']}", flush=True)

        resposta = client.models.generate_content(
            model=modelo,
            contents=caso["mensagem"],
            config=types.GenerateContentConfig(
                system_instruction=prompt,
                response_mime_type="application/json",
                response_schema=Oferta,
            ),
        )

        if not resposta.text:
            raise SystemExit("A API retornou uma resposta vazia.")

        extraido = Oferta.model_validate_json(resposta.text).model_dump()

        pendencias = [
            campo
            for campo, valor in extraido.items()
            if valor is None
        ]

        passou = extraido == caso["esperado"]
        total_aprovados += int(passou)

        print(json.dumps(extraido, ensure_ascii=False, indent=2))
        print("Pendências:", ", ".join(pendencias) or "nenhuma")
        print("Resultado:", "PASSOU" if passou else "DIVERGIU")

        if not passou:
            print(
                "Esperado:",
                json.dumps(caso["esperado"], ensure_ascii=False),
            )

    print(f"\nResumo: {total_aprovados}/{len(exemplos)} casos passaram.")

    if total_aprovados != len(exemplos):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
    