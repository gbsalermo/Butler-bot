"""Roteador para mensagens que misturam vários assuntos na mesma fala.

Ele é deliberadamente conservador: só assume a mensagem quando encontra pelo menos
dois blocos de domínios diferentes que consegue resolver com segurança. Não executa
faltas implícitas; consultas e sugestões podem coexistir numa única resposta.
"""
import re
import unicodedata

import academic_intelligence as ai
import attendance_patch as attendance
import companion_nlu_v2 as v2
import cooking_library as cooking
from deterministic_memory import _entities as personal_entities, _find_referenced, _supply
from telegram_api import send_message


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


def _split(text):
    clean=re.sub(r"^\s*butler[,.:;!?-]*\s*","",text or "",flags=re.I)
    parts=[p.strip(" ,.;") for p in re.split(r"[.!?;]+",clean) if p.strip(" ,.;")]
    out=[]
    connector=re.compile(r"\s+e\s+(?=(?:me\s+fala|me\s+passa|me\s+indica|lembra\s+que|me\s+lembra|tambem\s+|também\s+))",re.I)
    for part in parts:
        out.extend(x.strip() for x in connector.split(part) if x.strip())
    return out


def _domain(segment):
    n=_norm(segment)
    if any(x in n for x in ("receita","vaca atolada","macarrao","moqueca","vatapa","baiao","cozinhar","como fazer")):return "cooking"
    if any(x in n for x in ("racao","sache","petisco","areia")) and any(x in n for x in ("acabou","sem","falta","faltando","comprar","lembra")):return "pet_supply"
    if any(x in n for x in ("aula","materia","sistemas","fisica","prova","faltas","faltar","faltei")) or ai._weekday_from_text(segment) is not None:return "academic"
    return "conversation"


def _subject_terms(text):
    n=_norm(text)
    ignored={"segunda","terca","quarta","quinta","sexta","sabado","domingo","tenho","tem","aula","certo","ne","na","no","de","do","da","eu"}
    return {t for t in n.split() if len(t)>=4 and t not in ignored}


async def _schedule_candidates(db,uid,segment,target_date):
    """Resolve consulta acadêmica ambígua usando termos + dia da grade.

    Ex.: "segunda tenho sistemas?" pode corresponder a Sistemas Digitais I e ao
    Laboratório de Sistemas Digitais I. Nesse caso responde ambos, em vez de omitir.
    """
    terms=_subject_terms(segment)
    if not terms or not target_date:return []
    rows=await ai._rows(db.prepare("""
        SELECT s.id,s.name,ss.weekday,ss.start_time,ss.end_time,ss.location
        FROM subjects s
        JOIN subject_sessions ss ON ss.subject_id=s.id
        WHERE s.user_id=? AND s.active=1
        ORDER BY ss.start_time
    """).bind(uid))
    target_wd=target_date.weekday(); matches=[]
    for row in rows:
        wd=ai._weekday_from_text(str(ai._row(row,"weekday") or ""))
        if wd!=target_wd:continue
        name=_norm(ai._row(row,"name") or "")
        if any(term in name for term in terms):matches.append(row)
    return matches


def _social_reason(segment):
    """Extrai apenas contexto social explícito sem inferir relação ou compromisso."""
    m=re.search(r"\b(?:domingo|segunda|terca|terça|quarta|quinta|sexta|sabado|sábado)\b[^,.!?]{0,80}?\b(?:vou|ia)\s+sair\s+com\s+([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",segment or "",flags=re.I)
    if not m:return None
    day=re.search(r"\b(domingo|segunda|terca|terça|quarta|quinta|sexta|sabado|sábado)\b",segment or "",flags=re.I)
    return ((day.group(1).lower() if day else None),m.group(1).capitalize())


