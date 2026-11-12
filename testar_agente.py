"""Teste manual com Gemini real. Não grava ofertas nem aciona o n8n."""
import json

from agente_triagem import ErroTriagem, executar_triagem


def main():
    print("Mesa em Rede — triagem experimental com Gemini")
    print("Use dados fictícios. A mensagem será enviada ao Gemini.")
    print("Cada análise começa do zero. Digite sair para encerrar.\n")
    while True:
        mensagem = input("Oferta completa: ").strip()
        if mensagem.casefold() == "sair":
            return
        try:
            resultado = executar_triagem(mensagem)
        except ErroTriagem as erro:
            print(f"\nNão concluído: {erro}\n")
            continue
        print(json.dumps(resultado.para_dict(), ensure_ascii=False, indent=2))
        if resultado.perguntas:
            print("\nPara completar, reescreva a mensagem inteira com os dados solicitados.")
        print("\nPrévia fictícia. Revisão humana obrigatória; nada foi registrado.\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nTriagem encerrada.")
