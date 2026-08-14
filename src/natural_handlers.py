import os
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from src.assistant_views import WEEKDAYS, _day_parts
from src.daily_store import add_item, complete_item, list_items
from src.database import preferred_name
from src.finance_store import add_entry, month_report
from src.home_store import add_grocery_item
from src.natural_language import Intent, interpret, normalize, parse_date, parse_time, validate_future
from src.natural_store import event_count, record_event
from src.ui_layout import MAIN_KEYBOARD


def _fmt_money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "sem data"


def _flow_active(context: ContextTypes.DEFAULT_TYPE) -> bool:
    keys = {
        "new_daily_item", "quick_capture", "quick_item", "grocery", "goal", "workout", "routine",
        "goal_progress", "finance", "schedule_import", "protocol_log_exercises", "protocol_sub_exercises",
        "series_exercises", "history_names", "preferred_name_pending", "academic_edit", "natural_pending",
    }
    return any(key in context.user_data for key in keys if key != "natural_pending")


def _button_like(text: str) -> bool:
    return bool(re.match(r"^[\U0001F300-\U0001FAFF✅➕➖📅📚🏠🗓️🛒🎯🧘💰⬅️❌☑️✏️🗑️📋📈📊🔥🏋️🌙]", text.strip()))


def _find_candidates(kind: str, target: str | None, only_pending: bool = True):
    rows = list_items(kind=kind, only_pending=only_pending)
    if not rows:
        return []
    if not target:
        today = date.today().isoformat()
        def key(row):
            due = row["due_date"] or "9999-12-31"
            time = row["due_time"] or "23:59"
            return (0 if due == today else 1, due, time)
        return sorted(rows, key=key)[:3]
    target_n = normalize(target)
    scored = []
    for row in rows:
        title_n = normalize(row["title"])
        score = max(SequenceMatcher(None, target_n, title_n).ratio(), SequenceMatcher(None, target_n, title_n).quick_ratio())
        if target_n in title_n or title_n in target_n:
            score = max(score, .88)
        if score >= .42:
            scored.append((score, row))
    return [row for _, row in sorted(scored, key=lambda x: x[0], reverse=True)[:3]]


def _infer_category(description: str | None, kind: str) -> str:
    if kind == "entrada":
        return "renda"
    n = normalize(description or "")
    mapping = {
        "alimentação": ("lanche", "almoco", "almoço", "janta", "comida", "mercado", "cafe", "café", "restaurante", "ifood"),
        "transporte": ("uber", "99", "onibus", "ônibus", "gasolina", "combustivel", "combustível", "passagem"),
        "lazer": ("jogo", "cinema", "streaming", "festa", "bar", "show"),
        "compras": ("roupa", "amazon", "shopee", "mercado livre", "acessorio", "acessório", "compra"),
    }
    for category, words in mapping.items():
        if any(normalize(word) in n for word in words):
            return category
    return "outros"


def _agenda_text(target: date) -> str:
    weekday = WEEKDAYS[target.weekday()]
    parts = [f"📆 *{weekday.capitalize()}, {target.strftime('%d/%m/%Y')}*\n"]
    parts.extend(_day_parts(target, include_overdue=(target == date.today())))
    return "\n".join(parts)


def _overdue_text() -> str:
    rows = [r for r in list_items(kind="tarefa", only_pending=True) if r["due_date"] and r["due_date"] < date.today().isoformat()]
    if not rows:
        return "📌 Nada vencido. Eu até conferi duas vezes porque isso parece suspeitamente organizado."
    parts = [f"📌 *Pendências vencidas — {len(rows)}*\n"]
    for row in rows[:10]:
        due = datetime.fromisoformat(row["due_date"]).strftime("%d/%m")
        parts.append(f"• {row['title']} — venceu em {due}")
    if len(rows) > 10:
        parts.append(f"• ...e mais {len(rows)-10}. Não, eu não perdi a conta.")
    return "\n".join(parts)


