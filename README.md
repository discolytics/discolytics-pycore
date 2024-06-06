# 1. Installation

> pip install discolytics

# 2. Get API Key

Under the API Keys tab of your dashboard, create a new API key. Copy this key and your bot ID to connect within your codebase.

# 3. Example Usage

Initiate the client library in your codebase. Enter your bot ID and API key from the previous step to connect, as well as your bot token under the auth option.

> Your bot token is never sent to Discolytics servers. It is used by our client libraries on your machine to make requests to Discord on your behalf for metadata and analytics (such as to request your bot profile, guild count, etc).

```py
import discord
import os
from dotenv import load_dotenv
from discolytics import Discolytics
from time import sleep
import json

load_dotenv()

# initiate Discolytics client
discolytics = Discolytics({
    'api_key': os.getenv('DISCOLYTICS_KEY'),
    'auth': os.getenv('TOKEN'),
    'bot_id': 'YOUR_BOT_ID',
})

client = discord.Client(intents=discord.Intents.all(), enable_debug_events=True)

@client.event
async def on_ready():
    print(f'Client ready as {client.user}')

    # discolytics.start_command returns a function. Run this function once the command ends.
    end_command = discolytics.start_command(name='help', user_id='123')
    sleep(5)
    # run end_command once the command ends
    end_command()

# send events to Discolytics
@client.event
async def on_socket_raw_receive(raw_msg):
    if not isinstance(raw_msg, str):
            return
    msg = json.loads(raw_msg)
    event_type = msg.get("t")
    data = msg.get("d")
    if not data or not event_type:
        return

    guild_id = data.pop('guild_id', None)
    discolytics.send_event(name=event_type, guild_id=guild_id)

    # send interactions to discolytics
    if event_type == 'INTERACTION_CREATE':
        type = data.pop('type', None)
        if not type:
            return
        discolytics.post_interaction(type=type, guild_id=guild_id)

client.run(os.getenv('TOKEN'))
```

# Support

Join our Discord server for help and support.

- https://discord.gg/aDPeJDcumz