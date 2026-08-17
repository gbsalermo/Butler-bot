import json
from datetime import date, datetime, timezone

import app
import goal_operational as goals
import routine_integration


async def _save_checkpoint_authoritative(db,uid,routine,target_time=None):
    """Fonte única de conclusão de rotina + crédito em metas novas.

    Preserva routine_logs, mas não alimenta mais as metas genéricas legadas por
    categoria. Só metas explicitamente ligadas em goal_profiles recebem crédito.
    """
    routine_id=int(routine_integration._row(routine,"id"))
    scheduled=routine_integration._times(routine_integration._row(routine,"time_hhmm"))
    today=datetime.now(timezone.utc).astimezone(routine_integration.LOCAL_TZ).date()
    done=await routine_integration._status(db,routine_id,today,scheduled)

    if scheduled:
        if target_time and target_time in scheduled:
            done.add(target_time)
        elif target_time is None:
            pending=[t for t in scheduled if t not in done]
            if pending:done.add(pending[0])
    else:
        done.add("feito")

    complete=(not scheduled) or all(t in done for t in scheduled)
    status="feito" if complete else json.dumps({"done":sorted(done),"total":scheduled},ensure_ascii=False)
    await db.prepare("INSERT INTO routine_logs(routine_id,log_date,status) VALUES(?,?,?) ON CONFLICT(routine_id,log_date) DO UPDATE SET status=excluded.status").bind(routine_id,today.isoformat(),status).run()

    if complete:
        await goals.ensure_schema(db)
        profiles=await goals._rows(db.prepare("""
            SELECT goal_id,goal_type,start_date,target_date,status
            FROM goal_profiles
            WHERE linked_routine_id=? AND status='active'
        """).bind(routine_id))
        for p in profiles:
            gid=int(goals._row(p,"goal_id"));typ=goals._row(p,"goal_type")
            if typ!="habit":continue
            start=goals._row(p,"start_date");target=goals._row(p,"target_date")
            # Fora da janela, a rotina segue concluída normalmente, mas não adultera a meta.
            if start and today<date.fromisoformat(start):continue
            if target and today>date.fromisoformat(target):continue
            await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date,note) SELECT ?,1,?,'linked_routine' WHERE NOT EXISTS(SELECT 1 FROM goal_progress WHERE goal_id=? AND log_date=?)").bind(gid,today.isoformat(),gid,today.isoformat()).run()
            if start and target:
                total=max(1,(date.fromisoformat(target)-date.fromisoformat(start)).days+1)
                count=await db.prepare("SELECT COUNT(DISTINCT log_date) n FROM goal_progress WHERE goal_id=? AND log_date>=? AND log_date<=?").bind(gid,start,target).first()
                done_days=int(goals._row(count,"n",0) or 0)
                if done_days>=total:
                    await db.prepare("UPDATE goal_profiles SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE goal_id=?").bind(gid).run()
    return done,scheduled,complete


def install():
    routine_integration._save_checkpoint=_save_checkpoint_authoritative
