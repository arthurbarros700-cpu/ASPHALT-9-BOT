# Asphalt 9 — Bot Discord para gestão de clube

Bot em **Python** com **discord.py**, **comandos slash** (90+) e persistência **SQLite** (`aiosqlite`). Pensado para equipes de **Asphalt 9 Legends**: reputação semanal, eventos com RSVP, recrutamento, metas, garagem, histórico de guerras/GP, treinos, tarefas, enquetes, lembretes e moderação leve com auditoria.

## Requisitos

- Python 3.10+
- Conta de aplicação no [Discord Developer Portal](https://discord.com/developers/applications) com bot e escopo **applications.commands**

## Instalação rápida

```bash
pip install -r requirements.txt
cp .env.example .env
# Edite .env: DISCORD_TOKEN e, opcionalmente, DISCORD_GUILD_ID e BOT_OWNER_IDS
python main.py
```

### Variáveis de ambiente

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `DISCORD_TOKEN` | Sim | Token do bot |
| `DISCORD_GUILD_ID` | Não | Se preenchido, sincroniza comandos só nesse servidor (útil em desenvolvimento) |
| `BOT_OWNER_IDS` | Não | IDs separados por vírgula — acesso a `/admin_*` |
| `BOT_NAME` | Não | Nome exibido em `/sobre` |

## Permissões sugeridas no Discord

No mínimo: ver canais, enviar mensagens, incorporar links, ler histórico. Para `/limpar_mensagens`: **Gerenciar mensagens**. Comandos de staff usam **Gerenciar servidor** ou **Administrador** conforme o comando.

## Módulos de comandos (resumo)

- **Meta:** `/ajuda`, `/ping`, `/sobre`, `/convite_bot`, `/info_servidor`, `/stats_bot`
- **Clube:** `/clube_config`, `/clube_nome`, `/clube_tag`, `/clube_fuso`, canais padrão, regras, resumo
- **Membros:** registro, perfil, listagem, cargo interno, IGN, histórico, notas, exportação, busca por IGN
- **Reputação:** adicionar/remover/definir semana, rankings, reset semanal, `/meu_rep`
- **Eventos:** criar, listar, apagar, RSVP, participantes, divulgar no canal
- **Moderação:** strikes, lista negra, auditoria
- **Recrutamento:** candidatura, triagem, modelo de texto
- **Metas:** criar, listar, progresso, apagar
- **Garagem:** JSON flexível por membro, poder, templates de carros
- **Engajamento:** anúncios, lembretes, enquetes, papéis de escalação, check-in
- **Competitivo:** guerras, treinos, patrocínios, tarefas, dicas
- **Admin:** sync de comandos, diagnóstico de banco, broadcast, embed rápido, limpeza de canal, whois, membros por cargo

## Dados

O arquivo `asphalt9_club.sqlite3` é criado automaticamente na primeira execução.

## Licença

Uso interno do projeto; adapte conforme a política da sua equipe.
