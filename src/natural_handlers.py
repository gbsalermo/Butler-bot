import os
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from src.assistant_views import WEEKDAYS, _day_parts
from src.daily_store import add_item, complete_item, list_items
from src.finance_store import add_entry, month_report
from src.home_store import add_grocery_item, list_missing_groceries, mark_grocery_bought
from src.natural_language import Intent, interpret, normalize, parse_date, parse_time, validate_future
from src.natural_store import event_count, record_event
from src.ui_layout import MAIN_KEYBOARD


def _fmt_money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def _fmt_date(value: date | None) -> str: return value.strftime("%d/%m/%Y") if value else "sem data"
def _flow_active(context):
    keys={"new_daily_item","quick_capture","quick_item","grocery","goal","workout","routine","goal_progress","finance","schedule_import","protocol_log_exercises","protocol_sub_exercises","series_exercises","history_names","preferred_name_pending","academic_edit"}
    return any(k in context.user_data for k in keys)
def _button_like(text:str)->bool:
    return bool(re.match(r"^[\U0001F300-\U0001FAFF✅➕➖📅📚🏠🗓️🛒🎯🧘💰⬅️❌☑️✏️🗑️📋📈📊🔥🏋️🌙]",text.strip()))

def _find_candidates(kind:str,target:str|None,only_pending=True):
    rows=list_items(kind=kind,only_pending=only_pending)
    if not rows:return []
    if not target:
        today=date.today().isoformat()
        return sorted(rows,key=lambda r:(0 if r["due_date"]==today else 1,r["due_date"] or "9999-12-31",r["due_time"] or "23:59"))[:3]
    tn=normalize(target); scored=[]
    for row in rows:
        title=normalize(row["title"]); score=SequenceMatcher(None,tn,title).ratio()
        if tn in title or title in tn:score=max(score,.9)
        if score>=.42:scored.append((score,row))
    return [r for _,r in sorted(scored,key=lambda x:x[0],reverse=True)[:3]]

def _find_groceries(target:str):
    tn=normalize(target); scored=[]
    for row in list_missing_groceries():
        name=normalize(row["name"]); score=SequenceMatcher(None,tn,name).ratio()
        if tn in name or name in tn:score=max(score,.9)
        if score>=.42:scored.append((score,row))
    return [r for _,r in sorted(scored,key=lambda x:x[0],reverse=True)[:3]]

def _infer_category(description:str|None,kind:str)->str:
    if kind=="entrada":return "renda"
    n=normalize(description or "")
    mapping={"alimentação":("lanche","almoco","janta","comida","mercado","cafe","restaurante","ifood"),"transporte":("uber","99","onibus","gasolina","combustivel","passagem"),"lazer":("jogo","cinema","streaming","festa","bar","show"),"compras":("roupa","amazon","shopee","mercado livre","acessorio","compra")}
    for category,words in mapping.items():
        if any(normalize(w) in n for w in words):return category
    return "outros"

def _agenda_text(target:date)->str:
    parts=[f"📆 *{WEEKDAYS[target.weekday()].capitalize()}, {target.strftime('%d/%m/%Y')}*\n"]; parts.extend(_day_parts(target,include_overdue=(target==date.today()))); return "\n".join(parts)
def _overdue_text()->str:
    rows=[r for r in list_items(kind="tarefa",only_pending=True) if r["due_date"] and r["due_date"]<date.today().isoformat()]
    if not rows:return "📌 Nada vencido. Eu até conferi duas vezes porque isso parece suspeitamente organizado."
    parts=[f"📌 *Pendências vencidas — {len(rows)}*\n"]
    for row in rows[:10]:parts.append(f"• {row['title']} — venceu em {datetime.fromisoformat(row['due_date']).strftime('%d/%m')}")
    if len(rows)>10:parts.append(f"• ...e mais {len(rows)-10}. Não, eu não perdi a conta.")
    return "\n".join(parts)
def _grocery_text()->str:
    rows=list_missing_groceries()
    if not rows:return "🛒 Não está faltando nada registrado. Ou a casa está abastecida, ou ninguém me contou."
    return "🛒 *Faltando em casa*\n\n"+"\n".join(f"• {r['name']}"+(f" — {r['quantity']}" if r['quantity'] else "") for r in rows)
