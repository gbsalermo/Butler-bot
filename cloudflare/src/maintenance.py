"""Manutenção leve do Butler.

Cloudflare Workers não mantêm um cache de processo confiável entre invocações.
Aqui "limpar cache" significa podar somente estado operacional descartável:
- contexto conversacional antigo;
- sessões/wizards abandonados;
- notification_log antigo.

Nunca apaga Core, memória pessoal, histórico acadêmico, treino ou rotinas.
A manutenção é GLOBAL e só roda quando nenhum chat possui alerta nos próximos
20 minutos.
"""
from datetime import datetime, timedelta, timezone

from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ=timezone(timedelta(hours=UTC_OFFSET_HOURS))
MAINTENANCE_TIMES={(6,0),(12,0),(19,0)}
QUIET_WINDOW_MINUTES=20

DAY_NAMES=["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"]


def _row(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default

async def _rows(stmt):
    result=await stmt.all();data=getattr(result,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []


def _times(value):
    import re
    return list(dict.fromkeys(re.findall(r"\b(?:[01]\d|2[0-3]):[0-5]\d\b",value or "")))


def _applies(weekdays,target):
    import unicodedata
    def norm(v):
        v=unicodedata.normalize("NFKD",(v or "").lower());return "".join(c for c in v if not unicodedata.combining(c))
    value=norm(weekdays or "todos os dias")
    if not value or "todos os dias" in value or value in ("todos","diario","diaria"):return True
    return norm(DAY_NAMES[target.weekday()]) in value or norm(DAY_NAMES[target.weekday()].replace("-feira","")) in value


def _within(now,target):
    delta=target-now
    return timedelta(0)<=delta<timedelta(minutes=QUIET_WINDOW_MINUTES)


async def _has_upcoming_alert(db,now):
    """True se QUALQUER chat tiver alerta funcional nos próximos 20 min."""
    today=now.date();today_s=today.isoformat()

    # Tarefas/lembretes e compromissos. Compromisso avisa 5 min antes.
    items=await _rows(db.prepare("SELECT kind,due_time,details FROM daily_items WHERE status='pendente' AND due_date=? AND due_time IS NOT NULL").bind(today_s))
    for item in items:
        try:h,m=map(int,str(_row(item,"due_time")).split(":"))
        except Exception:continue
        target=datetime.combine(today,datetime.min.time(),tzinfo=LOCAL_TZ).replace(hour=h,minute=m)
        if _row(item,"kind")=="compromisso" and (_row(item,"details") or "")!="simple_reminder":target-=timedelta(minutes=5)
        if _within(now,target):return True

    # Checkpoints de rotina de todos os usuários.
    routines=await _rows(db.prepare("SELECT time_hhmm,weekdays FROM routines WHERE active=1 AND time_hhmm IS NOT NULL"))
    for routine in routines:
        if not _applies(_row(routine,"weekdays"),today):continue
        for t in _times(_row(routine,"time_hhmm")):
            try:h,m=map(int,t.split(":"))
            except Exception:continue
            target=datetime.combine(today,datetime.min.time(),tzinfo=LOCAL_TZ).replace(hour=h,minute=m)
            if _within(now,target):return True

    # Aulas: Butler avisa 10 minutos antes.
    weekday=DAY_NAMES[today.weekday()]
    sessions=await _rows(db.prepare("SELECT ss.start_time FROM subject_sessions ss JOIN subjects s ON s.id=ss.subject_id WHERE s.active=1 AND ss.weekday=?").bind(weekday))
    # Algumas grades usam "segunda" em vez de "segunda-feira".
    if not sessions:
        sessions=await _rows(db.prepare("SELECT ss.start_time FROM subject_sessions ss JOIN subjects s ON s.id=ss.subject_id WHERE s.active=1 AND ss.weekday=?").bind(weekday.replace("-feira","")))
    for session in sessions:
        try:h,m=map(int,str(_row(session,"start_time")).split(":"))
        except Exception:continue
        target=datetime.combine(today,datetime.min.time(),tzinfo=LOCAL_TZ).replace(hour=h,minute=m)-timedelta(minutes=10)
        if _within(now,target):return True
    return False


async def _already_ran(db,slot_key):
    row=await db.prepare("SELECT id FROM notification_log WHERE user_id=(SELECT MIN(id) FROM users) AND notification_key=? LIMIT 1").bind(slot_key).first()
    return bool(row)


async def _mark_ran(db,slot_key):
    owner=await db.prepare("SELECT MIN(id) id FROM users").first();uid=_row(owner,"id")
    if uid is not None:
        await db.prepare("INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(int(uid),slot_key).run()


async def _broadcast(db,token,text):
    users=await _rows(db.prepare("SELECT telegram_chat_id FROM users WHERE telegram_chat_id IS NOT NULL"))
    for user in users:
        try:await send_message(token,int(_row(user,"telegram_chat_id")),text)
        except Exception as exc:print(f"[maintenance] broadcast_error chat={_row(user,'telegram_chat_id')} type={type(exc).__name__}")


async def _cleanup(db):
    # Contexto curto: depois de 24h perde utilidade para referência conversacional.
    try:await db.prepare("DELETE FROM conversation_context WHERE datetime(updated_at) < datetime('now','-24 hours')").run()
    except Exception:pass

    # Sessão nula ou wizard abandonado há 12h. Não toca sessão recente/ativa.
    try:await db.prepare("DELETE FROM user_sessions WHERE state IS NULL OR datetime(updated_at) < datetime('now','-12 hours')").run()
    except Exception:pass

    # Log serve para idempotência diária; 45 dias é folga suficiente e limita crescimento.
    try:await db.prepare("DELETE FROM notification_log WHERE datetime(sent_at) < datetime('now','-45 days')").run()
    except Exception:pass


async def run_maintenance(db,token):
    now=datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    if (now.hour,now.minute) not in MAINTENANCE_TIMES:return False
    slot=f"maintenance:{now.date().isoformat()}:{now.strftime('%H:%M')}"
    if await _already_ran(db,slot):return False

    if await _has_upcoming_alert(db,now):
        print(f"[maintenance] skipped slot={slot} reason=alert_within_{QUIET_WINDOW_MINUTES}m")
        # Não marca como executada: dentro do mesmo minuto outro cron ainda pode tentar;
        # depois do minuto a janela de manutenção encerra e aguarda o próximo horário.
        return False

    await _mark_ran(db,slot)
    await _broadcast(db,token,"🚪 Vou só no banheiro rapidinho. Nada dramático, é manutenção da casa.")
    await _cleanup(db)
    await _broadcast(db,token,"🚽 Pronto, tudo conectado e descarga dada. Já estou operante.")
    print(f"[maintenance] ok slot={slot}")
    return True
