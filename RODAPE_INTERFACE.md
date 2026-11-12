# Rodapé ilustrado

Usa a imagem do fluxo enviada pela usuária, sem alterações na arte. O rodapé
aparece ao final da triagem e do painel de indicadores, centralizado e adaptado
à largura da tela, com limite de 692 pixels para evitar ampliação desnecessária.
Inclui descrição alternativa e legenda do fluxo.

As imagens dos personagens permanecem estáticas. Esta versão não inclui as
animações CSS nem o controle Animar personagens.

## Instalação

- Substitua `app.py` na raiz do projeto.
- Adicione `RODAPE_INTERFACE.md` à raiz.
- Coloque `fluxo-mesa-em-rede.png` na pasta `brand/exportacoes` existente.
- Se tiver copiado `ANIMACOES_INTERFACE.md` da etapa anterior, remova esse
  documento, pois aquela proposta foi substituída por este rodapé estático.

Mantenha os demais arquivos e imagens existentes. Não há novas dependências,
alterações de credenciais ou mudanças nas regras da triagem e do registro.

Reinicie o Streamlit e confira o fim das duas páginas, inclusive com a janela
mais estreita. O rodapé acompanha o conteúdo; não fica fixo sobre os formulários.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```
