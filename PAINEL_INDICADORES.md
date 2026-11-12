# Painel de indicadores — etapa 1

Nova página na navegação lateral do Streamlit. A página de triagem permanece no
mesmo aplicativo. A navegação preserva a mensagem, as correções em andamento e
o identificador da oferta durante a sessão.

## Fonte e atualização

Esta versão lê um CSV exportado da aba `ofertas` do Google Sheets. Não se conecta
automaticamente à planilha e não altera o workflow n8n. Registrar uma oferta na
triagem não atualiza o painel: exporte e importe o CSV novamente.

No Sheets, selecione a aba `ofertas` e use **Arquivo → Fazer download → Valores
separados por vírgulas (.csv, página atual)**. No aplicativo, escolha **Painel de
indicadores** na barra lateral e importe o arquivo.

O painel não envia o CSV ao Gemini ou ao n8n. O arquivo é processado na sessão
do aplicativo. A análise não grava ofertas, altera a planilha ou contata organizações.
Não há alteração de credenciais ou dependências do projeto.

## Indicadores e filtros

- Total de ofertas do recorte, contado por identificador único.
- Ofertas com e sem compatibilidade inicial.
- Taxa de compatibilidade = com compatibilidade / (com + sem compatibilidade).
- Ofertas não consultadas e com erro aparecem separadamente e não entram na taxa.
- Sem consultas concluídas, a taxa aparece como traço, não como zero por cento.
- Distribuição de ofertas por alimento e bairro, sem somar unidades de alimentos diferentes.
- Filtros por período do primeiro registro, bairro, alimento e situação da oferta.
- Por padrão, entram somente ofertas `registrada`. Canceladas podem ser selecionadas.

Os registros representam ofertas fictícias e resultados de uma consulta inicial.
Não representam entregas, doações concretizadas, pessoas atendidas ou capacidade
reservada. A consulta registra o resultado mais recente salvo, não um histórico.

## Importação

O CSV deve manter os 16 cabeçalhos originais da aba `ofertas`. Limites: 2 MB e
10.000 ofertas. Suporta UTF-8 com ou sem BOM, Windows-1252 e separador vírgula ou
ponto e vírgula. Linhas totalmente vazias e colunas extras de cabeçalho vazio
são toleradas. As categorias nos gráficos usam os rótulos registrados no CSV.

Identificadores repetidos, cabeçalhos repetidos, dados obrigatórios inválidos,
status desconhecidos ou totais de compatibilidade contraditórios bloqueiam o
cálculo e geram um aviso. Não há descarte silencioso de linhas inválidas nem
escolha automática de uma linha para cada identificador duplicado.

Datas de registro são interpretadas nos formatos ISO ou brasileiro; datas e
horas textuais exportadas do Sheets são aceitas. O recorte usa a data exibida
no arquivo, sem converter seu fuso. Exporte a aba com as datas formatadas,
não com números seriais. Todas as linhas precisam ter `dados_ficticios = sim`.

## Instalação

Na branch `painel-indicadores`, copie para a raiz do projeto:

- `app.py` — substitui a interface anterior.
- `painel_indicadores.py` — novo módulo.
- `teste_painel_indicadores.py` — testes de importação, filtros e indicadores.
- `teste_interface_painel.py` — testes de navegação e apresentação.
- `PAINEL_INDICADORES.md` — este documento.

Adicione `data/ofertas_exemplo.csv` à pasta `data` existente. Mantenha
`data/organizacoes.json` e os demais arquivos atuais do projeto.

## Testes

Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -m unittest teste_agente_triagem.py teste_integracao_n8n.py teste_interface_agente.py teste_painel_indicadores.py teste_interface_painel.py -v
```

Esperado: **58 testes**, `OK` (41 anteriores e 17 novos). Todos aprovados
localmente. Gemini e n8n são simulados nesses testes; nenhum registro é enviado.
O Streamlit pode mostrar avisos de `ScriptRunContext` durante os testes.

Para abrir a interface:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Conferência do exemplo

Selecione **Painel de indicadores → Exemplo fictício**. O exemplo é independente
da planilha e está identificado na tela. Ele inclui seis ofertas inventadas.
Com os filtros iniciais, uma cancelada fica de fora e o esperado é:

| Indicador | Valor |
| --- | ---: |
| Ofertas no recorte | 5 |
| Com compatibilidade | 2 |
| Sem compatibilidade | 1 |
| Não consultadas | 1 |
| Com erro | 1 |
| Taxa de compatibilidade | 66,7% |

Em **Situação da oferta → Todas**, o total passa a seis e a taxa a 75,0%.
Filtrando somente **Moema**, não há consultas concluídas e a taxa fica como traço.

Após conferir o exemplo, importe o CSV real da demonstração. Compare o total
com as linhas válidas da aba, usando o mesmo período e a mesma situação da oferta.
O exemplo nunca é mesclado aos registros importados.

## Limites desta etapa

Atualização por arquivo, sem leitura automática da planilha. A página deve ser
conferida visualmente no computador do usuário com o CSV exportado atual antes
do commit. Exportações usadas para conferência não precisam entrar no repositório;
o pacote inclui somente o exemplo sintético.
