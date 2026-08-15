import app
from owner_profile import is_owner, preferred_name_for


async def fast_ensure_user(db, chat_id, user):
    """Evita repetir o bootstrap completo a cada mensagem.

    Usuários já conhecidos precisam apenas de um SELECT. O fluxo original
    continua sendo usado na primeira interação para criar estado, metas,
    limites e, no caso do proprietário, semear o perfil pessoal.
    """
    existing = await db.prepare(
        "SELECT id,preferred_name,is_owner FROM users WHERE telegram_chat_id=?"
    ).bind(chat_id).first()

    if existing:
        uid = int(app.rowget(existing, "id"))
        preferred = app.rowget(existing, "preferred_name")
        return uid, False, preferred

    # Primeira interação: delega ao bootstrap original completo.
    return await _original_ensure_user(db, chat_id, user)


_original_ensure_user = app.ensure_user


def install_performance_patches():
    app.ensure_user = fast_ensure_user
