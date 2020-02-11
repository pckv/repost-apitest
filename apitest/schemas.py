import secrets
from dataclasses import dataclass, field, asdict
from functools import partial

random_string = partial(secrets.token_hex, 8)


@dataclass
class User:
    username: str = field(default_factory=random_string)
    password: str = field(default_factory=random_string)
    bio: str = None
    avatar_url: str = None

    @property
    def create(self):
        return {'username': self.username, 'password': self.password}

    login = create

    def edit(self, apply: bool = True, **fields):
        if apply:
            self.bio = fields.get('bio', self.bio)
            self.avatar_url = fields.get('avatar_url', self.avatar_url)

        return fields

    def compare(self, json_object: dict):
        return all(v == json_object[k] for k, v in asdict(self).items() if k in json_object)


@dataclass
class Resub:
    owner_username: str
    name: str = field(default_factory=random_string)
    description: str = field(default_factory=random_string)

    @property
    def create(self):
        return {'name': self.name, 'description': self.description}

    def edit(self, apply: bool = True, **fields):
        if apply:
            self.description = fields.get('description', self.description)
            self.owner_username = fields.get('new_owner_username', self.owner_username)

        return fields

    def compare(self, json_object: dict):
        return all(v == json_object[k] for k, v in asdict(self).items() if k in json_object)
