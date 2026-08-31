"""Ajustes de usabilidade de produção e lista persistente Ler/Ver Depois.

Chamado diretamente por ``entry.py`` antes do Core. A função ``install`` roda
por último na sequência de instalação atual; por isso ela NÃO deve recriar menus
operacionais com uma definição própria. Menus são autoritativos em
``operational_menu.py`` e aqui apenas sincronizamos ``app`` com essa fonte.
"""

import json

import app
import operational_menu
from nlu import parse_date, parse_time, validate_future
from performance_patch import reset_request_cache
from telegram_api import send_message


LATER_KB = [
    ["➕ Adicionar à lista", "📚 Livros"],
    ["🎬 Filmes", "🎓 Cursos"],
    ["🗂️ Outras"],
    ["✏️ Editar item", "🗑️ Remover item"],
    ["⬅️ Voltar ao cotidiano"],
]
CATEGORY_KB = [
    ["📚 Livro", "🎬 Filme"],
    ["🎓 Curso", "🗂️ Outra"],
    ["❌ Cancelar ação"],
]
CATEGORY_CHOICES = {
    "📚 Livro": "livro",
    "🎬 Filme": "filme",
    "🎓 Curso": "curso",
    "🗂️ Outra": "outra",
}
CATEGORY_EMPTY_LABELS = {
    "livro": "livros",
    "filme": "filmes",
    "curso": "cursos",
    "outra": "outros itens",
}
CATEGORY_TITLES = {
    "livro": "📚 Livros",
    "filme": "🎬 Filmes",
    "curso": "🎓 Cursos",
    "outra": "🗂️ Outras",
}
CANCEL_KB = [["❌ Cancelar ação"]]

LATER_ENTRY_TEXTS = {
    "📌 Ler/ver depois",
    "⬅️ Voltar ao cotidiano",
    "➕ Adicionar à lista",
    "📚 Livros",
    "🎬 Filmes",
    "🎓 Cursos",
    "🗂️ Outras",
    "✏️ Editar item",
    "🗑️ Remover item",
}
LATER_SCHEMA_TEXTS = {
    "📚 Livros",
    "🎬 Filmes",
    "🎓 Cursos",
    "🗂️ Outras",
    "✏️ Editar item",
    "🗑️ Remover item",
}


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def _rowget(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _send(token, chat_id, text, rows=None):
    return await send_message(token, chat_id, text, reply_markup=_kb(rows) if rows else None)


async def ensure_schema(db):
    """Garante defensivamente a tabela da lista apenas quando o fluxo a usa."""
    await db.prepare(
        """CREATE TABLE IF NOT EXISTS later_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            custom_category TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )"""
    ).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_later_items_user_category ON later_items(user_id, category, id)"
    ).run()


def install():
    app.MAIN_KB = [list(row) for row in operational_menu.MAIN_KB]
    app.COTIDIANO_KB = [list(row) for row in operational_menu.COTIDIANO_KB]


async def _resolve_user(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_rowget(row, "id")) if row else None


async def _handle_reminder_followup(db, token, chat_id, uid, text, state, payload):
    if state not in {"natural_when", "natural_when_time"}:
        return False

    if text == "❌ Cancelar ação":
        await app.clear_state(db, uid)
        await _send(token, chat_id, "Cancelei. Não salvei o lembrete.", app.MAIN_KB)
        return True

    if state == "natural_when":
        d = parse_date(text, app.now_local().date())
        tm = parse_time(text)
        if d and not tm:
            payload["due_date"] = d.isoformat()
            await app.set_state(db, uid, "natural_when_time", payload)
            await _send(token, chat_id, "Peguei o dia. Falta só a hora, tipo `15h` ou `15:30`.", CANCEL_KB)
            return True
        if not d or not tm:
            await _send(token, chat_id, "Preciso do dia. Pode mandar `hoje`, `amanhã`, `sexta` ou `24/09`.", CANCEL_KB)
            return True
    else:
        d_raw = payload.get("due_date")
        try:
            from datetime import date

            d = date.fromisoformat(d_raw) if d_raw else None
        except Exception:
            d = None
        tm = parse_time(text)
        if not tm:
            await _send(token, chat_id, "Só falta o horário. Ex.: `15h`, `15:30` ou `18h`.", CANCEL_KB)
            return True

    ok, msg = validate_future(d, tm, app.now_local().replace(tzinfo=None))
    if not ok:
        await _send(token, chat_id, msg, CANCEL_KB)
        return True

    await db.prepare(
        "INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,?,?,?,?,'pendente')"
    ).bind(uid, payload.get("kind", "tarefa"), payload.get("title", "Lembrete"), d.isoformat(), tm).run()
    await app.clear_state(db, uid)
    await _send(token, chat_id, f"✅ Fechado: {payload.get('title', 'Lembrete')} — {d.strftime('%d/%m')} às {tm}.", app.MAIN_KB)
    return True