def _finance_report_text() -> str:
    income, expenses, balance, cats, limits = month_report()
    if not income and not expenses:
        return "💰 Você pediu números, mas ainda não me deu números. Cadastre entradas e saídas primeiro; eu continuo sem acesso ao Banco Central da sua consciência."
    parts = ["💰 *Finanças deste mês*", f"• Entrou: *{_fmt_money(income)}*", f"• Saiu: *{_fmt_money(expenses)}*", f"• Saldo registrado: *{_fmt_money(balance)}*"]
    if cats:
        parts.append("\n*Maiores saídas:*")
        for category, amount in sorted(cats.items(), key=lambda x: x[1], reverse=True)[:4]:
            parts.append(f"• {category.title()}: {_fmt_money(amount)}")
    alerts = [(c, v, limits[c]) for c, v in cats.items() if c in limits and v > limits[c]]
    if alerts:
        parts.append("\n🚨 *Excessos:*" )
        for c, v, limit in alerts:
            parts.append(f"• {c.title()}: {_fmt_money(v)} / {_fmt_money(limit)}")
    return "\n".join(parts)


async def _ask_missing(update: Update, context: ContextTypes.DEFAULT_TYPE, intent: Intent) -> None:
    context.user_data["natural_pending"] = {"name": intent.name, **intent.data}
    missing = []
    if not intent.data.get("date"): missing.append("dia")
    if intent.name == "appointment_create" and not intent.data.get("time"): missing.append("horário")
    if intent.name == "task_create" and intent.data.get("date") and not intent.data.get("time"): missing.append("horário")
    what = " e ".join(missing) or "informação"
    await update.message.reply_text(f"Entendi *{intent.data.get('title') or 'isso'}*. Só falta o {what}. Pode mandar de forma natural, tipo `amanhã às 15h` ou `sexta 10h`.", parse_mode="Markdown")


