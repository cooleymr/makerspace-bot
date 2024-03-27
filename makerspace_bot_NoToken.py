# This example requires the 'message_content' intent.
import asyncio
import discord
import aiofiles  # to read .stl file
from discord.ext import commands
from datetime import datetime
import pandas as pd
import logging
import re
from datetime import datetime, timedelta
from discord.ext import commands
import io

BOT_TOKEN = 

STUDENT_CHANNEL_ID = 1194329078086508614
TA_CHANNEL_ID = 1210267165933174924
# STUDENT_CHANNEL_ID = 1201594371427029095
# TA_CHANNEL_ID = 1202485791247437856

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(),receive_messages=True)
bot.remove_command('help')

logging.basicConfig(level=logging.DEBUG)

def extract_gcode_data(file_content):
    filament_length_pattern = r'Filament length: (\d+\.\d+) mm'
    plastic_weight_pattern = r'Plastic weight: (\d+\.\d+) g'
    printing_time_pattern = r'Build time: ([0-9]+) hours ([0-9]+) minutes'
    material_cost_pattern = r'Material cost: (\d+\.\d+)'
    plastic_volume_pattern = r'Plastic volume: (\d+\.\d+) mm\^3'

    filament_length = None
    plastic_weight = None
    printing_time = None
    material_cost = None
    plastic_volume = None

    lines = file_content.split('\n')[-1000:]
    for line in lines:
        filament_length_match = re.search(filament_length_pattern, line)
        plastic_weight_match = re.search(plastic_weight_pattern, line)
        printing_time_match = re.search(printing_time_pattern, line)
        material_cost_match = re.search(material_cost_pattern, line)
        plastic_volume_match = re.search(plastic_volume_pattern, line)

        if filament_length_match:
            filament_length = float(filament_length_match.group(1))
        elif plastic_weight_match:
            plastic_weight = float(plastic_weight_match.group(1))
        elif printing_time_match:
            hours = int(printing_time_match.group(1))
            minutes = int(printing_time_match.group(2))
            printing_time = timedelta(hours=hours, minutes=minutes)
        elif material_cost_match:
            material_cost = float(material_cost_match.group(1))
        elif plastic_volume_match:
            plastic_volume = float(plastic_volume_match.group(1))

        if (filament_length is not None and
                plastic_weight is not None and
                printing_time is not None and
                material_cost is not None and
                plastic_volume is not None):
            break

    return filament_length, plastic_weight, printing_time, material_cost, plastic_volume

def extract_bgcode_data(bgcode_content):
    filament_length_pattern = r'filament used \[mm\]=([\d.]+)'
    plastic_weight_pattern = r'filament used \[g\]=([\d.]+)'
    material_cost_pattern = r'filament cost=([\d.]+)'
    plastic_volume_pattern = r'filament used \[cm3\]=([\d.]+)'
    printing_time_pattern = r'estimated printing time \(normal mode\)=([0-9]*)h? ?([0-9]+)m ([0-9]+)s'

    filament_length = None
    plastic_weight = None
    material_cost = None
    plastic_volume = None
    printing_time = None

    lines = bgcode_content.split('\n')[:100]
    for line in lines:
        filament_length_match = re.search(filament_length_pattern, line)
        plastic_weight_match = re.search(plastic_weight_pattern, line)
        material_cost_match = re.search(material_cost_pattern, line)
        plastic_volume_match = re.search(plastic_volume_pattern, line)
        printing_time_match = re.search(printing_time_pattern, line)

        if filament_length_match:
            filament_length = float(filament_length_match.group(1))
        elif plastic_weight_match:
            plastic_weight = float(plastic_weight_match.group(1))
        elif material_cost_match:
            material_cost = float(material_cost_match.group(1))
        elif plastic_volume_match:
            plastic_volume = float(plastic_volume_match.group(1))
        elif printing_time_match:
            hours = int(printing_time_match.group(1))
            minutes = int(printing_time_match.group(2))
            seconds = int(printing_time_match.group(3))
            printing_time = timedelta(hours=hours, minutes=minutes, seconds=seconds)

        if filament_length is not None and plastic_weight is not None and material_cost is not None and plastic_volume is not None and printing_time is not None:
            break

    return filament_length, plastic_weight, printing_time, material_cost, plastic_volume