async def _list_category(db, token, chat_id, uid, category):
    if category == "outra":
        result = await db.prepare(
            "SELECT id,name,custom_category FROM later_items WHERE user_id=? AND category='outra' ORDER BY custom_category,name"
        ).bind(uid).all()
    else:
        result = await db.prepare(
            "SELECT id,name,custom_category FROM later_items WHERE user_id=? AND category=? ORDER BY name"
        ).bind(uid, category).all()
    rows = list(getattr(result, "results", []) or [])
    if not rows:
        label = CATEGORY_EMPTY_LABELS[category]
        await _send(token, chat_id, f"Ainda não há {label} nessa lista.", LATER_KB)
        return
    parts = [CATEGORY_TITLES[category]]
    for row in rows:
        suffix = f" [{_rowget(row, 'custom_category')}]" if category == "outra" and _rowget(row, "custom_category") else ""
        parts.append(f"#{_rowget(row, 'id')} • {_rowget(row, 'name')}{suffix}")
    await _send(token, chat_id, "\n".join(parts), LATER_KB)


async def _handle_later_state(db, token, chat_id, uid, text, state, payload):
    if not state or not state.startswith("later_"):
        return False
    if text == "❌ Cancelar ação":
        await app.clear_state(db, uid)
        await _send(token, chat_id, "Operação cancelada.", LATER_KB)
        return True

    if state == "later_add_category":
        category = CATEGORY_CHOICES.get(text)
        if not category:
            await _send(token, chat_id, "Escolha Livro, Filme, Curso ou Outra.", CATEGORY_KB)
            return True
        payload["category"] = category
        await app.set_state(db, uid, "later_add_name", payload)
        await _send(token, chat_id, "Qual é o nome?", CANCEL_KB)
        return True

    if state == "later_add_name":
        name = text.strip()
        if len(name) < 1:
            await _send(token, chat_id, "Informe um nome válido.", CANCEL_KB)
            return True
        payload["name"] = name
        if payload.get("category") == "outra":
            await app.set_state(db, uid, "later_add_custom", payload)
            await _send(token, chat_id, "Que tipo é? Ex.: série, HQ, documentário, artigo...", CANCEL_KB)
            return True
        await db.prepare(
            "INSERT INTO later_items(user_id,name,category,custom_category) VALUES(?,?,?,NULL)"
        ).bind(uid, name, payload["category"]).run()
        await app.clear_state(db, uid)
        await _send(token, chat_id, f"✅ {name} foi salvo para depois.", LATER_KB)
        return True

    if state == "later_add_custom":
        custom = text.strip()
        if not custom:
            await _send(token, chat_id, "Informe o tipo desse item.", CANCEL_KB)
            return True
        await db.prepare(
            "INSERT INTO later_items(user_id,name,category,custom_category) VALUES(?,?,'outra',?)"
        ).bind(uid, payload["name"], custom).run()
        await app.clear_state(db, uid)
        await _send(token, chat_id, f"✅ {payload['name']} foi salvo em {custom}.", LATER_KB)
        return True

    if state in {"later_edit_id", "later_remove_id"}:
        raw = text.strip().lstrip("#")
        if not raw.isdigit():
            await _send(token, chat_id, "Digite somente o número do item.", CANCEL_KB)
            return True
        row = await db.prepare(
            "SELECT id,name,category,custom_category FROM later_items WHERE user_id=? AND id=?"
        ).bind(uid, int(raw)).first()
        if not row:
            await _send(token, chat_id, "Não encontrei esse item.", CANCEL_KB)
            return True
        if state == "later_remove_id":
            await db.prepare("DELETE FROM later_items WHERE user_id=? AND id=?").bind(uid, int(raw)).run()
            await app.clear_state(db, uid)
            await _send(token, chat_id, f"🗑️ {_rowget(row, 'name')} removido da lista.", LATER_KB)
            return True
        payload = {
            "id": int(raw),
            "category": _rowget(row, "category"),
            "custom_category": _rowget(row, "custom_category"),
        }
        await app.set_state(db, uid, "later_edit_name", payload)
        await _send(token, chat_id, f"Novo nome para {_rowget(row, 'name')}?", CANCEL_KB)
        return True

    if state == "later_edit_name":
        name = text.strip()
        if not name:
            await _send(token, chat_id, "Informe um nome válido.", CANCEL_KB)
            return True
        await db.prepare(
            "UPDATE later_items SET name=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND id=?"
        ).bind(name, uid, payload["id"]).run()
        await app.clear_state(db, uid)
        await _send(token, chat_id, "✅ Item atualizado.", LATER_KB)
        return True

    return False


