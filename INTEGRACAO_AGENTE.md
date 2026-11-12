# Agente de triagem na interface

O botão **Analisar mensagem** chama `executar_triagem`, em lugar de chamar
diretamente o extrator. O agente já deve estar instalado e validado na branch
`agente-triagem`.

## Instalação

Copie os três arquivos deste pacote para a raiz do projeto:

- `app.py`: substitui a interface anterior.
- `teste_interface_agente.py`: novo teste de fluxos da interface.
- `INTEGRACAO_AGENTE.md`: este documento.

Mantenha os módulos existentes, o prompt do agente, os personagens e a configuração.
Não há alteração de dependências, credenciais, workflow n8n ou estrutura da planilha.

## Comportamento

1. A mensagem é analisada pelo agente. Dados ausentes aparecem como perguntas.
2. Com os cinco campos válidos, o agente pode consultar o cadastro fictício e
   guardar uma prévia vinculada à oferta extraída e à mensagem analisada.
3. O usuário pode completar ou corrigir os campos da revisão sem chamar o Gemini
   novamente. Perguntas da triagem descrevem a mensagem originalmente analisada.
4. A análise não confirma a revisão. O resumo, a consulta e o registro só ficam
   disponíveis após a confirmação humana de uma revisão completa e válida.
5. A prévia do agente é aproveitada somente se os dados confirmados forem iguais
   aos dados extraídos. Uma revisão diferente exige uma nova consulta para obter
   um resultado de compatibilidade atualizado.
6. **Consultar organizações** continua disponível após a revisão. Essa consulta
   usa as regras locais e não chama o Gemini.
7. Uma revisão completa também pode ser registrada sem consulta, como antes.
   Nesse caso, o estado enviado é `nao_consultada`, nunca o resultado de outra oferta.
8. Só **Registrar oferta** envia dados ao n8n. O registro exige clique explícito e
   mantém a proteção existente contra repetição da mesma versão nesta sessão.

A prévia fica separada do resultado confirmado. Mudanças nos campos ou na mensagem
bloqueiam o uso de uma consulta antiga para registro. Falhas da análise limpam os
resultados anteriores e preservam o texto digitado.

A mensagem e os resultados fictícios das ferramentas retornam ao Gemini durante
a triagem. O aviso da interface informa esse fluxo. O registro envia somente o
payload revisado, conforme a integração existente; não envia a mensagem original.

## Testes locais

Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -m unittest teste_agente_triagem.py teste_integracao_n8n.py teste_interface_agente.py -v
```

Esperado: **41 testes**, `OK`. São 21 do agente, 14 do registro e 6 da interface.
As chamadas Gemini e n8n são simuladas. Os testes da interface usam o AppTest do
Streamlit e o cadastro fictício local. Não enviam ofertas, não consomem a API e
não gravam na planilha. O Streamlit pode emitir avisos de `ScriptRunContext`
durante esses testes; confira o resultado final da suíte.

## Conferência manual da interface

Execute:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Se o aplicativo estiver aberto no terminal, pare com Ctrl+C antes de reiniciar.

Use esta mensagem fictícia para o primeiro teste:

> Temos 25 unidades de pão na Vila Mariana, para retirada em 12/11/2026, das 9h às 10h.

Clique em **Analisar mensagem**. Verifique os campos preenchidos e o bloco de
triagem. Antes de confirmar a revisão, não deve aparecer o botão de registro.
Clique em **Confirmar revisão**: o resultado deve indicar uma organização
compatível, a Cozinha Comunitária A — Fictícia. Esse fluxo usa a API do Gemini.

Para testar correções depois, altere a quantidade para 60. A consulta anterior
deve desaparecer. Confirme novamente e clique em **Consultar organizações**:
o cadastro não deverá ter organização compatível com essa oferta.

Uma mensagem sem quantidade deve gerar uma pergunta. Preencha a quantidade no
formulário, confirme a revisão e consulte. Preencher o formulário não chama o
Gemini novamente.

O registro continua sendo uma ação separada e escreve na planilha somente se
o usuário clicar em **Registrar oferta**.

## Validação deste pacote

41 testes locais aprovados. O agente isolado também já foi validado pelo usuário
com Gemini real nos caminhos de oferta completa e quantidade ausente.
A nova interface ainda precisa de conferência manual no computador do usuário.
