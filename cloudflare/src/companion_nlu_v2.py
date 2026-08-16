import json
import re
import unicodedata
from datetime import date, timedelta

import academic_intelligence as ai
from settings import OWNER_CHAT_ID
from telegram_api import send_message

YES = ("sim", "pode", "pode sim", "faz isso", "faça isso", "bora", "manda ver", "fechou", "cria", "cria sim")
NO = ("nao", "não", "deixa", "deixa pra la", "deixa pra lá", "melhor nao", "melhor não", "cancela")

TOPICS = {
    "faculdade": ("faculdade", "prova", "provas", "materia", "matéria", "estudar", "estudo", "trabalho da faculdade", "semestre"),
    "dinheiro": ("dinheiro", "grana", "gasto", "gastei", "conta", "cartao", "cartão", "apertado", "bolsa"),
    "treino": ("treino", "academia", "musculacao", "musculação", "carga", "exercicio", "exercício"),
    "trabalho": ("estagio", "estágio", "trabalho", "servico", "serviço", "empresa", "codigo", "código"),
    "relacionamento": ("menina", "garota", "mulher", "namoro", "relacao", "relação", "ficante", "conversa com ela"),
    "saude": ("saude", "saúde", "dor", "cansaco", "cansaço", "sono", "peid", "gases", "barriga", "intestino", "cafe", "café"),
    "habitos": ("rotina", "habito", "hábito", "procrast", "enrolando", "adiando", "disciplina", "foco"),
}

NEGATIVE = (
    "to na merda", "tô na merda", "meio na merda", "ta foda", "tá foda", "fudido", "fudida",
    "desanimado", "desanimada", "preocupado", "preocupada", "ansioso", "ansiosa", "frustrado",
    "frustrada", "nao sei o que fazer", "não sei o que fazer", "complicado", "sobrecarregado",
    "sobrecarregada", "sem vontade", "sem animo", "sem ânimo", "to mal", "tô mal",
)

RECOMMENDATIONS = {
    "faculdade": {
        "livro": "A Mind for Numbers, da Barbara Oakley",
        "filme": "Sociedade dos Poetas Mortos, mais pelo jeito de olhar estudo e propósito do que por técnica",
        "desenho": "um episódio curto de Bluey pode servir melhor que fingir produtividade por duas horas quando a cabeça já saturou",
        "youtube": "procura por 'Barbara Oakley Learning How to Learn procrastination' ou 'active recall spaced repetition português'",
    },
    "habitos": {
        "livro": "Hábitos Atômicos, do James Clear",
        "filme": "Feitiço do Tempo, se quiser algo leve sobre repetição, escolha e mudança de padrão",
        "desenho": "BoJack Horseman tem episódios bons sobre padrão de comportamento, mas é uma indicação mais pesada",
        "youtube": "procura por 'James Clear hábitos identidade' ou 'procrastinação Tim Urban TED'",
    },
    "relacionamento": {
        "livro": "Comunicação Não Violenta, do Marshall Rosenberg, se a questão for conversar sem transformar tudo em disputa",
        "filme": "Questão de Tempo, se quiser algo leve sobre relacionamento sem manual de conquista",
        "desenho": "Hora de Aventura tem muita coisa boa sobre afeto, rejeição e amadurecimento escondida no caos",
        "youtube": "procura por 'comunicação não violenta relacionamentos' em vez de guru de conquista, pelo amor da firma",
    },
    "trabalho": {
        "livro": "O Programador Pragmático, se o problema estiver mais ligado a trabalho e desenvolvimento",
        "filme": "A Vida Secreta de Walter Mitty, se o peso for mais de direção e rotina do que técnico",
        "desenho": "Aggretsuko é praticamente terapia ocupacional em formato de desenho com death metal",
        "youtube": "procura por 'burnout trabalho organização prioridades' e evita vídeo prometendo produtividade de 18 horas por dia",
    },
}


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
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


async def _uid(db, chat_id):
    return await ai._uid(db, chat_id)


async def _save_state(db, uid, kind, payload):
    detail = json.dumps({"kind": kind, "payload": payload}, ensure_ascii=False)
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'companion_v2',?)").bind(uid, detail).run()


