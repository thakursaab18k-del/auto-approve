import os
import asyncio
from fastapi import FastAPI
import uvicorn
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsMentions
from telethon.errors import FloodWaitError

app = FastAPI()

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_PEER = os.environ.get("CHANNEL_PEER", "")

# Initialize the bot client globally
bot = TelegramClient('bot_session', API_ID, API_HASH)

async def approve_past_requests(event=None):
    msg = "🚀 Starting the approval loop..."
    print(msg)
    if event: await event.respond(msg)
    
    try:
        if CHANNEL_PEER.startswith("-100") or CHANNEL_PEER.isdigit():
            target_peer = int(CHANNEL_PEER)
        else:
            target_peer = CHANNEL_PEER
            
        channel = await bot.get_entity(target_peer)
    except Exception as e:
        error_msg = f"❌ Error finding channel: {e}"
        print(error_msg)
        if event: await event.respond(error_msg)
        return

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
                status = "✅ No more pending requests found."
                print(status)
                if event: await event.respond(status)
                break
                
            status_update = f"📥 Found {len(participants.users)} requests. Starting approvals..."
            print(status_update)
            if event: await event.respond(status_update)

            for user in participants.users:
                try:
                    await bot.hide_chat_join_request(channel, user.id, approve=True)
                    print(f"Approved: {user.first_name} ({user.id})")
                    approved_count += 1
                    await asyncio.sleep(1.5) # Safe delay
                    
                except FloodWaitError as e:
                    print(f"Rate limited. Waiting {e.seconds} seconds...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"Failed to approve user {user.id}: {e}")
            
            if len(participants.users) < limit:
                break
                
        except Exception as e:
            error_loop = f"❌ Error scanning list: {e}"
            print(error_loop)
            if event: await event.respond(error_loop)
            break

    final_msg = f"🎉 Finished job! Total approved: {approved_count}"
    print(final_msg)
    if event: await event.respond(final_msg)

# Command Handler: Trigger via Telegram message
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.respond("Hello! I received your command.")
    asyncio.create_task(approve_past_requests(event))

@app.get("/")
def home():
    return {"status": "Bot server is running"}

# Start telethon safely alongside FastAPI
@app.on_event("startup")
async def startup_event():
    print("Starting Telethon Client...")
    await bot.start(bot_token=BOT_TOKEN)
    # Also trigger once on boot automatically
    asyncio.create_task(approve_past_requests())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
