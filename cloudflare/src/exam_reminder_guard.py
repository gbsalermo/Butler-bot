import academic_intelligence as academic


async def _expire_past_exams(db):
    today = academic._now().date().isoformat()
    await db.prepare("""
        UPDATE daily_items
        SET status='concluido', completed_at=COALESCE(completed_at,CURRENT_TIMESTAMP)
        WHERE status='pendente'
          AND details LIKE 'exam:%'
          AND due_date < ?
    """).bind(today).run()


def install():
    original = academic.exam_reminders

    async def guarded(db, token):
        # Provas são eventos finitos: depois da data, deixam de ser pendentes.
        # O dispatcher acadêmico já usa notification_log por marco (7d/3d/1d/hoje/1h),
        # então cada aviso segue idempotente mesmo com o cron rodando várias vezes.
        await _expire_past_exams(db)
        await original(db, token)

    academic.exam_reminders = guarded