async def _last_state(db, uid):
    row = await db.prepare(
        "SELECT detail FROM natural_events WHERE user_id=? AND event_type='companion_v2' AND created_at>=datetime('now','-6 hours') ORDER BY id DESC LIMIT 1"
    ).bind(uid).first()
    if not row:
        return None
    try:
        return json.loads(_row(row, "detail") or "{}")
    except Exception:
        return None


def _has(text, words):
    n = _norm(text)
    return any(_norm(word) in n for word in words)


def _topic(text):
    n = _norm(text)
    scored = []
    for name, markers in TOPICS.items():
        score = sum(1 for marker in markers if _norm(marker) in n)
        if score:
            scored.append((score, name))
    return max(scored)[1] if scored else None


def _is_yes(n):
    return n in {_norm(x) for x in YES} or any(n.startswith(_norm(x) + " ") for x in YES)


def _is_no(n):
    return n in {_norm(x) for x in NO} or any(n.startswith(_norm(x) + " ") for x in NO)


def _relative_exam_date(text):
    n = _norm(text)
    m = re.search(r"daqui a (\d+) semanas?", n)
    if m:
        return ai._now().date() + timedelta(days=7 * int(m.group(1)))
    m = re.search(r"daqui a (\d+) dias?", n)
    if m:
        return ai._now().date() + timedelta(days=int(m.group(1)))
    return ai._date_from_phrase(text, ai._now().date())


async def _subject_matches(db, uid, text):
    subjects = await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    n = _norm(text)
    matches = []
    for subject in subjects:
        name = _norm(_row(subject, "name") or "")
        tokens = [t for t in name.split() if len(t) >= 4]
        if name and (name in n or any(t in n for t in tokens)):
            matches.append(subject)
    unique = []
    ids = set()
    for subject in matches:
        sid = int(_row(subject, "id"))
        if sid not in ids:
            ids.add(sid)
            unique.append(subject)
    return unique, subjects


