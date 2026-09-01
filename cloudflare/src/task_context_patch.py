import re
import unicodedata

import runtime_guard
import short_context
from telegram_api import send_message

TASK_KB = [["✅ Concluir tarefa", "⏰ Adiar tarefa"],["📌 Manter pendente", "🚫 Cancelar tarefa"],["⬅️ Voltar ao cotidiano"]]
CANCEL_KB = [["❌ Cancelar ação"]]

# Guarda a implementação base antes de instalar o patch. O wrapper abaixo só
# intercepta o segundo passo do adiamento; todos os demais estados continuam
# passando pelo runtime_guard original.
_BASE_RUNTIME_HANDLE_STATE = runtime_guard._handle_state


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _visible_tasks(db, uid):
    return await _rows(db.prepare("""
        SELECT id,title,due_date,due_time,status,postpone_count,completed_at,cancelled_at
        FROM daily_items
        WHERE user_id=? AND kind='tarefa' AND (
            status='pendente'
            OR (status='concluido' AND completed_at IS NOT NULL AND datetime(completed_at) >= datetime('now','-24 hours'))
            OR (status='cancelado' AND cancelled_at IS NOT NULL AND datetime(cancelled_at) >= datetime('now','-24 hours'))
        )
        ORDER BY CASE status WHEN 'pendente' THEN 0 WHEN 'concluido' THEN 1 ELSE 2 END,
                 COALESCE(due_date,'9999-12-31'), COALESCE(due_time,'99:99'), id
        LIMIT 40
    """).bind(uid))


async def _task_list(db, uid):
    rs = await _visible_tasks(db, uid)
    if not rs:
        return "✅ Nenhuma tarefa ativa. As antigas continuam no histórico; eu só parei de transformar essa tela num museu. 😌"

    # A ordem exibida vira contexto posicional curto. Assim `a segunda` aponta
    # para a segunda linha que o usuário realmente viu, não para uma nova busca
    # cuja ordenação possa ter mudado entre os turnos.
    await short_context.remember_list(
        db,
        uid,
        "tarefa",
        [int(_row(r, "id")) for r in rs],
        source="task_list",
    )

    out = ["✅ Tarefas"]
    for pos, r in enumerate(rs, 1):
        icon = {"pendente":"⏳", "concluido":"✅", "cancelado":"🚫"}.get(_row(r,"status"), "•")
        when = ""
        if _row(r,"due_date"):
            when = f" — {_row(r,'due_date')[8:10]}/{_row(r,'due_date')[5:7]}" + (f" {_row(r,'due_time')}" if _row(r,"due_time") else "")
        out.append(f"{icon} {pos}. {_row(r,'title')}{when}")
    out.append("\nA numeração vale só para esta lista. Concluídas/canceladas saem daqui após 24h, mas continuam no Histórico de tarefas.")
    return "\n".join(out)


async def _find_task(db, uid, text):
    raw = (text or "").strip()

    # Na tela de tarefas, números são posições temporárias, não IDs eternos do banco.
    m = re.search(r"#?(\d+)\b", raw)
    if m:
        pos = int(m.group(1))
        rs = await _visible_tasks(db, uid)
        if 1 <= pos <= len(rs):
            return rs[pos-1]

    # Referências naturais (`essa`, `ela`, `a segunda`) usam somente contexto
    # fresco e isolado por usuário.
    contextual = await short_context.resolve_daily_item(db, uid, raw, kind="tarefa")
    if contextual:
        return contextual

    target = re.sub(r"^(?:certo|ok|feito|concluir|conclui|finalizar|finaliza|cancelar|cancela|adiar|adia|manter|pendente)\s+", "", raw, flags=re.I).strip()
    if not target:
        return None
    rs = await _rows(db.prepare("SELECT * FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente'").bind(uid))
    nt = _norm(target)
    matches = [r for r in rs if nt in _norm(_row(r,"title")) or _norm(_row(r,"title")) in nt]
    return matches[0] if len(matches) == 1 else None