def _finance_report_text()->str:
    income,expenses,balance,cats,limits=month_report()
    if not income and not expenses:return "💰 Você pediu números, mas ainda não me deu números. Cadastre entradas e saídas primeiro; eu continuo sem acesso ao Banco Central da sua consciência."
    parts=["💰 *Finanças deste mês*",f"• Entrou: *{_fmt_money(income)}*",f"• Saiu: *{_fmt_money(expenses)}*",f"• Saldo registrado: *{_fmt_money(balance)}*"]
    if cats:
        parts.append("\n*Maiores saídas:*"); parts += [f"• {c.title()}: {_fmt_money(v)}" for c,v in sorted(cats.items(),key=lambda x:x[1],reverse=True)[:4]]
    alerts=[(c,v,limits[c]) for c,v in cats.items() if c in limits and v>limits[c]]
    if alerts:
        parts.append("\n🚨 *Excessos:*"); parts += [f"• {c.title()}: {_fmt_money(v)} / {_fmt_money(l)}" for c,v,l in alerts]
    return "\n".join(parts)

async def _ask_missing(update,context,intent):
    context.user_data["natural_pending"]={"name":intent.name,**intent.data}
    missing=[]
    if not intent.data.get("date"):missing.append("dia")
    if (intent.name=="appointment_create" or intent.data.get("reminder_request")) and not intent.data.get("time"):missing.append("horário")
    await update.message.reply_text(f"Entendi *{intent.data.get('title') or 'isso'}*. Só falta {' e '.join(missing) or 'um detalhe'}. Pode mandar `amanhã às 15h`, `sexta 10h` etc.",parse_mode="Markdown")

async def natural_followup(update:Update,context:ContextTypes.DEFAULT_TYPE):
    pending=context.user_data.get("natural_pending")
    if not pending or not update.message:return
    text=update.message.text or ""
    if text=="❌ Cancelar ação":
        context.user_data.pop("natural_pending",None); await update.message.reply_text("Cancelei. Nenhum compromisso sofreu durante este processo.",reply_markup=MAIN_KEYBOARD); raise ApplicationHandlerStop
    d,t=parse_date(text),parse_time(text)
    if d:pending["date"]=d
    if t:pending["time"]=t
    if not pending.get("date"):
        await update.message.reply_text("Ainda não peguei o dia. Ex.: `amanhã`, `sexta` ou `20/08`.",parse_mode="Markdown"); raise ApplicationHandlerStop
    if (pending["name"]=="appointment_create" or pending.get("reminder_request")) and not pending.get("time"):
        await update.message.reply_text("Peguei o dia. Falta só a hora, tipo `15h` ou `15:30`.",parse_mode="Markdown"); raise ApplicationHandlerStop
    valid,error=validate_future(pending.get("date"),pending.get("time"))
    if not valid:await update.message.reply_text(error); raise ApplicationHandlerStop
    kind="compromisso" if pending["name"]=="appointment_create" else "tarefa"
    add_item(kind,pending["title"],pending["date"].isoformat(),pending.get("time"),reminder_minutes=0)
    context.user_data.pop("natural_pending",None)
    when=_fmt_date(pending["date"])+(f" às {pending['time']}" if pending.get("time") else "")
    await update.message.reply_text(f"✅ Fechado. *{pending['title']}* — {when}. Eu lembro; você aparece. Esse era o acordo implícito.",parse_mode="Markdown",reply_markup=MAIN_KEYBOARD); raise ApplicationHandlerStop

async def _handle_create(update,context,intent):
    title=(intent.data.get("title") or "").strip(); d=intent.data.get("date"); t=intent.data.get("time"); reminder_request=bool(intent.data.get("reminder_request"))
    if not title:await update.message.reply_text("Entendi que você quer registrar algo, mas perdi justamente o que era. Reformula para mim."); return
    if t and not d:
        valid,_=validate_future(date.today(),t)
        if valid:d=date.today()
    if (intent.name=="appointment_create" and (not d or not t)) or (reminder_request and (not d or not t)):
        intent.data["date"],intent.data["time"]=d,t; await _ask_missing(update,context,intent); return
    valid,error=validate_future(d,t)
    if not valid:await update.message.reply_text(error); return
    kind="compromisso" if intent.name=="appointment_create" else "tarefa"; add_item(kind,title,d.isoformat() if d else None,t,reminder_minutes=0)
    when=(_fmt_date(d)+(f" às {t}" if t else "")) if d else "sem data por enquanto"
    if kind=="compromisso": extra="Eu aviso. Comparecer continua sendo uma responsabilidade surpreendentemente sua."
    elif d and t: extra="Eu cuido do lembrete; você cuida da parte inconveniente de realmente fazer."
    else: extra="Salvei na lista. Sem data e hora eu não vou fingir que existe lembrete automático."
    await update.message.reply_text(f"✅ *{'Compromisso' if kind=='compromisso' else 'Tarefa'} salvo:* {title} — {when}. {extra}",parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)

