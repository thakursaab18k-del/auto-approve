import os
import asyncio
from fastapi import FastAPI
import uvicorn
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, HideChatJoinRequestRequest
from telethon.tl.types import ChannelParticipantsMentions
from telethon.errors import FloodWaitError

app = FastAPI()

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_PEER = os.environ.get("CHANNEL_PEER", "")

bot = TelegramClient('bot_session', API_ID, API_HASH)

async def approve_past_requests():
    print("Initializing Telegram Bot...")
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
                
            print(f"📥 Found {len(participants.users)} requests. Starting approvals...")

            for user in participants.users:
                try:
                    # FIXED: Using raw API method to avoid version compatibility issues
                    await bot(HideChatJoinRequestRequest(
                        peer=channel,
                        user_id=user.id,
                        approved=True
                    ))
                    print(f"Approved: {user.first_name} ({user.id})")
                    approved_count += 1
                    await asyncio.sleep(1.5) # Safe delay to prevent rate limits
                    
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

@app.get("/")
def home():
    return {"status": "Bot server is running"}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(approve_past_requests())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
