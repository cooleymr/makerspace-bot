# This example requires the 'message_content' intent.
import discord
import aiofiles  # to read .stl file
from discord.ext import commands
from datetime import datetime
import pandas as pd
import logging
import re
from datetime import datetime, timedelta
from discord.ext import commands

BOT_TOKEN = 
# GENERAL_CHANNEL_ID = 1201630193060696115
# TA_CHANNEL_ID = 1202485791247437856
GENERAL_CHANNEL_ID = 1194329078086508614
TA_CHANNEL_ID = 1210267165933174924

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(),receive_messages=True)
bot.remove_command('help')

logging.basicConfig(level=logging.DEBUG)

# csv info: ["job_id", "user", "ta", "starttime", "endtime", "failed", "status", "thread_id", "time", "weight", "length", "volume", "cost"]

def parse_gcode_string(input_string):
    # Regular expressions to match different types of data
    build_time_pattern = r'Build time: (\d+) hours (\d+) minutes'
    filament_length_pattern = r'Filament length: (\d+\.\d+) mm'
    plastic_volume_pattern = r'Plastic volume: (\d+\.\d+) mm\^3'
    plastic_weight_pattern = r'Plastic weight: (\d+\.\d+) g'
    material_cost_pattern = r'Material cost: (\d+\.\d+)' 

    # Extracting data using regular expressions
    build_time_match = re.search(build_time_pattern, input_string)
    filament_length_match = re.search(filament_length_pattern, input_string)
    plastic_volume_match = re.search(plastic_volume_pattern, input_string)
    plastic_weight_match = re.search(plastic_weight_pattern, input_string)
    material_cost_match = re.search(material_cost_pattern, input_string)

    # Convert build time to datetime format
    build_time_hours = int(build_time_match.group(1))
    build_time_minutes = int(build_time_match.group(2))
    build_time = timedelta(hours=build_time_hours, minutes=build_time_minutes)

    # Extract other data
    filament_length = float(filament_length_match.group(1))
    plastic_volume = float(plastic_volume_match.group(1))
    plastic_weight = float(plastic_weight_match.group(1))
    material_cost = float(material_cost_match.group(1))

    return build_time, filament_length, plastic_volume, plastic_weight, material_cost

def parse_bgcode_string(input_string):
    # Regular expressions to match different types of data
    filament_length_pattern = r'filament used \[mm\]=(\d+\.\d+)'
    plastic_volume_pattern = r'filament used \[cm3\]=(\d+\.\d+)'
    plastic_weight_pattern = r'filament used \[g\]=(\d+\.\d+)'
    material_cost_pattern = r'filament cost=(\d+\.\d+)'

    # Extracting data using regular expressions
    filament_length_match = re.search(filament_length_pattern, input_string)
    plastic_volume_match = re.search(plastic_volume_pattern, input_string)
    plastic_weight_match = re.search(plastic_weight_pattern, input_string)
    material_cost_match = re.search(material_cost_pattern, input_string)

    # Extracted data
    filament_length = float(filament_length_match.group(1))
    plastic_volume = float(plastic_volume_match.group(1))
    plastic_weight = float(plastic_weight_match.group(1))
    material_cost = float(material_cost_match.group(1))

    # Calculate build time (placeholder, as it's not provided in the input)
    build_time = timedelta(hours=4, minutes=47)  # Placeholder build time

    # Format the output string
    output_string = f"Build time: {build_time.days} days {build_time.seconds // 3600} hours {(build_time.seconds // 60) % 60} minutes\n"
    output_string += f"Filament length: {filament_length} mm ({filament_length / 1000:.2f} m)\n"
    output_string += f"Plastic volume: {plastic_volume} mm^3 ({plastic_volume / 1000:.2f} cc)\n"
    output_string += f"Plastic weight: {plastic_weight} g ({plastic_weight / 454:.2f} lb)\n"
    output_string += f"Material cost: {material_cost}\n"

    return output_string


#Extract last 5 lines from .gcode file
def extract_gcode(file_name):
    with open(file_name, "r") as file:
        lines = file.readlines()
        last_lines = lines[-5:]
        # Remove semicolon and leading whitespace from each line
        last_lines = [line.strip().lstrip('; ') for line in last_lines]
        # Format each line with parameter: value
        formatted_message = '\n'.join(last_line.strip() for last_line in last_lines)
        return formatted_message

#Extracts lines 14-19 from .bgcode file
def extract_bgcode(file_name):
    with open(file_name, "r", encoding="iso-8859-1") as file:
        lines = file.readlines()
        last_lines = lines[13:19]
        # Remove semicolon and leading whitespace from each line
        last_lines = [line.strip().lstrip('; ') for line in last_lines]
        # Format each line with parameter: value
        formatted_message = '\n'.join(last_line.strip() for last_line in last_lines)
        return formatted_message




# Function to get .csv file
async def get_csv():
    try:
        print_jobs = pd.read_csv("print_jobs.csv")
        logging.debug(".csv - File found")
    except FileNotFoundError:
        print_jobs = pd.DataFrame(columns=["job_id", "thread_id", "user","ta", "starttime", "endtime", "failed", "status", "time", "weight", "length", "volume", "cost"])
        print_jobs.to_csv("print_jobs.csv", index=False)
        logging.debug(".csv - File created")
    return print_jobs



