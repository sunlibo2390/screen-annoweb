# encoding:utf-8

from json import loads
from typing import Any, Optional, Dict

from flask.blueprints import Blueprint
from flask.globals import request, session
from flask.json import jsonify
from flask.wrappers import Response
from flask_login.utils import current_user, login_required

from dao import dao
from util import load_anno, load_anno_direct

bp_task: Blueprint = Blueprint('task', __name__, url_prefix='/task')


@bp_task.route('/loadtask', methods=['POST'])
@login_required
def loadtask():
    uid: int = request.values.get('uid', 0, type=int)
    tid: int = request.values.get('tid', 0, type=int)

    gid: int = request.values.get('gid', 0, type=int)
    # print(gid, tid)
    task: Dict[str, Any] = dao.get_task_by_gid_tid(gid, tid)
    # print('task/loadtask', task)
    if gid == 1:
        task['text'] = task['review']
        task['reviews'] = [task['review']]
        task['aspect'] = '，'.join(eval(task['aspects']))
        task['anno_list'], task['aspect_list'] = dao.get_anno_by_gid_tid_uid(1, tid, uid)
    elif gid == 2:
        reviews = task['reviews']
        task['text'] = ""
        for review in reviews:
            task['text'] += "<div>" + review + "</div><br>"
        task['anno_list'], task['aspect_list'] = dao.get_anno_by_gid_tid_uid(2, tid, uid)

    # task['anno'] = load_anno(gid, cid, uid)
    dao.set_last_tid_by_gid_uid(uid, gid, tid)

    if current_user.adjudicator:
        arbi_tasks, aspect_list, arbi_list, review_state = dao.get_annotated_task_by_gid_tid_uid(uid, gid, tid)
        if len(review_state)>0:
            task['review_state'] = review_state
        task['arbi_tasks'] = arbi_tasks
        task['anno_list'] = [arbi_task[0] for arbi_task in arbi_tasks]  # list[str]
        task['aspect_list'] = aspect_list  # list[int]
        task['arbi_list'] = arbi_list
    # print('task/loadtask', task)

    return jsonify(task)


@bp_task.route('/loadanno', methods=['POST'])
@login_required
def loadanno():
    gid: int = request.values.get('gid', 0, type=int)
    tid: int = request.values.get('tid', 0, type=int)
    return jsonify(load_anno(gid, tid, current_user.uid))


@bp_task.route('/note', methods=['POST'])
@login_required
def note():
    gid: int = request.values.get('gid', 0, type=int)
    cid: int = request.values.get('cid', 0, type=int)
    roleset: int = request.values.get('roleset', -1, type=int)
    task: Dict[str, Any] = load_task(gid, cid)
    result: Dict[str, Any] = {'roleset': '', 'role': [], 'example': []}

    if roleset >= 0 and roleset < len(task['cand']):
        target: Dict[str, str] = task['cand'][roleset]
        rid: str = target['rid']
        result['roleset'] = f'{target["name"]}.{rid}: {target["desc"]}'
        result.update(dao.get_roleset_note_by_pred_rid(target['pred'], rid))

    return jsonify(result)


@bp_task.route('/save', methods=['POST'])
@login_required
def save():
    uid: int = current_user.uid
    tid: int = request.values.get('tid', 0, type=int)
    gid: int = request.values.get('gid', 0, type=int)

    if current_user.adjudicator:
        anno_list = request.values.get('anno_list', None, type=str)
        anno_list = eval(anno_list)
        arbi_list = request.values.get('arbi_list', None, type=str)
        # print('arbi_list', arbi_list)
        arbi_list = eval(arbi_list)
        state_list = request.values.get('state_list', None, type=str)  # 仲裁任务各标注的状态：接收/拒绝/未选择
        state_list = eval(state_list)
        aspect_list = request.values.get('aspect_list', None, type=str)  # 仲裁任务各标注的状态：接收/拒绝/未选择
        aspect_list = eval(aspect_list)
        aspect_list = ['/'.join(aspect) for aspect in aspect_list]  # 拼接
        aspect_list = list(set(aspect_list))  # 角度去重
        
        if gid==1:
            dao.save_task_by_gid_tid_uid(
                uid, gid, tid, anno_list, aspect_list, state_list, arbi_list
            )

        elif gid==2:
            review_state = request.values.get('review_state', None, type=str)
            review_state = eval(review_state)  
            dao.save_task_by_gid_tid_uid(
                uid, gid, tid, anno_list, aspect_list, 
                state_list, arbi_list, review_state = review_state
            )
        # dao.save_task_by_gid_tid_uid(uid, gid, tid, anno_list, aspect_list, state_list, arbi_list)
    else:
        anno_list: list[str] = request.values.get('anno_list', None, type=str)
        anno_list = eval(anno_list)
        anno_list = list(set(anno_list))  # 标注去重
        aspect_list: list[str] = request.values.get('aspect_list', None, type=str)

        # print("task/save", aspect_list)

        aspect_list = eval(aspect_list)
        aspect_list = ['/'.join(aspect) for aspect in aspect_list]  # 拼接
        aspect_list = list(set(aspect_list))  # 角度去重

        # print("task/save", aspect_list)
        
        if gid==1:
            dao.save_task_by_gid_tid_uid(
                uid, gid, tid, anno_list, aspect_list
            )

        elif gid==2:
            review_state = request.values.get('review_state', None, type=str)
            review_state = eval(review_state)  # 每条句子是否保留，0为删除，1为保留
            left_state = request.values.get('left_state', None, type=int)
            dao.save_task_by_gid_tid_uid(
                uid, gid, tid, anno_list, aspect_list, review_state = review_state, left_state=left_state
            )

    return jsonify({'success': True})


@bp_task.route('/report', methods=['POST'])
@login_required
def report():
    gid: int = request.values.get('gid', 0, type=int)
    tid: int = request.values.get('tid', 0, type=int)

    error_type: int = request.values.get('type', -1, type=int)
    error_info: str = request.values.get('info', "", type=str)
    success: bool = error_type > 0 and len(error_info)>0

    if success:
        dao.report_task_error(current_user.uid, gid, tid, error_type, error_info)

    return jsonify({'success': success})
