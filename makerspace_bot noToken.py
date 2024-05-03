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

BOT_TOKEN = ""

# Top is Real Channel ID
# STUDENT_CHANNEL_ID = 1194329078086508614
# TA_CHANNEL_ID = 1210267165933174924 

# Bottom is Test Channel ID
STUDENT_CHANNEL_ID = 1233325412671688774
TA_CHANNEL_ID = 1233325499678199879




bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(),receive_messages=True)
bot.remove_command('help')

logging.basicConfig(level=logging.DEBUG)


# Method to send DM to user with the message
async def dm_user(user, message):
    dm_channel = await user.create_dm()
    await dm_channel.send(message)

def extract_bgcode_data(file_content, line_count):
    filament_length_pattern = r'filament used \[mm\]=([\d.]+)'
    plastic_weight_pattern = r'filament used \[g\]=([\d.]+)'
    material_cost_pattern = r'filament cost=([\d.]+)'
    plastic_volume_pattern = r'filament used \[cm3\]=([\d.]+)'
    printing_time_pattern = r'estimated printing time \(normal mode\)=((?:\d+h )?)(\d+)m (\d+)s'

    filament_length = None
    plastic_weight = None
    material_cost = None
    plastic_volume = None
    printing_time = None

    lines = file_content.split('\n')[:line_count]
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
            hours = int(printing_time_match.group(1).replace('h', '')) if printing_time_match.group(1) else 0
            minutes = int(printing_time_match.group(2))
            seconds = int(printing_time_match.group(3))
            printing_time = timedelta(hours=hours, minutes=minutes, seconds=seconds)

        if filament_length is not None and plastic_weight is not None and material_cost is not None and plastic_volume is not None and printing_time is not None:
            break

        
            

    return filament_length, plastic_weight, printing_time, material_cost, plastic_volume

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

    lines = file_content.split('\n')
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

        if filament_length is not None and plastic_weight is not None and material_cost is not None and plastic_volume is not None and printing_time is not None:
            break

    if plastic_weight is None and printing_time is None:
        filament_length_pattern = r'filament used \[mm\] = ([\d.]+)'
        plastic_weight_pattern = r'filament used \[g\] = ([\d.]+)'
        material_cost_pattern = r'filament cost = ([\d.]+)'
        plastic_volume_pattern = r'filament used \[cm3\] = ([\d.]+)'
        printing_time_pattern = r'estimated printing time \(normal mode\) = ((?:\d+h )?)(\d+)m (\d+)s'

        filament_length = None
        plastic_weight = None
        material_cost = None
        plastic_volume = None
        printing_time = None

        lines = file_content.split('\n')
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
                hours = int(printing_time_match.group(1).replace('h', '')) if printing_time_match.group(1) else 0
                minutes = int(printing_time_match.group(2))
                seconds = int(printing_time_match.group(3))
                printing_time = timedelta(hours=hours, minutes=minutes, seconds=seconds)

            if filament_length is not None and plastic_weight is not None and material_cost is not None and plastic_volume is not None and printing_time is not None:
                break

    return filament_length, plastic_weight, printing_time, material_cost, plastic_volume




# Function to get .csv file, if not found create a new one
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

    # DM the user that the print job has started
    user = ctx.author
    dm_channel = await user.create_dm()
    await dm_channel.send("Your print job has started.")
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


# !complete - Completes the print job and marks it as completed
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