async def _handle_completion(update,intent):
    candidates=_find_candidates("tarefa",intent.data.get("target"),True)
    if not candidates:await update.message.reply_text("Não achei tarefa pendente parecida. Ou você já fez, ou está tentando me convencer por repetição. 👀"); return
    if len(candidates)==1:
        row=candidates[0]; complete_item(int(row["id"])); await update.message.reply_text(f"✅ *{row['title']}* concluída. Muito bem. Não espalha que eu disse isso.",parse_mode="Markdown",reply_markup=MAIN_KEYBOARD); return
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ {r['title'][:32]}",callback_data=f"nlu_done:{r['id']}")] for r in candidates]+[[InlineKeyboardButton("❌ Nenhuma",callback_data="nlu_cancel")]])
    await update.message.reply_text("Achei mais de uma candidata. Qual você finalmente terminou?",reply_markup=kb)

def _late_message(row)->str:
    previous=event_count("late_notice"); record_event("late_notice",int(row["id"]),row["title"])
    joke="Vou registrar como caso isolado. Estou sendo generoso com a estatística. 😌" if previous==0 else ("Segunda ocorrência. A palavra ‘isolado’ já está ficando difícil de defender. 👀" if previous==1 else f"Você vai se atrasar? Com {previous} aviso(s) anteriores, não chega a ser exatamente uma novidade. 😏")
    when=f" às {row['due_time']}" if row["due_time"] else ""; return f"⏰ *{row['title']}*{when}. {joke}\n\nNão alterei o horário; só registrei o aviso."

async def _handle_late(update,intent):
    candidates=_find_candidates("compromisso",intent.data.get("target"),True)
    if not candidates:await update.message.reply_text("Você vai se atrasar, mas eu não achei o compromisso na agenda. Conseguimos o atraso antes mesmo de localizar o evento."); return
    if len(candidates)>1:
        kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"⏰ {r['title'][:32]}",callback_data=f"nlu_late:{r['id']}")] for r in candidates]+[[InlineKeyboardButton("❌ Nenhum",callback_data="nlu_cancel")]])
        await update.message.reply_text("Para qual compromisso? Eu faço piada, mas tento fazer a piada sobre o evento certo.",reply_markup=kb); return
    await update.message.reply_text(_late_message(candidates[0]),parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)

async def _handle_grocery_bought(update,intent):
    candidates=_find_groceries(intent.data.get("target") or "")
    if not candidates:await update.message.reply_text("Não achei esse item entre os que estavam faltando. Talvez você tenha comprado tão rápido que nem deu tempo de me avisar antes."); return
    if len(candidates)==1:
        row=candidates[0]; mark_grocery_bought(int(row["id"])); await update.message.reply_text(f"🛒 Tirei *{row['name']}* da lista. Uma preocupação doméstica a menos.",parse_mode="Markdown",reply_markup=MAIN_KEYBOARD); return
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 {r['name'][:32]}",callback_data=f"nlu_grocery:{r['id']}")] for r in candidates]+[[InlineKeyboardButton("❌ Nenhum",callback_data="nlu_cancel")]])
    await update.message.reply_text("Qual desses você comprou?",reply_markup=kb)

async def _handle_workout_skip(update,intent):
    if os.getenv("BUTLER_VARIANT","personal")=="generic":
        await update.message.reply_text("😕 Entendi que hoje não vai rolar academia. Neste perfil ainda não tenho protocolo ativo para contabilizar falta sem inventar histórico.",reply_markup=MAIN_KEYBOARD); return
    try:
        from src.protocol_mass_handlers import _today_name
        from src.protocol_mass_store import get_state,skip_today
        state=get_state()
        if not state or not state["active"]:await update.message.reply_text("Entendi. Mas os trabalhos ainda nem começaram oficialmente, então não vou contar falta antes da largada.",reply_markup=MAIN_KEYBOARD); return
        reason=intent.data.get("reason"); skip_today(int(state["current_week"]),_today_name(),reason)
        await update.message.reply_text(f"😕 Anotado: hoje não teve treino.{f' Motivo: {reason}.' if reason else ''} Um dia acontece. Dois começam uma conversa. Três viram estatística e eu fico insuportável.",reply_markup=MAIN_KEYBOARD)
    except Exception:
        await update.message.reply_text("Entendi que você não vai treinar, mas não consegui registrar com segurança. Prefiro admitir do que falsificar seu histórico.",reply_markup=MAIN_KEYBOARD)