# !start command
@bot.command()
async def start(ctx):
    # Ensure command was invoked in a thread
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads.")
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
    # Ensure command was invoked in a thread
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads.")
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
    # Check if the command was invoked in a thread
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads.")
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
            in_progress_jobs.append(print_job)

    # Convert all items in print_jobs to strings
    in_progress_jobs = [str(item) for item in in_progress_jobs]
        
    # Send the print jobs
    if in_progress_jobs:
        await ctx.send("Number of waiting jobs:" + len(in_progress_jobs))
        await ctx.send("\n".join(in_progress_jobs))
    else:
        await ctx.send("No waiting print jobs.")

    # Send the .csv file
    with open("print_jobs.csv", "r") as file:
        await ctx.send(file=discord.File(file, "print_jobs.csv"))


    
# Bot online
@bot.event
async def on_ready():
    channel = bot.get_channel(GENERAL_CHANNEL_ID)
    await channel.send("Bot is online")

# Bot offline
@bot.event
async def on_disconnect():
    channel = bot.get_channel(GENERAL_CHANNEL_ID)
    await channel.send("Bot is online")


# Update the on_message function
@bot.event
async def on_message(message):
    if message.author == bot.user:
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
            await dm_channel.send("Submitting files to TAs for review")

            # Save the files to the local directory, ** non-essential part of code
            stl_content = await stl_file.read()
            gcode_content = await gcode_file.read()
            async with aiofiles.open(stl_file.filename, "wb") as stl_out_file:
                await stl_out_file.write(stl_content)
            async with aiofiles.open(gcode_file.filename, "wb") as gcode_out_file:
                await gcode_out_file.write(gcode_content)

            stl_file = discord.File(stl_file.filename)
            gcode_file = discord.File(gcode_file.filename)

            channel = bot.get_channel(TA_CHANNEL_ID)
            
            #If file is gcode file and if it is a .gcode file, extract the last 5 lines
            if gcode_file.filename.endswith(".gcode"):
                message_content = f"{user.name}'s files for review:" + "\n" + "\n" + (extract_gcode(gcode_file.filename))
                string = parse_gcode_string(message_content)
            #If file is gcode file and if it is a .bgcode file, extract lines 13-18
            elif gcode_file.filename.endswith(".bgcode"):
                message_content = f"{user.name}'s files for review:" + "\n" + "\n" + (extract_bgcode(gcode_file.filename))
                string = parse_bgcode_string(message_content)

            # Create a list to store all the files
            files = [stl_file, gcode_file]

            # Send the image files to the channel and add them to the files list
            for image_file in image_files:
                image_content = await image_file.read()
                async with aiofiles.open(image_file.filename, "wb") as image_out_file:
                    await image_out_file.write(image_content)
                image_file = discord.File(image_file.filename)
                files.append(image_file)

            # Send all the files together as one message object
            sent_message = await channel.send(message_content, files=files)

            # Create a thread named after the first file's name (everything before period)
            thread = await sent_message.create_thread(name=stl_file.filename.split('.')[0])
            await thread.send("Thread created")  # Add a message in the thread

            # Add the print job to the .csv file
            time = string(message_content)[0]
            length = string(message_content)[1]
            volume = string(message_content)[2]
            weight = string(message_content)[3]
            cost = string(message_content)[4]
            # Add line to the print job using the pandas library and without load_printjobs_ function
            print_jobs = await get_csv()
            new_row = {"job_id": len(print_jobs) + 1, "thread_id": thread.id, "user": user.name, "ta": "", "starttime": "", "endtime": "", "failed": False, "status": "waiting", "time": time, "weight": weight, "length": length, "volume": volume, "cost": cost}
            print_jobs.loc[len(print_jobs)] = new_row
            print_jobs.to_csv("print_jobs.csv", index=False)
            logging.debug("Print job added to .csv file")

        else:
            missing_files = []
            if not stl_file:
                missing_files.append(".stl or .3mf")
            if not gcode_file:
                missing_files.append(".gcode or .bgcode")
            if not image_files:
                missing_files.extend([".png or .jpg or .jpeg"])

            # Message the channel
            missing_files_str = '\n'.join(missing_files)
            await message.channel.send(f"Hi {message.author}! Please re-send your files. I'm missing {len(missing_files)} files:\n{missing_files_str}")




    await bot.process_commands(message)


@bot.command()
async def help(ctx):
    # Your custom help message here
    message_one = "!start - Start a print job\n!fail - Fail a print job\n!complete - Complete a print job\n!list - List all print jobs in progress"

    message_two = """.csv Details:
    job_id - Unique job id
    thread_id - Unique thread id to specific print
    user - Discord username of student who sent in print
    ta - Discord username of TA who entered in last command in thread
    starttime - Time of last !start command in thread (Overrides if multiple !start commands)
    endtime - Time of last !complete command in thread
    failed - If the print has been failed at least once (Cannot be overridden once true)
    status - Current status of print (waiting, started, failed, complete)
    time/weight/length/volume/cost - Metrics of print pulled from .gcode/.bgcode file"""


    await ctx.send("Commands:\nmessage_one + " + "\n" + message_two)

# Start the bot
bot.run(BOT_TOKEN)


#If completed do we want to be able to start the print back up again?
#Maybe check to see the functionality of this when conecting it to a JSON file



