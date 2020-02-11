from requests import get, post, patch

from apitest.schemas import User


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
    response = test(post, '/api/users', status=201, json=user1.create)
    assert user1.username == response['username']

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
    response = test(get, f'/api/users/{user1.username}', status=200)
    assert user1.username == response['username']

    print('Test get current user without authorization')
    test(get, '/api/users/me', status=401)

    print('Test get current user with user1 token')
    response = test(get, '/api/users/me', token=user1_token, status=200)
    assert user1.username == response['username']

    print('Test edit current user without authorization')
    test(patch, '/api/users/me', status=401, json=user1.edit(bio='Unchanged bio'))

    print('Test edit current user bio only')
    response = test(patch, '/api/users/me', token=user1_token, status=200, json=user1.edit(bio='Custom bio'))
    assert user1.bio == response['bio']
    assert user1.avatar_url == response['avatar_url']

    print('Test edit current user avatar_url only')
    response = test(patch, '/api/users/me', token=user1_token, status=200, json=user1.edit(avatar_url='Custom url'))
    assert user1.bio == response['bio']
    assert user1.avatar_url == response['avatar_url']

    print('Test edit current user bio and avatar_url')
    response = test(patch, '/api/users/me', token=user1_token, status=200,
                    json=user1.edit(bio='Custom bio 2', avatar_url='Custom url 2'))
    assert user1.bio == response['bio']
    assert user1.avatar_url == response['avatar_url']
