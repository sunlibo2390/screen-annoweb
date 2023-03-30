# encoding:utf-8

from flask_login.mixins import UserMixin
from typing import Any, Dict, List, Tuple
from dao import dao


class User(UserMixin):
    def __init__(self, uid: int):
        if not dao.has_user_uid(uid):
            raise ValueError(uid)

        self.uid: int = uid
        self.name: str = dao.get_name_by_uid(self.uid)
        # self.ontest: bool = dao.is_user_ontest_by_uid(self.uid)
        self.adjudicator: bool = dao.is_user_adjudicator_by_uid(self.uid)

        '''self.limit: Dict[int, int] = {x['gid']: x['limit'] for x in dao.get_user_group_list_by_uid(
            uid, 'both' if self.ontest else 'formal'
        )}'''

    def get_id(self):
        return str(self.uid)