# Function to get .csv file
async def get_csv():
    try:
        print_jobs = pd.read_csv("print_jobs.csv")
        logging.debug(".csv - File found")
    except FileNotFoundError:
        print_jobs = pd.DataFrame(columns= ["job_id", "user", "ta", "starttime", "endtime", "failed", "status", "thread_id", "printing_time", "plastic_weight", "filament_length", "plastic_volume", "material_cost"])
        print_jobs.to_csv("print_jobs.csv", index=False)
        logging.debug(".csv - File created")
    return print_jobs



# !start command
@bot.command()
async def start(ctx):
    # Ensure command was invoked in the TA channel and inside a thread
    if ctx.channel.parent_id != TA_CHANNEL_ID or not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads in the TA channel.")
        return
    
    # Ensure print job has already started or is not failed in the thread
    thread = ctx.channel
    messages = []
    async for message in thread.history(limit=100):
        if message.author == bot.user and message.content.startswith("Print job failed."):
            break
        elif message.author == bot.user and message.content.startswith("Print job started."):
            await ctx.send("Print has already started. Type !fail to cancel the command or !complete to complete it.")
            return

    # DM user the print job has started
    user = ctx.author
    dm_channel = await user.create_dm()
    await dm_channel.send("Your print job has now started")
    await ctx.send("Print job started.")

    # Update the .csv row with the start data
    print_jobs = await get_csv()
    for index, row in print_jobs.iterrows():
        if row["thread_id"] == thread.id:
            print_jobs.at[index, "status"] = "started"
            print_jobs["starttime"] = print_jobs["starttime"].astype(str)
            print_jobs.at[index, "starttime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.debug(".csv - Row updated with start")
            break
    print_jobs.to_csv("print_jobs.csv", index=False)
    

# !fail command
@bot.command()
async def fail(ctx):
    # Ensure command was invoked in the TA channel and inside a thread
    if ctx.channel.parent_id != TA_CHANNEL_ID or not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads in the TA channel.")
        return
    
    # Ensure print job has already failed or was started again in the thread
    thread = ctx.channel
    messages = []
    async for message in thread.history(limit=100):
        if message.author == bot.user and message.content.startswith("Print job started."):
            break
        elif message.author == bot.user and message.content.startswith("Print job failed."):
            await ctx.send("Print has already failed. Type !start to start the print again.")
            return
    
    # DM the user that the print job has started
    user = ctx.author
    dm_channel = await user.create_dm()
    await dm_channel.send("Your print job has failed")
    await ctx.send("Print job failed.")

    # Update the .csv row with the fail data
    print_jobs = await get_csv()
    for index, row in print_jobs.iterrows():
        if row["thread_id"] == thread.id:
            print_jobs.at[index, "status"] = "failed"
            print_jobs["failed"] = "true"
            logging.debug(".csv - Row updated with fail")
            break
    print_jobs.to_csv("print_jobs.csv", index=False)


# !complete command
@bot.command()
async def complete(ctx):
    # Ensure command was invoked in the TA channel and inside a thread
    if ctx.channel.parent_id != TA_CHANNEL_ID or not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads in the TA channel.")
        return
    
    # Check if a print job has already completed in the thread
    thread = ctx.channel
    messages = thread.history(limit=100)
    async for message in messages:
        if message.author == bot.user and message.content.startswith("Print job completed."):
            await ctx.send("Print has already been completed.")
            return

    # DM the user that the print job has started
    user = ctx.author
    dm_channel = await user.create_dm()
    await dm_channel.send("Your print job has completed")
    await ctx.send("Print job completed.")

    # Update the .csv row with the complete data
    print_jobs = await get_csv()
    for index, row in print_jobs.iterrows():
        if row["thread_id"] == thread.id:
            print_jobs.at[index, "status"] = "completed"
            print_jobs["endtime"] = print_jobs["endtime"].astype(str)
            print_jobs.at[index, "endtime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.debug(".csv - Row updated with complete")
            break
    print_jobs.to_csv("print_jobs.csv", index=False)


# !list command
@bot.command()
async def list(ctx):
    # Getting only in progress jobs
    print_jobs = pd.read_csv("print_jobs.csv")
    in_progress_jobs = []
    for _, print_job in print_jobs.iterrows():
        if print_job['status'] == "waiting" or print_job['status'] == "failed":
            job_info = f"Id: {print_job['job_id']} User: {print_job['user']} Time: {print_job['printing_time']} Weight: {print_job['plastic_weight']} Length: {print_job['filament_length']} Volume: {print_job['plastic_volume']} Cost: {print_job['material_cost']}"
            in_progress_jobs.append(job_info)

    # Send the print jobs
    if in_progress_jobs:
        await ctx.send("Number of waiting jobs: " + str(len(in_progress_jobs)))
        await ctx.send("\n".join(in_progress_jobs))
    else:
        await ctx.send("No waiting print jobs.")

    # Send the .csv file
    with open("print_jobs.csv", "r") as file:
        await ctx.send(file=discord.File(file, "print_jobs.csv"))


    
# Bot online
@bot.event
async def on_ready():
    channel = bot.get_channel(STUDENT_CHANNEL_ID)
    try:
        await get_csv()
        logging.debug("Bot is online")
        await channel.send("Bot is online!\nType !help for a list of commands")
    except AttributeError as e:
        logging.error(f"Error sending message: {e}")
        logging.error("STUDENT_CHANNEL_ID failed")
    

# Bot offline
@bot.event
async def on_disconnect():
    channel = bot.get_channel(STUDENT_CHANNEL_ID)
    await channel.send("Bot is offline")
    logging.debug("Bot is offline")
# Bot shutdown
@bot.event
async def on_error(event, *args, **kwargs):
    channel = bot.get_channel(STUDENT_CHANNEL_ID)
    await channel.send("Bot is offline")
    logging.debug("Bot is offline")


# Update the on_message function
@bot.event
async def on_message(message):
    # Ignore if not in STUENT_CHANNEL_ID or TA_CHANNEL_ID
    if message.author == bot.user or message.channel.id not in [STUDENT_CHANNEL_ID, TA_CHANNEL_ID]:
        return

    # If message contains a .stl, 3d print file(.gcode, .bgcode), image file(.png, .jpg, or .jpeg)file, read the file and send the content to new channel with specific channel id
    if message.attachments:
        stl_file = None
        gcode_file = None
        image_files = []

        # Extracting .stl, .gcode, .png, .jpg, .jpeg files from the message
        for attachment in message.attachments:
            if attachment.filename.endswith(".stl") or attachment.filename.endswith(".3mf"):
                stl_file = attachment
            elif attachment.filename.endswith(".gcode") or attachment.filename.endswith(".bgcode"):
                gcode_file = attachment
            elif attachment.filename.endswith((".png", ".jpg", ".jpeg")):
                image_files.append(attachment)

        # If all required attachments are present, send them to the TA channel
        if stl_file and gcode_file and image_files:

            # Send a DM to the user that the files are being submitted
            user = message.author
            dm_channel = await user.create_dm()
            await dm_channel.send("Submitting print to TAs for review")
            
            # Read the content of the stl and gcode files and create discord.File objects
            stl_content = await stl_file.read()
            gcode_content = await gcode_file.read()
            stl_file = discord.File(io.BytesIO(stl_content), filename=stl_file.filename)
            gcode_file = discord.File(io.BytesIO(gcode_content), filename=gcode_file.filename)

            # Download files to be sent with message
            files = []
            for attachment in message.attachments:
                file_content = await attachment.read()
                file = discord.File(io.BytesIO(file_content), filename=attachment.filename)
                files.append(file)

            # Extract print data from .gcode/.bgcode file
            if gcode_file.filename.endswith(".gcode"):
                gcode_content = gcode_content.decode()
                filament_length, plastic_weight, printing_time, material_cost, plastic_volume = extract_gcode_data(gcode_content)
            elif gcode_file.filename.endswith(".bgcode"):
                bgcode_content = gcode_content.decode('iso-8859-1')
                filament_length, plastic_weight, printing_time, material_cost, plastic_volume = extract_bgcode_data(bgcode_content)

            # Send message and files to ta channel
            channel = bot.get_channel(TA_CHANNEL_ID)
            message_content = f"New print for review:\n\nUsername: {user.name}\nPlastic Weight: {plastic_weight}g\nEstimated Printing Time: {printing_time}"
            sent_message = await channel.send(message_content, files=files)
            logging.debug("Files sent to TA channel")

            # Create thread named after the first file's name (everything before period)
            thread = await sent_message.create_thread(name=stl_file.filename.split('.')[0])
            await thread.send("Thread created")  # Add a message in the thread

            # Add line to the print job using the pandas library and without load_printjobs_function
            print_jobs = await get_csv()
            new_row = {"job_id": len(print_jobs) + 1, "thread_id": thread.id, "user": user.name, "ta": "", "starttime": "", "endtime": "", "failed": False, "status": "waiting", "printing_time": printing_time, "plastic_weight": plastic_weight, "filament_length": filament_length, "plastic_volume": plastic_volume, "material_cost": material_cost}
            print_jobs.loc[len(print_jobs)] = new_row
            print_jobs.to_csv("print_jobs.csv", index=False)
            logging.debug("Print job added to .csv file")

        else: # If any of the required files are missing, message the user
            missing_files = []
            if not stl_file:
                missing_files.append("- Project File (.stl or .3mf)")
            if not gcode_file:
                missing_files.append("- Converted file (.gcode or .bgcode)")
            if not image_files:
                missing_files.extend(["- Screenshot of your print (.png or .jpg or .jpeg)"])

            # Message the channel
            missing_files_str = '\n'.join(missing_files)
            await message.channel.send(f"Hi {message.author}! Please re-send your files. I'm missing {len(missing_files)} files:\n{missing_files_str}")
    await bot.process_commands(message)

# !help command to get a list of all commands
@bot.command()
async def help(ctx):
    import io

    general_commands = "GENERAL COMMANDS: \n!help - Get a list of all commands\n!list - Get a list of all waiting print jobs and .csv of print job history\n\n"

    ta_commands = "TA COMMANDS: \n!start - Start a print job\n!fail - Fail a print job\n!complete - Complete a print job\n!clear - Clear all messages in the channel (Available only for Admin)\n\n"

    csv_details = """.csv Details:
    job_id - Unique job id
    thread_id - Unique thread id to specific print
    user - Discord username of student who sent in print
    ta - Discord username of TA who entered in last command in thread
    starttime - Time of last !start command in thread (Overrides if multiple !start commands)
    endtime - Time of last !complete command in thread
    failed - If the print has been failed at least once (Cannot be overridden once true)
    status - Current status of print (waiting, started, failed, complete)
    time/weight/length/volume/cost - Metrics of print pulled from .gcode/.bgcode file"""

    # Create a temporary text file in memory
    temp_file = io.StringIO(general_commands + ta_commands + csv_details)

    # Send the temporary text file
    await ctx.send(file=discord.File(temp_file, "help_message.txt"))

# !clean command that removes the last 3 times the bot says "Bot is online" or "Bot is offline"
@bot.command()
async def clean(ctx):
    messages = []
    async for message in ctx.channel.history(limit=100):
        messages.append(message)
    count = 0
    for message in messages:
        if message.author == bot.user and ("bot is online" in message.content.lower() or "bot is offline" in message.content.lower()):
            if count < 3:
                await message.delete()
                count += 1
    logging.info(f"Deleted {count} messages.")

# !remove command that clears the last message sent by the bot in the channel
@bot.command()
async def remove(ctx):
    messages = []
    async for message in ctx.channel.history(limit=100):
        messages.append(message)
    count = 0
    for message in messages:
        if message.author == bot.user:
            if count < 1:
                await message.delete()
                count += 1
    logging.info(f"Deleted {count} messages.")
    logging.info(f"!remove command used")


# !Clear command that clears all messages in the channel ** Only for testing purposes ** 
@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx):
    # Ensure the user wants to clear the channel
    await ctx.send("Are you sure you want to clear ALL messages in the channel? This cannot be undone. Type 'yes' to confirm.")

    def check(m):
        return m.channel == ctx.channel

    try:
        message = await bot.wait_for('message', check=check, timeout=10.0)
        if message.content == 'yes':
            await ctx.channel.purge()
            await ctx.send("Channel cleared.")
        else:
            raise asyncio.TimeoutError
    except asyncio.TimeoutError:
        await ctx.send("Clear cancelled.")
@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You are missing Administrator permission(s) to run this command.")


# Start the bot
bot.run(BOT_TOKEN)
