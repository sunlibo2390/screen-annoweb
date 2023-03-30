# encoding:utf-8

from typing import Union, Dict, List, Tuple
from urllib.parse import ParseResult, urljoin, urlparse

from flask import abort
from flask.blueprints import Blueprint
from flask.globals import request, session
from flask.helpers import url_for
from flask.templating import render_template
from flask.wrappers import Response
from flask_login.utils import current_user, login_required, logout_user
from werkzeug.utils import redirect

from dao import dao

bp_route: Blueprint = Blueprint('route', __name__)


# 根路由
@bp_route.route('/')
def home():
    return render_template('/index.html')


# 登录路由
@bp_route.route('/login')
def login():
    for target in request.args.get('next', url_for('route.home'), str), request.referrer:
        # print('登录路由', target)
        if target:
            ref_url: ParseResult = urlparse(request.host_url)
            test_url: ParseResult = urlparse(urljoin(request.host_url, target))

            if test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc:
                return redirect(target) if current_user.is_authenticated else \
                    render_template('/login.html', next_page=target)
    else:
        abort(400)


# 登出路由
@bp_route.route("/logout")
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('route.home'))


# 重置密码路由
@bp_route.route("/reset")
@login_required
def reset():
    target = request.args.get('next', url_for('route.groups'), str)
    return render_template('/reset.html', next_page=target)


# 选择任务组
@bp_route.route('/groups')
@login_required
def groups():
    return render_template('/groups.html')


# 标注页面
@bp_route.route('/annotation')
@login_required
def annotation():
    uid: int = current_user.uid

    print('referrer', request.referrer)
    print('path', request.path)
    print('url', request.url)
    print('args', request.args)
    gid: int = request.args.get('gid', 0, int)
    if gid == 0:
        gid = int(request.referrer[-1])
    print('annotation', uid, gid)
    tid_list = dao.get_tid_list_by_gid_uid(uid, gid)
    last_tid: int = dao.get_last_tid_by_gid_uid(uid, gid)

    if last_tid not in tid_list:
        last_tid = tid_list[0]

    task_list: Dict[int, Tuple[str, str, int]] = dao.get_task_list_by_gid_uid(uid, gid)

    if len(task_list) == 0:
        return redirect(url_for('route.groups'))

    return render_template(
        '/annotation.html',
        tid_list=tid_list,
        last_tid=last_tid,
        gid=gid,
        uid=uid,
        tasks=task_list,  # dict[int, tuple[tid:int, annotated:int]]
    )


# 标注页面
@bp_route.route('/arbitration')
@login_required
def arbitration():
    uid: int = current_user.uid
    gid: int = request.args.get('gid', 0, int)
    print('route.arbitration', uid, gid)
    tid_list = dao.get_tid_list_by_gid_uid(uid, gid)
    last_tid: int = dao.get_last_tid_by_gid_uid(uid, gid)

    if last_tid not in tid_list:
        last_tid = tid_list[0]

    task_list: Dict[int, Tuple[str, str, int]] = dao.get_task_list_by_gid_uid(uid, gid)
    if len(task_list) == 0:
        return redirect(url_for('route.groups'))

    return render_template(
        '/arbitration.html',
        tid_list=tid_list,
        last_tid=last_tid,
        uid=uid,
        gid=gid,
        tasks=task_list  # dict[int, tuple[tid:int, annotated:int]]
    )


# 参考结果
@bp_route.route('/compare')
@login_required
def compare():
    uid = 0
    # gid_list = [1 for i in range(10)] + [2 for j in range(10)]
    # gid_list = [1 for i in range(7)] + [2 for j in range(8)]

    # tid_list = [0, 120, 122, 150, 192, 1006, 1121] + [6, 397, 484, 871, 957, 1885, 1894, 1935]
    task1_tid_list = dao.get_tid_list_by_gid_uid(uid, 1)
    task2_tid_list = dao.get_tid_list_by_gid_uid(uid, 2)
    tid_list = task1_tid_list + task2_tid_list
    gid_list = [1 for i in task1_tid_list] + [2 for j in task2_tid_list]

    # last_tid: int = dao.get_last_tid_by_gid_uid(uid, gid)
    last_tid: int = tid_list[0]

    task1_list: Dict[int, Tuple[str, int]] = dao.get_task_list_by_gid_uid(uid, 1)
    task2_list: Dict[int, Tuple[str, int]] = dao.get_task_list_by_gid_uid(uid, 2)
    task_list = dict(task1_list)
    task_list.update(task2_list)

    if len(task_list) == 0:
        return redirect(url_for('route.groups'))

    return render_template(
        '/compare.html',
        tid_list=tid_list,
        last_tid=last_tid,
        uid=uid,
        gid_list=gid_list,
        tasks=task_list  # dict[int, tuple[tid:int, annotated:int]]
    )