# !setWeight command that is used inside the thread that is created when a print is submitted. This command is used to add the weight of the print to the .csv file to it's respective print job. To use this, the user should type something like "!addWeight 100" to add 100g to the print job. Then the bot types a confirmation message such as "Weight added: 100g"
@bot.command()
async def setWeight(ctx):
    # Ensure command was invoked in the TA channel and inside a thread
    if ctx.channel.parent_id != TA_CHANNEL_ID or not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads in the TA channel.")
        return
    
    await ctx.send("Please enter the weight in grams within the next 10 seconds.")
    
    def check_weight(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
    
    try:
        weight_message = await bot.wait_for('message', check=check_weight, timeout=10)
        weight = float(weight_message.content)
        
        # Update the .csv row with the weight data
        print_jobs = await get_csv()
        for index, row in print_jobs.iterrows():
            if row["thread_id"] == ctx.channel.id:
                print_jobs.at[index, "plastic_weight"] = weight
                logging.debug(f".csv - Row updated with weight: {weight}")
                break
        print_jobs.to_csv("print_jobs.csv", index=False)
        await ctx.send(f"Weight added: {weight}g")
        
    except asyncio.TimeoutError:
        await ctx.send("Command cancelled.")

# !list - Sends a list of all waiting print jobs
@bot.command()
async def list(ctx):
    # Reload the updated .csv data
    print_jobs = await get_csv()
    
    in_progress_jobs = []
    for _, print_job in print_jobs.iterrows():
        if print_job['status'] == "waiting" or print_job['status'] == "failed":
            job_info = f"Id: {print_job['job_id']} User: {print_job['user']} Time: {print_job['printing_time']} Weight: {print_job['plastic_weight']} Length: {print_job['filament_length']} Volume: {print_job['plastic_volume']} Cost: {print_job['material_cost']}"
            in_progress_jobs.append(job_info)

    # Send the print jobs
    if in_progress_jobs:
        await ctx.send("Number of waiting jobs: " + str(len(in_progress_jobs)))
        long_message = "\n".join(in_progress_jobs)
        chunks = [long_message[i:i+2000] for i in range(0, len(long_message), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send("No waiting print jobs.")


#!getCSV - Sends .csv file to user
@bot.command()
async def getCSV(ctx):
    logging.debug("!getCSV command used")
    try:
        with open("print_jobs.csv", "rb") as file:
            csv_file = discord.File(file, filename="print_jobs.csv")
            await ctx.send(file=csv_file)
            logging.debug("File sent successfully")
    except FileNotFoundError:
        logging.debug("File not found")
        await ctx.send("File not found. Please check the file path and try again.")
    except Exception as e:
        logging.debug(f"An error occurred: {e}")
        await ctx.send("An error occurred. Please try again.")


#Replaces .csv file. Allows user 10 seconds to upload a new .csv file.
@bot.command()
async def replaceCSV(ctx):
    await ctx.send("Please upload a new .csv file to replace the current one. This file MUST be named: print_jobs.csv\nYou have 10 seconds to upload the file.")
    def check(m):
        return m.channel == ctx.channel and m.author == ctx.author and m.attachments
    try:
        message = await bot.wait_for('message', check=check, timeout=10.0)
        attachment = message.attachments[0]
        if attachment.filename.endswith(".csv"):
            file_content = await attachment.read()
            with open("print_jobs.csv", "wb") as file:
                file.write(file_content)
            await ctx.send("File replaced.")
        else:
            await ctx.send("Please upload a .csv file.")
    except asyncio.TimeoutError:
        await ctx.send("Command cancelled.")

# Update the on_message function
@bot.event
async def on_message(message):
    try:
        # Ignore if not in STUDENT_CHANNEL_ID or TA_CHANNEL_ID or if the message's parent channel is not the STUDENT or TA channel
        if message.author == bot.user or (message.channel.id not in [STUDENT_CHANNEL_ID, TA_CHANNEL_ID] and message.channel.parent_id not in [STUDENT_CHANNEL_ID, TA_CHANNEL_ID]):
            logging.debug("Ignoring message: Sent by bot, wrong channel(Inside thread and not inside thread), or is a command")
            return
    except AttributeError:
        logging.debug("Ignoring message: AttributeError - 'TextChannel' object has no attribute 'parent_id'")
        return
    
    # # Ignore .gcode files
    # if message.attachments:
    #     gcode_file = None
    #     for attachment in message.attachments:
    #         if attachment.filename.endswith(".gcode"):
    #             gcode_file = attachment
    #             break
    #     if gcode_file:
    #         await message.channel.send("Please re-send your file as a .bgcode file, not .gcode.")
    #         logging.debug("Returning message to re-send .bgcode file")
    #         return
            

    # If message contains a .stl, 3d print file(.gcode, .bgcode), image file(.png, .jpg, or .jpeg)file, read the file and send the content to new channel with specific channel id
    if message.attachments:
        stl_file = None
        gcode_file = None
        image_files = []

        #Ignore if the message just contains a .csv file and nothing else
        if len(message.attachments) == 1 and message.attachments[0].filename.endswith(".csv"):
            logging.debug("Ignoring message: Only .csv file attached")
            return
        
        #When the file is submitted properly, have the bot like the message
        await message.add_reaction("👍")

        # Extracting .stl, .gcode, .png, .jpg, .jpeg files from the message
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(".stl") or attachment.filename.lower().endswith(".3mf"):
                stl_file = attachment
            elif attachment.filename.lower().endswith(".gcode") or attachment.filename.lower().endswith(".bgcode"):
                gcode_file = attachment
            elif attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                image_files.append(attachment)

        # If all required attachments are present, send them to the TA channel
        if stl_file and gcode_file and image_files:
            
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
            if gcode_file.filename.endswith(".bgcode"):
                file_content = gcode_content.decode('iso-8859-1')
                filament_length, plastic_weight, printing_time, material_cost, plastic_volume = extract_bgcode_data(file_content, 100)


            # Check if message contains a "@" symbol, if yes, change the user to the mentioned user
            user = message.author
            if "@" in message.content:
                await message.channel.send("Do you want to submit this print on behalf of the mentioned user? (yes/no)")
                def check(m):
                    # Only process messages from the same channel
                    return m.channel == message.channel
                try:
                    # Wait for a response
                    response = await bot.wait_for('message', check=check, timeout=10.0)
                    if 'yes' in response.content.lower():
                        user = message.mentions[0]
                        await message.channel.send(f"Continuing with the mentioned user: {user}.")
                    else:
                        await message.channel.send("Continuing with the original user.")

                except asyncio.TimeoutError:
                    await message.channel.send("No response received. Continuing with the original user.")
            else:
                pass

            # Send message and files to ta channel
            channel = bot.get_channel(TA_CHANNEL_ID)
            message_content = f"New print for review:\n\nUsername: {user}\nPlastic Weight: {plastic_weight}g\nEstimated Printing Time: {printing_time}"
            sent_message = await channel.send(message_content, files=files)
            logging.debug("Files sent to TA channel")

            # Create thread named after the first file's name (everything before period)
            thread = await sent_message.create_thread(name=stl_file.filename.split('.')[0])
            await thread.send(":exclamation:START PRINT HERE:exclamation:\n\n!start - Start the print\n!fail - Fail the print\n!complete - Complete the print\n!setWeight - Change the weight of the print")

            # Add print to the .csv file
            print_jobs = await get_csv()
            new_row = {"job_id": len(print_jobs) + 1, "thread_id": thread.id, "user": user, "ta": "", "starttime": "", "endtime": "", "failed": False, "status": "waiting", "printing_time": printing_time, "plastic_weight": plastic_weight, "filament_length": filament_length, "plastic_volume": plastic_volume, "material_cost": material_cost}
            print_jobs.loc[len(print_jobs)] = new_row
            print_jobs.to_csv("print_jobs.csv", index=False)
            logging.debug("Print job added to .csv file")

            #DM user(s) that print has been submitted
            await dm_user(message.author, "Hello! I'm the Makserpace Bot. Your print submission has been forwarded to the TA's.\nI'll also let you know when your print has been started, failed (maybe), and completed!\nIf you have any questions, feel free to ask them in the 'print-jobs' channel. Thanks!")
            if user != message.author:
                await dm_user(user, "Hello! I'm the Makserpace Bot. Your print submission has been forwarded to the TA's.\nI'll also let you know when your print has been started, failed (maybe), and completed!\nIf you have any questions, feel free to ask them in the 'print-jobs' channel. Thanks!")
            



        else: # If any of the required files are missing, message user in channel
            missing_files = []
            if not stl_file:
                missing_files.append("- Project File (.stl or .3mf)")
            if not gcode_file:
                missing_files.append("- Converted file (.bgcode)")
            if not image_files:
                missing_files.extend(["- Screenshot of your print (.png or .jpg or .jpeg)"])
            missing_files_str = '\n'.join(missing_files)
            await message.channel.send(f"Hi {message.author}! Please re-send all 3 of your required files. I'm missing {len(missing_files)} files:\n{missing_files_str}")
    
    await bot.process_commands(message)

# !help command to get a list of all commands
@bot.command()
async def help(ctx):
    import io

    how_to_use = "HOW TO USE: \n1. Upload a .stl / .3mf file\nUpload a .gcode / .bgcode file\nUpload a .png / .jpg / .jpeg file\n2.Type '@__user__' in submit on behalf of another user instead of you\n"

    general_commands = "GENERAL COMMANDS: \n!help - Get a list of all commands\n!list - Get a list of all waiting print jobs and .csv of print job history\n\n"

    ta_commands = "TA COMMANDS: \n!start - Start a print job\n!fail - Fail a print job\n!complete - Complete a print job\n!list - Show waiting prints\n!replaceCSV - Replace .csv file with a new file\n!getCSV - Get .csv file storing all the data\n!remove - Remove last message sent by bot\n!clear - Clear all messages in the channel (Available only for Admin)\n\n"

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
    temp_file = io.StringIO(how_to_use + general_commands + ta_commands + csv_details)

    # Send the temporary text file
    await ctx.send(file=discord.File(temp_file, "help_message.txt"))

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

# Bot online
@bot.event
async def on_ready():
    student_channel = bot.get_channel(STUDENT_CHANNEL_ID)
    ta_channel = bot.get_channel(TA_CHANNEL_ID)
    try:
        await get_csv()
        logging.debug("Bot is online")
        await student_channel.send("Bot is online!\nType !help for a list of commands\nType '@__user__' in message to submit on behalf of another user")
        await ta_channel.send("Bot is online!\n!list - Show waiting prints\n!replaceCSV - Replace .csv file with new file\n!getCSV - Get .csv file storing all print data\n!help - Get list of more commands")
    except AttributeError as e:
        logging.error(f"Error sending message: {e}")
        logging.error("Channel ID failed")

# Start the bot
bot.run(BOT_TOKEN)