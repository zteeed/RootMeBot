from datetime import datetime, timedelta
import time
from datetime import datetime, timedelta
from html import unescape
from typing import Dict, List, Optional, Tuple, Union

from discord.channel import TextChannel
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context

import bot.manage.channel_data as channel_data
from bot.api.fetch import search_rootme_user, get_solved_challenges, get_diff, get_all_challenges
from bot.api.parser import Parser
from bot.colors import green
from bot.constants import LANGS, emoji2, emoji3, emoji5, limit_size, medals
from bot.database.manager import DatabaseManager
from bot.display.update import add_emoji
from bot.wraps import stop_if_args_none

challenges_type = Optional[Dict[str, Union[str, int, List[str]]]]
all_challenges = {}  #  all challenges by discord_server


def display_parts(message: str) -> List[str]:
    message = message.split('\n')
    tosend = ''
    stored = []
    for part in message:
        if len(tosend + part + '\n') >= limit_size:
            stored.append(tosend)
            tosend = ''
        tosend += part + '\n'
    stored.append(tosend)
    return stored


async def display_add_user(db: DatabaseManager, id_discord_server: int, bot: Bot, name: str) -> str:
    """ Check if user exist in RootMe """
    all_users = await search_rootme_user(name)
    if not all_users:
        return add_emoji(bot, f'RootMe profile for {name} can\'t be established', emoji3)

    if len(all_users) > 1:
        tosend = f'Several users exists with the following username: "{name}"\nYou might want to choose between these:\n'
        all_users = all_users[:10]  # select top 10
        """
        all_users_usernames = [user['username'] for user in all_users]
        if len(list(set(all_users_usernames))) == 1:  # same username with different id_user
            for user in all_users:
                tosend += f'• {user["username"]}-{user["id_user"]} (Score: {user["score"]})\n'
        else:
            for user in all_users:
                tosend += f'• {user["username"]} (Score: {user["score"]})\n'
        """
        for user in all_users:
            tosend += f'• {user["username"]}-{user["id_user"]} (Score: {user["score"]})\n'
        return add_emoji(bot, tosend, emoji3)

    """ Add user to database """
    user = all_users[0]
    if await db.user_exists(id_discord_server, user['username']):
        return add_emoji(bot, f'User "{name}" already exists in team', emoji5)
    else:
        await db.create_user(
            id_discord_server, user['id_user'], user['username'], user['score'], user['number_challenge_solved']
        )
        return add_emoji(bot, f'User {user["username"]} successfully added in team', emoji2)


async def display_remove_user(db: DatabaseManager, id_discord_server: int, bot: Bot, name: str) -> str:
    """ Remove user from data.json """
    if not await db.user_exists(id_discord_server, name):
        return add_emoji(bot, f'User {name} is not in team', emoji5)
    else:
        await db.delete_user(id_discord_server, name)
        return add_emoji(bot, f'User {name} successfully removed from team', emoji2)


async def display_scoreboard(db: DatabaseManager, id_discord_server: int) -> str:
    tosend = ''
    users = await db.select_users(id_discord_server)
    users = sorted(users, key=lambda x: x['score'], reverse=True)
    for rank, user in enumerate(users):
        username, score = user['rootme_username'], user['score']
        if rank < len(medals):
            tosend += f'{medals[rank]} {username} --> Score = {score} \n'
        else:
            tosend += f' • • • {username} --> Score = {score} \n'
    return tosend


def user_has_solved(challenge_selected: str, solved_challenges: List[Dict[str, Union[str, int]]]) -> bool:
    test = [challenge['titre'] == challenge_selected for challenge in solved_challenges]
    return True in test


async def display_who_solved(db: DatabaseManager, id_discord_server: int, challenge_title_query: str) \
        -> Tuple[Optional[str], Optional[str]]:

    challenge_found = await Parser.find_challenge(challenge_title_query)
    if not challenge_found:
        return f'Challenge "{challenge_title_query}" cannot be found in challenge list.', challenge_title_query

    challenges = list(challenge_found[0].values())
    if len(challenges) > 1:
        tosend = f'Several challenges exists with the following challenge title query: "{challenge_title_query}"\n' \
            f'You might want to choose between these:\n'
        for challenge in challenges:
            tosend += f'• {challenge["titre"]}\n'
        return tosend, challenge_title_query

    tosend = ''
    rootme_challenge_selected = challenges[0]
    users = await db.select_users(id_discord_server)
    users = sorted(users, key=lambda x: x['score'], reverse=True)
    for user in users:
        user_info = await Parser.extract_rootme_profile_complete(user['rootme_user_id'])
        if user_info is None:  #  User {user["rootme_username"]} score is equal to zero
            continue
        challenge_solved = user_info['validations']
        challenge_solved_ids = [challenge['id_challenge'] for challenge in challenge_solved]
        if rootme_challenge_selected['id_challenge'] not in challenge_solved_ids:
            continue  # user did not solve selected_challenge
        tosend += f' • {user["rootme_username"]}\n'
    if not tosend:
        tosend = f'Nobody solved "{rootme_challenge_selected["titre"]}".'
    return tosend, rootme_challenge_selected["titre"]


