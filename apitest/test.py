from requests import get, post, patch

from apitest.schemas import User, Resub


def test_everything(url: str):
    def test(method, endpoint: str, *, token=None, status: int, compare=None, skip_token_test: bool = False, **kwargs):
        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token['access_token']

        r = method(f'{url}/api{endpoint}', headers=headers, **kwargs)
        assert r.status_code == status, f'{endpoint}: Expected {status}, got {r.status_code}\n{r.text}'
        obj = r.json()

        if compare:
            assert compare.compare(obj), f'{endpoint}: Failed object check, got:\n{obj}\nExpected:\n{compare}'

        # Do extra authorization tests when token is provided
        if token and not skip_token_test:
            print('\tWithout authorization')
            test(method, endpoint, status=401, skip_token_test=True, **kwargs)

            print('\tWith invalid token')
            test(method, endpoint, token={'access_token': 'not.a.token'}, status=400, skip_token_test=True, **kwargs)

        return obj

    user1 = User()

    print('Test get user1 before creation')
    test(get, f'/users/{user1.username}', status=404)

    print('Test create user1')
    test(post, '/users', status=201, compare=user1, json=user1.create)

    print('Test create user1 with same username')
    test(post, '/users', status=400, json=user1.create)

    print('Test login nonexistent user')
    test(post, '/auth/token', status=401, data=User().login)

    print('Test login invalid user1 password')
    test(post, '/auth/token', status=401, data=User(username=user1.username).login)

    print('Test login user1')
    user1_token = test(post, '/auth/token', status=200, data=user1.login)
    assert 'access_token' in user1_token

    print('Test get user1')
    test(get, f'/users/{user1.username}', status=200, compare=user1)

    print('Test get current user with user1 token')
    test(get, '/users/me', token=user1_token, status=200, compare=user1)

    print('Test edit current user bio only')
    test(patch, '/users/me', token=user1_token, status=200, compare=user1, json=user1.edit(bio='Custom bio'))

    print('Test edit current user avatar_url only')
    test(patch, '/users/me', token=user1_token, status=200, compare=user1,
         json=user1.edit(avatar_url='Custom url'))

    print('Test edit current user bio and avatar_url')
    test(patch, '/users/me', token=user1_token, status=200, compare=user1,
         json=user1.edit(bio='Custom bio 2', avatar_url='Custom url 2'))

    print('Test get resubs is list')
    response = test(get, '/resubs', status=200)
    assert type(response) is list

    resub_user1 = Resub(owner_username=user1.username)

    print('Test get resub_user1 before creation')
    test(get, f'/resubs/{resub_user1.name}', status=404)

    print('Test create resub_user1')
    test(post, '/resubs', status=201, token=user1_token, compare=resub_user1, json=resub_user1.create)

    print('Test create resub_user1 with same name')
    test(post, '/resubs', status=400, token=user1_token, compare=resub_user1, json=resub_user1.create)

    print('Test resub_user1 in get resubs')
    resubs = test(get, '/resubs', status=200)
    assert any(resub_user1.compare(resub) for resub in resubs)

    print('Test get resub_user1')
    test(get, f'/resubs/{resub_user1.name}', status=200, compare=resub_user1)

    print('Test resub_user1 in get user1 resubs')
    resubs = test(get, f'/users/{user1.username}/resubs', status=200)
    assert any(resub_user1.compare(resub) for resub in resubs)

    print('Test edit nonexistent resub description as user1')
    test(patch, f'/resubs/{Resub(owner_username=user1.username).name}', status=404, token=user1_token,
         json=resub_user1.edit(description='Nonexistent description', apply=False), skip_token_test=True)

    print('Test edit resub_user1 description as user1')
    test(patch, f'/resubs/{resub_user1.name}', status=200, token=user1_token, compare=resub_user1,
         json=resub_user1.edit(description='User1 description'))

    print('Test transfer resub_user1 ownership to nonexistent user')
    test(patch, f'/resubs/{resub_user1.name}', status=404, token=user1_token,
         json=resub_user1.edit(new_owner_username=User().username, apply=False))

    user2 = User()

    print('Test create user2')
    test(post, '/users', status=201, compare=user2, json=user2.create)

    print('Test login user2')
    user2_token = test(post, '/auth/token', status=200, data=user2.login)
    assert 'access_token' in user2_token

    print('Test edit resub_user1 description as user2')
    test(patch, f'/resubs/{resub_user1.name}', status=403, token=user2_token,
         json=resub_user1.edit(description='User2 description', apply=False))

    print('Test transfer resub_user1 ownership to user2')
    test(patch, f'/resubs/{resub_user1.name}', status=200, token=user1_token, compare=resub_user1,
         json=resub_user1.edit(new_owner_username=user2.username))

    print('Test edit resub_user1 description as user1 when user2 is owner')
    test(patch, f'/resubs/{resub_user1.name}', status=403, token=user1_token,
         json=resub_user1.edit(description='User1 description 2', apply=False))

    print('Test edit resub_user1 description as user2 when user2 is owner')
    test(patch, f'/resubs/{resub_user1.name}', status=200, token=user2_token, compare=resub_user1,
         json=resub_user1.edit(description='User2 description 2'))

    print('Test resub_user1 in get user2 resubs when user2 is owner')
    resubs = test(get, f'/users/{user2.username}/resubs', status=200)
    assert any(resub_user1.compare(resub) for resub in resubs)
