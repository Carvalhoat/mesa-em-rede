# Uso de IA no Mesa em Rede

## Identidade visual

Usei um Gem personalizado no Gemini para explorar e revisar
propostas de identidade visual.

Também usei o ChatGPT para estruturar o briefing, avaliar as
propostas e orientar a organização inicial do projeto.

Explorei uma composição com dois pratos e as letras M/R.
Escolhi a proposta B2, com três pontos e duas conexões,
para representar restaurante, triagem humana e organização receptora.

A escolha final da marca foi feita por mim.

## Documentação

Usei o ChatGPT para preparar o conteúdo inicial do README
e orientar sua edição no Cursor.

## Próxima aplicação planejada

Usar a API do Gemini para extrair dados de mensagens fictícias
e comparar as respostas com um gabarito definido manualmente.


## Primeiro teste de extração

- Data: 10/11/2026.
- Modelo utilizado: gemini-3.5-flash-lite.
- Prompt: prompts/extracao_v1.md.
- Dados fictícios: data/exemplos.json.
- Execução: teste_extracao.py.
- Resultado: 2 de 2 casos passaram.

Na mensagem completa, os cinco campos corresponderam ao gabarito.
Na mensagem sem horário, o modelo retornou null nesse campo
e o código identificou horario_retirada como pendência.

Durante a execução, ocorreu um erro 503 de indisponibilidade
temporária. Uma execução posterior concluiu os dois casos.

Este teste verifica o funcionamento inicial. A avaliação com
mensagens variadas será realizada na próxima etapa.