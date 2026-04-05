# Legião Espartan — Painel Discord (Asphalt 9)

Bot focado em **um centro de comando visual**: **painel fixo** no canal configurado, com **dois selects** (área → ação) e **formulários (modais)** para entrada de dados. **100 funções** mapeadas em `legion_actions.py` e tratadas em `panel.py`.

**Não** há dezenas de comandos slash para memorizar: o fluxo normal é só **abrir o painel** e navegar pelos menus. Existe apenas **`/painel`** (staff) para **recuperação** se a mensagem fixa for apagada.

## Logo “animado” (Legião Espartan)

O Discord **não anima** várias imagens dentro de um único embed ao mesmo tempo. O efeito de animação é feito assim:

1. Defina **`PANEL_LOGO_URLS`** com **várias URLs** (GIF ou PNG), **separadas por vírgula** — por exemplo frames exportados do seu logo animado.
2. O bot **alterna o thumbnail** do embed do painel a cada **`LOGO_CYCLE_SECONDS`** segundos (com **mais de uma** URL configurada).

Hospede os ficheiros (Imgur, CDN, anexo Discord copiando URL, etc.) e cole as URLs na variável.

## Variáveis de ambiente (Discloud)

| Variável | Uso |
|----------|-----|
| `DISCORD_TOKEN` | Token do bot (obrigatório) |
| `DISCORD_GUILD_ID` | ID do servidor (recomendado) |
| `PANEL_CHANNEL_ID` | Canal onde o painel fica **fixo** (recomendado) |
| `BOT_OWNER_IDS` | IDs dos donos (separados por vírgula) — ações “dono” + repostar painel |
| `LEGION_NAME` | Título do painel (ex.: Legião Espartan) |
| `PANEL_LOGO_URLS` | URLs dos frames do logo, separadas por vírgula |
| `LOGO_CYCLE_SECONDS` | Intervalo da rotação do thumbnail (2–60) |
| `BOT_NAME` | Nome interno / rodapé |

Na **Discloud**, configure estas variáveis no painel do aplicativo. O ficheiro `discloud.config` aponta `MAIN=main.py`, `TYPE=bot`, `RAM=512`, `VERSION=3.11`.

## Execução local

```bash
pip install -r requirements.txt
cp .env.example .env
# Edite .env
python main.py
```

## Permissões Discord

- Bot: `applications.commands`, ver canais, enviar mensagens, embeds, ler histórico.
- Membros com **Gerenciar servidor** usam ações de staff no painel.
- **Administrador** para ações marcadas como admin.
- **IDs em `BOT_OWNER_IDS`** para diagnóstico e **repostar painel**.

## Persistência

SQLite em `asphalt9_club.sqlite3` (criado automaticamente). Na Discloud o disco persiste conforme o plano.

## Estrutura

- `legion_actions.py` — 100 ações (5 categorias × 20)
- `panel.py` — views persistentes, embed, dispatch, modais
- `database.py` — dados do clube + `panel_message_id` e estado do logo
- `cogs/painel.py` — comando `/painel` (opcional / recuperação)
