"""Experiência de treino: menu por estado e consulta semanal, sem alterar o plano."""
import re
from datetime import timedelta

import app
from owner_profile import is_owner
from telegram_api import send_message

TODAY = "📅 Treino de hoje"
TOMORROW = "📅 Treino de amanhã"
CHOOSE_DAY = "🗓️ Escolher dia"
CHOOSE_STATE = "workout_choose_day"
WEEK = "🗓️ Semana completa"
NEXT = "📆 Próximas semanas"
VIEW_WEEKS = "📆 Ver semanas"
MORE = "⚙️ Mais opções"
BACK = "⬅️ Treinos"
START = "🚀 Começar os trabalhos"
END = "⏹️ Encerrar trabalhos"
RESTART = "🔄 Reiniciar os trabalhos"
DAY_NAMES = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")


def _kb(rows):
    return app.kb(rows)


def _get(row, key, default=None):
    return app.rowget(row, key, default)


def workout_keyboard(owner, active=False, finished=False, week=None):
    """Menu da academia: apenas consulta, registro e acompanhamento diário."""
    rows = [
        [TODAY, CHOOSE_DAY],
        [VIEW_WEEKS, "📝 Registrar série"],
        ["📈 Progresso", MORE],
    ]
    if owner and not active and not finished:
        rows.append([START])
    rows.append(["⬅️ Início"])
    return rows


def weeks_keyboard(owner):
    rows = [[WEEK]]
    if owner:
        rows[0].append(NEXT)
    rows.append([BACK])
    return rows


def more_keyboard(owner, active=False, finished=False):
    """Ações infrequentes fora da tela principal, sem retirar recursos."""
    rows = [
        ["✅ Finalizar treino", "😕 Não consegui treinar hoje"],
        ["📊 Histórico de cargas", "🔁 Substituir exercício"],
    ]
    if owner:
        if active:
            rows.append([END, RESTART])
        elif finished:
            rows.append([RESTART])
    rows.extend([["📥 Importar treino por PDF/texto"], [BACK]])
    return rows


def _exercise_lines(exercises):
    lines = []
    for i, exercise in enumerate(exercises, 1):
        name = str(exercise.get("name") or "Exercício")
        sets = exercise.get("sets")
        reps = exercise.get("reps")
        load = exercise.get("load")
        raw = exercise.get("raw") or {}
        if reps is None:
            reps = raw.get("reps") or raw.get("repeticoes") or raw.get("repetições")
        if load is None:
            load = raw.get("carga") or raw.get("load")
        extra = []
        if sets:
            extra.append(f"{sets} séries")
        if reps:
            extra.append(f"{reps} reps" if str(reps).strip().isdigit() else str(reps))
        if load:
            extra.append(str(load))
        detail = " • ".join(extra) if extra else "séries conforme ficha"
        lines.append(f"  {i}. {name}\n     {detail}")
    return lines


async def _status(db, uid, owner):
    if not owner:
        return 1, True, False
    row = await db.prepare(
        "SELECT current_week,active,finished_at FROM protocol_mass_state WHERE user_id=?"
    ).bind(uid).first()
    if row is None:
        return 1, False, False
    return int(_get(row, "current_week", 1) or 1), bool(int(_get(row, "active", 0) or 0)), bool(_get(row, "finished_at"))


def _week_exercises(owner, week, weekday, generic_plan):
    if owner:
        return [
            {"name": e.get("name"), "sets": e.get("series"), "reps": e.get("reps"),
             "load": e.get("load"), "raw": e}
            for e in app.WEEKS.get(str(week), {}).get(weekday, [])
        ]
    # O patch de cardio adiciona um exercício extra mesmo em dias vazios.
    # A visualização semanal respeita o que foi realmente cadastrado.
    listed = [e for e in generic_plan if app.norm(e.get("name")) != "cardio"]
    if not listed and len(generic_plan) == 1 and app.norm(generic_plan[0].get("name")) == "cardio":
        return []
    return generic_plan


