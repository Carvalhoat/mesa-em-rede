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
mensagens variadas foi ampliada na etapa descrita a seguir.


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

Para a capa do README, usei geração de imagem no ChatGPT com referências da
marca e dos personagens aprovados. Defini a composição com logo, nome, slogan
e quatro elementos: Pratinho acenando, Pratinho pesquisando, caminhão com alimentos
e Pratinho segurando uma refeição com cenoura, brócolis e arroz. Conferi a
simulação e aprovei sua utilização na documentação do repositório.

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
| Solicitação de ferramentas durante a triagem | Agente Gemini, com execução limitada pelo Python |
| Validação dos campos e controle de estado | Código Python |
| Correção e confirmação dos dados | Pessoa responsável pela triagem |
| Consulta de compatibilidade | Regras em Python e cadastro fictício |
| Persistência da oferta revisada | Clique humano, workflow n8n e Google Sheets |
| Cálculo de indicadores | Código Python sobre CSV importado, sem inferência de IA |
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

As mensagens analisadas, os dados extraídos e os resultados fictícios das
ferramentas são transmitidos à API do Gemini durante a triagem do agente.
A revisão e a consulta permanecem na sessão até o registro explícito.
Na versão com integração, clicar em Registrar oferta envia os campos
revisados e a consulta atual ao n8n, para gravação no Google Sheets.
A mensagem original não faz parte desse registro. As credenciais são configuradas
no `.env` local ou na área Secrets do Streamlit Community Cloud, fora do repositório.
O CSV importado pelo painel não é enviado ao Gemini nem ao n8n.

## Próximas etapas

Ampliar a avaliação com novas mensagens e preparar a demonstração em vídeo.
A publicação online e a verificação do registro pela interface foram concluídas
nas etapas descritas a seguir. A atualização automática dos indicadores e o
aperfeiçoamento do controle de acesso e da persistência ficam para evolução futura.


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
simulados. Posteriormente, conferi o botão contra o workflow real tanto
localmente quanto na versão publicada, verificando a linha gravada na planilha.

O envio exige ação explícita. O aplicativo mantém o mesmo ID nos
reenvios da sessão e não repete chamadas automaticamente após falhas.
Os testes de duplicação foram sequenciais; o Sheets ainda não oferece
controle transacional ou garantia de unicidade para chamadas concorrentes.

A planilha não contém dados de beneficiários, a mensagem original ou
o token do webhook. As credenciais ficam no n8n, no `.env` local e na área
Secrets da hospedagem, conforme a responsabilidade de cada serviço.
O histórico de execuções do n8n pode incluir o header de autenticação,
portanto não deve ser publicado ou compartilhado sem revisão.

O arquivo `workflows/registrar-oferta-modelo.json` é uma versão pública
do fluxo sem credenciais, dados fixados ou identificadores da conta e
da planilha. Quem importar o modelo precisará selecionar suas próprias
credenciais e configurar o documento de destino.

## Agente de triagem com ferramentas

Com apoio do ChatGPT, acrescentei `agente_triagem.py` e o prompt
`prompts/agente_v1.md`, usando function calling do SDK Google Gen AI.
O agente solicita extração e consulta, mas o código controla as ferramentas
permitidas, os dados de entrada, as pendências e os limites de execução.

A extração reutiliza o módulo existente. A consulta continua sendo determinística;
o modelo não inventa a capacidade do cadastro nem decide a compatibilidade
por texto livre. O resultado oficial é montado pelo Python a partir das ferramentas.
O agente não possui ferramenta de escrita, contato ou confirmação de doação.

Primeiro testei o módulo separado da interface, com respostas simuladas.
Nos testes reais, uma conexão interrompida revelou a necessidade de tratar
exceções de `httpx2` além de `httpx`. Outra falha retornou HTTP 400: o papel
`tool` no histórico não era aceito. Com apoio do ChatGPT, corrigi o retorno
para `user`, mantendo `function_response`, identificadores e conteúdo das chamadas.
Esses casos receberam verificações de regressão.

