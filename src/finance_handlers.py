from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, ConversationHandler, MessageHandler, filters
from src.finance_store import add_entry, month_report, previous_month_report
from src.ui_layout import FINANCE_KEYBOARD

AMOUNT, CATEGORY, DESCRIPTION = range(800,803)
CATEGORIES = ReplyKeyboardMarkup([["🍛 Alimentação","🚌 Transporte"],["🎮 Lazer","🛍️ Compras"],["💰 Renda","📦 Outros"],["❌ Cancelar ação"]], resize_keyboard=True)

def _money(v): return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.')

async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['finance']={'kind':'entrada' if update.message.text=='➕ Entrada' else 'saida'}
    await update.message.reply_text("💸 Quanto? Só o valor. Ex.: `35,90`.", parse_mode='Markdown', reply_markup=ReplyKeyboardRemove()); return AMOUNT
async def amount(update, context):
    try: value=float((update.message.text or '').replace('R$','').replace('.','').replace(',','.').strip())
    except ValueError: await update.message.reply_text("Me ajuda a te ajudar: manda só um valor, tipo `35,90`."); return AMOUNT
    if value<=0: await update.message.reply_text("Valor maior que zero, chefe. Contabilidade criativa fica para outro projeto."); return AMOUNT
    context.user_data['finance']['amount']=value
    await update.message.reply_text("Categoria?", reply_markup=CATEGORIES); return CATEGORY
async def category(update, context):
    text=(update.message.text or '').strip()
    if text=='❌ Cancelar ação': context.user_data.pop('finance',None); await update.message.reply_text("Cancelado. O dinheiro, espero, também.", reply_markup=FINANCE_KEYBOARD); return ConversationHandler.END
    clean=text.split(' ',1)[-1].lower(); context.user_data['finance']['category']=clean
    await update.message.reply_text("Descrição curta? Ex.: `mercado`, `bolsa`, `lanche`. Ou `-` para pular.", reply_markup=ReplyKeyboardRemove()); return DESCRIPTION
async def description(update, context):
    data=context.user_data.pop('finance'); desc=(update.message.text or '').strip(); desc=None if desc=='-' else desc
    add_entry(data['kind'], data['amount'], data['category'], desc)
    if data['kind']=='saida': msg=f"💸 {_money(data['amount'])} saiu. Registrado. Tô vendo dinheiro sair e até agora nada de concreto. Adianta em que mesmo? 😏"
    else: msg=f"💰 {_money(data['amount'])} entrou. Finalmente uma seta apontando na direção agradável. Não se acostume com meu entusiasmo."
    await update.message.reply_text(msg, reply_markup=FINANCE_KEYBOARD); return ConversationHandler.END

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    income, expenses, balance, cats, limits=month_report(); pi, pe, pb, _, _=previous_month_report()
    if not income and not expenses:
        await update.message.reply_text("📊 Você quer relatório financeiro sem ter me contado para onde o dinheiro foi. Ambicioso. Cadastre entradas e saídas primeiro; eu ainda não leio extrato por telepatia.", reply_markup=FINANCE_KEYBOARD); raise ApplicationHandlerStop
    parts=["📊 *Relatório do mês*",f"\n💰 Entradas: *{_money(income)}*",f"💸 Saídas: *{_money(expenses)}*",f"🏦 Saldo registrado: *{_money(balance)}*"]
    if cats:
        parts.append("\n*Por categoria:*"); parts += [f"• {k.title()}: {_money(v)}" for k,v in sorted(cats.items(), key=lambda x:x[1], reverse=True)]
    if pi or pe:
        delta=expenses-pe
        parts.append(f"\n📈 Mês anterior: {_money(pe)} em saídas. Este mês está {_money(abs(delta))} {'acima' if delta>0 else 'abaixo'}.")
    alerts=[(c,v,limits[c]) for c,v in cats.items() if c in limits and v>limits[c]]
    if alerts:
        parts.append("\n🚨 *Alertas de excesso:*" ); parts += [f"• {c.title()}: {_money(v)} / limite {_money(l)}. A categoria pediu liberdade e você deu independência financeira." for c,v,l in alerts]
    parts.append("\nIsso é o que eu consigo provar com o que você registrou. Quer controle de verdade? A parte chata é simples: continuar me contando quando o dinheiro entra e, principalmente, quando ele foge. Sim, eu sei. Um saco. 😌")
    await update.message.reply_text('\n'.join(parts), parse_mode='Markdown', reply_markup=FINANCE_KEYBOARD); raise ApplicationHandlerStop

def register_finance_handlers(application):
    conv=ConversationHandler(entry_points=[MessageHandler(filters.Regex(r"^(➕ Entrada|➖ Gasto)$"), start_entry)], states={AMOUNT:[MessageHandler(filters.TEXT & ~filters.COMMAND, amount)], CATEGORY:[MessageHandler(filters.TEXT & ~filters.COMMAND, category)], DESCRIPTION:[MessageHandler(filters.TEXT & ~filters.COMMAND, description)]}, fallbacks=[])
    application.add_handler(conv, group=-6)
    application.add_handler(MessageHandler(filters.Regex(r"^(📊 Resumo do mês|📈 Histórico)$"), report), group=-6)