async def _week_sections(db, uid, owner, week):
    monday = app.now_local().date() - timedelta(days=app.now_local().date().weekday())
    blocks = []
    for day in range(7):
        target = monday + timedelta(days=day)
        weekday = app.WEEKDAY_NAMES[day]
        plan = [] if owner else (await app.workout_plan(db, uid, False, target))[3]
        exercises = _week_exercises(owner, week, weekday, plan)
        if not exercises:
            blocks.append(f"▫️ {DAY_NAMES[day]} — Sem treino cadastrado")
            continue
        heading = f"🏋️ {DAY_NAMES[day]} • {len(exercises)} exercício(s)"
        if day == app.now_local().date().weekday():
            heading += " • hoje"
        blocks.append("\n".join([heading] + _exercise_lines(exercises)))
    return blocks


async def show_week(db, token, chat, uid, owner, week):
    current, active, finished = await _status(db, uid, owner)
    if owner and not (1 <= week <= len(app.WEEKS)):
        await send_message(token, chat, "Essa semana não existe na ficha.", reply_markup=_kb(workout_keyboard(owner, active, finished, current)))
        return
    title = f"🗓️ Semana {week}/{len(app.WEEKS)}" if owner else "🗓️ Sua divisão semanal"
    if owner and week != current:
        title += " • consulta, sem alterar a semana atual"
    chunks = [title]
    sections = await _week_sections(db, uid, owner, week)
    for section in sections:
        if len("\n\n".join(chunks + [section])) > 3700:
            await send_message(token, chat, "\n\n".join(chunks))
            chunks = [title + " (continuação)"]
        chunks.append(section)
    menu = weeks_keyboard(owner)
    if owner:
        browse = []
        if week > 1:
            browse.append(f"📆 Semana {week - 1}")
        if week < len(app.WEEKS):
            browse.append(f"📆 Semana {week + 1}")
        if browse:
            menu.insert(1, browse)
    await send_message(token, chat, "\n\n".join(chunks), reply_markup=_kb(menu))


async def _today_text(db, uid, owner):
    wd, week, active, exercises = await app.workout_plan(db, uid, owner)
    if owner and not active:
        return "🏋️ Protocolo pausado/encerrado. Abra o menu para iniciar ou reiniciar."
    if not exercises or (len(exercises) == 1 and app.norm(exercises[0].get("name")) == "cardio"):
        return f"🗓️ {wd.capitalize()}\nSem treino cadastrado para hoje. Consulte a semana completa."
    today = app.now_local().date()
    out = [f"🏋️ TREINO DE HOJE • {wd.capitalize()}" + (f" • Semana {week}/{len(app.WEEKS)}" if owner else "")]
    completed = 0
    from ux_bugfixes import _expected_sets, _set_count
    from workout_progress_patch import _references, _fmt_ref
    for i, ex in enumerate(exercises, 1):
        name = ex.get("name") or "Exercício"
        expected = _expected_sets(ex.get("sets"))
        done = await _set_count(db, uid, owner, week, name, today)
        finished = expected > 0 and done >= expected
        if finished:
            completed += 1
        out.append(f"\n{'✅' if finished else '▫️'} {i}. {name}" + (f"  [{done}/{expected} séries]" if expected else f"  [{done} séries]"))
        out.extend(_exercise_lines([ex])[0].split("\n")[1:])
        if owner:
            last, _ = await _references(db, uid, name, week)
            if last:
                out.append(f"     Última referência: {_fmt_ref(last)}")
    out.append(f"\n✅ {completed}/{len(exercises)} exercícios concluídos")
    out.append("📝 Para registrar: Exercício | 40 kg | 10 reps")
    return "\n".join(out)


def _day_key(value):
    """Converte um dia reconhecido em uma chave (sem inferir conversas comuns)."""
    value = app.norm(value)
    if value in ("hoje", "amanha"):
        return value
    for index, weekday in enumerate(app.WEEKDAY_NAMES):
        if value in (app.norm(weekday), app.norm(DAY_NAMES[index])):
            return str(index)
    return None