async def _academic_piece(db,uid,segment):
    n=_norm(segment); lines=[]
    subject,subjects=await ai._subject_lookup(db,uid,segment)
    target_date=ai._date_from_phrase(segment,ai._now().date())

    if target_date and any(x in n for x in ("tenho","tem aula","aula","certo","ne","né")):
        if subject:
            sessions=await ai._rows(db.prepare("SELECT weekday,start_time,end_time,location FROM subject_sessions WHERE subject_id=? ORDER BY start_time").bind(ai._row(subject,"id")))
            target_wd=target_date.weekday(); matching=[]
            for session in sessions:
                wd=ai._weekday_from_text(str(ai._row(session,"weekday") or ""))
                if wd==target_wd:matching.append(session)
            if matching:
                details=[]
                for s in matching:
                    loc=f" — {ai._row(s,'location')}" if ai._row(s,"location") else ""
                    details.append(f"{ai._row(s,'start_time')}{loc}")
                lines.append(f"📚 Sim. {ai._row(subject,'name')} está na sua grade de {ai.DAY_NAMES[target_wd]}: "+", ".join(details)+".")
            else:
                lines.append(f"📚 Não achei {ai._row(subject,'name')} na sua grade de {ai.DAY_NAMES[target_wd]}.")
        else:
            candidates=await _schedule_candidates(db,uid,segment,target_date)
            if candidates:
                rendered=[]; seen=set()
                for row in candidates:
                    key=(ai._row(row,"name"),ai._row(row,"start_time"))
                    if key in seen:continue
                    seen.add(key)
                    loc=f" — {ai._row(row,'location')}" if ai._row(row,"location") else ""
                    rendered.append(f"{ai._row(row,'name')} às {ai._row(row,'start_time')}{loc}")
                lines.append(f"📚 Sim. Na {ai.DAY_NAMES[target_date.weekday()]} você tem: "+"; ".join(rendered)+".")

    if any(x in n for x in ("pensando em faltar","queria faltar","quero faltar","vou faltar","matar aula","matar a aula")):
        label=ai._row(subject,"name") if subject else "essa aula"
        lines.append(f"Sobre faltar {label}: entendi que você está cogitando isso, mas não registrei falta nenhuma. Só mexo nas faltas quando a decisão fica explícita/confirmada.")
        social=_social_reason(segment)
        if social:
            day,name=social
            lines.append(f"Entendi também o contexto: {day} você pretende sair com {name}. Estou usando isso só para entender a conversa; não cadastrei {name} como relação nem criei compromisso.")

    if "faltas" in n and any(x in n for x in ("quantas","quanto","tenho","nela","nessa")):
        if subject:
            lines.append(await attendance._attendance_report(db,uid,int(ai._row(subject,"id"))))
        else:
            lines.append(await attendance._attendance_report(db,uid))
    return lines


async def _cooking_piece(db,uid,segment):
    n=_norm(segment)
    book,title,data=cooking._find_exact(n)
    if not data:return []
    await cooking._save_recipe_context(db,uid,book,title,data)
    return [cooking._format(title,data)]


async def _pet_piece(db,uid,segment):
    item=_supply(segment)
    if not item:return []
    entities=await personal_entities(db,uid); referenced=_find_referenced(entities,segment)
    pets=[e for e in entities if e.get("kind")=="pet"]
    if referenced and referenced.get("kind")!="pet":referenced=None
    if not referenced and len(pets)==1:referenced=pets[0]
    pet=(referenced or {}).get("name") or "seu pet"
    await v2._save_state(db,uid,"confirm_pet_supply",{"item":item,"pet":pet})
    return [f"🐾 E anotei o contexto de {pet}: acabou {item}. Quer que eu coloque {item} na lista de itens faltando? Responde `pode` ou `deixa`."]


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await ai._uid(db,int(chat_id))
    if not uid:return False

    segments=_split(text)
    domains=[_domain(s) for s in segments]
    meaningful={d for d in domains if d!="conversation"}
    academic_multi=(len(segments)==1 and domains and domains[0]=="academic" and "falt" in _norm(segments[0]) and "quant" in _norm(segments[0]))
    if len(meaningful)<2 and not academic_multi:return False

    pieces=[]; handled_domains=set()
    for segment,domain in zip(segments,domains):
        current=[]
        if domain=="academic":current=await _academic_piece(db,uid,segment)
        elif domain=="cooking":current=await _cooking_piece(db,uid,segment)
        elif domain=="pet_supply":current=await _pet_piece(db,uid,segment)
        if current:
            pieces.extend(current); handled_domains.add(domain)

    if len(handled_domains)<2 and not (academic_multi and pieces):return False
    await send_message(token,int(chat_id),"\n\n".join(pieces))
    return True
