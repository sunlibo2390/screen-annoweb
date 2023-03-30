# encoding:utf-8

from flask.blueprints import Blueprint
from flask.globals import request
from flask.json import jsonify
from flask.wrappers import Response
from flask_login import login_user

from dao import dao
from user import User

bp_auth: Blueprint = Blueprint('auth', __name__, url_prefix='/auth')


@bp_auth.route('/auth', methods=['POST'])
def auth():
    username: str = request.values.get('username', '', type=str)
    password: str = request.values.get('password', '', type=str)
    uid: int = dao.validate_user(username, password)
    print("auth", uid, username, password)
    if uid == -1:
        return jsonify({'success': 0})
    else:
        login_user(User(uid))
        return jsonify({'success': 1})


@bp_auth.route('/reset', methods=['POST'])
def reset():
    username: str = request.values.get('username', '', type=str)
    old_pwd: str = request.values.get('old_pwd', '', type=str)
    new_pwd: str = request.values.get('new_pwd', '', type=str)
    reconfirmation: str = request.values.get('reconfirmation', '', type=str)
    # 若两次输入的新密码不一致
    if new_pwd != reconfirmation:
        return jsonify({'success': -1})

    uid: int = dao.reset_user_pwd(username, old_pwd, new_pwd)
    print("reset", uid, username, new_pwd)
    if uid == -1:
        return jsonify({'success': 0})
    else:
        login_user(User(uid))
        return jsonify({'success': 1})
