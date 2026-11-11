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

## Aplicação da IA na extração

Integrei a API do Gemini para extrair dados de mensagens fictícias
e comparei as respostas com um gabarito definido manualmente.
Essa etapa está implementada na aplicação.


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


## Ampliação do teste de extração

- Data: 10/11/2026.
- Modelo: gemini-3.5-flash-lite.
- Prompt: prompts/extracao_v1.md.
- Resultado observado: 6 de 6 casos passaram em uma execução completa.

Foram verificados os seguintes cenários:
- Mensagem completa.
- Horário ausente.
- Quantidade aproximada.
- Data relativa.
- Horário com apenas um limite.
- Quantidades contraditórias.

Configurei tentativas automáticas com espera crescente e limite
de quatro tentativas por chamada para lidar com falhas temporárias.

Os resultados verificam as regras do prompt nesses seis exemplos
sintéticos. A avaliação com mensagens adicionais continua pendente.


## Interface de triagem em Streamlit

Usei o agente do Cursor para implementar a interface e compartilhar
a lógica de extração entre a aplicação e o script de teste.

Revisei o funcionamento executando testes manuais no navegador.

### Verificações realizadas

- Extração de uma mensagem completa.
- Correção manual da quantidade e confirmação do resumo.
- Invalidação da confirmação quando os campos da revisão mudam.
- Identificação de horário ausente e preenchimento manual.
- Bloqueio de horário inválido.
- Bloqueio da confirmação quando a mensagem original muda.

Após a reorganização do código, os seis casos sintéticos
de extração passaram novamente.

Na versão inicial, a aplicação funcionava localmente e os dados revisados
permaneciam apenas na sessão. O registro persistente foi acrescentado
na etapa de integração descrita ao final deste documento.
A mensagem original é enviada à API do Gemini para análise.

Na revisão do código, identifiquei e corrigi uma falha na validação
de caracteres como ² no campo de quantidade. O teste manual confirmou
a rejeição com uma mensagem de orientação, sem interromper a tela.


## Evolução visual com personagens

Desenvolvi os personagens com apoio do ChatGPT, Gemini e Recraft.
Os SVGs foram ajustados e os PNGs exportados com transparência.

A interface recebeu cabeçalho transparente, etapas visíveis,
botão para carregar um exemplo e ilustrações associadas à revisão
e à confirmação da oferta.

Verifiquei localmente a análise e a confirmação de uma oferta
completa na nova interface.

## Consulta de organizações receptoras fictícias

Implementei a consulta de organizações com apoio do ChatGPT na
preparação do código e na orientação dos testes. Revisei os resultados
na interface e integrei a etapa à branch principal do projeto.

O cadastro de demonstração contém três organizações fictícias.
A consulta utiliza regras determinísticas em Python para verificar
alimento aceito, bairro atendido, capacidade por oferta, dia da semana
e sobreposição de horários. Não utiliza um modelo de IA para decidir
a compatibilidade.

A aplicação apresenta os motivos de cada classificação e a janela de
horário em comum quando há compatibilidade. A sugestão depende de
avaliação humana e não envia mensagens, reserva capacidade ou confirma
a doação.

### Verificações realizadas

- O script `teste_organizacoes.py` verificou três de três classificações
  corretas para a oferta inicial de 25 unidades de pão na Vila Mariana.
- Com 60 unidades na Vila Mariana, nenhuma organização foi compatível.
- Com 60 unidades em Moema, das 09:00 às 10:00, apenas o Centro
  Comunitário C foi compatível.
- Com 60 unidades em Moema, das 11:00 às 12:00, nenhuma organização
  foi compatível: o término às 11:00 não cria um intervalo compartilhado.
- Foram verificados a necessidade de reconfirmar a revisão e o descarte
  do resultado anterior após alterações nos dados.

Os cenários adicionais ao script inicial foram testados manualmente
na interface. Eles não representam uma suíte automatizada completa.

## Divisão de responsabilidades

| Parte do fluxo | Responsabilidade |
| --- | --- |
| Extração da mensagem | Gemini, seguindo o prompt do projeto |
| Validação dos campos e controle de estado | Código Python |
| Correção e confirmação dos dados | Pessoa responsável pela triagem |
| Consulta de compatibilidade | Regras em Python e cadastro fictício |
| Aceite e condições reais de uma doação | Não implementados no protótipo |

Usei IA também como apoio à implementação, à revisão de código e à
atualização da documentação. As decisões de escopo, a aprovação da
identidade visual e a conferência dos resultados foram realizadas por mim.

## Limites da avaliação e tratamento dos dados

Os testes utilizaram dados sintéticos. O resultado de seis de seis
casos de extração não mede a precisão do modelo em mensagens reais
nem garante o mesmo resultado em execuções futuras.

O protótipo não verifica condições sanitárias, validade dos alimentos
ou condições de transporte. A capacidade é considerada por oferta,
sem controle de reservas ou soma de ofertas simultâneas.

As mensagens analisadas são transmitidas à API do Gemini. A revisão e a consulta permanecem na sessão até o registro explícito.
Na versão com integração, clicar em Registrar oferta envia os campos
revisados e a consulta atual ao n8n, para gravação no Google Sheets.
A mensagem original não faz parte desse registro. A chave da API é configurada localmente no
arquivo `.env`, que não deve ser publicado.

## Próximas etapas

Ampliar a avaliação com novas mensagens, documentar resultados e
preparar a demonstração online. O registro no Sheets pelo n8n foi acrescentado ao protótipo.
A verificação final pela interface e a publicação online continuam pendentes.


## Automação com n8n e registro no Sheets

Configurei um workflow no n8n Cloud com apoio do ChatGPT, usando:

1. Webhook POST autenticado por header.
2. Validação dos dados revisados em JavaScript.
3. Busca por `oferta_id` na planilha.
4. Preparação do registro, preservando a data original.
5. Inclusão ou atualização da linha no Sheets em modo RAW.
6. Resposta de confirmação ou rejeição com HTTP 422.

Testei o workflow com ofertas fictícias pelo terminal. Confirmei a
gravação de uma oferta nova, o reenvio sequencial sem duplicar a linha,
a preservação do primeiro horário e o bloqueio da quantidade zero
antes do acesso ao Sheets.

A automação é um fluxo determinístico. O n8n não utiliza IA para gravar
a planilha nem recalcula o resultado da consulta recebido da aplicação.
A extração por Gemini continua sendo uma etapa separada.

Usei apoio do ChatGPT na implementação do botão Registrar oferta e do
módulo `integracao_n8n.py`. A implementação passou por 14 testes locais
do módulo e verificações da interface com extração, consulta e webhook
simulados. A gravação do botão contra o workflow real ainda precisa
ser conferida no ambiente de demonstração.

O envio exige ação explícita. O aplicativo mantém o mesmo ID nos
reenvios da sessão e não repete chamadas automaticamente após falhas.
Os testes de duplicação foram sequenciais; o Sheets ainda não oferece
controle transacional ou garantia de unicidade para chamadas concorrentes.

A planilha não contém dados de beneficiários, a mensagem original ou
o token do webhook. As credenciais ficam no n8n e no `.env` local.
O histórico de execuções do n8n pode incluir o header de autenticação,
portanto não deve ser publicado ou compartilhado sem revisão.

O arquivo `workflows/registrar-oferta-modelo.json` é uma versão pública
do fluxo sem credenciais, dados fixados ou identificadores da conta e
da planilha. Quem importar o modelo precisará selecionar suas próprias
credenciais e configurar o documento de destino.
