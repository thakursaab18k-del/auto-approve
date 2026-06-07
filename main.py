import os
import asyncio
from fastapi import FastAPI
import uvicorn
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsMentions
from telethon.errors import FloodWaitError

# CRITICAL: Render looks for this exact line. It cannot be missing!
app = FastAPI()

# --- CONFIGURATION (Pulled securely from Render Environment) ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_PEER = os.environ.get("CHANNEL_PEER", "")

async def approve_past_requests():
    print("Initializing Telegram Bot...")
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    try:
        if CHANNEL_PEER.startswith("-100") or CHANNEL_PEER.isdigit():
            target_peer = int(CHANNEL_PEER)
        else:
            target_peer = CHANNEL_PEER
            
        channel = await bot.get_entity(target_peer)
    except Exception as e:
        print(f"Error finding channel: {e}")
        await bot.disconnect()
        return

    print("Fetching pending join requests from the past...")
    approved_count = 0
    limit = 100
    
    while True:
        try:
            participants = await bot(GetParticipantsRequest(
                channel=channel,
                filter=ChannelParticipantsMentions(),
                offset=0,
                limit=limit,
                hash=0
            ))
            
            if not participants.users:
                print("No more pending requests found.")
                break
                
            for user in participants.users:
                try:
                    await bot.hide_chat_join_request(channel, user.id, approve=True)
                    print(f"Approved: {user.first_name} ({user.id})")
                    approved_count += 1
                    await asyncio.sleep(1.0) 
                    
                except FloodWaitError as e:
                    print(f"Rate limited. Waiting {e.seconds} seconds...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"Failed to approve user {user.id}: {e}")
            
            if len(participants.users) < limit:
                break
                
        except Exception as e:
            print(f"Error scanning list: {e}")
            break

    print(f"Finished job. Total approved: {approved_count}")
    await bot.disconnect()

# CRITICAL: Render hits this web endpoint to verify the service is alive
@app.get("/")
def home():
    return {"status": "Bot server is running"}

# CRITICAL: This starts your approval loop automatically when Render boots the file
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(approve_past_requests())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
