# encoding:utf-8

from hmac import new
from typing import Any, Optional, Union, Dict, List, Tuple

from pymongo.collection import Collection, Cursor
from pymongo.database import Database
from pymongo.mongo_client import MongoClient
from pymongo.errors import PyMongoError


def singleton(cls):
    _instance = {}

    def inner(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return inner


@singleton
class DAO:
    def __init__(self, host: str, username: str, password: str, database: str, authSource: str):
        self.__client: MongoClient = MongoClient(host=host, username=username,
                                                 password=password, authSource=authSource)

        self._db: Database = self.__client[database]  # 数据库
        self._cols: Dict[str, Collection] = {x: self._db[x] for x in [
            'user_gpt', 'task1_gpt', 'task2_gpt', 'anno_gpt', 'arbi_gpt', 'hist_gpt', 'error_gpt'
        ]}  # 数据库表名字典，表名:数据表

    # 验证用户密码
    def validate_user(self, name: str, pwd: str):
        user_query: Optional[Dict[str, Any]] = self._query(
            'user_gpt', {'name': name, 'active': True}, 'one', fields=['uid', 'password']
        )
        # print(user_query)
        if user_query is None:
            return -1

        # gen: str = new(user_query['key'].encode('utf8'), pwd.encode('utf8'), 'MD5').hexdigest()
        # print(gen)
        # (pwd, user_query['password'])
        return -1 if pwd != user_query['password'] else int(user_query['uid'])

    # 重置用户密码
    def reset_user_pwd(self, name, old_pwd, new_pwd):
        print(old_pwd, type(old_pwd))
        user_query: Optional[Dict[str, Any]] = self._query(
            'user_gpt', {'name': name, 'active': True, 'password': old_pwd}, 'one', fields=['uid']
        )
        print(user_query)
        if user_query is None:
            return -1
        else:
            try:
                self._update('user_gpt', {'name': name, 'active': True, 'password': old_pwd}, {'password': new_pwd})
                return int(user_query['uid'])
            except:
                return -1

    def has_user_uid(self, uid: int):
        return uid >= 0 and self._query('user_gpt', {'uid': uid, 'active': True}, 'one') is not None

    def get_name_by_uid(self, uid: int):
        user_query: Optional[dict[str, str]] = self._query(
            'user_gpt', {'uid': uid, 'active': True}, 'one', fields=['name']
        )

        return '' if user_query is None else user_query['name']

    # 判断用户是否为仲裁
    def is_user_adjudicator_by_uid(self, uid: int):
        user_query: Optional[dict[str, str]] = self._query(
            'user_gpt', {'uid': uid, 'active': True}, 'one', fields=['adjudicator']
        )

        return user_query is not None and user_query['adjudicator']

    # 判断用户任务是否完成
    def is_annotated_by_gid_tid_uid(self, uid, gid, tid):
        
        if gid==2:
            result = self._query('task2_gpt', {'tid': tid}, 'one', fields=['left_state'])
            if result['left_state']==-1:
                return -1
            elif result['left_state']==0 or result['left_state']==1:
                return 0

        elif gid==1:
            result = self._query('anno_gpt', {'gid': gid, 'uid': uid, 'tid': tid}, 'one', fields=['anno_list', 'aspect_list'])
            if result is not None:
                if len(result['anno_list']) > 0 and len(result['aspect_list']) > 0:
                    return 1
                elif len(result['anno_list']) == 0 and len(result['aspect_list']) == 0:
                    return -1
                else:
                    return -2
            else:
                return -1

    # 判断用户仲裁任务是否完成
    def is_arbitrated_by_gid_tid_uid(self, uid, gid, tid):
        result = self._query('anno_gpt', {'gid': gid, 'uid': {'$ne': uid}, 'tid': tid}, 'all')
        # print('is_arbitrated_by_gid_tid_uid', uid, gid, tid)
        all_rejected = True
        for task in result:
            # print(task)
            if task['state'] == -1:  # 有任务未选择接收或拒绝
                return -1
            elif task['state'] == 1:
                all_rejected = False
        # print('all_rejected', all_rejected)
        if all_rejected:
            uid_result = self._query('anno_gpt', {'gid': gid, 'uid': uid, 'tid': tid}, 'all')
            if len(list(uid_result)) > 0:
                return 1  # 全部拒绝且补充了标注
            else:
                return -1  # 全部拒绝但没有补充标注
        else:
            return 1  # 没有全部拒绝，但全都选择了

    # 获取用户最后标注的任务id
    def get_last_tid_by_gid_uid(self, uid: int, gid: int):
        query: Optional[dict[str, int]] = self._query('hist_gpt', {'uid': uid, 'gid': gid}, 'one',
                                                      fields=['tid'])
        # print(query)
        return 0 if query is None else query['tid']

    def get_tid_list_by_gid_uid(self, uid: int, gid: int):
        user_data = self._query('user_gpt', {'uid': uid, 'active': True}, 'one')
        if gid == 1:
            tid_list = user_data['task1_ids']
        elif gid == 2:
            tid_list = user_data['task2_ids']
        tid_list.sort()
        print('tid_list', tid_list)
        return tid_list

    def get_task_list_by_gid_uid(self, uid: int, gid: int, adjudicator: bool = False):
        is_adjudicator: bool = self.is_user_adjudicator_by_uid(uid)
        print('get_task_list_by_gid_uid', uid, gid)
        user_data = self._query('user_gpt', {'uid': uid, 'active': True}, 'one')

        tid_list = user_data['task%d_ids' % gid]
        tasks: Dict[int, Tuple[str, int]] = {
            x['tid']: (
                x['object'],
                self.is_arbitrated_by_gid_tid_uid(uid, gid, x['tid']) if adjudicator
                else self.is_annotated_by_gid_tid_uid(uid, gid, x['tid'])
            )
            for x in self._query(
                'task%d_gpt' % gid, {'tid': {"$in": tid_list}}, 'all', fields=['tid', 'object']
            )
        }
        print('tasks', tasks)

        return tasks

    def get_task_by_gid_tid(self, gid, tid):
        if gid == 1:
            task = self._query(
                'task1_gpt', {'tid': tid}, 'one',
                fields=['tid', 'review', 'aspects', 'object']
            )
        elif gid == 2:
            task = self._query(
                'task2_gpt', {'tid': tid}, 'one',
                fields=['tid', 'reviews', 'aspect', 'object', 'review_state', 'left_state']
            )
            try:
                review_state = task['review_state']
                return task
            except:
                task['review_state'] = [1 for review in task['reviews']]
        return task

    def get_anno_by_gid_tid_uid(self, gid, tid, uid):
        print(gid, tid, uid)
        annos = self._query(
            'anno_gpt', {'gid': gid, 'tid': tid, 'uid': uid}, 'one',
            fields=['anno_list', 'aspect_list']
        )
        print(annos)
        if annos is None:
            return [], []
        else:
            anno_list = annos['anno_list']
            aspect_list = [aspect.split('/') for aspect in annos['aspect_list']]
            return anno_list, aspect_list

    def get_annotated_task_by_gid_tid_uid(self, uid, gid, tid):
        # print(uid, gid, tid)
        arbi_tasks = self._query(
            'arbi_gpt', {'uid': uid, 'gid': gid, 'tid': tid},
            'one', fields=['anno_list', 'state_list', 'aspect_list', 'arbi_list', 'review_state'])
        if arbi_tasks is not None:
            # 若被仲裁过
            anno_list = arbi_tasks['anno_list']
            state_list = arbi_tasks['state_list']
            anno_num = len(anno_list)
            aspect_list = [aspect.split('/') for aspect in arbi_tasks['aspect_list']]
            if gid==2:
                review_state = arbi_tasks['review_state']
            else:
                review_state = []
            try:
                arbi_list = arbi_tasks['arbi_list']
            except:
                arbi_list = []
            return [(anno_list[i], state_list[i]) for i in range(anno_num)], aspect_list, arbi_list, review_state
        else:
            # 若没有被仲裁过
            annotated_tasks = self._query(
                'anno_gpt', {'uid': {'$ne': uid}, 'gid': gid, 'tid': tid},
                'all', fields=['anno_list', 'aspect_list'])
            # print('get_annotated_task_by_gid_tid_uid', len(list(annotated_tasks)))
            task_list = []
            all_aspect_list = []
            for task in annotated_tasks:
                for anno in task['anno_list']:
                    task_list.append(
                        (anno, -1)
                    )
                all_aspect_list += task["aspect_list"]  # list[str]
            all_aspect_list = list(set(all_aspect_list))
            all_aspect_list = [aspect.split('/') for aspect in all_aspect_list]  # list[list[str]]

            return task_list, all_aspect_list, [], []

    def get_task_annotators_by_gid_cid(self, gid: int, tid: int):
        task: Optional[dict[str, Any]] = self._query(
            'anno_gpt', {'gid': gid, 'tid': tid}, 'one', fields=['uid']
        )

        return [] if task is None else task['anno']

    def count_annotated_by_uid_gid_tidlist(self, uid, gid, tid_list):
        if gid == 2:
            annotated_tasks = self._query('task2_gpt', {'tid': {'$in': tid_list}}, 'all',
                                      fields=["left_state"])
            finished_num = 0
            for task in annotated_tasks:
                '''print(
                    'dao/count__annotated',
                    finished_num,
                    task['anno_list'],
                    len(task['anno_list'])
                )'''
                if task['left_state']==0 or task['left_state']==1:
                    finished_num += 1
            return finished_num
        elif gid==1:
            annotated_tasks = self._query('anno_gpt', {'uid': uid, 'gid': gid, 'tid': {'$in': tid_list}}, 'all',
                                          fields=["anno_list", "aspect_list"])
            finished_num = 0
            for task in annotated_tasks:
                '''print(
                    'dao/count__annotated',
                    finished_num,
                    task['anno_list'],
                    len(task['anno_list'])
                )'''
                if len(task['anno_list']) > 0 and len(task['aspect_list']) > 0:
                    finished_num += 1
            return finished_num

    def count_arbitrated_by_uid_gid_tidlist(self, uid, gid, tid_list):
        finished_num = 0
        arbitrated_tasks = self._query('arbi_gpt', {'uid': uid, 'gid': gid, 'tid': {'$in': tid_list}}, 'all',
                                       fields=["adjudicated"])
        finished_num = 0
        for task in arbitrated_tasks:
            if task['adjudicated'] == 1:
                finished_num += 1
        '''for tid in tid_list:
            state = self._query('arbi', {'uid': uid, 'gid': gid, 'tid': tid}, 'one', fields=["state"])
            if state == 1:
                finished_num += 1'''

        '''state_list = self._query('arbi', {'uid': uid, 'gid': gid}, 'all', fields=["state"])
        for state in state_list:
            if state == 1:
                finished_num += 1'''
        return finished_num

    def set_last_tid_by_gid_uid(self, uid: int, gid: int, tid: int):
        try:
            self._update('hist_gpt', {'gid': gid, 'uid': uid}, {'tid': tid})
        except PyMongoError:
            pass

    def save_task_by_gid_tid_uid(self, uid: int, gid: int, tid: int, anno_list: List[str], aspect_list: List[str],
                                 anno_state_list: List[int] = None, arbi_list: List[str] = None, 
                                 review_state: List[int] = None, left_state: int = -1):
        try:
            # 标注环节
            # 清空该用户对该任务的原有标注
            annos = self._query('anno_gpt', {'gid': gid, 'tid': tid, 'uid': uid}, 'all')
            for anno in annos:
                self._remove('anno_gpt', {'gid': gid, 'tid': tid, 'uid': uid})
            print("insert start", 'gid:%d'%gid, 'tid%d'%tid)
            self._insert('anno_gpt',
                         {'gid': gid, 'tid': tid, 'uid': uid, 'anno_list': anno_list, 'aspect_list': aspect_list,
                          'state': -1})
            print("insert end")

            if gid==2 and review_state is not None:
                self._update('task2_gpt', {'tid':tid}, {'review_state':review_state, 'left_state':left_state})

        except PyMongoError:
            pass

    def is_arbitrated_by_list(self, aspect_list, anno_state_list, arbi_list):
        adjudicated = -1
        if len(aspect_list) > 0:
            # 必须有aspect
            all_rejected = True
            all_judged = True
            for state in anno_state_list:
                if state != 0:
                    all_rejected = False
                if state == -1:
                    all_judged = False
            # 如果全部拒绝
            if all_rejected:
                # 必须有补充标注
                if len(arbi_list) > 0:
                    adjudicated = 1
                else:
                    adjudicated = -1
            elif all_judged:
                adjudicated = 1
            else:
                adjudicated = -1
        else:
            adjudicated = -1
        return adjudicated

    def report_task_error(self, uid, gid, tid, error_type, error_info):
        error = self._query('error_gpt', {"uid": uid, "gid": gid, "tid": tid}, "one")
        if error is not None:
            self._remove('error_gpt', {"uid": uid, "gid": gid, "tid": tid})
        self._insert('error_gpt', {"uid": uid, "gid": gid, "tid": tid, "type": error_type, "info": error_info})

    def _query(self,
               col: str,
               filter: Dict[str, Any],
               mode,
               fields: Optional[List[str]] = None
               ):
        source: Collection = self._cols[col]  # 列名col对应数据列
        if mode == 'count':
            return source.count(filter)  # 根据filter筛选并统计总数
        projection: Optional[Dict[str, bool]]

        if fields is None:
            projection = None
        else:
            projection = {x: True for x in fields}
            projection['_id'] = False

        return (
            source.find_one if mode == 'one' else source.find
        )(filter, projection=projection)

    def _aggregate(self, col: str, pipeline: List[Dict[str, Any]]):
        return self._cols[col].aggregate(pipeline)

    def _insert(self, col: str, doc: Dict[str, Any]):
        self._cols[col].insert_one(doc)

    def _update(self, col: str, filter: Dict[str, Any], doc: Dict[str, Any]):
        self._cols[col].update_one(filter, {'$set': doc}, upsert=True)

    def _remove(self, col: str, filter: Dict[str, Any]):
        self._cols[col].delete_one(filter)


dao: DAO = DAO('47.113.193.232', 'root', 'sLb17729033632..', 'annotation', 'admin')
