from datetime import date

import app
import goal_operational as goals
import routine_integration
import runtime_guard
from telegram_api import send_message


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _habit_count_in_window(db,gid,start_date,target_date):
    row=await db.prepare("SELECT COUNT(DISTINCT log_date) n FROM goal_progress WHERE goal_id=? AND log_date>=? AND log_date<=?").bind(gid,start_date,target_date).first()
    return int(goals._row(row,"n",0) or 0)


def install():
    original=routine_integration._save_checkpoint

    async def save_with_window_guard(db,uid,routine,target_time=None):
        result=await original(db,uid,routine,target_time)
        done,scheduled,complete=result
        if complete:
            await goals.ensure_schema(db)
            profiles=await goals._rows(db.prepare("SELECT goal_id,start_date,target_date,status FROM goal_profiles WHERE linked_routine_id=? AND goal_type='habit' AND status!='removed'").bind(int(goals._row(routine,"id"))))
            for p in profiles:
                gid=int(goals._row(p,"goal_id"));start=goals._row(p,"start_date");target=goals._row(p,"target_date")
                if not start or not target:continue
                total=max(1,(date.fromisoformat(target)-date.fromisoformat(start)).days+1)
                count=await _habit_count_in_window(db,gid,start,target)
                if count>=total:
                    await db.prepare("UPDATE goal_profiles SET status='completed',completed_at=COALESCE(completed_at,CURRENT_TIMESTAMP) WHERE goal_id=?").bind(gid).run()
                else:
                    # Corrige qualquer conclusão prematura do vínculo legado/contador global.
                    await db.prepare("UPDATE goal_profiles SET status='active',completed_at=NULL WHERE goal_id=? AND status='completed'").bind(gid).run()
        return result

    routine_integration._save_checkpoint=save_with_window_guard


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    uid=await goals._uid(db,int(chat_id))
    if uid is None:return False
    state,payload=await runtime_guard._state(db,uid)
    if state!="goal_progress_value" or payload.get("goal_type")!="habit":return False
    profile=await db.prepare("SELECT start_date,target_date FROM goal_profiles WHERE goal_id=?").bind(payload.get("goal_id")).first()
    target=goals._row(profile,"target_date")
    if target and app.now_local().date()>date.fromisoformat(target):
        await runtime_guard._clear(db,uid)
        await send_message(token,int(chat_id),f"⏳ O prazo dessa meta terminou em {date.fromisoformat(target).strftime('%d/%m')}. Não vou maquiar um dia atrasado como se estivesse dentro da meta. Você pode editar o prazo ou criar uma nova.",reply_markup=_kb(goals.GOAL_KB))
        return True
    return False
