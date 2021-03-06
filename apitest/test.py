import random
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from requests import get, post, patch, delete

from apitest.schemas import User, Resub, Post, Comment


@dataclass
class TestStats:
    count: int = 0
    elapsed_seconds: int = 0


def test_everything(url: str, logging: bool = True) -> TestStats:
    """Perform all tests and return statistics when passed."""
    stats = TestStats()
    started = datetime.now()

    def log(*args):
        if logging:
            print(*args)

    def test(method, endpoint: str, *, token=None, status: int, compare=None, skip_token_test: bool = False, **kwargs):
        stats.count += 1
        error_prefix = f'{method.__name__.upper()} {endpoint}'

        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token['access_token']

        if method == patch:
            headers['content-type'] = 'application/patch+json'

        # Do extra authorization tests when token is provided
        if token and not skip_token_test:
            log('\tWithout authorization')
            test(method, endpoint, status=401, skip_token_test=True, **kwargs)

            log('\tWith invalid token')
            test(method, endpoint, token={'access_token': 'not.a.token'}, status=401, skip_token_test=True, **kwargs)

        r = method(f'{url}/api{endpoint}', headers=headers, **kwargs)
        assert r.status_code == status, f'{error_prefix}\nGot: {r.status_code}\nExpected: {status}\nResponse: {r.text}'
        if r.status_code >= 300 or r.status_code == 204:
            return

        obj = r.json()

        if compare:
            assert compare.compare(obj,
                                   update=True), f'{error_prefix} Failed object check:\nGot: {obj}\nExpected: {compare}'

        return obj

    # NOTE:
    # some endpoints add a / at the end. This is because root endpoints
    # in FastAPI require this at the end. The server should redirect
    # posts without the / to the endpoint with it, but future behaviour
    # should perhaps be considered to allow calls to endpoints with no
    # trailing /

    random.seed()

    user1 = User()

    log('Test get user1 before creation')
    test(get, f'/users/{user1.username}', status=404)

    log('Test create user1')
    test(post, '/users/', status=201, compare=user1, json=user1.create)

    log('Test create user1 with same username')
    test(post, '/users/', status=400, json=user1.create)

    log('Test login nonexistent user')
    test(post, '/auth/token', status=400, data=User().login)

    log('Test login invalid user1 password')
    test(post, '/auth/token', status=400, data=User(username=user1.username).login)

    log('Test login user1')
    user1_token = test(post, '/auth/token', status=200, data=user1.login)
    assert 'access_token' in user1_token

    log('Test get user1')
    test(get, f'/users/{user1.username}', status=200, compare=user1)

    log('Test get current user with user1 token')
    test(get, '/users/me', token=user1_token, status=200, compare=user1)

    log('Test edit current user bio only')
    test(patch, '/users/me', token=user1_token, status=200, compare=user1, json=user1.edit(bio='Custom bio'))

    log('Test edit current user avatar_url only')
    test(patch, '/users/me', token=user1_token, status=200, compare=user1, json=user1.edit(avatar_url='Custom url'))

    log('Test edit current user bio and avatar_url')
    test(patch, '/users/me', token=user1_token, status=200, compare=user1,
         json=user1.edit(bio='Custom bio 2', avatar_url='Custom url 2'))

    log('Test get resubs is list')
    response = test(get, '/resubs/', status=200)
    assert type(response) is list

    resub1 = Resub(owner_username=user1.username)

    log('Test get resub1 before creation')
    test(get, f'/resubs/{resub1.name}', status=404)

    log('Test create resub1')
    test(post, '/resubs/', status=201, token=user1_token, compare=resub1, json=resub1.create)

    log('Test create resub1 with same name')
    test(post, '/resubs/', status=400, token=user1_token, compare=resub1, json=resub1.create)

    log('Test resub1 in get resubs')
    resubs = test(get, '/resubs/', status=200)
    assert any(resub1.compare(r) for r in resubs)

    log('Test get resub1')
    test(get, f'/resubs/{resub1.name}', status=200, compare=resub1)

    log('Test get user1 resubs has resub1')
    resubs = test(get, f'/users/{user1.username}/resubs', status=200)
    assert any(resub1.compare(r) for r in resubs)

    log('Test edit nonexistent resub description as user1')
    test(patch, f'/resubs/{Resub(owner_username=user1.username).name}', status=404, token=user1_token,
         json=resub1.edit(description='Nonexistent description', apply=False), skip_token_test=True)

    log('Test edit resub1 description as user1')
    test(patch, f'/resubs/{resub1.name}', status=200, token=user1_token, compare=resub1,
         json=resub1.edit(description='User1 description'))

    log('Test transfer resub1 ownership to nonexistent user')
    test(patch, f'/resubs/{resub1.name}', status=404, token=user1_token,
         json=resub1.edit(new_owner_username=User().username, apply=False))

    user2 = User()

    log('Test create user2')
    test(post, '/users/', status=201, compare=user2, json=user2.create)

    log('Test login user2')
    user2_token = test(post, '/auth/token', status=200, data=user2.login)
    assert 'access_token' in user2_token

    log('Test edit resub1 description as user2')
    test(patch, f'/resubs/{resub1.name}', status=403, token=user2_token,
         json=resub1.edit(description='User2 description', apply=False))

    log('Test get user2 resubs does not have resub1 before transfer ownership')
    resubs = test(get, f'/users/{user2.username}/resubs', status=200)
    assert not any(resub1.compare(r) for r in resubs)

    log('Test transfer resub1 ownership to user2')
    test(patch, f'/resubs/{resub1.name}', status=200, token=user1_token, compare=resub1,
         json=resub1.edit(new_owner_username=user2.username))

    log('Test edit resub1 description as user1 when user2 is owner')
    test(patch, f'/resubs/{resub1.name}', status=403, token=user1_token,
         json=resub1.edit(description='User1 description 2', apply=False))

    log('Test edit resub1 description as user2 when user2 is owner')
    test(patch, f'/resubs/{resub1.name}', status=200, token=user2_token, compare=resub1,
         json=resub1.edit(description='User2 description 2'))

    log('Test get user2 resubs has resub1 when user2 is owner')
    resubs = test(get, f'/users/{user2.username}/resubs', status=200)
    assert any(resub1.compare(r) for r in resubs)

    log('Test get posts in resub1 is list')
    posts = test(get, f'/resubs/{resub1.name}/posts/', status=200)
    assert type(posts) is list

    log('Test get posts in nonexistent resub')
    test(get, f'/resubs/{Resub(owner_username=user1.username).name}/posts/', status=404)

    post1 = Post(author_username=user1.username, parent_resub_name=resub1.name)

    log('Test create post in resub1 as user1')
    test(post, f'/resubs/{resub1.name}/posts/', status=201, token=user1_token, compare=post1, json=post1.create)

    log('Test get post1')
    test(get, f'/posts/{post1.id}', status=200, compare=post1)

    post1_copy = copy(post1)

    log('Test create same post in resub1 as user1')
    test(post, f'/resubs/{resub1.name}/posts/', status=201, token=user1_token, compare=post1_copy,
         json=post1_copy.create)

    log('Test get post1_copy')
    test(get, f'/posts/{post1_copy.id}', status=200, compare=post1_copy)

    log('Test get posts in resub1 has both post1')
    posts = test(get, f'/resubs/{resub1.name}/posts/', status=200)
    assert any(post1.compare(p) for p in posts)
    assert any(post1_copy.compare(p) for p in posts)

    post2 = Post(author_username=user2.username, parent_resub_name=resub1.name)

    log('Test create post in resub1 as user2')
    test(post, f'/resubs/{resub1.name}/posts/', status=201, token=user2_token, compare=post2, json=post2.create)

    log('Test get post2')
    test(get, f'/posts/{post2.id}', status=200, compare=post2)

    log('Test get nonexistent post in resub1')
    test(get, f'/resubs/{resub1.name}/posts/9999999999', status=404)

    log('Test get user1 posts has post1')
    posts = test(get, f'/users/{user1.username}/posts', status=200)
    assert any(post1.compare(p) for p in posts)

    log('Test user1 edit post1 title')
    test(patch, f'/posts/{post1.id}', status=200, token=user1_token, compare=post1,
         json=post1.edit(title='Custom title'))

    log('Test user1 add content to post1')
    test(patch, f'/posts/{post1.id}', status=200, token=user1_token, compare=post1,
         json=post1.edit(content='Custom content'))

    log('Test user1 add url to post1 and remove content')
    test(patch, f'/posts/{post1.id}', status=200, token=user1_token, compare=post1,
         json=post1.edit(content=None, url='Custom url'))

    log('Test user1 change post1 content and url')
    test(patch, f'/posts/{post1.id}', status=200, token=user1_token, compare=post1,
         json=post1.edit(content='Custom content 2', url='Custom url 2'))

    log('Test user2 edit post1 title')
    test(patch, f'/posts/{post1.id}', status=403, token=user2_token, json=post1.edit(title='User2 title', apply=False))

    log('Test user1 set post1 title to null')
    test(patch, f'/posts/{post1.id}', status=422, token=user1_token, json=post1.edit(title=None, apply=False))

    def test_vote_entity(path: str, entity_name: str, entity: Union[Post, Comment]):
        log(f'Test user1 vote -2 {entity_name}')
        test(patch, f'{path}/vote/-2', status=422, token=user1_token)

        log(f'Test user1 vote 2 {entity_name}')
        test(patch, f'{path}/vote/2', status=422, token=user1_token)

        log(f'Test user1 vote 0 {entity_name}')
        test(patch, f'{path}/vote/0', status=200, token=user1_token, compare=entity)

        log(f'Test user1 vote -1 {entity_name}')
        entity.votes = -1
        test(patch, f'{path}/vote/-1', status=200, token=user1_token, compare=entity)

        log(f'Test user1 vote -1 {entity_name} again')
        test(patch, f'{path}/vote/-1', status=200, token=user1_token, compare=entity)

        log(f'Test user2 vote -1 {entity_name}')
        entity.votes = -2
        test(patch, f'{path}/vote/-1', status=200, token=user2_token, compare=entity)

        log(f'Test user1 vote 1 {entity_name}')
        entity.votes = 0
        test(patch, f'{path}/vote/1', status=200, token=user1_token, compare=entity)

        log(f'Test user2 vote 0 {entity_name}')
        entity.votes = 1
        test(patch, f'{path}/vote/0', status=200, token=user2_token, compare=entity)

        log(f'Test user2 vote 1 {entity_name}')
        entity.votes = 2
        test(patch, f'{path}/vote/1', status=200, token=user2_token, compare=entity)

    test_vote_entity(f'/posts/{post1.id}', 'post1', post1)

    log('Test get post1 has correct votes')
    test(get, f'/posts/{post1.id}', status=200, compare=post1)

    log('Test get comments from post1 is list')
    comments = test(get, f'/posts/{post1.id}/comments/', status=200)
    assert type(comments) is list

    log('Test get comments from nonexistent post')
    test(get, f'/resubs/{resub1.name}/posts/9999999999/comments/', status=404)

    comment1 = Comment(author_username=user1.username, parent_resub_name=resub1.name, parent_post_id=post1.id)

    log('Test create comment in post1 from user1')
    test(post, f'/posts/{post1.id}/comments/', status=201, token=user1_token, compare=comment1, json=comment1.create)

    comment1_copy = copy(comment1)

    log('Test create same comment in post1 from user1')
    test(post, f'/posts/{post1.id}/comments/', status=201, token=user1_token, compare=comment1_copy,
         json=comment1_copy.create)

    log('Test get comments in post1 has both comment1')
    comments = test(get, f'/posts/{post1.id}/comments/', status=200)
    assert any(comment1.compare(c) for c in comments)
    assert any(comment1_copy.compare(c) for c in comments)

    log('Test get user1 comments has comment1')
    comments = test(get, f'/users/{user1.username}/comments/', status=200)
    assert any(comment1.compare(c) for c in comments)

    comment2 = Comment(author_username=user2.username, parent_resub_name=resub1.name, parent_post_id=post1.id)

    log('Test create comment in post1 as user2')
    test(post, f'/posts/{post1.id}/comments/', status=201, token=user2_token, compare=comment2, json=comment2.create)

    comment1_reply = Comment(author_username=user2.username, parent_resub_name=resub1.name, parent_post_id=post1.id,
                             parent_comment_id=comment1.id)

    log('Test create reply to comment1 as user2')
    test(post, f'/comments/{comment1.id}', status=201, token=user2_token, compare=comment1_reply,
         json=comment1_reply.create)

    log('Test edit comment1 content as user1')
    test(patch, f'/comments/{comment1.id}', status=200, token=user1_token, compare=comment1,
         json=comment1.edit(content='Custom content'))

    log('Test set comment1 content to null')
    test(patch, f'/comments/{comment1.id}', status=422, token=user1_token,
         json=comment1.edit(content=None, apply=False))

    log('Test edit comment1 as user2')
    test(patch, f'/comments/{comment1.id}', status=403, token=user2_token,
         json=comment1.edit(content='User2 content', apply=False))

    test_vote_entity(f'/comments/{comment1.id}', 'comment1', comment1)

    log('Test get comemnts in post1 has comment1 with correct votes')
    comments = test(get, f'/posts/{post1.id}/comments/', status=200)
    assert any(comment1.compare(c) for c in comments)

    user3 = User()

    log('Test create user3')
    test(post, f'/users/', status=201, compare=user3, json=user3.create)

    log('Test login user3')
    user3_token = test(post, '/auth/token', status=200, data=user3.login)
    assert 'access_token' in user3_token

    log('Test delete comment1_reply as user3 (neither resub owner nor comment author)')
    test(delete, f'/comments/{comment1_reply.id}', status=403, token=user3_token)

    log('Test delete comment1_reply as user2 (comment author and resub owner)')
    test(delete, f'/comments/{comment1_reply.id}', status=204, token=user2_token)

    log('Test delete comment2 as user1 (neither resub owner nor comment author)')
    test(delete, f'/comments/{comment2.id}', status=403, token=user1_token)

    log('Test delete comment2 as user2 (comment author)')
    test(delete, f'/comments/{comment2.id}', status=204, token=user2_token)

    log('Test get user2 comments no longer has comment2 and comment1_reply after deleting')
    comments = test(get, f'/users/{user2.username}/comments', status=200)
    assert not any(comment2.compare(c) for c in comments)
    assert not any(comment1_reply.compare(c) for c in comments)

    log('Test delete comment1_copy as user2 (resub owner)')
    test(delete, f'/comments/{comment1_copy.id}', status=204, token=user2_token)

    log('Test delete comment1 as user1 (comment author)')
    test(delete, f'/comments/{comment1.id}', status=204, token=user1_token)

    log('Test get user1 comments no longer has comment1 and comment1_copy after deleting')
    comments = test(get, f'/users/{user1.username}/comments', status=200)
    assert not any(comment1.compare(c) for c in comments)
    assert not any(comment1_copy.compare(c) for c in comments)

    log('Test get comments in post1 no longer has comment1, comment2, comment1_copy and comment1_reply')
    comments = test(get, f'/posts/{post1.id}/comments/', status=200)
    assert not any(comment1.compare(c) for c in comments)
    assert not any(comment2.compare(c) for c in comments)
    assert not any(comment1_copy.compare(c) for c in comments)
    assert not any(comment1_reply.compare(c) for c in comments)

    log('Test delete post2 as user1 (neither resub owner nor post author')
    test(delete, f'/posts/{post2.id}', status=403, token=user1_token)

    log('Test delete post2 as user2 (resub owner and post author)')
    test(delete, f'/posts/{post2.id}', status=204, token=user2_token)

    log('Test get post2 after deleting')
    test(get, f'/posts/{post2.id}', status=404)

    log('Test get user2 posts no longer has post2 after deleting')
    posts = test(get, f'/users/{user2.username}/posts', status=200)
    assert not any(post2.compare(p) for p in posts)

    log('Test delete post1 as user2 (resub owner)')
    test(delete, f'/posts/{post1.id}', status=204, token=user2_token)

    log('Test get post1 after deleting')
    test(get, f'/posts/{post1.id}', status=404)

    log('Test delete post1_copy as user1 (post author)')
    test(delete, f'/posts/{post1_copy.id}', status=204, token=user1_token)

    log('Test get post1_copy after deleting')
    test(get, f'/posts/{post1_copy.id}', status=404)

    log('Test get user1 posts no longer has post1 and post1_copy after deleting')
    posts = test(get, f'/users/{user1.username}/posts', status=200)
    assert not any(post1.compare(p) for p in posts)
    assert not any(post1_copy.compare(p) for p in posts)

    log('Test get posts in resub1 no longer has post1, post2 and post1_copy')
    posts = test(get, f'/resubs/{resub1.name}/posts', status=200)
    assert not any(post1.compare(p) for p in posts)
    assert not any(post2.compare(p) for p in posts)
    assert not any(post1_copy.compare(p) for p in posts)

    log('Test delete resub1 as user1 (previous resub owner)')
    test(delete, f'/resubs/{resub1.name}', status=403, token=user1_token)

    log('Test delete resub1 as user2 (resub owner)')
    test(delete, f'/resubs/{resub1.name}', status=204, token=user2_token)

    log('Test get resub1 after deleting')
    test(get, f'/resubs/{resub1.name}', status=404)

    log('Test get resubs no longer has resub1')
    resubs = test(get, f'/resubs/', status=200)
    assert not any(resub1.compare(r) for r in resubs)

    log('Test get user2 resubs no longer has resub1 after deleting')
    resubs = test(get, f'/users/{user2.username}/resubs', status=200)
    assert not any(resub1.compare(r) for r in resubs)

    def test_delete_user(user_model_name: str, user: User, user_token):
        log(f'Test delete {user_model_name}')
        test(delete, f'/users/me', status=204, token=user_token)

        log(f'Test get {user_model_name} after deleting')
        test(get, f'/users/{user.username}', status=404)

        log(f'Test get current user with {user_model_name} token is unauthorized (test invalid token)')
        test(get, f'/users/me', status=401, token=user_token)

        log(f'Test login as {user_model_name} no longer possible')
        test(post, f'/auth/token', status=400, data=user.login)

    test_delete_user('user3', user3, user3_token)
    test_delete_user('user2', user2, user2_token)
    test_delete_user('user1', user1, user1_token)

    stats.elapsed_seconds = (datetime.now() - started).total_seconds()
    return stats
