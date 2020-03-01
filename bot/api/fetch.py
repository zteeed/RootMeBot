from typing import Dict, List, Tuple, Optional
import re

from bot.constants import LANGS
from bot.api.parser import Parser, response_profile_complete
from bot.colors import red


async def search_rootme_user_all_langs(username: str) -> List[Dict[str, str]]:
    all_users = []
    for lang in LANGS:
        content = await Parser.extract_rootme_profile(username, lang)
        if content is None:
            continue
        content = content[0]
        all_users += list(content.values())
    return all_users


async def search_rootme_user(username: str) -> Optional[List]:
    result_id_user = re.findall(r'-(\d+)$', username)
    if result_id_user:
        id_user = int(result_id_user[0])
        content = await Parser.extract_rootme_profile_complete(id_user)
        real_username = '-'.join(username.split('-')[:-1])
        if content is not None and content['nom'] != real_username:  # content might be None if score = 0
            return None
        all_users = await search_rootme_user_all_langs(real_username)
        if not all_users:
            return None
        if id_user not in [int(user['id_auteur']) for user in all_users]:
            return None
        #  username = real_username
        all_users = [user for user in all_users if user['id_auteur'] == str(id_user)]
    else:
        all_users = await search_rootme_user_all_langs(username)
        if not all_users:
            return None
    all_users_complete = []
    for user in all_users:
        user_data = await Parser.extract_rootme_profile_complete(user['id_auteur'])
        if user_data is not None:
            all_users_complete.append(dict(
                id_user=int(user['id_auteur']),
                username=user_data['nom'],
                score=int(user_data['score']),
                number_challenge_solved=len(user_data['validations'])
            ))
        else:  # user exists but score is equal to zero
            all_users_complete.append(dict(
                id_user=int(user['id_auteur']),
                username=user['nom'],
                score=0,
                number_challenge_solved=0
            ))
    all_users_complete = sorted(all_users_complete, key=lambda x: int(x['score']), reverse=True)
    return all_users_complete


async def get_scores(users: List[str], lang: str):
    scores = [await Parser.extract_score(user, lang) for user in users]
    scores = [int(score) for score in scores]
    """ Sort users by score desc """
    return [{'name': x, 'score': int(y)} for y, x in sorted(zip(scores, users), reverse=True)]


async def get_details(username: str, lang: str):
    return await Parser.extract_rootme_details(username, lang)


def get_stats_category(categories_stats: List[Dict], category: str) -> Optional[Dict[str, int]]:
    for category_stats in categories_stats:
        category_name = category_stats['name'].replace(' ', '')
        if category_name == category:
            return category_stats['stats_categories']


async def get_remain(username: str, lang: str, category: Optional[str] = None) -> Tuple[int, int]:
    details = await get_details(username, lang)
    details = details[0]
    if category is None:
        return details['nb_challenges_solved'], details['nb_challenges_tot']
    else:
        category_stats = get_stats_category(details['categories'], category)
        return category_stats['num_challenges_solved'], category_stats['total_challenges_category']


async def get_challenges(lang: str):
    return await Parser.extract_challenges(lang)


async def get_solved_challenges(id_user: int) -> Optional[response_profile_complete]:
    solved_challenges_data = await Parser.extract_rootme_profile_complete(id_user)
    if solved_challenges_data is None:
        red(f'Error trying to fetch solved challenges.')
        return None
    return solved_challenges_data['validations']


def get_diff(solved_user1, solved_user2):
    if solved_user1 == solved_user2:
        return None, None
    test1 = list(map(lambda x: x['id_challenge'], solved_user1))
    test2 = list(map(lambda x: x['id_challenge'], solved_user2))
    user1_diff = list(filter(lambda x: x['id_challenge'] not in test2, solved_user1))[::-1]
    user2_diff = list(filter(lambda x: x['id_challenge'] not in test1, solved_user2))[::-1]
    return user1_diff, user2_diff
