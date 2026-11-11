# Registro de ofertas no n8n

## Instalação no projeto existente

1. No GitHub Desktop, crie a branch `integracao-n8n` a partir da `main` atualizada.
2. Copie `app.py`, `integracao_n8n.py`, `teste_integracao_n8n.py`, `README.md`, `AI_USAGE.md` e este guia para a pasta principal do projeto. Substitua os arquivos anteriores de mesmo nome.
3. Copie a pasta `workflows` para a pasta principal do projeto. O modelo público é documentação reproduzível: não substitua nem reimporte sobre o fluxo que já foi testado na sua conta.
4. Preserve `extracao.py`, `organizacoes.py`, `requirements.txt`, `.streamlit` e os arquivos de `brand` existentes. A integração usa a biblioteca padrão do Python e `python-dotenv`, já utilizado no projeto.
5. Abra o `.env` existente e acrescente a URL do webhook. Preserve as chaves existentes. Não substitua o arquivo pelo exemplo deste guia.

```dotenv
N8N_WEBHOOK_URL=https://SEU-ESPACO.app.n8n.cloud/webhook-test/mesa-em-rede/ofertas
N8N_WEBHOOK_TOKEN=SEU_TOKEN_LOCAL_JA_CONFIGURADO
```

Os valores acima são marcadores de exemplo. Use a URL copiada do seu bloco Webhook e o mesmo token da credencial Header Auth, cujo nome de header é `X-Mesa-Token`. Não envie o token no chat e não salve chaves no JSON público ou no GitHub.

## Primeiro teste pela aplicação

1. Execute os testes sem rede:

```powershell
.\.venv\Scripts\python.exe teste_integracao_n8n.py
```

2. Se a aplicação estiver aberta, encerre-a com Ctrl+C no terminal correspondente e inicie novamente:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

3. Informe uma oferta fictícia, analise, confira os campos, confirme a revisão e consulte organizações.
4. No n8n, clique em Execute workflow na tela do fluxo completo.
5. Quando estiver aguardando a chamada da URL de teste, volte à aplicação e clique em Registrar oferta.
6. Confira a mensagem de sucesso e procure no Sheets o identificador mostrado na tela. O prefixo será `oferta_`. As duas ofertas `demo_n8n_001` e `demo_n8n_002` são testes anteriores e permanecem na planilha.
7. O texto original é enviado ao Gemini na análise. Somente os campos revisados e a consulta atual são enviados ao n8n no registro.

A URL de teste precisa estar escutando para cada chamada. Um HTTP 404 nessa etapa costuma indicar que é necessário clicar novamente em Execute workflow. Não use apenas Execute step no bloco Webhook para testar a gravação completa.

## Reenvio e edição

- Após o sucesso, o botão fica desativado para os mesmos dados confirmados.
- Editar a revisão bloqueia o resumo e o registro até reconfirmar. A consulta antiga é descartada.
- Reconfirmar e registrar a revisão alterada atualiza a mesma oferta durante a sessão. O n8n preserva `registrado_em`.
- Consultar novamente atualiza o instante da consulta e permite atualizar o resultado na mesma linha.
- Iniciar uma nova análise gera um novo ID. Recarregar a página não recupera o ID da sessão anterior.
- Após timeout ou falha de comunicação, confira primeiro a execução e o Sheets. O reenvio manual mantém o ID da sessão. Não há reenvio automático.
- O mecanismo foi testado com reenvios sequenciais. Não há transação nem bloqueio para duas chamadas simultâneas com o mesmo ID.

## Uso com URL de produção

Após validar o botão contra a URL de teste:

1. No n8n, publique o workflow com Publish.
2. Abra Webhook, selecione Production URL e copie a URL.
3. Troque apenas `N8N_WEBHOOK_URL` no `.env` pela URL de produção. O caminho deixará de conter `webhook-test` e usará `webhook`.
4. Reinicie a aplicação e teste uma oferta fictícia.
5. A URL de produção usa o workflow publicado e dispensa clicar em Execute workflow a cada envio. Alterações no fluxo precisam ser publicadas novamente.

O arquivo exportado recebido estava com `active: false`; publicar ainda é uma ação a realizar na conta. O teste gratuito do n8n tem prazo. Mantenha uma cópia do workflow e decida a hospedagem antes do encerramento.

## Respostas da integração

| Resposta | Comportamento da tela |
| --- | --- |
| HTTP 200, `registro_ok`, `registrado: true` | Confirma a gravação |
| HTTP 422 | Informa rejeição dos campos, sem confirmar gravação |
| HTTP 401 ou 403 | Orienta conferir a autenticação |
| HTTP 404 | Orienta conferir URL, escuta de teste ou publicação |
| Timeout, erro de rede, HTTP 500 ou resposta inesperada | Mantém o resultado como não confirmado e pede conferência antes de reenviar |

Não aceite apenas HTTP 200 como prova: o corpo também precisa confirmar a gravação. Erros do Sheets e inconsistências encontradas em Preparar registro continuam interrompendo a execução e podem retornar HTTP 500. A interface trata esse retorno sem afirmar sucesso ou ausência de gravação.

## Modelo público do workflow

`workflows/registrar-oferta-modelo.json` preserva a lógica e as conexões do fluxo exportado, mas remove referências de credenciais, IDs da planilha, metadados da instância e dados fixados. Para reutilizar em outra conta, selecione credenciais, documento e aba em cada bloco Google Sheets, configure Header Auth e publique quando os testes estiverem concluídos.

O cadastro de organizações e o restaurante aceito são fixos nesta demonstração. Modificar as abas de cadastro não modifica automaticamente `data/organizacoes.json`, `organizacoes.py` ou as validações do workflow.