async def _handle_runtime_state(db, token, chat, uid, text):
    """Evita que o segundo passo do adiamento tente escolher a tarefa de novo.

    `guard_task_postpone_when` já carrega `id` e `title` no payload. No handler
    base, o prefixo `guard_task_` é testado antes desse estado específico; por
    isso textos como `amanhã às 8h` caem em `_find_task()` e o bot volta a pedir
    qual tarefa deve ser adiada. Aqui tratamos esse estado primeiro e preservamos
    o alvo selecionado no turno anterior.
    """
    state, payload = await runtime_guard._state(db, uid)
    if state != "guard_task_postpone_when":
        return await _BASE_RUNTIME_HANDLE_STATE(db, token, chat, uid, text)

    # Cancelamento continua usando exatamente a regra/teclado do runtime base.
    if text in ("❌ Cancelar ação", "/cancelar"):
        return await _BASE_RUNTIME_HANDLE_STATE(db, token, chat, uid, text)

    from nlu import parse_date, parse_time, validate_future

    due_date = parse_date(text, runtime_guard._now().date())
    due_time = parse_time(text)
    if not due_date:
        await runtime_guard._send(
            token,
            chat,
            "Não entendi a nova data. Ex.: `amanhã às 18h`.",
            runtime_guard.CANCEL_KB,
        )
        return True

    ok, msg = validate_future(
        due_date,
        due_time,
        runtime_guard._now().replace(tzinfo=None),
    )
    if not ok:
        await runtime_guard._send(token, chat, msg, runtime_guard.CANCEL_KB)
        return True

    task_id = payload.get("id")
    title = payload.get("title")
    if not task_id or not title:
        # Sessão inconsistente: limpa o estado em vez de adiar uma tarefa errada.
        await runtime_guard._clear(db, uid)
        await runtime_guard._send(
            token,
            chat,
            "Perdi a referência da tarefa. Abra Tarefas e escolha novamente qual deseja adiar.",
            runtime_guard.TASK_KB,
        )
        return True

    await db.prepare(
        "UPDATE daily_items SET due_date=?,due_time=?,status='pendente',"
        "postpone_count=postpone_count+1,snoozed_until=? WHERE id=? AND user_id=?"
    ).bind(
        due_date.isoformat(),
        due_time,
        f"{due_date.isoformat()} {due_time}" if due_time else due_date.isoformat(),
        int(task_id),
        uid,
    ).run()
    await runtime_guard._clear(db, uid)
    await runtime_guard._send(
        token,
        chat,
        f"⏰ {title} adiada para {due_date.strftime('%d/%m')}"
        + (f" às {due_time}" if due_time else "")
        + ". O calendário aceitou. Eu estou processando. 😏",
        runtime_guard.TASK_KB,
    )
    return True


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await _uid(db, int(chat_id))
    if not uid:
        return False

    text = (message.get("text") or "").strip()
    n = _norm(text)

    # Quando um lembrete acabou de apontar uma tarefa, "adiar" não deve perguntar qual tarefa.
    # O contexto, porém, expira: um `depois` solto muito tempo mais tarde não
    # pode ressuscitar uma tarefa antiga.
    postpone_only = n in (
        "adiar", "adia", "depois", "mais tarde", "agora nao", "agora não",
        "deixa pra depois", "deixa para depois", "nao agora", "não agora", "daqui a pouco"
    )
    if not postpone_only:
        return False

    ctx = await short_context.latest(db, uid)
    if not ctx or ctx.get("kind") != "tarefa" or not ctx.get("id"):
        return False

    task = await db.prepare("SELECT id,title,status FROM daily_items WHERE id=? AND user_id=? AND kind='tarefa'").bind(int(ctx["id"]), uid).first()
    if not task or _row(task,"status") != "pendente":
        return False

    await runtime_guard._set_state(db, uid, "guard_task_postpone_when", {
        "id": int(_row(task,"id")),
        "title": _row(task,"title")
    })
    await send_message(
        token,
        int(chat_id),
        f"⏰ Beleza, {_row(task,'title')} fica para depois. Pra quando?\nEx.: `daqui a 30 minutos`, `hoje às 14h`, `amanhã às 10h` ou `segunda`.",
        reply_markup=_kb(CANCEL_KB),
    )
    return True


def install():
    # A Etapa 1.3 transforma short_context na única autoridade de contexto curto.
    # Chamadores antigos de conversation_layer._remember/_context passam pela
    # mesma expiração e pelo mesmo histórico sem precisarem ser migrados de uma vez.
    short_context.install()
    runtime_guard._task_list = _task_list
    runtime_guard._find_task = _find_task
    runtime_guard._handle_state = _handle_runtime_state