async def _create_exam_plan(db, uid, payload):
    due = date.fromisoformat(payload["due_date"])
    subject_ids = payload["subject_ids"]
    subjects = []
    for sid in subject_ids:
        subject = await db.prepare("SELECT id,name FROM subjects WHERE id=? AND user_id=?").bind(sid, uid).first()
        if subject:
            subjects.append(subject)
    if len(subjects) < 2:
        return 0, 0

    exams = 0
    for subject in subjects:
        detail = f"exam:{_row(subject,'id')}"
        exists = await db.prepare("SELECT id FROM daily_items WHERE user_id=? AND details=? AND due_date=? AND status='pendente' LIMIT 1").bind(uid, detail, due.isoformat()).first()
        if not exists:
            await ai._save_exam(db, uid, subject, due, None)
            exams += 1

    start = ai._now().date() + timedelta(days=1)
    total_days = max((due - start).days, 0)
    created = 0
    if total_days:
        for offset in range(total_days):
            d = start + timedelta(days=offset)
            if d >= due:
                break
            subject = subjects[offset % len(subjects)]
            remaining = (due - d).days
            if remaining <= 2:
                stage = "revisão ativa + questões-chave"
            elif remaining <= max(4, total_days // 3):
                stage = "exercícios e correção dos erros"
            else:
                stage = "teoria + resumo curto"
            title = f"Estudo — {_row(subject,'name')}: {stage}"
            details = f"study-plan:{_row(subject,'id')}:{due.isoformat()}"
            exists = await db.prepare("SELECT id FROM daily_items WHERE user_id=? AND details=? AND due_date=? LIMIT 1").bind(uid, details, d.isoformat()).first()
            if not exists:
                await db.prepare("INSERT INTO daily_items(user_id,kind,title,details,due_date,status) VALUES(?,'tarefa',?,?,?,'pendente')").bind(uid, title, details, d.isoformat()).run()
                created += 1
    return exams, created


async def _create_digestive_checkins(db, uid):
    today = ai._now().date()
    created = 0
    for i in range(1, 8):
        d = today + timedelta(days=i)
        details = "companion:digestion:7d"
        exists = await db.prepare("SELECT id FROM daily_items WHERE user_id=? AND details=? AND due_date=? LIMIT 1").bind(uid, details, d.isoformat()).first()
        if not exists:
            await db.prepare("INSERT INTO daily_items(user_id,kind,title,details,due_date,status) VALUES(?,'tarefa','Check-in: água + café + desconforto',?,?,'pendente')").bind(uid, details, d.isoformat()).run()
            created += 1
    return created


async def _handle_pending(db, token, chat_id, uid, text):
    state = await _last_state(db, uid)
    if not state:
        return False
    kind = state.get("kind")
    payload = state.get("payload") or {}
    n = _norm(text)

    if kind == "collect_exam_subjects":
        matches, subjects = await _subject_matches(db, uid, text)
        if len(matches) < 2:
            names = "\n".join(f"• {_row(s,'name')}" for s in subjects[:12])
            await send_message(token, chat_id, "Peguei a ideia, mas ainda não consegui identificar duas matérias cadastradas nessa frase. Me manda os dois nomes.\n\nAs ativas são:\n" + names)
            return True
        chosen = matches[:2]
        proposal = {
            "due_date": payload["due_date"],
            "subject_ids": [int(_row(s, "id")) for s in chosen],
            "subjects": [_row(s, "name") for s in chosen],
        }
        await _save_state(db, uid, "confirm_exam_plan", proposal)
        await send_message(token, chat_id, f"Beleza: {_row(chosen[0],'name')} e {_row(chosen[1],'name')} no dia {date.fromisoformat(payload['due_date']).strftime('%d/%m')}. Posso cadastrar as duas provas e montar um plano diário alternando teoria/resumo, exercícios e revisão até lá?")
        return True

    if kind == "confirm_exam_plan" and (_is_yes(n) or _is_no(n)):
        if _is_no(n):
            await _save_state(db, uid, "idle", {})
            await send_message(token, chat_id, "Fechado. Não mexi em nada. O caos continua artesanal.")
            return True
        exams, tasks = await _create_exam_plan(db, uid, payload)
        await _save_state(db, uid, "idle", {})
        await send_message(token, chat_id, f"Pronto. Cadastrei {exams} prova(s) que ainda não estavam salvas e criei {tasks} bloco(s) de estudo até {date.fromisoformat(payload['due_date']).strftime('%d/%m')}. Não fiz um cronograma de influencer: fui alternando conteúdo, exercício e revisão.")
        return True

    if kind == "confirm_digestive_checkin" and (_is_yes(n) or _is_no(n)):
        if _is_no(n):
            await _save_state(db, uid, "idle", {})
            await send_message(token, chat_id, "Tranquilo. Não criei rotina nenhuma. E vou fingir que esta conversa nunca envolveu seu intestino.")
            return True
        created = await _create_digestive_checkins(db, uid)
        await _save_state(db, uid, "idle", {})
        await send_message(token, chat_id, f"Feito. Criei {created} check-in(s) para os próximos 7 dias: água, café e como o desconforto ficou. É só observação de hábito, não diagnóstico. Se piorar ou vier algo preocupante, aí é assunto para avaliação de saúde, não para meu banco de dados.")
        return True

    if kind == "social_showoff":
        if any(x in n for x in ("ela ta lendo", "ela esta lendo", "ela viu", "ela ta vendo", "ela está lendo", "ela está vendo")):
            await send_message(token, chat_id, "Opa. Nesse caso: prazer. Sou extremamente profissional, ele é organizadíssimo e nenhuma das duas afirmações precisa ser auditada agora.")
            return True
        if any(x in n for x in ("ela gostou", "ela achou bonito", "ela achou bonitinho", "ela disse que tu e bonito", "ela disse que voce e bonito")):
            await send_message(token, chat_id, "Finalmente alguém nessa conversa com critério. Chefe, anota aí: minha aprovação pública está subindo.")
            return True

    return False


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id) != int(OWNER_CHAT_ID):
        return False
    uid = await _uid(db, int(chat_id))
    if not uid:
        return False
    text = (message.get("text") or "").strip()
    if not text:
        return False
    n = _norm(text)

    if await _handle_pending(db, token, int(chat_id), uid, text):
        return True

    if ("falando de tu" in n or "falando de voce" in n or "mostrando tu" in n or "mostrando voce" in n) and any(x in n for x in ("menina", "garota", "ela", "uma mina")):
        await _save_state(db, uid, "social_showoff", {})
        await send_message(token, int(chat_id), "Ih rapaz. Então capricha na propaganda. Só omite a parte em que eu preciso lembrar você das coisas que você mesmo mandou eu lembrar.")
        return True

    if any(x in n for x in ("ela ta lendo", "ela esta lendo", "ela ta vendo", "ela esta vendo")):
        state = await _last_state(db, uid)
        if state and state.get("kind") == "social_showoff":
            await send_message(token, int(chat_id), "Prazer. Não acredite em tudo que ele contou sobre mim. Principalmente se ele estiver tentando parecer organizado.")
            return True

    gas_problem = any(x in n for x in ("peidando", "peidar", "muito gas", "muitos gases", "gases demais"))
    if gas_problem:
        if any(x in n for x in ("sangue", "dor forte", "febre", "vomitando", "vomito persistente", "piorando muito")):
            await send_message(token, int(chat_id), "Aí eu corto a piada. Com sintoma forte ou sinal preocupante junto, não vou bancar médico nem tentar resolver com rotina. Vale procurar avaliação de saúde.")
            return True
        await _save_state(db, uid, "confirm_digestive_checkin", {})
        await send_message(token, int(chat_id), "Rapaz, dado operacional que eu não pedi, mas recebido. Sem inventar diagnóstico: dá para observar por 7 dias água, quantidade de café e se o desconforto melhora ou piora. Posso criar um check-in diário curto para isso. Quer?")
        return True

    exam_pressure = "prova" in n and ("duas" in n or "2" in n) and any(x in n for x in ("mesmo dia", "no mesmo dia", "nao sei o que fazer", "não sei o que fazer"))
    if exam_pressure:
        due = _relative_exam_date(text)
        if due and due > ai._now().date():
            await _save_state(db, uid, "collect_exam_subjects", {"due_date": due.isoformat()})
            await send_message(token, int(chat_id), f"Duas provas no mesmo dia em {due.strftime('%d/%m')} dá para organizar sem fazer culto ao desespero. Quais são as duas matérias? Se elas já estiverem cadastradas, eu reconheço pelo nome e monto a proposta.")
            return True

    recommendation_request = any(x in n for x in ("me indica", "indica algo", "livro", "filme", "desenho", "video", "vídeo", "youtube", "yt"))
    if recommendation_request:
        topic = _topic(text)
        if not topic:
            state = await _last_state(db, uid)
            topic = ((state or {}).get("payload") or {}).get("topic")
        catalog = RECOMMENDATIONS.get(topic or "")
        if catalog:
            await send_message(token, int(chat_id), "Tenho umas coisas nesse tema sem precisar abrir a internet:\n" + f"📚 {catalog['livro']}\n🎬 {catalog['filme']}\n📺 {catalog['desenho']}\n▶️ No YouTube: {catalog['youtube']}\n\nSe quiser, eu também posso guardar o tema e puxar uma dessas quando você estiver nesse contexto de novo.")
            return True

    if _has(text, NEGATIVE):
        topic = _topic(text)
        await _save_state(db, uid, "conversation_problem", {"topic": topic})
        if topic == "faculdade":
            await send_message(token, int(chat_id), "Entendi. Isso parece mais faculdade te atropelando do que só um 'tô desanimado'. Me diz o que está apertando mais — prova, trabalho, conteúdo acumulado ou tudo resolveu formar uma quadrilha?")
        elif topic == "dinheiro":
            await send_message(token, int(chat_id), "Peguei. Se o problema é grana, eu consigo olhar isso como problema concreto: o que está pesando mais, gasto fora do normal, conta chegando ou simplesmente entrou pouco este mês?")
        elif topic == "trabalho":
            await send_message(token, int(chat_id), "Tá. Então não vou te responder com frase de caneca. O que te quebrou mais: demanda demais, problema que não anda, gente te pressionando ou cansaço acumulado?")
        else:
            await send_message(token, int(chat_id), "É, pelo jeito o 'meio' nessa frase está fazendo hora extra. Me conta o que aconteceu; eu tento separar o que é só dia ruim do que dá para transformar em alguma ação concreta.")
        return True

    return False
