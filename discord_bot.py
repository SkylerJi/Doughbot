import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions
from ai_discord_functions import image_is_safe, message_is_safe
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio
import json
import datetime

load_dotenv()

# Create a lock for each file
servers_lock = asyncio.Lock()
warnings_lock = asyncio.Lock()
sensitivity_lock = asyncio.Lock()

# Save servers settings to file
async def save_servers():
    async with servers_lock:
        try:
            with open("servers.json", "w") as file:
                json.dump(servers, file)
        except IOError as e:
            print(f"Error saving servers: {e}")

# Save warnings to file
async def save_warnings():
    async with warnings_lock:
        try:
            with open("warnings.json", "w") as file:
                json.dump(warning_list, file)
        except IOError as e:
            print(f"Error saving warnings: {e}")


# Load servers settings from file
try:
    with open("servers.json", "r") as file:
        servers = json.load(file)
except FileNotFoundError:
    servers = {}

try:
    with open("warnings.json", "r") as file:
        warning_list = json.load(file)
except FileNotFoundError:
    warning_list = {}

async def save_sensitivity():
    async with sensitivity_lock:
        try:
            with open("sensitivity.json", "w") as file:
                json.dump(sensitivity, file)
        except IOError as e:
            print(f"Error saving sensitivity: {e}")

# Load sensitivity settings from file
try:
    with open("sensitivity.json", "r") as file:
        sensitivity = json.load(file)
except FileNotFoundError:
    sensitivity = {}


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.tree.command(name="help", description="Shows commands and information for the Dough AI bot.")
async def aihelp(interaction: discord.Interaction):
    await interaction.response.send_message(
        """
**Help:**
```
help: Shows this information.
set_warnings <warnings>: Sets the number of warnings a user can have before muting them.
set_mute_time <time>: Sets the amount of time a user is muted for after having too many warnings. Example: 1d, 3m, 5s, 6h
use_warnings <boolean>: Whether to use warnings and mute the user, or just only delete the message.
set_sensitivity <float from 0-1>: The image moderation sensitivity. As sensitivity increases, image moderation becomes more strict, and as sensitivity decreases, image moderation becomes less strict.
set_logs_channel <channel id>: The logs channel id that Dough will log logs to. Note that Dough must have permission to view and send messages to this channel.

Scanning & Moderation Commands:
scan_channel [channel] [limit]: Scan previous messages in a channel for inappropriate content. Default limit is 100 messages.
delete_flagged: Delete messages that were flagged in the last scan.
list_violators: List users who had inappropriate messages in the last scan.
ban_violators [min_violations] [exclude_users]: Ban users who had inappropriate messages. Optional minimum violation count and excluded user IDs.
confirm_ban: Confirm and execute pending bans from ban_violators command.
```

Note the default presets:
```
set_warnings: 3
set_mute_time: 10m
use_warnings: False
set_sensitivity: 0.5
set_logs_channel: None (will not log any deletions)
```

Also note that the Dough role should be **ABOVE** all other members, in order to create and enforce the muted role.
""", ephemeral = True)

