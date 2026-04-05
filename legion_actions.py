"""Definição das 100 ações do painel Legião Espartan (5 categorias × 20 ações)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["any", "member", "staff", "admin", "owner"]


@dataclass(frozen=True, slots=True)
class LegionAction:
    id: str
    label: str
    description: str
    tier: Tier


def _a(i: str, label: str, desc: str, tier: Tier = "any") -> LegionAction:
    return LegionAction(id=i, label=label[:100], description=desc[:100], tier=tier)


# —— Clube & reputação (20) ——
CLUBE: list[LegionAction] = [
    _a("c01", "Visão geral do clube", "Nome, tag, fuso e canais salvos", "any"),
    _a("c02", "Definir nome do clube", "Modal: nome oficial", "staff"),
    _a("c03", "Definir tag do clube", "Modal: tag curta", "staff"),
    _a("c04", "Definir fuso horário", "Modal: ex. America/Sao_Paulo", "staff"),
    _a("c05", "Canal de avisos REP", "Modal: ID do canal texto", "staff"),
    _a("c06", "Canal de eventos", "Modal: ID do canal texto", "staff"),
    _a("c07", "Canal de recrutamento", "Modal: ID do canal texto", "staff"),
    _a("c08", "Salvar regras internas", "Modal: texto das regras", "staff"),
    _a("c09", "Resumo público", "Embed de boas-vindas / regras", "any"),
    _a("c10", "Minha reputação", "REP semana e total", "member"),
    _a("c11", "Ranking REP semana", "Top 10 semanal", "any"),
    _a("c12", "Ranking REP total", "Top 10 acumulado", "any"),
    _a("c13", "Adicionar REP", "Modal: ID usuário, quantidade, motivo", "staff"),
    _a("c14", "Remover REP", "Modal: ID usuário, quantidade", "staff"),
    _a("c15", "Definir REP semanal", "Modal: ID usuário, valor", "staff"),
    _a("c16", "Reset REP semanal", "Zera semana de todos", "staff"),
    _a("c17", "Dica calendário ISO", "Como formatar datas nos modais", "any"),
    _a("c18", "Modelo briefing GP", "Texto tático sugerido", "staff"),
    _a("c19", "Exportar dados JSON", "Snapshot membros/eventos/metas", "staff"),
    _a("c20", "Ping latência", "Teste WS do bot", "any"),
]

# —— Membros & garagem (20) ——
MEMBROS: list[LegionAction] = [
    _a("m01", "Registrar-me", "Modal: seu IGN", "member"),
    _a("m02", "Meu perfil", "Ficha e REP", "member"),
    _a("m03", "Perfil por ID", "Modal: ID Discord", "staff"),
    _a("m04", "Listar membros", "Top por REP total", "any"),
    _a("m05", "Cargo interno", "Modal: ID + cargo texto", "staff"),
    _a("m06", "Atualizar meu IGN", "Modal: novo IGN", "member"),
    _a("m07", "Histórico IGN (eu)", "Últimas mudanças", "member"),
    _a("m08", "Histórico IGN (ID)", "Modal: ID alvo", "staff"),
    _a("m09", "Notas staff", "Modal: ID + notas", "staff"),
    _a("m10", "Excluir cadastro", "Modal: ID (admin)", "admin"),
    _a("m11", "Buscar por IGN", "Modal: trecho", "staff"),
    _a("m12", "Check-in atividade", "Atualiza última atividade", "member"),
    _a("m13", "Ver minha garagem", "JSON salvo", "member"),
    _a("m14", "Garagem por ID", "Modal: ID", "staff"),
    _a("m15", "Definir campo garagem", "Modal: chave + valor", "member"),
    _a("m16", "Poder da garagem", "Modal: número", "member"),
    _a("m17", "Remover campo garagem", "Modal: chave", "member"),
    _a("m18", "Add template carro", "Modal: nome; estrelas; classe", "staff"),
    _a("m19", "Listar templates", "Catálogo de carros", "any"),
    _a("m20", "Quem sou eu (staff)", "Modal: ID — dados Discord", "staff"),
]

# —— Eventos & engajamento (20) ——
EVENTOS: list[LegionAction] = [
    _a("e01", "Criar evento", "Modal: título; início ISO; fim; descrição", "staff"),
    _a("e02", "Listar eventos", "Próximos agendados", "any"),
    _a("e03", "Apagar evento", "Modal: ID evento", "staff"),
    _a("e04", "RSVP evento", "Modal: ID; status", "member"),
    _a("e05", "Participantes RSVP", "Modal: ID evento", "any"),
    _a("e06", "Divulgar evento", "Modal: ID — posta no canal", "staff"),
    _a("e07", "Criar anúncio", "Modal: título + corpo", "staff"),
    _a("e08", "Anúncios recentes", "Últimos salvos", "any"),
    _a("e09", "Publicar último anúncio", "No canal do painel", "staff"),
    _a("e10", "Agendar lembrete", "Modal: minutos; mensagem", "member"),
    _a("e11", "Listar lembretes", "Pendentes no servidor", "staff"),
    _a("e12", "Cancelar lembrete", "Modal: ID", "staff"),
    _a("e13", "Criar enquete", "Modal: pergunta | opções", "staff"),
    _a("e14", "Votar enquete", "Modal: ID; índice opção", "member"),
    _a("e15", "Resultado enquete", "Modal: ID", "any"),
    _a("e16", "Encerrar enquete", "Modal: ID", "staff"),
    _a("e17", "Papel escalação add", "Modal: nome; ordem; descrição", "staff"),
    _a("e18", "Listar papéis escalação", "Táticos salvos", "any"),
    _a("e19", "Broadcast staff", "Modal: mensagem → canal painel", "staff"),
    _a("e20", "Embed rápido", "Modal: título; descrição; cor hex", "staff"),
]

# —— Moderação & recrutamento (20) ——
STAFF: list[LegionAction] = [
    _a("s01", "Strike — adicionar", "Modal: ID; motivo", "staff"),
    _a("s02", "Strikes — ver", "Modal: ID membro", "staff"),
    _a("s03", "Strikes — limpar", "Modal: ID (admin)", "admin"),
    _a("s04", "Lista negra add", "Modal: ID; motivo", "admin"),
    _a("s05", "Lista negra remover", "Modal: ID", "admin"),
    _a("s06", "Lista negra ver", "Últimas entradas", "staff"),
    _a("s07", "Auditoria recente", "Log de ações do bot", "staff"),
    _a("s08", "Candidatar-se", "Modal: IGN; garagem; mensagem", "member"),
    _a("s09", "Candidaturas listar", "Modal: status vazio=todas", "staff"),
    _a("s10", "Aprovar candidatura", "Modal: ID", "staff"),
    _a("s11", "Recusar candidatura", "Modal: ID", "staff"),
    _a("s12", "Candidaturas pendentes", "Só abertas", "staff"),
    _a("s13", "Modelo recrutamento", "Texto padrão de requisitos", "staff"),
    _a("s14", "Meta — criar", "Modal: título; alvo; unidade; prazo", "staff"),
    _a("s15", "Metas listar", "Ativas recentes", "any"),
    _a("s16", "Meta progresso", "Modal: ID meta; delta", "staff"),
    _a("s17", "Meta apagar", "Modal: ID", "staff"),
    _a("s18", "Limpar mensagens", "Modal: quantidade 1–50 (admin)", "admin"),
    _a("s19", "Membros com cargo", "Modal: ID cargo", "staff"),
    _a("s20", "Info servidor", "Estatísticas Discord", "any"),
]

# —— Competitivo & sistema (20) ——
COMP: list[LegionAction] = [
    _a("k01", "Guerra registrar", "Modal: adversário; resultado; data; placar", "staff"),
    _a("k02", "Guerras histórico", "Últimas registradas", "any"),
    _a("k03", "Treino agendar", "Modal: tema; quando ISO; notas", "staff"),
    _a("k04", "Treinos listar", "Próximos", "any"),
    _a("k05", "Patrocínio add", "Modal: parceiro; valor; datas", "staff"),
    _a("k06", "Patrocínios listar", "Últimos", "any"),
    _a("k07", "Tarefa criar", "Modal: título; ID responsável; prazo", "staff"),
    _a("k08", "Tarefas listar", "Modal: status ou vazio", "staff"),
    _a("k09", "Tarefa status", "Modal: ID; novo status", "staff"),
    _a("k10", "Sobre o painel", "Stack e versão", "any"),
    _a("k11", "Atualizar painel", "Re-render embed + logos", "staff"),
    _a("k12", "Repostar painel", "Nova mensagem (antiga inválida)", "owner"),
    _a("k13", "Ping banco de dados", "Teste SQLite (dono)", "owner"),
    _a("k14", "Stats tabelas", "Contagens por tabela (dono)", "owner"),
    _a("k15", "Listar ações (índice)", "Referência rápida IDs", "any"),
    _a("k16", "Convite bot OAuth2", "Permissões sugeridas", "staff"),
    _a("k17", "Discloud: dica deploy", "RAM, MAIN, variáveis", "owner"),
    _a("k18", "Legião — slogan", "Texto motivacional fixo", "any"),
    _a("k19", "Estratégia defensiva", "Dicas ghost / nitro", "any"),
    _a("k20", "Suporte técnico", "Contate donos do bot", "any"),
]

CATEGORIES: list[tuple[str, str, list[LegionAction]]] = [
    ("clube", "Clube & reputação", CLUBE),
    ("membros", "Membros & garagem", MEMBROS),
    ("eventos", "Eventos & engajamento", EVENTOS),
    ("moderacao", "Moderação & metas", STAFF),
    ("competitivo", "Competitivo & sistema", COMP),
]

ALL_ACTIONS: dict[str, LegionAction] = {}
for _cat, _title, actions in CATEGORIES:
    for act in actions:
        ALL_ACTIONS[act.id] = act

assert len(ALL_ACTIONS) == 100, f"esperado 100 ações, tem {len(ALL_ACTIONS)}"
