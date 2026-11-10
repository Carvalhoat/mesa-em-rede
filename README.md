![Mesa em Rede](brand/logo-com-assinatura.png)

# Mesa em Rede

Projeto de portfólio que usa inteligência artificial para apoiar
a triagem de excedentes alimentares, com revisão humana.

## Problema

Informações sobre excedentes podem chegar em mensagens informais
e incompletas. Organizar esses dados e verificar o que falta exige
trabalho de quem faz a triagem.

## Proposta

Transformar mensagens de restaurantes em ofertas estruturadas,
identificar informações pendentes e sugerir organizações
compatíveis para avaliação pela pessoa responsável.

## Fluxo planejado

1. Receber a mensagem do restaurante.
2. Extrair os dados com IA.
3. Identificar informações ausentes.
4. Permitir revisão e correção.
5. Consultar organizações compatíveis.
6. Registrar a oferta após aprovação humana.

## Status

Em desenvolvimento. A interface local em Streamlit permite
analisar mensagens com IA, corrigir campos e confirmar a revisão.

Os seis casos sintéticos de extração passaram após a integração
da interface. Também foram verificados manualmente os fluxos
de correção, complementação e bloqueio de dados inválidos
ou desatualizados.

A próxima etapa é consultar organizações fictícias compatíveis
com a oferta revisada.

## Escopo inicial

O protótipo será demonstrado com um restaurante e três
organizações receptoras fictícias.

## Identidade visual

O símbolo B2 representa a conexão entre o restaurante,
a pessoa responsável pela triagem e a organização receptora.

O briefing e os arquivos da marca estão na pasta `brand`.

## Autoria

Amanda Carvalho Teixeira.

## Como executar no Windows

1. Instale o Python e abra um terminal na pasta do projeto.
2. Crie o ambiente virtual:

   `py -m venv .venv`

3. Instale as dependências:

   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

4. Copie `.env.example` para `.env` e preencha `GEMINI_API_KEY`.
5. Inicie a aplicação:

   `.\.venv\Scripts\python.exe -m streamlit run app.py`

Para executar os seis casos sintéticos:

`.\.venv\Scripts\python.exe teste_extracao.py`