async def natural_followup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pending = context.user_data.get("natural_pending")
    if not pending or not update.message:
        return
    text = update.message.text or ""
    if text == "❌ Cancelar ação":
        context.user_data.pop("natural_pending", None)
        await update.message.reply_text("Cancelei. Nenhum compromisso sofreu durante este processo.", reply_markup=MAIN_KEYBOARD)
        raise ApplicationHandlerStop
    d = parse_date(text)
    t = parse_time(text)
    if d: pending["date"] = d
    if t: pending["time"] = t
    if not pending.get("date"):
        await update.message.reply_text("Ainda não peguei o dia. Ex.: `amanhã`, `sexta` ou `20/08`.")
        raise ApplicationHandlerStop
    if pending["name"] == "appointment_create" and not pending.get("time"):
        await update.message.reply_text("Peguei o dia. Falta só a hora, tipo `15h` ou `15:30`.")
        raise ApplicationHandlerStop
    if pending["name"] == "task_create" and not pending.get("time"):
        # tarefa com data pode existir sem hora, mas a frase de follow-up normalmente veio para completar o lembrete
        await update.message.reply_text("Quer horário também? Mande `15h` ou diga `sem horário`.")
        if normalize(text) in {"sem horario", "sem hora"}:
            pending["time"] = None
        else:
            raise ApplicationHandlerStop
    valid, error = validate_future(pending.get("date"), pending.get("time"))
    if not valid:
        await update.message.reply_text(error)
        raise ApplicationHandlerStop
    kind = "compromisso" if pending["name"] == "appointment_create" else "tarefa"
    add_item(kind, pending["title"], pending["date"].isoformat(), pending.get("time"), reminder_minutes=0)
    context.user_data.pop("natural_pending", None)
    when = f"{_fmt_date(pending['date'])}" + (f" às {pending['time']}" if pending.get("time") else "")
    await update.message.reply_text(f"✅ Fechado. *{pending['title']}* — {when}. Eu lembro; você aparece. Esse era o acordo implícito.", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    raise ApplicationHandlerStop


async def _handle_create(update: Update, context: ContextTypes.DEFAULT_TYPE, intent: Intent) -> None:
    title = (intent.data.get("title") or "").strip()
    d = intent.data.get("date")
    t = intent.data.get("time")
    if not title:
        await update.message.reply_text("Eu entendi que você quer registrar algo, mas perdi justamente a parte do que era. Reformula para mim.")
        return
    if t and not d:
        # horário sem dia: assume hoje apenas se ainda for futuro
        valid_today, _ = validate_future(date.today(), t)
        if valid_today:
            d = date.today()
    if intent.name == "appointment_create" and (not d or not t):
        intent.data["date"] = d; intent.data["time"] = t
        await _ask_missing(update, context, intent)
        return
    valid, error = validate_future(d, t)
    if not valid:
        await update.message.reply_text(error)
        return
    kind = "compromisso" if intent.name == "appointment_create" else "tarefa"
    add_item(kind, title, d.isoformat() if d else None, t, reminder_minutes=0)
    if d:
        when = _fmt_date(d) + (f" às {t}" if t else "")
    else:
        when = "sem data por enquanto"
    noun = "Compromisso" if kind == "compromisso" else "Tarefa"
    extra = " Eu cuido do lembrete; você cuida da parte inconveniente de realmente fazer." if kind == "tarefa" else " Eu aviso. Comparecer ainda continua sendo uma responsabilidade surpreendentemente sua."
    await update.message.reply_text(f"✅ *{noun} salvo:* {title} — {when}.{extra}", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def _handle_completion(update: Update, intent: Intent) -> None:
    candidates = _find_candidates("tarefa", intent.data.get("target"), True)
    if not candidates:
        await update.message.reply_text("Eu procurei essa tarefa e não achei nada pendente parecido. Ou você já fez, ou está tentando me convencer disso por repetição. 👀")
        return
    if len(candidates) == 1:
        row = candidates[0]
        complete_item(int(row["id"]))
        await update.message.reply_text(f"✅ *{row['title']}* concluída. Muito bem. Não espalha que eu disse isso.", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
        return
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ {r['title'][:32]}", callback_data=f"nlu_done:{r['id']}")] for r in candidates] + [[InlineKeyboardButton("❌ Nenhuma", callback_data="nlu_cancel")]])
    await update.message.reply_text("Achei mais de uma candidata. Qual delas você está alegando que finalmente terminou?", reply_markup=keyboard)


async def _handle_late(update: Update, intent: Intent) -> None:
    candidates = _find_candidates("compromisso", intent.data.get("target"), True)
    if not candidates:
        await update.message.reply_text("Você vai se atrasar, mas eu não achei um compromisso correspondente na agenda. Admirável: conseguimos o atraso sem nem localizar o evento.")
        return
    row = candidates[0]
    previous = event_count("late_notice")
    record_event("late_notice", int(row["id"]), row["title"])
    if previous == 0:
        joke = "Vou registrar como um caso isolado. Estou sendo generoso com a estatística. 😌"
    elif previous == 1:
        joke = "Segunda ocorrência. A palavra ‘isolado’ já está ficando difícil de defender. 👀"
    else:
        joke = f"Você vai se atrasar? Com {previous} aviso(s) anteriores, não chega a ser exatamente uma novidade. 😏"
    when = f" às {row['due_time']}" if row["due_time"] else ""
    await update.message.reply_text(f"⏰ *{row['title']}*{when}. {joke}\n\nNão alterei o horário do compromisso; só registrei o aviso.", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def _handle_workout_skip(update: Update, intent: Intent) -> None:
    if os.getenv("BUTLER_VARIANT", "personal") == "generic":
        await update.message.reply_text("😕 Entendi que hoje não vai rolar academia. Neste perfil eu ainda não tenho um protocolo ativo para marcar falta automaticamente, então não vou inventar histórico.", reply_markup=MAIN_KEYBOARD)
        return
    try:
        from src.protocol_mass_handlers import _today_name
        from src.protocol_mass_store import get_state, skip_today
        state = get_state()
        if not state or not state["active"]:
            await update.message.reply_text("Entendi. Mas os trabalhos ainda nem começaram oficialmente, então não vou contabilizar falta antes da largada.", reply_markup=MAIN_KEYBOARD)
            return
        reason = intent.data.get("reason")
        skip_today(int(state["current_week"]), _today_name(), reason)
        reason_text = f" Motivo: {reason}." if reason else ""
        await update.message.reply_text(f"😕 Anotado: hoje não teve treino.{reason_text} Um dia acontece. Dois começam uma conversa. Três viram estatística e eu fico insuportável.", reply_markup=MAIN_KEYBOARD)
    except Exception:
        await update.message.reply_text("Eu entendi que você não vai treinar, mas não consegui registrar isso com segurança agora. Prefiro admitir do que falsificar seu histórico.", reply_markup=MAIN_KEYBOARD)


async def _handle_finance_add(update: Update, intent: Intent) -> None:
    kind = intent.data["kind"]
    amount = float(intent.data["amount"])
    desc = intent.data.get("description")
    category = _infer_category(desc, kind)
    add_entry(kind, amount, category, desc)
    if kind == "saida":
        msg = f"💸 {_fmt_money(amount)} saiu em *{category}*. Registrado. O dinheiro corre com uma disposição física que eu gostaria de ver em outras áreas."
    else:
        msg = f"💰 {_fmt_money(amount)} entrou como *{category}*. Excelente. Por alguns segundos o fluxo financeiro apontou para o lado certo."
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def natural_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""
    if data == "nlu_cancel":
        await query.edit_message_text("Certo. Não mexi em nada.")
        return
    if data.startswith("nlu_done:"):
        item_id = int(data.split(":", 1)[1])
        row = next((r for r in list_items(kind="tarefa", only_pending=True) if int(r["id"]) == item_id), None)
        if row and complete_item(item_id):
            await query.edit_message_text(f"✅ {row['title']} concluída. Demorou? Não importa. Está feita.")
        else:
            await query.edit_message_text("Essa tarefa já mudou de estado. Pelo menos alguma coisa aconteceu.")


async def natural_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    text = (update.message.text or "").strip()
    if not text or _button_like(text) or _flow_active(context):
        return
    intent = interpret(text)
    if not intent:
        return

    if intent.name in {"task_create", "appointment_create"}:
        await _handle_create(update, context, intent)
    elif intent.name == "grocery_add":
        items = intent.data.get("items") or []
        if not items:
            return
        for item in items:
            add_grocery_item(item)
        await update.message.reply_text(f"🛒 Anotei {len(items)} item(ns): " + ", ".join(items) + ". Pronto. Memória terceirizada com sucesso.", reply_markup=MAIN_KEYBOARD)
    elif intent.name == "agenda_query":
        target = intent.data.get("date") or date.today()
        await update.message.reply_text(_agenda_text(target), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif intent.name == "agenda_range":
        parts = ["🗓️ *Próximos 7 dias*\n"]
        for offset in range(7):
            target = date.today() + timedelta(days=offset)
            parts.append(f"\n{_agenda_text(target)}")
        await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif intent.name == "overdue_query":
        await update.message.reply_text(_overdue_text(), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif intent.name == "task_complete":
        await _handle_completion(update, intent)
    elif intent.name == "late_notice":
        await _handle_late(update, intent)
    elif intent.name == "workout_skip":
        await _handle_workout_skip(update, intent)
    elif intent.name == "finance_add":
        await _handle_finance_add(update, intent)
    elif intent.name == "finance_report":
        await update.message.reply_text(_finance_report_text(), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    else:
        return
    raise ApplicationHandlerStop


def register_natural_handlers(application) -> None:
    application.add_handler(CallbackQueryHandler(natural_callback, pattern=r"^nlu_(?:done:\d+|cancel)$"), group=-8)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_followup), group=-8)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_message), group=8)
