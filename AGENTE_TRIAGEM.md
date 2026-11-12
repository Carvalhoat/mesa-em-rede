# Agente de triagem — etapa 1

Módulo experimental separado da interface Streamlit. O Gemini solicita ferramentas
por function calling; o Python confere os pedidos e executa somente duas ferramentas
permitidas: `extrair_oferta` e `consultar_organizacoes`.

A extração usa o módulo e o prompt já existentes. A consulta usa o mesmo cadastro
fictício e as mesmas regras determinísticas do aplicativo. O agente não tem
ferramenta para registrar, enviar mensagens, reservar capacidade ou confirmar doação.

## Instalação

Na branch `agente-triagem`, copie os arquivos deste pacote para a raiz do projeto:

- `agente_triagem.py`
- `teste_agente_triagem.py`
- `testar_agente.py`
- `AGENTE_TRIAGEM.md`
- `prompts/agente_v1.md` (dentro da pasta `prompts` existente)

Mantenha `extracao.py`, `organizacoes.py`, `data/organizacoes.json`,
`prompts/extracao_v1.md`, `app.py`, `.env` e os demais arquivos existentes.
O pacote não contém cópias desses arquivos, chaves ou dados de acesso.
Usa as dependências já listadas no `requirements.txt` do projeto.

## Verificação local sem chamadas à API

Abra o PowerShell na raiz do projeto, onde estão `app.py` e `.venv`:

```powershell
.\.venv\Scripts\python.exe -m unittest teste_agente_triagem.py -v
```

São 21 testes (dois específicos de httpx2 são ignorados se ele não estiver instalado).
As respostas do modelo e a extração são simuladas; a consulta
de compatibilidade usa também o módulo e o cadastro fictício reais fornecidos.
Não precisa de chave válida, não consome Gemini e não registra ofertas.

## Teste manual com Gemini

Somente depois dos testes locais:

```powershell
.\.venv\Scripts\python.exe testar_agente.py
```

Usa `GEMINI_API_KEY` e `GEMINI_MODEL` do `.env` atual. Não publique o `.env`.
O modelo configurado precisa oferecer function calling. Se a API recusar o modelo
ou houver indisponibilidade/cota, a validação real continua pendente.
Não é necessário ativar o workflow do n8n para este teste.

Primeira mensagem sugerida (fictícia):

> Temos 25 unidades de pão na Vila Mariana, para retirada em 12/11/2026, das 9h às 10h.

Resultado esperado: `pronta_para_revisao`, sem pendências, uma organização
compatível (`org_demo_001`), revisão humana obrigatória e `registrado: false`.
O campo `ferramentas` deve mostrar `extrair_oferta` e `consultar_organizacoes`.

Depois, teste uma oferta incompleta:

> Temos pão na Vila Mariana para retirada em 12/11/2026, das 9h às 10h.

Resultado esperado: `aguardando_dados`, pendência de quantidade, uma pergunta
sobre unidades exatas e `consulta: null`. Não deve consultar com dados pendentes.

Digite `sair` para encerrar.

## Limites desta etapa

- Uma mensagem completa por análise; não há memória de conversa. Para corrigir
  pendências, reescreva a oferta completa na próxima entrada.
- As perguntas e os dados finais são montados pelo Python a partir das ferramentas.
  O texto livre do modelo não pode confirmar registro nem criar resultados oficiais.
- Campos ausentes, quantidade inválida, data inválida ou intervalo inválido impedem
  a consulta. Datas relativas continuam pendentes conforme o prompt de extração.
- No máximo quatro chamadas de orquestração e quatro pedidos de ferramentas por
  execução. Extração e consulta repetidas usam cache dentro da mesma execução.
- A extração reutiliza sua própria chamada Gemini e política de tentativas; portanto
  uma análise do agente pode consumir mais chamadas que a análise atual do app.
- Apenas o texto da oferta é enviado ao extrator. Os dados extraídos e os resultados
  fictícios das ferramentas retornam ao Gemini para a orquestração. Não use dados reais
  de beneficiários nos testes. Não há gravação local de conversas neste módulo.
- A consulta é uma prévia. O resultado não confirma revisão, segurança do alimento,
  disponibilidade real, contato com organizações ou doação.
- O aplicativo e o fluxo de registro existentes continuam separados deste módulo.
  A integração visual será uma etapa posterior, após validar o teste real.

## Validação realizada

21 testes locais aprovados com respostas simuladas, incluindo bloqueio de ferramentas
de escrita, troca de argumentos, consulta com pendências, loop, falha de conexão,
preservação de assinatura/ID das chamadas e isolamento entre análises.
Nenhuma chamada real ao Gemini foi feita durante a preparação deste pacote.

### Correção de conexão

Os resultados de ferramentas são devolvidos com papel `user` e partes
`function_response`, preservando nome, ID e conteúdo da chamada original.
Um teste verifica os papéis aceitos em todo o ciclo de extração e consulta.

O tratamento agora cobre `httpx` e `httpx2`, incluindo uma falha de conexão dentro
do extrator reutilizado. Um erro de rede mostra uma mensagem curta e mantém o
programa aberto para outra tentativa, em vez de encerrar com traceback.
Isso não corrige a origem da interrupção de rede e não confirma que o Gemini
respondeu. Não há desativação de verificação TLS ou alteração de credenciais.

Referência técnica: SDK oficial Google Gen AI Python,
https://github.com/googleapis/python-genai#manually-declare-and-invoke-a-function-for-function-calling