async def display_duration(db: DatabaseManager, context: Context, args: Tuple[str], delay: timedelta) \
        -> List[Dict[str, Optional[str]]]:
    database_users = await db.select_users(context.guild.id)
    if len(args) == 1:
        if not await db.user_exists(context.guild.id, args[0]):
            tosend = f'User {args[0]} is not in team.'
            tosend_list = [{'user': args[0], 'msg': tosend}]
            return tosend_list
        else:
            username = args[0]
            users = [db.find_user(database_users, context.guild.id, username)]
    else:
        users = await db.select_users(context.guild.id)

    now = datetime.now()
    tosend_list = []
    for user in users:
        user_info = await Parser.extract_rootme_profile_complete(user["rootme_user_id"])
        if user_info is None:  #  User {user["rootme_username"]} score is equal to zero
            continue
        challenges_solved = user_info['validations']
        challenges_solved = sorted(challenges_solved, key=lambda x: x['date'], reverse=True)

        tosend = ''
        for challenge in challenges_solved:
            date = datetime.strptime(challenge['date'], "%Y-%m-%d %H:%M:%S")
            diff = now - date
            if diff >= delay:
                continue
            challenge_info = await Parser.extract_challenge_info(challenge['id_challenge'])
            tosend += f' • {unescape(challenge_info["titre"])} ({challenge_info["score"]} points) - {challenge["date"]}\n'
        tosend_list.append({'user': user, 'msg': tosend})

    test = [item['msg'] == '' for item in tosend_list]
    if len(users) == 1 and False not in test:
        tosend = f'No challenges solved by {users[0]["rootme_username"]} :frowning:'
        tosend_list = [{'user': None, 'msg': tosend}]
    elif False not in test:
        tosend = 'No challenges solved by anyone :frowning:'
        tosend_list = [{'user': None, 'msg': tosend}]

    return tosend_list


async def display_week(db: DatabaseManager, context: Context, args: Tuple[str]) \
        -> List[Dict[str, Optional[str]]]:
    return await display_duration(db, context, args, timedelta(weeks=1))


async def display_today(db: DatabaseManager, context: Context, args: Tuple[str]) -> List[Dict[str, Optional[str]]]:
    return await display_duration(db, context, args, timedelta(days=1))


@stop_if_args_none
async def display_diff_one_side(user_diff: List[Dict[str, str]]) -> str:
    tosend = ''
    for challenge in user_diff:
        challenge_info = await Parser.extract_challenge_info(challenge['id_challenge'])
        tosend += f' • {unescape(challenge_info["titre"])} ({challenge_info["score"]} points)\n'
    return tosend


async def display_diff(db: DatabaseManager, id_discord_server: int, username1: str, username2: str) \
        -> List[Dict[str, Optional[str]]]:
    if not await db.user_exists(id_discord_server, username1):
        tosend = f'User {username1} is not in team.'
        tosend_list = [{'user': username1, 'msg': tosend}]
        return tosend_list
    if not await db.user_exists(id_discord_server, username2):
        tosend = f'User {username2} is not in team.'
        tosend_list = [{'user': username2, 'msg': tosend}]
        return tosend_list

    database_users = await db.select_users(id_discord_server)
    user1 = db.find_user(database_users, id_discord_server, username1)
    user2 = db.find_user(database_users, id_discord_server, username2)
    solved_user1 = await get_solved_challenges(user1['rootme_user_id'])
    solved_user1 = sorted(solved_user1, key=lambda x: x['date'])  # sort challenge solved by date
    solved_user2 = await get_solved_challenges(user2['rootme_user_id'])
    solved_user2 = sorted(solved_user2, key=lambda x: x['date'])  # sort challenge solved by date

    user1_diff, user2_diff = get_diff(solved_user1, solved_user2)
    tosend_list = []

    tosend = await display_diff_one_side(user1_diff)
    tosend_list.append({'user': username1, 'msg': tosend})
    tosend = await display_diff_one_side(user2_diff)
    tosend_list.append({'user': username2, 'msg': tosend})
    return tosend_list