@bot.tree.command(name="set_logs_channel", description="Set a server wide channel id for logging messages.")
@app_commands.describe(logs_channel_id = "Logs Channel ID")
async def set_logs_channel(interaction: discord.Interaction, logs_channel_id: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    try:
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['logs_channel_id'] = logs_channel_id
        await save_servers()
        await interaction.response.send_message(f"**Successfully set logs channel id to: {logs_channel_id}**", ephemeral=True)
    except:
        await interaction.response.send_message("**Failed to parse logs channel id. Logs Channel ID must be an integer.**", ephemeral=True)

    
@bot.tree.command(name="use_warnings", description="Whether to automatically mute users after a certain amount of warnings.")
@app_commands.describe(use_warnings = "Use Warnings")
async def use_warnings(interaction: discord.Interaction, use_warnings: bool):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
    servers[str(interaction.guild.id)]['use_warnings'] = use_warnings
    await save_servers()
    await interaction.response.send_message(f"Successfully set use_warnings to **{use_warnings}**.", ephemeral=True)

@bot.tree.command(name="set_sensitivity", description="Set a server wide image moderation sensitivity.")
@app_commands.describe(sensitivity = "Image Moderation Sensitivity")
async def set_sensitivity(interaction: discord.Interaction, sensitivity: float):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    if sensitivity > 1:
        await interaction.response.send_message("**Failed to parse sensitivity. Sensitivity must be a number from 0-1.**", ephemeral=True)
        return
    try:
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['sensitivity'] = sensitivity
        await save_servers()
        await interaction.response.send_message(f"**Successfully set image moderation sensitivity to: {sensitivity}**", ephemeral=True)
    except:
        await interaction.response.send_message("**Failed to parse sensitivity. Sensitivity must be a number from 0-1.**", ephemeral=True)


@bot.tree.command(name="set_warnings", description="Set a server wide warnings limit before muting a member.")
@app_commands.describe(warning_count = "Warning Count")
async def set_warnings(interaction: discord.Interaction, warning_count: int):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    try:
        warnings = warning_count
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['warnings'] = warnings
        await save_servers()
        await interaction.response.send_message(f"**Successfully set warnings to: {warnings}**", ephemeral=True)
    except:
        await interaction.response.send_message("**Failed to parse warnings. Warnings must be an integer.**", ephemeral=True)

@bot.tree.command(name="set_mute_time", description="Set a server wide mute time to mute a member for.")
@app_commands.describe(mute_time = "Mute Time")
async def set_mute_time(interaction: discord.Interaction, mute_time: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    try:
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['mute_time'] = mute_time
        await save_servers()
        await interaction.response.send_message(f"**Successfully set mute time to {mute_time}**", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message("**Invalid duration input**", ephemeral=True)


BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_TRIGGERING_WORDS = os.getenv("USE_TRIGGERING_WORDS")

if USE_TRIGGERING_WORDS == "True":
    TRIGGERING_WORDS_FILE = os.getenv("TRIGGERING_WORDS")
    if TRIGGERING_WORDS_FILE:
        with open(TRIGGERING_WORDS_FILE, "r") as file:
            TRIGGERING_WORDS = file.read().split(",")
    else:
        TRIGGERING_WORDS = []
else:
    TRIGGERING_WORDS = []

if not BOT_TOKEN or not OPENAI_API_KEY:
    print("You did not set your .env file correctly.")
    exit()


async def tempmute(ctx, member: discord.Member=None):
    guild = ctx.guild
    warnings = servers[str(guild.id)].get('warnings', 3)
    time = servers[str(guild.id)].get('mute_time', '10m')
    reason = f"sending more than {warnings} inappropriate messages."
    bot_member = guild.get_member(bot.user.id)
    try:
        seconds = int(time[:-1])
        duration = time[-1]
        if duration == "s":
            seconds = seconds * 1
        elif duration == "m":
            seconds = seconds * 60
        elif duration == "h":
            seconds = seconds * 60 * 60
        elif duration == "d":
            seconds = seconds * 86400
        else:
            await ctx.send("Invalid duration input")
            return
    except Exception as e:
        print(e)
        await ctx.send("Invalid duration input")
        return

    Muted = discord.utils.get(guild.roles, name="Muted")
    if not Muted:
        Muted = await guild.create_role(name="Muted")
        all_roles = await guild.fetch_roles()
        for i in range(len(all_roles)):
            if all_roles[i] in [y for y in bot_member.roles]:
                role_of_muted = len(all_roles)-i-1
        try:
            await Muted.edit(reason=None, position=role_of_muted)
        except:
            await ctx.send("**Failed to mute user, ensure that the bot role is above all other roles.**")
            return
        for channel in guild.channels:
            await channel.set_permissions(Muted, speak=False, send_messages=False, read_message_history=True, read_messages=True)

    await member.add_roles(Muted, reason=reason)
    muted_embed = discord.Embed(title="Muted User", description=f"{member.mention} was muted for {reason} Muted for {time}.")
    await ctx.send(embed=muted_embed)
    await asyncio.sleep(seconds)
    await member.remove_roles(Muted)
    unmute_embed = discord.Embed(title="Mute Over!", description=f'{member.mention} is now unmuted.')
    await ctx.send(embed=unmute_embed)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    await bot.wait_until_ready()
    if message.author.id == bot.user.id:
        return
    sent_message = message
    guild = message.guild
    if str(guild.id) not in servers:  # If server is not in servers, add it
        servers[str(guild.id)] = {'use_warnings': False, 'warnings': 3, 'mute_time': '10m'}
        await save_servers()

    use_warnings = servers[str(guild.id)].get('use_warnings', False)
    warnings = servers[str(guild.id)].get('warnings', 3)

    if str(guild.id) not in warning_list:
        warning_list[str(guild.id)] = {}
        await save_warnings()
    

    if USE_TRIGGERING_WORDS == "True":
            if not any(map(message.content.__contains__, TRIGGERING_WORDS)):
                return
            else:
                print("Triggering word found in the filter, sending to OpenAI...")

    # if message.attachments:
    #     attachments = message.attachments
    #     for attachment in attachments:
    #         if attachment.content_type.startswith("image"):
    #             await attachment.save("toModerate.jpeg")
    #             sensitivity = servers[str(guild.id)].get('sensitivity', 0.5)
    #             result = await image_is_safe(sensitivity=sensitivity)

    #             if not result:
    #                 await sent_message.delete()
    #                 print("Deleted a message with an inappropriate image. The message was sent from " + str(sent_message.author.id))

    #                 logs_channel_id = servers[str(guild.id)].get('logs_channel_id', None)
    #                 if logs_channel_id:
    #                     logs_channel = bot.get_channel(int(logs_channel_id))
    #                     await logs_channel.send(f"Deleted an image from {sent_message.author.mention} because it was inappropriate.")

    #                 if not use_warnings:
    #                     await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate.")
    #                     return
    #                 if message.author.id in warning_list[str(guild.id)]:
    #                     warning_list[str(guild.id)][message.author.id] += 1
    #                     await save_warnings()
    #                     if warning_list[str(guild.id)][message.author.id] >= warnings:
    #                         await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate.")
    #                         await tempmute(sent_message.channel, sent_message.author)
    #                         warning_list[str(guild.id)][message.author.id] = 0
    #                         await save_warnings()
    #                     else:
    #                         await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) -  warning_list[str(guild.id)][message.author.id]) + " warnings left.")
    #                 else:
    #                     warning_list[str(guild.id)][message.author.id] = 1
    #                     await save_warnings()
    #                     await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) - warning_list[str(guild.id)][message.author.id]) + " warnings left.")
    #                 return
    
    if not message.attachments and not await(message_is_safe(message.content, OPENAI_API_KEY)):
        await sent_message.delete()
        print("Deleted an inappropriate message. The message was sent from " + str(sent_message.author.id))

        logs_channel_id = servers[str(guild.id)].get('logs_channel_id', None)
        if logs_channel_id:
            logs_channel = bot.get_channel(int(logs_channel_id))
            await logs_channel.send(f"Deleted a message from {sent_message.author.mention} because it was inappropriate. The message was: '{sent_message.content}'")

        if not use_warnings:
            # await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate.")
            return
        if message.author.id in warning_list[str(guild.id)]:
            warning_list[str(guild.id)][message.author.id] += 1
            await save_warnings()
            if warning_list[str(guild.id)][message.author.id] >= warnings:
                # await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate.")
                await tempmute(sent_message.channel, sent_message.author)
                warning_list[str(guild.id)][message.author.id] = 0
                await save_warnings()
            else:
                await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) - warning_list[str(guild.id)][message.author.id]) + " warnings left.")
        else:
            warning_list[str(guild.id)][message.author.id] = 1
            await save_warnings()
            await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) - warning_list[str(guild.id)][message.author.id]) + " warnings left.")
    
    await bot.process_commands(message)

    @bot.event
    async def on_message_edit(message_before, message_after):
        await on_message(message_after)
    

