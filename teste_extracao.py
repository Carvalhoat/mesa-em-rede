import json
from pathlib import Path

from extracao import ErroExtracao, extrair_oferta


def main() -> None:
    pasta_projeto = Path(__file__).resolve().parent
    exemplos = json.loads(
        (pasta_projeto / "data" / "exemplos.json").read_text(encoding="utf-8")
    )
    total_aprovados = 0

    for caso in exemplos:
        print(f"\nAnalisando: {caso['id']}", flush=True)

        try:
            extraido = extrair_oferta(caso["mensagem"]).model_dump()
        except ErroExtracao as erro:
            raise SystemExit(str(erro)) from None

        pendencias = [
            campo for campo, valor in extraido.items() if valor is None
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
