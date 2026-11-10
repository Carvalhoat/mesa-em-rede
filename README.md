![Mesa em Rede](brand/logo-com-assinatura.png)

# Mesa em Rede

Projeto de portfólio que usa inteligência artificial para apoiar a triagem de excedentes alimentares, com revisão humana e consulta a organizações receptoras fictícias.

## Problema

Informações sobre excedentes podem chegar em mensagens informais e incompletas. Organizar esses dados e verificar o que falta exige trabalho de quem faz a triagem.

## Proposta

Transformar mensagens de restaurantes em ofertas estruturadas, identificar informações pendentes e sugerir organizações compatíveis para avaliação pela pessoa responsável. A proposta é apoiar uma rede de redistribuição de alimentos para organizações que atendem pessoas em situação de vulnerabilidade social.

## Status e fluxo implementado

Protótipo local em Streamlit, demonstrado com mensagens fictícias de um restaurante e um cadastro de três organizações receptoras fictícias.

1. Informar a mensagem do restaurante ou carregar um exemplo.
2. Analisar a mensagem com a API do Gemini.
3. Conferir os campos extraídos e as informações ausentes.
4. Corrigir ou complementar os dados na revisão humana.
5. Confirmar a revisão.
6. Consultar organizações e verificar os motivos de compatibilidade ou incompatibilidade.

Alterar a mensagem original exige nova análise. Alterar os campos revisados exige nova confirmação e invalida a consulta anterior.

## Dados da oferta

| Campo | Formato esperado |
| --- | --- |
| Item | Nome do alimento |
| Quantidade | Número inteiro positivo, em unidades |
| Bairro | Bairro da oferta |
| Data de retirada | `AAAA-MM-DD` |
| Horário de retirada | `HH:MM-HH:MM`, com fim posterior ao início |

Informações ausentes ou ambíguas devem permanecer como `null` na extração e ser conferidas pela pessoa responsável. A consulta exige os cinco campos preenchidos e válidos.

## Critérios da consulta

A consulta é feita por regras em Python. Uma organização precisa atender simultaneamente a todos os critérios:

- Aceitar o alimento informado.
- Atender ao bairro da oferta.
- Ter capacidade por oferta igual ou superior à quantidade informada.
- Estar disponível no dia da semana da retirada.
- Ter um intervalo de horário em comum com a oferta.

A comparação dos nomes de alimentos e bairros desconsidera diferenças de maiúsculas, acentos e espaços extras. Não interpreta sinônimos nem estima proximidade geográfica.

O intervalo compartilhado precisa ter duração positiva: se a organização encerra às 11:00 e a oferta começa às 11:00, não há compatibilidade de horário. Quando há compatibilidade, a consulta apresenta a janela em comum.

## Limitações da demonstração

- O cadastro e as ofertas de demonstração são fictícios.
- A compatibilidade é uma sugestão para avaliação humana; não confirma uma doação.
- A aplicação não envia mensagens, agenda retiradas nem reserva capacidade.
- A capacidade é verificada por oferta, sem somar ofertas simultâneas ou dividir uma oferta entre organizações.
- As regras não avaliam condições sanitárias, validade dos alimentos ou condições de transporte.
- Os dados da oferta e da revisão ficam apenas na sessão da aplicação, sem gravação em arquivo ou banco de dados.
- A mensagem enviada para análise é transmitida à API do Gemini. Use dados fictícios na demonstração.

## Como executar no Windows

Abra um terminal na pasta principal do projeto. É necessário ter Python instalado e uma chave válida da API do Gemini.

1. Crie o ambiente virtual, caso ainda não exista:

   ```powershell
   py -m venv .venv
   ```

2. Instale as dependências:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Copie `.env.example` para `.env`, caso ainda não tenha configurado o arquivo, e preencha `GEMINI_API_KEY` com sua chave. Não publique o arquivo `.env`.

4. Inicie a aplicação:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run app.py
   ```

5. Abra o endereço local indicado pelo Streamlit no terminal. Para encerrar, pressione `Ctrl+C` no terminal.

## Exemplo para demonstração

```text
Temos 25 unidades de pão na Vila Mariana. A retirada é dia 12/11/2026, das 09:00 às 10:00.
```

Após a análise, confira os cinco campos e confirme a revisão antes de consultar organizações.

## Validação realizada

Para executar os seis casos sintéticos de extração, com chamada à API do Gemini:

```powershell
.\.venv\Scripts\python.exe teste_extracao.py
```

Resultado observado: seis de seis casos passaram em uma execução completa. Os casos cobrem mensagem completa, horário ausente, quantidade aproximada, data relativa, horário com apenas um limite e quantidades contraditórias. Esse resultado se limita aos exemplos testados.

Para executar a verificação inicial da consulta, sem chamada ao Gemini:

```powershell
.\.venv\Scripts\python.exe teste_organizacoes.py
```

Resultado observado: três de três classificações corretas para a oferta inicial. Esse script verifica as classificações das três organizações; os cenários adicionais abaixo foram verificados manualmente na interface.

| Oferta de pão em 12/11/2026 | Resultado observado |
| --- | --- |
| 25 unidades, Vila Mariana, 09:00–10:00 | Cozinha Comunitária A compatível; B sem capacidade; C fora do bairro |
| 60 unidades, Vila Mariana, 09:00–10:00 | Nenhuma organização compatível |
| 60 unidades, Moema, 09:00–10:00 | Centro Comunitário C compatível |
| 60 unidades, Moema, 11:00–12:00 | Nenhuma organização compatível |

Também foram verificados os fluxos de correção, complementação de informações ausentes, rejeição de quantidade e horário inválidos, bloqueio de revisão desatualizada e invalidação da consulta após alterações.

## Organização do projeto

| Arquivo ou pasta | Função |
| --- | --- |
| `app.py` | Interface e estado do fluxo de triagem |
| `extracao.py` | Integração com Gemini e lógica de extração |
| `organizacoes.py` | Regras de compatibilidade |
| `data/exemplos.json` | Casos sintéticos de extração |
| `data/organizacoes.json` | Cadastro fictício das organizações |
| `prompts/extracao_v1.md` | Instruções de extração |
| `teste_extracao.py` | Comparação da extração com gabaritos |
| `teste_organizacoes.py` | Verificação inicial das classificações |
| `brand/` | Briefing, marca e personagens |
| `AI_USAGE.md` | Registro do uso de IA no desenvolvimento |

## Identidade visual

O símbolo B2 representa a conexão entre o restaurante, a pessoa responsável pela triagem e a organização receptora. O personagem pratinho e o caminhão ilustram as etapas do fluxo.

A identidade utiliza verde escuro `#234539`, creme `#FFF7EB` e terracota `#AD4D35`. O briefing e os arquivos da marca estão na pasta `brand`.

## Próximas etapas

- Ampliar os casos de teste e a avaliação da extração.
- Preparar a demonstração e a publicação online do protótipo.
- Avaliar persistência de ofertas e integrações externas em uma etapa posterior.

## Autoria

Amanda Carvalho Teixeira.
