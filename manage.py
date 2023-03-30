# encoding:utf-8

from argparse import ArgumentParser
from typing import Optional

from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_login.login_manager import LoginManager
from waitress import serve

from auth import bp_auth
from compare import bp_compare
from groups import bp_groups
from route import bp_route
from task import bp_task
from user import User

app = Flask(__name__)

app.register_blueprint(bp_route)
app.register_blueprint(bp_auth)
app.register_blueprint(bp_groups)
app.register_blueprint(bp_task)
app.register_blueprint(bp_compare)

app.config.from_mapping(
    SECRET_KEY='0018ad8e2b505036d3f9bf08bf5bcfe7f9ecb680500de8b47b9521e9d9ee10cb',
    SESSION_COOKIE_NAME='awt_cookie'
)

bootstrap = Bootstrap5(app)

login_manager = LoginManager(app)
login_manager.login_message = '请登录后操作！'
login_manager.login_view = 'route.login'


@login_manager.user_loader
def load_user(uid):
    try:
        return User(int(uid))
    except ValueError:
        return None


def run_server(dev):
    from os import environ
    environ['FLASK_ENV'] = 'development'
    app.run(host='0.0.0.0', port=5000)
    # app.run(host='47.113.193.232', port=5000)


parser = ArgumentParser(description='Launch the flask server.')
parser.add_argument('-d', '--dev', action='store_true', help='enable development mode')

if __name__ == '__main__':
    run_server(parser.parse_args().dev)