def _explicit_day_request(text):
    """Aceita apenas comandos claramente relacionados ao treino."""
    normalized = app.norm(text)
    for prefix in ("qual e o ", "qual o ", "qual ", "me mostra o ",
                   "mostra o ", "quero ver o ", "ver o "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    match = re.fullmatch(r"treino(?: de| da| do| para| na| no)? (.+)", normalized)
    return _day_key(match.group(1)) if match else None


def _target_day(key, today):
    if key == "hoje":
        return today
    if key == "amanha":
        return today + timedelta(days=1)
    return today + timedelta(days=(int(key) - today.weekday()) % 7)


def _day_keyboard():
    return [
        [TOMORROW, "📅 Segunda", "📅 Terça"],
        ["📅 Quarta", "📅 Quinta", "📅 Sexta"],
        ["📅 Sábado", "📅 Domingo"],
        ["⬅️ Treinos"],
    ]


async def show_day(db, token, chat, uid, owner, target):
    """Consulta por data: sem salvar execução, avançar ciclo ou lançar séries."""
    today = app.now_local().date()
    current, active, finished = await _status(db, uid, owner)
    if target == today:
        content = await _today_text(db, uid, owner)
    else:
        weekday, week, _active, plan = await app.workout_plan(db, uid, owner, target)
        exercises = _week_exercises(owner, current, weekday, plan)
        header = (
            f"🏋️ TREINO DE {DAY_NAMES[target.weekday()].upper()} • {target.strftime('%d/%m/%Y')}"
            + (f"\n📋 Semana {current}/{len(app.WEEKS)} do protocolo (consulta)" if owner else "")
        )
        if exercises:
            content = "\n".join(
                [header, ""] + _exercise_lines(exercises)
                + ["", "📌 Prévia da ficha; nenhum registro foi alterado."]
            )
        else:
            content = header + "\n\n▫️ Nenhum treino cadastrado para este dia."
    await send_message(
        token, chat, content,
        reply_markup=_kb(workout_keyboard(owner, active, finished, current)),
    )


async def _restart(db, uid):
    # Histórico só pode ser apagado após confirmação explícita.
    for table in ("workout_logs", "workout_set_logs", "protocol_mass_sessions", "protocol_mass_set_logs"):
        await db.prepare(f"DELETE FROM {table} WHERE user_id=?").bind(uid).run()
    await db.prepare(
        "UPDATE protocol_mass_state SET current_week=1,active=0,started_at=NULL,finished_at=NULL WHERE user_id=?"
    ).bind(uid).run()


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    chat = (message.get("chat") or {}).get("id")
    if chat is None or not text:
        return False
    owner = is_owner(int(chat))
    command = app.norm(text)
    choices = {
        app.norm("🏋️ Treino"), app.norm("🏋️ Musculação"), app.norm(TODAY),
        app.norm(TOMORROW), app.norm(CHOOSE_DAY),
        app.norm(VIEW_WEEKS), app.norm(MORE), app.norm(BACK),
        app.norm(WEEK), app.norm(NEXT), app.norm(START), app.norm(END),
        app.norm(RESTART), app.norm("🔄 Reiniciar treinos"),
    }
    match = re.fullmatch(r"(?:semana)\s+(\d{1,2})", command)
    requested_day = _explicit_day_request(text)
    bare_day = _day_key(command)
    # Fora da seleção de dias, "sexta"/"amanhã" continuam sendo da agenda.
    confirmations = {"encerrar", "apagar treinos", "cancelar", "nao", app.norm("❌ Cancelar ação")}
    back = command == app.norm(BACK)
    if command not in choices and not match and not requested_day and not bare_day and command not in confirmations and not back:
        return False
    user = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat)).first()
    if not user:
        return False
    uid = int(_get(user, "id"))
    state, _ = await app.get_state(db, uid)
    confirmation = state in ("workout_end_confirm", "workout_restart_confirm")
    choosing = state == CHOOSE_STATE
    if not confirmation and command not in choices and not match and not requested_day and not choosing:
        return False
    # Não sequestrar respostas de outros fluxos, como uma data da agenda.
    if state and not choosing and not confirmation and (match or (requested_day and command not in choices)):
        return False
    current, active, finished = await _status(db, uid, owner)

    async def send(text_to_send):
        await send_message(token, int(chat), text_to_send,
                           reply_markup=_kb(workout_keyboard(owner, active, finished, current)))

    if choosing:
        if back or command in ("cancelar", app.norm("❌ Cancelar ação")):
            await app.clear_state(db, uid)
            await send("🏋️ Treinos. Escolha uma das opções abaixo.")
            return True
        selected_day = requested_day or bare_day
        if selected_day is not None:
            await app.clear_state(db, uid)
            await show_day(db, token, int(chat), uid, owner, _target_day(selected_day, app.now_local().date()))
            return True
        if command not in choices and not match:
            await send_message(
                token, int(chat),
                "Escolha um dia no teclado ou digite segunda, terça, ... sábado, domingo.",
                reply_markup=_kb(_day_keyboard()),
            )
            return True
        await app.clear_state(db, uid)

    if confirmation:
        if command in (app.norm("❌ Cancelar ação"), "cancelar", "nao"):
            await app.clear_state(db, uid)
            await send("Ação cancelada. Seu histórico foi preservado.")
            return True
        expected = "encerrar" if state == "workout_end_confirm" else "apagar treinos"
        if command != expected:
            await send(f"Responda {expected.upper()} para confirmar ou Cancelar para voltar.")
            return True
        await app.clear_state(db, uid)
        if state == "workout_end_confirm":
            await db.prepare(
                "UPDATE protocol_mass_state SET active=0,finished_at=CURRENT_TIMESTAMP WHERE user_id=? AND active=1"
            ).bind(uid).run()
            await send_message(token, int(chat), "⏹️ Protocolo encerrado. Seus registros continuam disponíveis.",
                               reply_markup=_kb(workout_keyboard(owner, False, True, current)))
        else:
            await _restart(db, uid)
            await send_message(token, int(chat), "🔄 Protocolo reiniciado. Histórico apagado após confirmação; pronto para começar novamente.",
                               reply_markup=_kb(workout_keyboard(owner, False, False, 1)))
        return True

    if command in (app.norm("🏋️ Treino"), app.norm("🏋️ Musculação")):
        if owner:
            info = f"Semana atual: {current}/{len(app.WEEKS)} • " + ("Em andamento" if active else ("Encerrado" if finished else "Ainda não iniciado"))
        else:
            info = "Sua ficha pessoal • consulte os exercícios ou importe sua divisão"
        await send(f"🏋️ TREINOS\n{info}\n\nO que precisa fazer?")
        return True
    if back:
        await send("🏋️ Treinos. Escolha a próxima ação.")
        return True
    if command == app.norm(VIEW_WEEKS):
        await send_message(
            token, int(chat), "📆 Planejamento: quer ver a semana atual ou as próximas?",
            reply_markup=_kb(weeks_keyboard(owner)),
        )
        return True
    if command == app.norm(MORE):
        await send_message(
            token, int(chat), "⚙️ Outras ações de treino:",
            reply_markup=_kb(more_keyboard(owner, active, finished)),
        )
        return True
    if command == app.norm(START):
        if not owner:
            await send("Seu treino não exige ativar o protocolo pessoal. Importe sua ficha e consulte Treino de hoje.")
        elif active:
            await send("Os trabalhos já começaram. Não é necessário ativar de novo.")
        elif finished:
            await send("O protocolo foi encerrado. Para começar um novo ciclo, use Reiniciar os trabalhos (com confirmação).")
        else:
            await db.prepare(
                "INSERT INTO protocol_mass_state(user_id,current_week,active,started_at,finished_at) "
                "VALUES(?,1,1,CURRENT_TIMESTAMP,NULL) ON CONFLICT(user_id) "
                "DO UPDATE SET active=1,started_at=CURRENT_TIMESTAMP,finished_at=NULL"
            ).bind(uid).run()
            await send_message(token, int(chat), "🚀 Protocolo iniciado. Boa volta aos treinos! Consulte a ficha de hoje.",
                               reply_markup=_kb(workout_keyboard(True, True, False, current)))
        return True
    if command == app.norm(END):
        if not owner or not active:
            await send("Não há protocolo em andamento para encerrar.")
        else:
            await app.set_state(db, uid, "workout_end_confirm", {})
            await send_message(token, int(chat), "⏹️ Encerrar o protocolo? O histórico será preservado.\n\nResponda ENCERRAR ou Cancelar.",
                               reply_markup=_kb([["ENCERRAR", "❌ Cancelar ação"]]))
        return True
    if command in (app.norm(RESTART), app.norm("🔄 Reiniciar treinos")):
        if not owner:
            await send("O reinício do protocolo pessoal não se aplica ao seu perfil.")
        else:
            await app.set_state(db, uid, "workout_restart_confirm", {})
            await send_message(token, int(chat), "⚠️ Reiniciar apaga todo o histórico de treino registrado neste perfil e volta para a semana 1.\n\nResponda APAGAR TREINOS ou Cancelar.",
                               reply_markup=_kb([["APAGAR TREINOS", "❌ Cancelar ação"]]))
        return True
    if command == app.norm(CHOOSE_DAY):
        await app.set_state(db, uid, CHOOSE_STATE, {})
        await send_message(
            token, int(chat), "🗓️ Qual dia você quer consultar?\nPode escolher pelo botão ou digitar o dia.",
            reply_markup=_kb(_day_keyboard()),
        )
        return True
    if command == app.norm(TODAY):
        await send(await _today_text(db, uid, owner))
        return True
    if command == app.norm(TOMORROW) or requested_day is not None:
        key = "amanha" if command == app.norm(TOMORROW) else requested_day
        await show_day(db, token, int(chat), uid, owner, _target_day(key, app.now_local().date()))
        return True
    if command == app.norm(WEEK):
        await show_week(db, token, int(chat), uid, owner, current)
        return True
    if command == app.norm(NEXT):
        if not owner:
            await send("📆 Sua ficha semanal continua a mesma nas próximas semanas. Veja Semana completa para todos os dias.")
            return True
        remaining = list(range(current + 1, len(app.WEEKS) + 1))
        if not remaining:
            await send("Você está na última semana da ficha.")
            return True
        lines = [f"📆 Próximas semanas • atual {current}/{len(app.WEEKS)}"]
        for number in remaining:
            days = app.WEEKS.get(str(number), {})
            n = sum(bool(days.get(day)) for day in app.WEEKDAY_NAMES)
            lines.append(f"• Semana {number}: {n} dia(s) de treino")
        lines.append("\nToque na semana desejada ou digite: semana 3")
        menu = [[f"📆 Semana {w}" for w in remaining[i:i + 3]] for i in range(0, len(remaining), 3)]
        menu.append([BACK])
        await send_message(token, int(chat), "\n".join(lines), reply_markup=_kb(menu))
        return True
    if match:
        if not owner:
            await show_week(db, token, int(chat), uid, owner, 1)
        else:
            await show_week(db, token, int(chat), uid, owner, int(match.group(1)))
        return True
    return False


def install():
    # Respostas do assistente antigo (incluindo após registrar uma série)
    # voltam ao mesmo menu enxuto. Estado/ativação são avaliados ao entrar
    # em Treino; por isso o teclado estático não exibe ações destrutivas.
    app.WORKOUT_KB = workout_keyboard(owner=False)
