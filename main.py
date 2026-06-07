import os
import asyncio
from fastapi import FastAPI
import uvicorn
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError

app = FastAPI()

# --- CONFIGURATION (Pulled securely from Render Environment) ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "") # This holds your phone number now
CHANNEL_PEER = os.environ.get("CHANNEL_PEER", "")

# We initialize the client
bot = TelegramClient('bot_session', API_ID, API_HASH)

async def approve_past_requests():
    print("Connecting to Telegram using your personal account session...")
    try:
        # If BOT_TOKEN is your phone number, it logs you in as a user account
        if BOT_TOKEN.startswith('+') or BOT_TOKEN.isdigit():
            await bot.start(phone=BOT_TOKEN)
        else:
            await bot.start(bot_token=BOT_TOKEN)
            
        print("🎉 Login successful! Your personal account is connected.")
    except Exception as login_err:
        print(f"❌ Login failed. Make sure you entered the correct code in the logs: {login_err}")
        return
    
    try:
        if CHANNEL_PEER.startswith("-100") or CHANNEL_PEER.isdigit():
            target_peer = int(CHANNEL_PEER)
        else:
            target_peer = CHANNEL_PEER
        channel = await bot.get_entity(target_peer)
    except Exception as e:
        print(f"❌ Error finding channel: {e}")
        return

    print("🔄 Scanning ALL past pending join requests...")
    approved_count = 0
    limit = 100
    
    while True:
        try:
            participants = await bot(functions.channels.GetParticipantsRequest(
                channel=channel,
                filter=types.ChannelParticipantsMentions(),
                offset=0,
                limit=limit,
                hash=0
            ))
            
            if not participants.users:
                print("✅ All past pending requests have been cleared!")
                break
                
            print(f"📥 Found {len(participants.users)} requests. Starting approvals...")

            for user in participants.users:
                try:
                    # Using raw user-session safe API method
                    await bot(functions.channels.HideChatJoinRequestRequest(
                        peer=channel,
                        user_id=user.id,
                        approved=True
                    ))
                    print(f"Approved: {user.first_name} ({user.id})")
                    approved_count += 1
                    await asyncio.sleep(1.5) # Safe delay to avoid account bans
                    
                except FloodWaitError as e:
                    print(f"Rate limited by Telegram. Waiting {e.seconds} seconds...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"Failed to approve user {user.id}: {e}")
            
            if len(participants.users) < limit:
                break
                
        except Exception as e:
            print(f"❌ Error scanning list: {e}")
            break

    print(f"🎉 Task Complete! Total approved from past: {approved_count}")
    await bot.disconnect()

@app.get("/")
def home():
    return {"status": "User account service is active"}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(approve_past_requests())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
