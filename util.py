# encoding:utf-8

from typing import Any, Optional, Dict, List

from flask.globals import session

from dao import dao


def get_task_key(gid: int, cid: int, annotation: bool):
    return f'{gid}-{cid}-{"a" if annotation else "t"}'


def update_cookie_pool(key: str, pool_key: str):
    pool: List[str] = session.get(pool_key, [])
    if key in pool:
        pool.remove(key)
    pool.append(key)

    if len(pool) > 3:
        old: str = pool.pop(0)
        session.pop(old, None)

    session[pool_key] = pool


def load_anno(gid: int, tid: int, uid: int):
    anno_list, aspect_list = dao.get_anno_by_gid_tid_uid(gid, tid, uid)
    return {"anno_list": anno_list, "aspect_list": aspect_list}


def load_anno_direct(gid: int, cid: int, uid: int):
    task: Dict[str, Any] = load_task(gid, cid)
    anno: Dict[str, Any] = dao.get_task_anno_by_gid_sid_pid_uid(gid, task['sid'], task['pid'],
                                                                uid, force=True)

    if len(anno) == 0:
        anno = {k: task[k] for k in ('rs', 'tag')}
    return anno
