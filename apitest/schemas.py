import secrets
from dataclasses import dataclass, field, asdict
from functools import partial

random_string = partial(secrets.token_hex, 8)


def property_to_dict(**fields):
    @property
    def create(self):
        return {v: getattr(self, k) for k, v in fields.items()}

    return create


def method_edit(**editable_fields):
    def edit(self, apply: bool = True, **fields):
        if apply:
            for k, v in editable_fields.items():
                if v in fields:
                    setattr(self, k, fields[v])

        return fields

    return edit


def method_compare(**update_fields):
    def compare(self, json_object: dict, update: bool = False):
        if update:
            for k, v in update_fields.items():
                setattr(self, k, json_object[v])

        return all(v == json_object[k] for k, v in asdict(self).items() if k in json_object)

    return compare


@dataclass
class User:
    username: str = field(default_factory=random_string)
    password: str = field(default_factory=random_string)
    bio: str = None
    avatar_url: str = None

    create = property_to_dict(username='username', password='password')
    edit = method_edit(bio='bio', avatar_url='avatar_url')
    compare = method_compare()

    @property
    def login(self):
        return {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
            'client_id': 'repost',
            'scope': 'user'
        }


@dataclass
class Resub:
    owner_username: str
    name: str = field(default_factory=random_string)
    description: str = field(default_factory=random_string)

    create = property_to_dict(name='name', description='description')
    edit = method_edit(description='description', owner_username='new_owner_username')
    compare = method_compare()


@dataclass
class Post:
    author_username: str
    parent_resub_name: str
    title: str = field(default_factory=random_string)
    url: str = None
    content: str = None
    id: int = None
    votes: int = 0

    create = property_to_dict(title='title', url='url', content='content')
    edit = method_edit(title='title', url='url', content='content')
    compare = method_compare(id='id')


@dataclass
class Comment:
    author_username: str
    parent_resub_name: str
    parent_post_id: int
    parent_comment_id: int = None
    content: str = field(default_factory=random_string)
    id: int = None
    votes: int = 0

    create = property_to_dict(content='content')
    edit = method_edit(content='content')
    compare = method_compare(id='id')