Em 12/11/2026, conferi dois caminhos com o Gemini real pelo terminal:

- Oferta completa de 25 unidades de pão na Vila Mariana: os cinco campos foram
  extraídos, as duas ferramentas foram chamadas e uma organização foi compatível.
- Oferta sem quantidade: o campo permaneceu `null`, foi feita uma pergunta e
  a consulta de organizações não foi executada.

As perguntas finais são construídas pelo Python a partir das pendências.
Cada análise considera uma mensagem completa; não implementei memória conversacional.
As correções também podem ser feitas diretamente no formulário da interface.

## Integração do agente à interface

Usei o ChatGPT na preparação do código e dos testes, e conferi o fluxo no
navegador. A prévia do agente fica separada da revisão confirmada. Ela só é
aproveitada se os dados confirmados corresponderem à mesma oferta.

Na conferência manual, alterei a quantidade de 25 para 60 unidades. Confirmei
a revisão, refiz a consulta local e obtive nenhuma organização compatível.
Registrei essa versão pelo n8n e confirmei na planilha a quantidade corrigida,
o status `sem_compativeis` e o total zero.

As alterações foram organizadas em branch e pull request e integradas à `main`
depois dos testes. Não usei o resultado do agente como confirmação humana.

## Indicadores e rodapé

Implementei o painel com apoio do ChatGPT para ler um CSV exportado da aba
`ofertas`, validar registros e apresentar filtros e gráficos. Os indicadores
são calculados em Python, sem inferência do Gemini.

A taxa considera somente consultas concluídas. Ofertas não consultadas ou com
erro não entram no denominador; sem consultas concluídas, a taxa fica sem valor.
IDs duplicados e dados inconsistentes bloqueiam o cálculo. O exemplo fictício
é separado dos dados importados e não é mesclado ao CSV.

Conferi o exemplo na interface: cinco ofertas no recorte padrão e taxa de 66,7%.
Depois importei o CSV da demonstração: cinco ofertas, três com compatibilidade,
duas sem e taxa de 60%. Esses valores descrevem aquele arquivo naquele momento,
não uma medida de impacto social nem um total permanente da aplicação.

Optei por manter os personagens estáticos e incluir uma imagem do fluxo no rodapé,
após conferir tamanho e espaçamento no navegador. A imagem é ilustrativa e não
indica que uma doação foi realizada.

## Publicação e validação online

Em 12/11/2026, publiquei a aplicação no Streamlit Community Cloud, a partir
da branch `main`, usando Python 3.12. Configurei as credenciais na área Secrets.
O ChatGPT orientou as etapas de publicação; a autorização das contas e a inserção
dos segredos foram feitas por mim.

Demonstração: https://mesa-em-rede.streamlit.app/

Conferi online a análise e a consulta de uma oferta fictícia de 25 unidades de
pão na Vila Mariana, para retirada em 16/11/2026, das 09h às 10h. Uma organização
foi compatível. Cliquei em Registrar oferta e confirmei a linha correspondente
no Google Sheets. O painel de exemplo também apresentou os valores esperados
na hospedagem.

## Estado da avaliação automatizada

A versão publicada foi verificada com 58 testes locais aprovados: 21 do agente,
14 da integração n8n, seis da interface do agente, 12 da importação e dos
indicadores e cinco da interface do painel. As chamadas externas foram simuladas.
Esses testes são separados das conferências manuais e das chamadas reais à API.

O ChatGPT auxiliou na escrita do código, dos testes e da documentação. Executei
os testes no meu ambiente, compartilhei os resultados, conferi as telas e a
planilha, aprovei o comportamento e realizei commits, pull requests e merges.

Os testes validam os cenários cobertos, não uma garantia geral de precisão ou
robustez em produção. Não avaliei a aplicação com dados reais de restaurantes
ou beneficiários, chamadas concorrentes de gravação ou confirmação de doações.
