from datetime import date

from src.daily_store import list_items


def daily_context() -> dict:
    pending = list_items(only_pending=True)
    today = date.today().isoformat()
    today_items = [item for item in pending if item["due_date"] == today]
    overdue = [item for item in pending if item["due_date"] and item["due_date"] < today]
    return {
        "pending_total": len(pending),
        "today_total": len(today_items),
        "overdue_total": len(overdue),
    }


def context_comment(ctx: dict) -> str | None:
    overdue = int(ctx.get("overdue_total", 0))
    pending = int(ctx.get("pending_total", 0))
    today = int(ctx.get("today_total", 0))

    if overdue >= 5:
        return f"Temos {overdue} coisas atrasadas. Isso já deixou de ser lista e virou patrimônio histórico."
    if overdue >= 2:
        return f"Aviso diplomático: {overdue} pendências já passaram da data."
    if pending >= 8:
        return f"Temos {pending} pendências abertas. Colecionar era para ser hobby, chefe."
    if today >= 5:
        return f"Hoje tem {today} coisas marcadas. Dia compacto, aparentemente."
    if pending == 0:
        return "Nenhuma pendência aberta. Estranho. Silencioso demais por aqui."
    return None
