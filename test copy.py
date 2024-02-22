# This example requires the 'message_content' intent.
import discord
import aiofiles  # to read .stl file
from discord.ext import commands
import json

BOT_TOKEN = 
# CHANNEL_ID = 1201630193060696115
CHANNEL_ID = 1197618503163842681

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(),receive_messages=True)


@bot.event
async def on_ready():
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello World")



#Function to extract last couple lines of code form a .gcode file
def extract_gcode(file_name):
    with open(file_name, "r") as file:
        lines = file.readlines()
        last_lines = lines[-5:]
        return last_lines    



# !start command
@bot.command()
async def start(ctx):
    # Check if the command was invoked in a thread
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads.")
        return
    
    # Check if a print job has already started or is not failed in the thread
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
    await dm_channel.send("Your print job has now started")
    await ctx.send("Print job started.")

    # Update the list of print jobs and save it to the JSON file
    print_jobs = load_print_jobs()
    print_jobs.append({"user": user.name, "channel": thread.name, "status": "started"})
    save_print_jobs(print_jobs)

    await ctx.send("Print job started.")

# !fail command
@bot.command()
async def fail(ctx):
    # Check if the command was invoked in a thread
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("This command can only be used inside threads.")
        return
    
    # Check if a print job has already failed or was started again in the thread
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




# Load print job data from JSON file. Creating file if not found.
def load_print_jobs():
    try:
        with open("print_jobs.json", "r") as file:
            print("print_jobs.json found")
            return json.load(file)
    except FileNotFoundError:
        with open("print_jobs.json", "w") as file:
            json.dump([], file)
            print("print_jobs.json not found, created print_jobs.json")
        return []

# Save print job data to JSON file
def save_print_jobs(print_jobs):
    with open("print_jobs.json", "w") as file:
        json.dump(print_jobs, file)

# Function to update print job data
def update_print_jobs(print_job):
    print_jobs = load_print_jobs()
    print_jobs.append(print_job)
    save_print_jobs(print_jobs)

# Function to get a formatted list of print jobs
def get_print_job_list():
    print_jobs = load_print_jobs()
    job_list = []
    for job in print_jobs:
        job_list.append(f"Job ID: {job['job_id']}, Status: {job['status']}")
    return job_list

# Function to get the next available job ID
def get_next_job_id():
    print_jobs = load_print_jobs()
    if print_jobs:
        return print_jobs[-1]['job_id'] + 1
    else:
        return 1

# Function to update print job status
def update_print_job_status(job_id, status):
    print_jobs = load_print_jobs()
    for job in print_jobs:
        if job['job_id'] == job_id:
            job['status'] = status
            break
    save_print_jobs(print_jobs)

# Function to handle the !list command
@bot.command()
async def list(ctx):
    job_list = get_print_job_list()
    if job_list:
        await ctx.send("Print Jobs:")
        await ctx.send("\n".join(job_list))
    else:
        await ctx.send("No print jobs found.")

    # Send the JSON file
    with open("print_jobs.json", "r") as file:
        await ctx.send(file=discord.File(file, "print_jobs.json"))




# Update the on_ready function
@bot.event
async def on_ready():
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello World")



# Update the on_message function
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # If message contains a .stl, .gcode, .png, .jpg, or .jpeg file, read the file and send the content to new channel with specific channel id
    if message.attachments:
        stl_file = None
        gcode_file = None
        image_files = []

        # Extracting .stl, .gcode, .png, .jpg, .jpeg files from the message
        for attachment in message.attachments:
            if attachment.filename.endswith(".stl"):
                stl_file = attachment
            elif attachment.filename.endswith(".gcode"):
                gcode_file = attachment
            elif attachment.filename.endswith((".png", ".jpg", ".jpeg")):
                image_files.append(attachment)

        # Check if all required files are present
        if stl_file and gcode_file and image_files:
            user = message.author #Student who sent the files
            dm_channel = await user.create_dm()
            await dm_channel.send("Submitting files to TAs for review")
            stl_content = await stl_file.read()
            gcode_content = await gcode_file.read()

            async with aiofiles.open(stl_file.filename, "wb") as stl_out_file:
                await stl_out_file.write(stl_content)
            async with aiofiles.open(gcode_file.filename, "wb") as gcode_out_file:
                await gcode_out_file.write(gcode_content)

            stl_file = discord.File(stl_file.filename)
            gcode_file = discord.File(gcode_file.filename)

            channel = bot.get_channel(1202485791247437856)
            message_content = f"{user.name}'s files for review:" + "\n" + "Build Details: " + "\n" + "\n".join(extract_gcode(gcode_file.filename))

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

            # Create a thread for the message
            thread = await sent_message.create_thread(name="Print Job")
            await thread.send("Thread created")  # Add a message in the thread

        else:
            missing_files = []
            if not stl_file:
                missing_files.append(".stl")
            if not gcode_file:
                missing_files.append(".gcode")
            if not image_files:
                missing_files.extend([".png", ".jpg", ".jpeg"])

            dm_channel = await user.create_dm()
            await dm_channel.send(f"You need to send the following file(s): {', '.join(missing_files)}")

    await bot.process_commands(message)


bot.run(BOT_TOKEN)