async def process_message(message, guild_id, sensitivity):
    """Process a single message and return results if inappropriate."""
    if message.author.bot:
        return None
        
    results = []
    
    # Check text content
    if message.content:
        is_safe = await message_is_safe(message.content, OPENAI_API_KEY)
        if not is_safe:
            results.append({
                'author': message.author,
                'content': message.content,
                'id': message.id,
                'channel': message.channel
            })
    
    # Check attachments
    # if message.attachments:
    #     for attachment in message.attachments:
    #         if attachment.content_type and attachment.content_type.startswith("image"):
    #             try:
    #                 # Use a unique filename for each image to prevent conflicts
    #                 filename = f"toModerate_{message.id}_{attachment.filename}"
    #                 await attachment.save(filename)
    #                 if not await image_is_safe(sensitivity=sensitivity):
    #                     results.append({
    #                         'author': message.author,
    #                         'content': f"[Inappropriate Image] {attachment.url}",
    #                         'id': message.id,
    #                         'channel': message.channel
    #                     })
    #                 # Cleanup temp file
    #                 os.remove(filename)
    #             except Exception as e:
    #                 print(f"Error processing image: {e}")
    
    return results
@bot.tree.command(
    name="scan_channel",
    description="Scan previous messages in a channel for inappropriate content"
)
@app_commands.describe(
    channel="The channel to scan (defaults to current channel)",
    limit="Number of messages to scan (default: 100)"
)
async def scan_channel(
    interaction: discord.Interaction, 
    channel: discord.TextChannel = None,
    limit: int = 100
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    
    if not target_channel.permissions_for(interaction.guild.me).read_message_history:
        await interaction.response.send_message(
            f"I don't have permission to read messages in {target_channel.mention}",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message(
        f"Starting scan of last {limit} messages in {target_channel.mention}...", 
        ephemeral=True
    )
    
    try:
        # Collect all messages first
        messages = [message async for message in target_channel.history(limit=limit)]
        total_messages = len(messages)
        
        # Get sensitivity setting
        sensitivity = servers[str(interaction.guild.id)].get('sensitivity', 0.5)
        
        # Process messages in batches
        batch_size = 10  # Adjust this number as needed
        sem = asyncio.Semaphore(10)  # Limit concurrent API calls within each batch
        inappropriate_messages = []
        
        for i in range(0, total_messages, batch_size):
            batch = messages[i:i+batch_size]
            
            async def process_with_semaphore(message):
                async with sem:
                    return await process_message(message, interaction.guild.id, sensitivity)
            
            # Process current batch
            batch_results = await asyncio.gather(
                *[process_with_semaphore(message) for message in batch],
                return_exceptions=True
            )
            
            # Process batch results
            batch_inappropriate = []
            for result in batch_results:
                if isinstance(result, list) and result:
                    batch_inappropriate.extend(result)
            
            inappropriate_messages.extend(batch_inappropriate)
            
            # Log progress
            progress = min(i + batch_size, total_messages)
            progress_msg = f"Processed {progress}/{total_messages} messages. "
            if batch_inappropriate:
                progress_msg += f"Found {len(batch_inappropriate)} inappropriate messages in this batch."
            else:
                progress_msg += "No inappropriate content in this batch."
            
            await interaction.followup.send(progress_msg, ephemeral=True)
        
        # Final summary
        if inappropriate_messages:
            summary = f"**Final Results - Inappropriate Content Found in {target_channel.mention}:**\n"
            for msg in inappropriate_messages:
                summary += f"\n• Message by {msg['author'].mention} (ID: {msg['id']})\n"
                content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                summary += f"  Content: {content_preview}\n"
                
            # Split into chunks if too long
            if len(summary) > 2000:
                chunks = [summary[i:i+1900] for i in range(0, len(summary), 1900)]
                for chunk in chunks:
                    await interaction.followup.send(chunk, ephemeral=True)
            else:
                await interaction.followup.send(summary, ephemeral=True)
                
            await interaction.followup.send(
                f"Total: Found {len(inappropriate_messages)} inappropriate messages. "
                "Reply with `/delete_flagged` to remove these messages.", 
                ephemeral=True
            )
            
            interaction.client.flagged_messages = inappropriate_messages
            
        else:
            await interaction.followup.send(
                f"Scan complete: No inappropriate content found in {target_channel.mention}.", 
                ephemeral=True
            )
            
    except Exception as e:
        await interaction.followup.send(f"An error occurred while scanning: {str(e)}", ephemeral=True)

@bot.tree.command(name="delete_flagged", description="Delete the messages that were flagged in the last scan.")
async def delete_flagged(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
        
    if not hasattr(interaction.client, 'flagged_messages'):
        await interaction.response.send_message("No flagged messages found. Please run `/scan_channel` first.", ephemeral=True)
        return
        
    deleted_count = 0
    failed_count = 0
    
    await interaction.response.send_message("Starting deletion of flagged messages...", ephemeral=True)
    
    for msg in interaction.client.flagged_messages:
        try:
            channel = msg['channel']
            message = await channel.fetch_message(msg['id'])
            await message.delete()
            deleted_count += 1
        except Exception as e:
            print(f"Failed to delete message {msg['id']}: {e}")
            failed_count += 1
            
    summary = f"Deletion complete. Successfully deleted {deleted_count} messages."
    if failed_count > 0:
        summary += f"\nFailed to delete {failed_count} messages."
        
    await interaction.followup.send(summary, ephemeral=True)
    
    # Clear the flagged messages
    interaction.client.flagged_messages = []

@bot.tree.command(name="list_violators", description="List users who had inappropriate messages in the last scan.")
async def list_violators(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
        
    if not hasattr(interaction.client, 'flagged_messages'):
        await interaction.response.send_message("No flagged messages found. Please run `/scan_channel` first.", ephemeral=True)
        return
    
    # Count violations per user
    violation_counts = {}
    for msg in interaction.client.flagged_messages:
        author = msg['author']
        violation_counts[author.id] = violation_counts.get(author.id, {
            'mention': author.mention,
            'name': f"{author.name}#{author.discriminator}",
            'count': 0
        })
        violation_counts[author.id]['count'] += 1
    
    if not violation_counts:
        await interaction.response.send_message("No violations found.", ephemeral=True)
        return
    
    # Create summary message
    summary = "**Violation Summary:**\n\n"
    for user_id, data in violation_counts.items():
        summary += f"• {data['mention']} ({data['name']})\n"
        summary += f"  Violations: {data['count']}\n"
    
    await interaction.response.send_message(summary, ephemeral=True)

@bot.tree.command(
    name="ban_violators",
    description="Ban users who had inappropriate messages, with option to exclude specific users."
)
@app_commands.describe(
    min_violations="Minimum violations required for ban (default: 1)",
    exclude_users="Comma-separated list of user IDs to exclude from ban"
)
async def ban_violators(
    interaction: discord.Interaction,
    min_violations: int = 1,
    exclude_users: str = None
):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
        
    if not hasattr(interaction.client, 'flagged_messages'):
        await interaction.response.send_message("No flagged messages found. Please run `/scan_channel` first.", ephemeral=True)
        return
    
    # Parse excluded users
    excluded_ids = set()
    if exclude_users:
        try:
            excluded_ids = set(int(uid.strip()) for uid in exclude_users.split(','))
        except ValueError:
            await interaction.response.send_message("Invalid user ID format in exclude_users. Use comma-separated numeric IDs.", ephemeral=True)
            return
    
    # Count violations per user
    violation_counts = {}
    for msg in interaction.client.flagged_messages:
        author = msg['author']
        if author.id not in excluded_ids:  # Skip excluded users
            violation_counts[author.id] = violation_counts.get(author.id, {
                'user': author,
                'count': 0
            })
            violation_counts[author.id]['count'] += 1
    
    # Filter users by minimum violations
    users_to_ban = {
        uid: data for uid, data in violation_counts.items()
        if data['count'] >= min_violations
    }
    
    if not users_to_ban:
        await interaction.response.send_message(
            f"No users found with {min_violations} or more violations.",
            ephemeral=True
        )
        return
    
    # Confirm before banning
    confirmation = f"About to ban {len(users_to_ban)} users with {min_violations}+ violations:\n\n"
    for uid, data in users_to_ban.items():
        confirmation += f"• {data['user'].mention} ({data['user'].name}#{data['user'].discriminator})"
        confirmation += f" - {data['count']} violations\n"
    
    confirmation += "\nAre you sure? Use `/confirm_ban` to proceed."
    
    # Store ban data for confirmation
    interaction.client.pending_bans = users_to_ban
    
    await interaction.response.send_message(confirmation, ephemeral=True)

@bot.tree.command(name="confirm_ban", description="Confirm and execute pending bans from ban_violators command.")
async def confirm_ban(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    if not hasattr(interaction.client, 'pending_bans'):
        await interaction.response.send_message("No pending bans found. Please run `/ban_violators` first.", ephemeral=True)
        return
    
    banned_count = 0
    failed_count = 0
    
    await interaction.response.send_message("Executing bans...", ephemeral=True)
    
    for uid, data in interaction.client.pending_bans.items():
        try:
            await interaction.guild.ban(
                data['user'],
                reason=f"Automated ban: {data['count']} inappropriate message violations"
            )
            banned_count += 1
        except Exception as e:
            print(f"Failed to ban user {uid}: {e}")
            failed_count += 1
    
    summary = f"Ban execution complete.\nSuccessfully banned: {banned_count} users"
    if failed_count > 0:
        summary += f"\nFailed to ban: {failed_count} users"
    
    await interaction.followup.send(summary, ephemeral=True)
    
    # Clear pending bans
    interaction.client.pending_bans = {}

@bot.tree.command(name="check_members", description="Check join dates of server members")
@app_commands.describe(
    threshold_days="Only show accounts newer than this many days (optional)",
    include_offline="Include offline members in the check (default: False)"
)
async def check_members(
    interaction: discord.Interaction,
    threshold_days: int = None,
    include_offline: bool = False
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Gathering member information...", ephemeral=True)

    current_time = discord.utils.utcnow()
    members_info = []

    # Get all members or only online ones
    if include_offline:
        members = interaction.guild.members
    else:
        members = [m for m in interaction.guild.members if m.status != discord.Status.offline]

    for member in members:
        account_age = (current_time - member.created_at).days
        server_age = (current_time - member.joined_at).days if member.joined_at else 0

        # If threshold is set, only include members with newer accounts
        if threshold_days is None or account_age < threshold_days:
            members_info.append({
                'member': member,
                'account_age': account_age,
                'server_age': server_age
            })

    # Sort by account age (newest first)
    members_info.sort(key=lambda x: x['account_age'])

    if not members_info:
        await interaction.followup.send("No members found matching the criteria.", ephemeral=True)
        return

    # Create summary message in chunks due to Discord's message length limits
    chunks = []
    current_chunk = "**Member Join Date Information:**\n\n"

    for info in members_info:
        member = info['member']
        entry = (f"• {member.mention} ({member.name})\n"
                f"  Account created: {member.created_at.strftime('%Y-%m-%d')} ({info['account_age']} days ago)\n"
                f"  Joined server: {member.joined_at.strftime('%Y-%m-%d')} ({info['server_age']} days ago)\n\n")

        if len(current_chunk) + len(entry) > 1900:  # Discord limit is 2000, leaving room for extra chars
            chunks.append(current_chunk)
            current_chunk = entry
        else:
            current_chunk += entry

    if current_chunk:
        chunks.append(current_chunk)

    # Send all chunks
    for chunk in chunks:
        await interaction.followup.send(chunk, ephemeral=True)

    summary = f"\nTotal members checked: {len(members_info)}"
    if not include_offline:
        summary += " (online only)"
    if threshold_days:
        summary += f"\nShowing accounts newer than {threshold_days} days"
    
    await interaction.followup.send(summary, ephemeral=True)

@bot.tree.command(name="reload", description="Reload the bot's commands")
async def reload(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
        
    try:
        # Defer the response first to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Reloaded {len(synced)} command(s)", ephemeral=True)
    except Exception as e:
        try:
            await interaction.followup.send(f"An error occurred while reloading: {str(e)}", ephemeral=True)
        except:
            print(f"Failed to reload commands: {str(e)}")

@bot.tree.command(
    name="find_suspicious_joins",
    description="Find users who joined the server within X days of creating their Discord account"
)
@app_commands.describe(
    max_days="Maximum days between account creation and server join (default: 3)",
    include_offline="Include offline members in the check (default: False)",
    action="Action to take: 'none' (default), 'mute', or 'ban'",
    mute_duration="Duration for mute (e.g., '1h', '1d', '30m'). Default: '1d'"
)
async def find_suspicious_joins(
    interaction: discord.Interaction,
    max_days: int = 3,
    include_offline: bool = False,
    action: str = "none",
    mute_duration: str = "1d"
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Validate action parameter
    action = action.lower()
    if action not in ["none", "mute", "ban"]:
        await interaction.response.send_message("Invalid action. Must be 'none', 'mute', or 'ban'.", ephemeral=True)
        return

    if action == "ban" and not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You do not have permission to ban members.", ephemeral=True)
        return

    if action == "mute" and not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("You do not have permission to mute members.", ephemeral=True)
        return

    await interaction.response.send_message("Scanning for suspicious join patterns...", ephemeral=True)

    suspicious_members = []
    total_members = 0
    
    # Get all members or only online ones
    members = interaction.guild.members if include_offline else [m for m in interaction.guild.members if m.status != discord.Status.offline]
    total_members = len(members)

    for member in members:
        if member.joined_at:  # Check if join date is available
            time_diff = member.joined_at - member.created_at
            days_diff = time_diff.total_seconds() / (24 * 60 * 60)  # Convert to days
            
            if 0 <= days_diff <= max_days:  # Only include non-negative differences within threshold
                suspicious_members.append({
                    'member': member,
                    'days_until_join': round(days_diff, 1)
                })

    if not suspicious_members:
        await interaction.followup.send(
            f"No suspicious accounts found among {total_members} checked members.", 
            ephemeral=True
        )
        return

    # Calculate statistics
    suspicious_count = len(suspicious_members)
    percentage = (suspicious_count / total_members) * 100 if total_members > 0 else 0
    
    # Create summary message
    summary = f"**Suspicious Account Statistics:**\n\n"
    summary += f"• Total members checked: {total_members}\n"
    summary += f"• Suspicious accounts found: {suspicious_count}\n"
    summary += f"• Percentage: {percentage:.1f}%\n"
    summary += f"• Criteria: Joined within {max_days} days of account creation\n"
    
    if not include_offline:
        summary += "\n(Only online members were checked)"

    if action != "none":
        # Store action data for confirmation
        interaction.client.pending_suspicious_action = {
            'members': suspicious_members,
            'action': action,
            'mute_duration': mute_duration
        }
        summary += f"\n\nUse `/confirm_suspicious_action` to {action} these accounts"
        if action == "mute":
            summary += f" for {mute_duration}"
    
    await interaction.followup.send(summary, ephemeral=True)

@bot.tree.command(
    name="confirm_suspicious_action",
    description="Confirm and execute action (ban/mute) for suspicious accounts identified in the last scan"
)
async def confirm_suspicious_action(interaction: discord.Interaction):
    if not hasattr(interaction.client, 'pending_suspicious_action'):
        await interaction.response.send_message(
            "No pending actions found. Please run `/find_suspicious_joins` first.", 
            ephemeral=True
        )
        return
    
    action_data = interaction.client.pending_suspicious_action
    action = action_data['action']
    members = action_data['members']
    
    if action == "ban" and not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You do not have permission to ban members.", ephemeral=True)
        return
    
    if action == "mute" and not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("You do not have permission to mute members.", ephemeral=True)
        return
    
    await interaction.response.send_message(
        f"Beginning {action} process for {len(members)} suspicious accounts...", 
        ephemeral=True
    )
    
    success_count = 0
    failed_count = 0
    failed_members = []
    
    for info in members:
        member = info['member']
        try:
            if action == "ban":
                await interaction.guild.ban(
                    member,
                    reason=f"Suspicious account: joined {info['days_until_join']} days after creation"
                )
            else:  # mute
                # Parse duration
                duration = action_data['mute_duration']
                try:
                    amount = int(duration[:-1])
                    unit = duration[-1].lower()
                    if unit == 's':
                        seconds = amount
                    elif unit == 'm':
                        seconds = amount * 60
                    elif unit == 'h':
                        seconds = amount * 3600
                    elif unit == 'd':
                        seconds = amount * 86400
                    else:
                        raise ValueError("Invalid duration unit")
                    
                    await member.timeout(
                        discord.utils.utcnow() + datetime.timedelta(seconds=seconds),
                        reason=f"Suspicious account: joined {info['days_until_join']} days after creation"
                    )
                except ValueError:
                    await interaction.followup.send(f"Invalid mute duration format: {duration}. Use format like '1h', '1d', '30m'", ephemeral=True)
                    return
                
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_members.append(f"{member.name} (Error: {str(e)})")
    
    # Create result message
    result = f"{action.title()} operation completed:\n• Successfully {action}ed: {success_count} members\n"
    if failed_count > 0:
        result += f"• Failed to {action}: {failed_count} members\n\nFailed {action}s:"
        for failed in failed_members:
            result += f"\n• {failed}"
    
    await interaction.followup.send(result, ephemeral=True)
    
    # Clear pending action
    interaction.client.pending_suspicious_action = None

bot.run(BOT_TOKEN)
