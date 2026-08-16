import re
import unicodedata

import companion_nlu_v2 as v2
from deterministic_memory import _entities, _find_referenced
from settings import OWNER_CHAT_ID
from telegram_api import send_message


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id)!=int(OWNER_CHAT_ID): return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"): return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=_norm(text)

    if n in ("obrigado","obrigada","valeu","vlw","brigado","brigada","tmj","tamo junto"):
        await send_message(token,int(chat_id),"Tamo junto, chefe. Meu salário continua inexistente, mas seguimos."); return True

    if n in ("kkkk","kkk","kkkkk","haha","hahaha","rs","rsrs") or (len(n)<30 and any(x in n for x in ("kkkk","hahaha"))):
        await send_message(token,int(chat_id),"Ri não. Eu tenho logs."); return True

    if any(x in n for x in ("tudo bem butler","butler tudo bem","como voce ta","como você tá","como ta butler","como tá butler")):
        await send_message(token,int(chat_id),"Dentro do possível pra um gato empregado sem carteira assinada. E por aí?"); return True

    if any(x in n for x in ("quem e voce","quem é você","o que voce e","o que você é","quem e butler","quem é butler")):
        await send_message(token,int(chat_id),"Butler. Assistente, fiscal de pendência e gato laranja por decisão administrativa. A parte importante é que eu tento lembrar das coisas pra você não precisar carregar tudo na cabeça."); return True

    if any(x in n for x in ("bom trabalho","mandou bem","boa butler","ai sim butler","aí sim butler")):
        await send_message(token,int(chat_id),"Finalmente uma avaliação de desempenho favorável. Vou registrar mentalmente antes que mude de ideia."); return True

    entities=await _entities(db,uid)
    referenced=_find_referenced(entities,text)
    if referenced and any(x in n for x in ("quem e","quem é","o que e","o que é","voce lembra","você lembra","lembra quem")):
        name=referenced.get("name")
        if referenced.get("kind")=="pet":
            species=referenced.get("species") or "pet"; color=referenced.get("color")
            extra=f" e é {color}" if color else ""
            await send_message(token,int(chat_id),f"Lembro. {name} é seu {species}{extra}. Cadastro informal da firma segue funcionando."); return True

    # Comentários cotidianos curtos: responde sem tentar transformar em ação.
    if len(n)<=90:
        if any(x in n for x in ("to com sono","tô com sono","morrendo de sono","sono demais")):
            await send_message(token,int(chat_id),"Aí já é o corpo protocolando pedido de encerramento do expediente. Se não tiver bomba pendente agora, eu respeitaria o sindicato."); return True
        if any(x in n for x in ("to com fome","tô com fome","morrendo de fome")):
            await send_message(token,int(chat_id),"Isso aí costuma ter solução mais objetiva que a maioria dos seus problemas. Vai comer alguma coisa decente."); return True
        if any(x in n for x in ("que calor","ta calor","tá calor","calor demais")):
            await send_message(token,int(chat_id),"Clima colaborando pra transformar qualquer obrigação em atividade de alto risco. Água, chefe. Pelo menos essa eu posso defender sem reunião."); return True
        if any(x in n for x in ("que frio","ta frio","tá frio","frio demais")):
            await send_message(token,int(chat_id),"Perfeito pra não sair de lugar nenhum e chamar isso de estratégia térmica."); return True

    return False
