from typing import TypedDict, Optional
import requests
import time
import json
import threading
import psutil
import os
from . import __version__

DISCORD_API_URL = 'https://discord.com/api/v10'

def parse_token(token: str):
    if token.startswith('Bot'):
        return token
    else:
        return f'Bot {token}'
    
def set_interval(func, sec):
    def wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, wrapper)
    t.start()
    return t

class LogLevels(TypedDict):
    debug: bool
    error: bool
    info: bool

class Options(TypedDict):
    bot_id: str
    api_key: str
    client_type: Optional[int]
    client_version: Optional[str]
    data_api_url: Optional[str]
    api_url: Optional[str]
    auth: str
    primary: Optional[bool]
    log_levels: Optional[LogLevels]

class Command(TypedDict):
    end: any

class Discolytics:
    def __init__(self, options: Options):
        self.bot_id = options.get('bot_id')
        self.api_key = options.get('api_key')
        
        if options.get('client_type') is None:
            self.client_type = 4
        else:
            self.client_type = options.get('client_type')
        
        if options.get('client_version') is None:
            self.client_version = __version__
        else:
            self.client_version = options.get('client_version')
        
        if options.get('data_api_url') is None:
            self.data_api_url = 'https://data.discolytics.com/api'
        else:
            self.data_api_url = options.get('data_api_url')

        if options.get('api_url') is None:
            self.api_url = 'https://api.discolytics.com/api'
        else:
            self.api_url = options.get('api_url')

        self.auth = parse_token(options.get('auth'))

        if options.get('primary') is None:
            self.primary = True
        else:
            self.primary = options.get('primary')

        if options.get('log_levels') is None:
            self.log_levels = LogLevels(debug=False, error=True, info=True)
        else:
            self.log_levels = options.get('log_levels')

        self.pending_events = []
        self.pending_interactions = []
        self.pending_commands = []

        def post_data():
            self.post_events()
            self.post_interactions()
            self.post_commands()

        set_interval(post_data, 15)

        if self.primary:
            self.patch_bot({})
            self.get_bot()

            def post_system_usage():
                [cpu, mem] = self.get_system_usage()
                self.post_cpu_usage(cpu)
                self.post_mem_usage(mem)
            set_interval(post_system_usage, 10)

            self.send_heartbeat()
            set_interval(self.send_heartbeat, 30)

            self.post_guild_count()
            set_interval(self.post_guild_count, 60 * 30)

        self.log(level='info', msg='Client ready')
    
    def get_system_usage(self):
        pid = os.getpid()
        process = psutil.Process(pid)
        cpu_usage = process.cpu_percent(interval=1)
    
        memory_info = process.memory_info()
        memory_usage = memory_info.rss
        
        return [cpu_usage, memory_usage]

    def log(self, level, msg):
        if self.log_levels.get(level) == False:
            return

        print(f'Discolytics | {level} | {msg}')

    def get_bot(self):
        res = requests.get(f'{self.api_url}/bots/{self.bot_id}', headers={'Authorization': self.api_key})
        if res.status_code != 200:
            self.log(level='error', msg='Failed to get bot')
            return None
        
        data = res.json()

        # update profile every 24h
        update_profile = data['profileLastUpdated'] is None or (time.time() * 1000) - data['profileLastUpdated'] > 1000 * 60 * 60 * 24

        if update_profile == False:
            self.log(level='debug', msg='Not time to update profile')
            return data
        
        user = self.get_bot_user()
        if user is not None:
            success = self.patch_bot({'botUserId': user['id'], 'botUserName': user['username'], 'botUserAvatar': self.get_avatar_url(user)})
            if success:
                self.log(level='info', msg='Updated bot profile')
            else:
                self.log(level='error', msg='Failed to update bot profile')
        
    def patch_bot(self, data):
        body = {**data, 'clientType': self.client_type, 'clientVersion': self.client_version}
        res = requests.patch(f'{self.api_url}/bots/{self.bot_id}', headers={'Authorization': self.api_key, 'Content-Type': 'application/json'}, json=body)
        if res.status_code != 200:
            self.log(level='error', msg='Failed to patch bot')
        return res.status_code == 200
    
    def convert_pending_events(self):
        def fn(event):
            return {
                'name': event['name'],
                'guildId': event['guild_id']
            }

        return list(map(fn, self.pending_events))

    def post_events(self):
        res = requests.post(f'{self.data_api_url}/bots/{self.bot_id}/events', headers={'Authorization': self.api_key, 'Content-Type': 'application/json'}, json={'events': self.convert_pending_events()})

        count = len(self.pending_events)
        self.pending_events = []

        if res.status_code != 201:
            self.log(level='error', msg=f'Failed to post {count} events')
            return False
        else:
            self.log(level='debug', msg=f'Posted {count} events')
            return True
        
    def send_event(self, name: str, guild_id: Optional[str]):
        self.pending_events.append({'name': name, 'guild_id': guild_id})
        self.log(level='debug', msg=f'Added event to queue : {name} (Guild ID: {guild_id})')

    def convert_pending_interactions(self):
        def fn(interaction):
            return {
                'type': interaction['type'],
                'guildId': interaction['guild_id']
            }

        return list(map(fn, self.pending_interactions))

    def post_interactions(self):
        res = requests.post(f'{self.data_api_url}/bots/{self.bot_id}/interactions', headers={'Authorization': self.api_key, 'Content-Type': 'application/json'}, json={'interactions': self.convert_pending_interactions()})

        count = len(self.pending_interactions)
        self.pending_interactions = []

        if res.status_code != 201:
            self.log(level='error', msg=f'Failed to post {count} interactions')
            return False
        else:
            self.log(level='debug', msg=f'Posted {count} interactions')
            return True
        
    def post_interaction(self, type: int, guild_id: Optional[str]):
        self.pending_interactions.append({'type': type, 'guild_id': guild_id})
        self.log(level='debug', msg=f'Added interaction to queue : {type} (Guild ID: {guild_id})')

    def post_cpu_usage(self, value: int):
        res = requests.post(f'{self.data_api_url}/bots/{self.bot_id}/cpuUsage', headers={'Authorization': self.api_key, 'Content-Type': 'application/json'}, json={"value": value, 'clientType': self.client_type})

        if res.status_code != 201:
            self.log(level='error', msg=f'Failed to post CPU usage : {value}')
            return False
        
        return True
    
    def post_mem_usage(self, value: int):
        res = requests.post(f'{self.data_api_url}/bots/{self.bot_id}/memUsage', headers={'Authorization': self.api_key, 'Content-Type': 'application/json'}, json={"value": value, 'clientType': self.client_type})

        if res.status_code != 201:
            self.log(level='error', msg=f'Failed to post memory usage : {value}')
            return False
        
        return True
    
    def start_command(self, name: str, user_id: str) -> Command:
        start = time.time() * 1000
        def end(metadata=None):
            json_string = None
            if metadata is not None:
                json_string = json.dumps(metadata)
            
            end = time.time() * 1000
            duration = int(end - start)
            
            self.post_command(name=name, user_id=user_id, duration=duration, metadata=json_string)
        
        return end
    
    def convert_pending_commands(self):
        def fn(command):
            return {
                'name': command['name'],
                'userId': command['user_id'],
                'duration': command['duration'],
                'metadata': command['metadata']
            }

        return list(map(fn, self.pending_commands))

    def post_commands(self):
        res = requests.post(f'{self.data_api_url}/bots/{self.bot_id}/commands', headers={'Authorization': self.api_key, 'Content-Type': 'application/json'}, json={'commands': self.convert_pending_commands()})

        count = len(self.pending_commands)
        self.pending_commands = []

        if res.status_code != 201:
            self.log(level='error', msg=f'Failed to post {count} commands')
            return False
        else:
            self.log(level='debug', msg=f'Posted {count} commands')
            return True

    def post_command(self, name: str, user_id: str, duration: int, metadata: Optional[str]):
        self.pending_commands.append({'name': name, 'user_id': user_id, 'duration': duration, 'metadata': metadata})
        self.log(level='debug', msg=f'Added command to queue : {name} (User ID: {user_id})')

    def get_bot_user(self):
        res = requests.get(f'{DISCORD_API_URL}/users/@me', headers={'Authorization': self.auth})
        if res.status_code != 200:
            self.log(level='error', msg='Failed to get bot user')
            return None
        
        data = res.json()
        return data
        
    def get_avatar_url(self, user):
        if user['avatar'] is None:
            return 'https://cdn.discordapp.com/embed/avatars/0.png'
        else:
            return f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
    
    def send_heartbeat(self):
        res = requests.post(f'{self.data_api_url}/bots/{self.bot_id}/heartbeat', headers={'Authorization': self.api_key})

        if res.status_code != 201:
            self.log(level='error', msg='Failed to send heartbeat')
            return False
        else:
            return True
        
    def get_application(self):
        res = requests.get(f'{DISCORD_API_URL}/applications/@me', headers={'Authorization': self.auth})

        if res.status_code != 200:
            self.log(level='error', msg='Failed to get Discord application')
            return None

        data = res.json()
        return data
    
    def get_guild_count(self):
        application = self.get_application()
        if application is None:
            return None
        else:
            return application['approximate_guild_count']
        
    def post_guild_count(self):
        count = self.get_guild_count()
        if count is None:
            return False
        
        res = requests.post(f'{self.data_api_url}/bots/{self.bot_id}/guildCount', headers={'Authorization': self.api_key, 'Content-Type': 'application/json'}, json={'count': count})

        if res.status_code != 201:
            self.log(level='error', msg=f'Failed to post guild count : {count}')
            return False
        
        return True
