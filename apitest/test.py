import secrets
from dataclasses import dataclass, field
from functools import partial

from requests import get, post


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


def test_everything(url: str):
    def test(method, endpoint: str, *, token=None, status: int, **kwargs):
        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token['access_token']

        r = method(url + endpoint, headers=headers, **kwargs)
        assert r.status_code == status, f'{endpoint}: Expected {status}, got {r.status_code}'
        return r.json()

    user1 = User()

    print('Test get user1 before creation')
    test(get, f'/api/users/{user1.username}', status=404)

    print('Test create user1')
    user1_json = test(post, '/api/users', status=201, json=user1.create)
    assert user1.username == user1_json['username']

    print('Test create user1 with same username')
    test(post, '/api/users', status=400, json=user1.create)

    print('Test login nonexistent user')
    test(post, '/api/auth/token', status=401, data=User().login)

    print('Test login invalid user1 password')
    test(post, '/api/auth/token', status=401, data=User(username=user1.username).login)

    print('Test login user1')
    user1_token = test(post, '/api/auth/token', status=200, data=user1.login)
    assert 'access_token' in user1_token

    print('Test get user1')
    user1_json = test(get, f'/api/users/{user1.username}', status=200)
    assert user1.username == user1_json['username']

    print('Test get current user without authorization')
    test(get, f'/api/users/me', status=401)

    print('Test get current user with user1 token')
    user1_json = test(get, f'/api/users/me', token=user1_token, status=200)
    assert user1.username == user1_json['username']
