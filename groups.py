# encoding:utf-8

from typing import Any, Dict, List, Tuple

from flask.blueprints import Blueprint
from flask.globals import request, session
from flask.helpers import url_for
from flask.json import jsonify
from flask.wrappers import Response
from flask_login.utils import current_user, login_required

from dao import dao

bp_groups: Blueprint = Blueprint('groups', __name__, url_prefix='/groups')


@bp_groups.route('/load', methods=['POST'])
@login_required
def load():
    uid: int = current_user.uid

    tid_list1 = dao.get_tid_list_by_gid_uid(uid, 1)
    tid_list2 = dao.get_tid_list_by_gid_uid(uid, 2)

    if current_user.adjudicator:
        finished1 = dao.count_arbitrated_by_uid_gid_tidlist(uid, 1, tid_list1)
        finished2 = dao.count_arbitrated_by_uid_gid_tidlist(uid, 2, tid_list2)
        href1 = url_for('route.arbitration', gid=1)
        href2 = url_for('route.arbitration', gid=2)
    else:
        finished1 = dao.count_annotated_by_uid_gid_tidlist(uid, 1, tid_list1)
        finished2 = dao.count_annotated_by_uid_gid_tidlist(uid, 2, tid_list2)
        href1 = url_for('route.annotation', gid=1)
        href2 = url_for('route.annotation', gid=2)
    groups = {
        'task1': {'title': '单一评论论点归纳', 'left': len(tid_list1)-finished1, 'annotated': finished1, 'href': href1},
        'task2': {'title': '多评论实体情感一致性筛选', 'left': len(tid_list2)-finished2, 'annotated': finished2, 'href': href2},
    }
    return jsonify(groups)


@bp_groups.route('/update', methods=['POST'])
@login_required
def update():
    session['key'] = request.values.get('key', 0, type=int)
    session['order'] = request.values.get('order', 0, type=int)
    session['part'] = request.values.get('part', 0, type=int)

    session['gid_list'] = request.values.get(
        'gid', list(dao.get_user_group_status_by_uid(current_user.uid).keys()),
        type=lambda x: [int(y) for y in x.split(',')]
    )

    return jsonify({'success': 1})
