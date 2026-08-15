import app


def install():
    original = app.agenda_text

    async def wrapped(*args, **kwargs):
        text = await original(*args, **kwargs)
        lines = []
        for line in text.splitlines():
            # Na agenda base, tarefas usam ✅ como ícone de tipo e compromissos usam 📅.
            # Mantemos o ✅ final como status de concluído e trocamos apenas o ícone inicial.
            if line.startswith("• ✅ "):
                line = line.replace("• ✅ ", "• 📝 ", 1)
            lines.append(line)
        return "\n".join(lines)

    app.agenda_text = wrapped
