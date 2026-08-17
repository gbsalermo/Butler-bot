import re
import unicodedata
from datetime import date

import academic_intelligence as ai
import app
from telegram_api import send_message


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9:/ ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def handle_message(db, token, message):
    chat = (message.get("chat") or {}).get("id")
    if chat is None:
        return False
    uid = await ai._uid(db, int(chat))
    if not uid:
        return False

    text = (message.get("text") or "").strip()
    n = _norm(text)
    if "prova" not in n:
        return False

    starters = (
        "marca a prova", "marque a prova", "marca minha prova", "marque minha prova",
        "coloca a prova", "coloque a prova", "bota a prova", "anota a prova",
        "agenda a prova", "agende a prova", "registra a prova", "registre a prova",
        "cadastra a prova", "cadastre a prova", "adiciona a prova", "adicione a prova",
        "marca prova", "coloca prova", "bota prova", "anota prova", "agenda prova",
        "tenho uma prova", "tenho prova", "vou ter prova", "vai ter prova", "minha prova de",
        "prova de", "prova da", "prova do",
    )
    if not any(n.startswith(x) for x in starters):
        return False

    today = ai._now().date()
    due = ai._date_from_phrase(text, today)
    tm = app.parse_time(text)

    m = re.search(
        r"prova\s+(?:de|da|do)\s+(.+?)(?=\s+(?:para|pro|pra|em|no|na|dia|hoje|amanha|segunda|terca|quarta|quinta|sexta|sabado|domingo|proxima|proximo|as)\b|\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?|$)",
        n,
    )
    subject_text = m.group(1).strip() if m else ""
    subject, subjects = await ai._subject_lookup(db, uid, subject_text)

    if not subject:
        if subject_text:
            names = "\n".join(f"• {ai._row(s,'name')}" for s in subjects[:12])
            await send_message(
                token, int(chat),
                f"Entendi que você quer marcar uma prova, mas não achei uma matéria única para `{subject_text}`.\n\nMatérias ativas:\n{names}\n\nEscolhe uma delas. Até eu tenho limites para adivinhar nome de disciplina. 😏",
                reply_markup=_kb(ai.ACADEMIC_KB),
            )
            return True
        return False

    if not due:
        await ai.runtime_guard._set_state(db, uid, "ai_exam_date", {
            "subject_id": int(ai._row(subject, "id")),
            "subject": ai._row(subject, "name"),
        })
        await send_message(
            token, int(chat),
            f"📝 Prova de {ai._row(subject,'name')}. Para quando? Pode mandar `24/09`, `dia 24`, `próxima terça`... eu faço a parte chata do calendário.",
            reply_markup=_kb(ai.CANCEL_KB),
        )
        return True

    if due < today:
        await send_message(token, int(chat), "Essa data já passou. Se a ideia era voltar no tempo para estudar antes, infelizmente o Cloudflare ainda não oferece esse binding. 😌")
        return True

    title = await ai._save_exam(db, uid, subject, due, tm)
    await send_message(
        token, int(chat),
        f"📝 {title} cadastrada para {due.strftime('%d/%m')}" + (f" às {tm}" if tm else "") + ". Vou lembrar antes. Agora a parte inconveniente: eventualmente você vai ter que estudar. 😏",
        reply_markup=_kb(ai.ACADEMIC_KB),
    )
    return True
