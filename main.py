async def approve_past_requests():
    print("Initializing Telegram Bot...")
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # --- FIXED CHANNEL PEER HANDLING ---
    try:
        # Check if the CHANNEL_PEER looks like a numeric ID
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
