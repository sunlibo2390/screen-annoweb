# encoding:utf-8

from typing import Any, Dict, List, Tuple

from flask.blueprints import Blueprint
from flask.json import jsonify
from flask.wrappers import Response
from flask_login.utils import current_user, login_required

from dao import dao

bp_compare: Blueprint = Blueprint('compare', __name__, url_prefix='/compare')


@bp_compare.route('/load', methods=['POST'])
@login_required
def load():
    uid: int = current_user.uid
    gold_group: List[int] = dao.get_user_group_list_by_uid(0, 'trial', True)
    user_group: List[int] = dao.get_user_group_list_by_uid(uid, 'trial', True)
    titles: Dict[int, str] = dao.get_group_titles_by_group_list(gold_group)
    sentences: Dict[Tuple[int, int], Dict[str, Any]] = dao.get_sentences_by_group_list(gold_group)

    gold_tasks: Dict[int, Dict[Tuple[int, int],
                               Dict[str, Any]]] = dao.get_tasks_by_group_list_uid(gold_group, 0)
    user_tasks: Dict[int, Dict[Tuple[int, int],
                               Dict[str, Any]]] = dao.get_tasks_by_group_list_uid(user_group, uid)

    compare_result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    other_result: Dict[str, Dict[str, Any]] = {}

    for gid in gold_group:
        title: str = titles[gid]
        current_gold_tasks: Dict[Tuple[int, int], Dict[str, Any]] = gold_tasks[gid]
        tasks: Dict[str, Dict[str, Any]] = {}

        for (sid, pid), gold_content in current_gold_tasks.items():
            sentence: Dict[str, Any] = sentences[gid, sid]
            text: str = sentence['text']
            word: List[str] = sentence['word']
            gold_roleset: int = gold_content['roleset']
            gold_tag: List[int] = gold_content['tag']

            tasks[f'{text} ({pid + 1:02d} - {word[pid]})'] = {
                'word': word, 'gold_rs': gold_roleset, 'gold_tag': gold_tag
            }

        if gid in user_group:
            current_user_tasks: Dict[Tuple[int, int], Dict[str, Any]] = user_tasks[gid]

            for (sid, pid), user_content in current_user_tasks.items():
                sentence: Dict[str, Any] = sentences[gid, sid]
                text: str = sentence['text']
                word: List[str] = sentence['word']
                user_roleset: int = user_content['roleset']
                user_tag: List[int] = user_content['tag']

                tasks[f'{text} ({pid + 1:02d} - {word[pid]})'].update({
                    'user_rs': user_roleset, 'user_tag': user_tag,
                })

            compare_result[title] = tasks
        elif not current_user.ontest:
            other_result[title] = tasks

    return jsonify({'compare': compare_result, 'other': other_result})