async def _handle_finance_add(update,intent):
    kind=intent.data["kind"]; amount=float(intent.data["amount"]); desc=intent.data.get("description"); category=_infer_category(desc,kind); add_entry(kind,amount,category,desc)
    msg=f"💸 {_fmt_money(amount)} saiu em *{category}*. Registrado. O dinheiro corre com uma disposição física que eu gostaria de ver em outras áreas." if kind=="saida" else f"💰 {_fmt_money(amount)} entrou como *{category}*. Excelente. Por alguns segundos o fluxo apontou para o lado certo."
    await update.message.reply_text(msg,parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)

async def natural_callback(update,context):
    q=update.callback_query
    if not q:return
    await q.answer(); data=q.data or ""
    if data=="nlu_cancel":await q.edit_message_text("Certo. Não mexi em nada."); return
    prefix,item=data.split(":",1); item_id=int(item)
    if prefix=="nlu_done":
        row=next((r for r in list_items(kind="tarefa",only_pending=True) if int(r["id"])==item_id),None)
        await q.edit_message_text(f"✅ {row['title']} concluída. Demorou? Não importa. Está feita." if row and complete_item(item_id) else "Essa tarefa já mudou de estado.")
    elif prefix=="nlu_late":
        row=next((r for r in list_items(kind="compromisso",only_pending=True) if int(r["id"])==item_id),None)
        if row:await q.edit_message_text(_late_message(row),parse_mode="Markdown")
        else:await q.edit_message_text("Esse compromisso já mudou de estado.")
    elif prefix=="nlu_grocery":
        row=next((r for r in list_missing_groceries() if int(r["id"])==item_id),None)
        if row and mark_grocery_bought(item_id):await q.edit_message_text(f"🛒 {row['name']} saiu da lista. Menos uma coisa para esquecer.")
        else:await q.edit_message_text("Esse item já não estava mais na lista.")

async def natural_message(update,context):
    if not update.message or not update.effective_chat:return
    text=(update.message.text or "").strip()
    if not text or _button_like(text) or _flow_active(context):return
    intent=interpret(text)
    if not intent:return
    if intent.name in {"task_create","appointment_create"}:await _handle_create(update,context,intent)
    elif intent.name=="grocery_add":
        items=intent.data.get("items") or []
        for item in items:add_grocery_item(item)
        await update.message.reply_text(f"🛒 Anotei {len(items)} item(ns): "+", ".join(items)+". Memória terceirizada com sucesso.",reply_markup=MAIN_KEYBOARD)
    elif intent.name=="grocery_query":await update.message.reply_text(_grocery_text(),parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)
    elif intent.name=="grocery_bought":await _handle_grocery_bought(update,intent)
    elif intent.name=="agenda_query":await update.message.reply_text(_agenda_text(intent.data.get("date") or date.today()),parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)
    elif intent.name=="agenda_range":
        parts=["🗓️ *Próximos 7 dias*"]; parts += [_agenda_text(date.today()+timedelta(days=i)) for i in range(7)]; await update.message.reply_text("\n\n".join(parts),parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)
    elif intent.name=="overdue_query":await update.message.reply_text(_overdue_text(),parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)
    elif intent.name=="task_complete":await _handle_completion(update,intent)
    elif intent.name=="late_notice":await _handle_late(update,intent)
    elif intent.name=="workout_skip":await _handle_workout_skip(update,intent)
    elif intent.name=="finance_add":await _handle_finance_add(update,intent)
    elif intent.name=="finance_report":await update.message.reply_text(_finance_report_text(),parse_mode="Markdown",reply_markup=MAIN_KEYBOARD)
    else:return
    raise ApplicationHandlerStop

def register_natural_handlers(application):
    application.add_handler(CallbackQueryHandler(natural_callback,pattern=r"^nlu_(?:done|late|grocery):\d+$|^nlu_cancel$"),group=-8)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,natural_followup),group=-8)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,natural_message),group=8)
