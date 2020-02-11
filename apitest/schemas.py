import secrets
from dataclasses import dataclass, field
from functools import partial


@dataclass
class User:
    username: str = field(default_factory=partial(secrets.token_hex, 8))
    password: str = field(default_factory=partial(secrets.token_hex, 8))
    bio: str = None
    avatar_url: str = None

    @property
    def create(self):
        return {'username': self.username, 'password': self.password}

    login = create

    def edit(self, **fields):
        for k, v in fields.items():
            setattr(self, k, v)

        return fields