async def display_diff_with(db: DatabaseManager, id_discord_server: int, bot: Bot, selected_username: str):
    if not await db.user_exists(id_discord_server, selected_username):
        tosend = f'User {selected_username} is not in team.'
        tosend_list = [{'user': selected_username, 'msg': tosend}]
        return tosend_list

    tosend_list = []
    users = await db.select_users(id_discord_server)
    selected_user = db.find_user(users, id_discord_server, selected_username)
    solved_user_select = await get_solved_challenges(selected_user['rootme_user_id'])

    for user in users:
        solved_user = await get_solved_challenges(user['rootme_user_id'])
        user_diff, user_diff_select = get_diff(solved_user, solved_user_select)
        if user_diff:
            tosend = await display_diff_one_side(user_diff)
            tosend_list.append({'user': user["rootme_username"], 'msg': tosend})
    return tosend_list


async def display_flush(channel: TextChannel, context: Context) -> str:
    result = await channel_data.flush(channel)
    if channel is None or not result:
        return 'An error occurs while trying to flush channel data.'
    return f'Data from channel has been flushed successfully by {context.author}.'


async def display_reset_database(db: DatabaseManager, id_discord_server: int, bot: Bot) -> str:
    """ Reset discord database """
    users = await db.select_users(id_discord_server)
    usernames = [user['rootme_username'] for user in users]
    for name in usernames:
        await db.delete_user(id_discord_server, name)
    return add_emoji(bot, f'Database has been successfully reset', emoji2)


async def display_cron(id_discord_server: int, db: DatabaseManager) -> List[Tuple[Optional[str], Optional[str]]]:
    # check updates about challenges data
    global all_challenges
    
    new_list_all_challenges = await get_all_challenges()
    if id_discord_server not in list(all_challenges.keys()):
        all_challenges[id_discord_server] = new_list_all_challenges

    list_all_challenges = all_challenges[id_discord_server]

    if len(new_list_all_challenges) > len(list_all_challenges):
        challenges = [chall for chall in new_list_all_challenges if chall not in list_all_challenges]
        message_title = f'NEW CHALLENGE !!!'
        tosend = f''
        for challenge in challenges:
            print(challenge)
            tosend += f' • {unescape(challenge["titre"])}'
            """
            challenge_info = await Parser.extract_challenge_info(challenge['id_challenge'])
            tosend += f' • {challenge_info["titre"]} ({challenge_info["score"]} points)'
            tosend += f'\n --> Category: {challenge_info["rubrique"]}'
            #  tosend += f'\n • URL: {challenge_info["url_challenge"]}'
            tosend += f'\n --> Difficulty: {challenge_info["difficulte"]}\n'
            """
        # update challenges list
        all_challenges[id_discord_server] = new_list_all_challenges
        return [(message_title, tosend)]
    
    messages = []
    # check updates about user data
    users = await db.select_users(id_discord_server)
    for user in users:
        time.sleep(1)
        print(user)
        number_challenge_solved, score = user['number_challenge_solved'], user['score']
        user_data = await Parser.extract_rootme_profile_complete(user['rootme_user_id'])
        if user_data is None:  #  User {user["rootme_username"]} score is equal to zero
            continue
        if len(user_data['validations']) == number_challenge_solved:
            continue

        if number_challenge_solved > 0:
            new_challenges_solved = user_data['validations'][:-number_challenge_solved][::-1]  # last solved + reverse order
        else:
            new_challenges_solved = user_data['validations'][::-1]  # all solves because there was no solve before + reverse
        
        for new_challenge in new_challenges_solved:
            challenge_info = await Parser.extract_challenge_info(new_challenge['id_challenge'])
            if challenge_info is None:
                continue
            score += int(challenge_info["score"])
            green(f'{user["rootme_username"]} --> {unescape(challenge_info["titre"])}')
            message_title = f'New challenge solved by {user["rootme_username"]}'
            tosend = f' • {unescape(challenge_info["titre"])} ({challenge_info["score"]} points)'
            tosend += f'\n • Category: {challenge_info["rubrique"]}'
            #  tosend += f'\n • URL: {challenge_info["url_challenge"]}'
            tosend += f'\n • Difficulty: {challenge_info["difficulte"]}'
            tosend += f'\n • Date: {new_challenge["date"]}'
            tosend += f'\n • New score: {score}'
            messages.append((message_title, tosend))
        
        score = int(user_data["score"])
        number_challenge_solved = len(user_data["validations"])
        await db.update_user_info(id_discord_server, user['rootme_username'], score, number_challenge_solved)

    return messages


async def display_api_query(path: str) -> Optional[str]:
    return await Parser.make_custom_query(path)