async def handle_message(db, token, message):
    # Primeiro handler comum do dispatcher: abre um cache novo por update para os
    # módulos seguintes reaproveitarem usuário/estado.
    reset_request_cache()

    text = (message.get("text") or "").strip()
    chat_id = int((message.get("chat") or {}).get("id") or 0)
    if not text or not chat_id:
        return False

    uid = await _resolve_user(db, chat_id)
    if uid is None:
        return False
    state, payload = await app.get_state(db, uid)

    relevant_state = state in {"natural_when", "natural_when_time"} or bool(state and state.startswith("later_"))
    if not relevant_state and text not in LATER_ENTRY_TEXTS:
        return False

    # O DDL defensivo da lista só roda quando a própria lista está em uso.
    if (state and state.startswith("later_")) or text in LATER_SCHEMA_TEXTS:
        await ensure_schema(db)

    if await _handle_reminder_followup(db, token, chat_id, uid, text, state, payload):
        return True
    if await _handle_later_state(db, token, chat_id, uid, text, state, payload):
        return True

    if text == "📌 Ler/ver depois":
        await _send(
            token,
            chat_id,
            "📌 Ler/ver depois\n\nUma lista simples para guardar livros, filmes, cursos e outras coisas para depois.",
            LATER_KB,
        )
        return True
    if text == "⬅️ Voltar ao cotidiano":
        await _send(token, chat_id, "🏠 Cotidiano", app.COTIDIANO_KB)
        return True
    if text == "➕ Adicionar à lista":
        await app.set_state(db, uid, "later_add_category", {})
        await _send(token, chat_id, "Qual categoria?", CATEGORY_KB)
        return True
    if text == "📚 Livros":
        await _list_category(db, token, chat_id, uid, "livro")
        return True
    if text == "🎬 Filmes":
        await _list_category(db, token, chat_id, uid, "filme")
        return True
    if text == "🎓 Cursos":
        await _list_category(db, token, chat_id, uid, "curso")
        return True
    if text == "🗂️ Outras":
        await _list_category(db, token, chat_id, uid, "outra")
        return True
    if text == "✏️ Editar item":
        await app.set_state(db, uid, "later_edit_id", {})
        await _send(token, chat_id, "Digite o número do item que deseja editar.", CANCEL_KB)
        return True
    if text == "🗑️ Remover item":
        await app.set_state(db, uid, "later_remove_id", {})
        await _send(token, chat_id, "Digite o número do item que deseja remover.", CANCEL_KB)
        return True

    return False
