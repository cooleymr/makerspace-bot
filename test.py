# This example requires the 'message_content' intent.
import discord
import aiofiles  # to read .stl file
from discord.ext import commands
import json
from datetime import datetime

BOT_TOKEN = "MTIwMDU2NTQwMjQ4OTU5MzkyNg.GsnSRG.SEEZqj5L3ybP6hVa5BFKrLnvZ0MKHx43Hx1G6I"
CHANNEL_ID = 1201630193060696115

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(),receive_messages=True)


@bot.event
async def on_ready():
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Hello World")



#Function to extract last 5 lines from .gcode file
def extract_gcode(file_name):
    with open(file_name, "r") as file:
        lines = file.readlines()
        last_lines = lines[-5:]
        # Remove semicolon and leading whitespace from each line
        last_lines = [line.strip().lstrip('; ') for line in last_lines]
        # Format each line with parameter: value
        formatted_message = '\n'.join(last_line.strip() for last_line in last_lines)
        return formatted_message

#Function to extract lines 13-18 from .mgcode file
def extract_gmcode(file_name):
    with open(file_name, "r") as file:
        lines = file.readlines()
        last_lines = lines[13:18]
        # Remove semicolon and leading whitespace from each line
        last_lines = [line.strip().lstrip('; ') for line in last_lines]
        # Format each line with parameter: value
        formatted_message = '\n'.join(last_line.strip() for last_line in last_lines)
        return formatted_message


    





# Load print job data from JSON file. Creating file if not found.
# Return the list of print j
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

# # Function to copy print job onto new print job
# def update_print_job(status, end_time, failed):
#     new_job = old_job.copy()
#     new_job['job_id'] = old_job['job_id'] + 1
#     new_job['status'] = "Started"
#     new_job['start_time'] = datetime.now().isoformat()
#     new_job['end_time'] = None
#     new_job['failed'] = False
#     return new_job


# Function to get a formatted list of print jobs
def get_print_job_list():
    print_jobs = load_print_jobs()
    job_list = []
    for job in print_jobs:
        job_list.append({
            "id": "job['job_id']",
            "user": job['user'], 
            "channel": job['channel'], 
            "status": job['status'],
            "start_time": job['start_time'],  
            "end_time": job['end_time'],  
            "failed": job['failed']  
        })
    return job_list

# # Function to update print job status
# UPDATE TO BE VERSATILE AND BE USED FOR FAIL AND COMPLETE 
# def update_print_job_status(user, status):
#     print_jobs = load_print_jobs()
#     for job in print_jobs:
#         if job['user'] == user:
#             job['status'] = status
#             break
#     save_print_jobs(print_jobs)



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

    # Add the print job to the JSON file
    print_jobs = load_print_jobs()
    print_jobs.append({
        "id": len(print_jobs) + 1,
        "user": user.name, 
        "status": "started",
        "start_time": datetime.now().isoformat(),  # Current time when the command is written
        "end_time": None,  # Empty end time
        "failed": False,  # Boolean indicating if the job failed
        "complete time": None,
        "build_time": None,
        "filament_length": None,
        "plastic_volume": None,
        "plastic_weight": None,
        "material_cost": None,
    })


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

    update_print_job_status(thread.name.split("-")[-1], "Failed")


# Function to handle the !list command
@bot.command()
async def list(ctx):
    job_list = get_print_job_list()

    # Convert all items in job_list to strings
    job_list = [str(item) for item in job_list]
    
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


    # print_jobs = load_print_jobs()
    # for job in print_jobs:
    #     thread = await channel.create_thread(name=f"Print Job {job['job_id']}")
    #     if job['status'] == "Started":
    #         await thread.send("Print job started")
    #     elif job['status'] == "Completed":
    #         await thread.send("Print job completed")


# Update the on_message function
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # If message contains a .stl, 3d print file(.gcode, .mgcode), image file(.png, .jpg, or .jpeg)file, read the file and send the content to new channel with specific channel id
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

        # If all required attachments are present, send them to the TA channel
        if stl_file and gcode_file and image_files:

            # Send a DM to the user that the files are being submitted
            user = message.author #Student who sent the files
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

            channel = bot.get_channel(1202485791247437856)
            message_content = f"{user.name}'s files for review:" + "\n" + "\n" + (extract_gcode(gcode_file.filename))

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


#If completed do we want to be able to start the print back up again?
#Maybe check to see the functionality of this when conecting it to a JSON file




# # Wait for messages in the thread
#             async for thread_message in thread.history():
#                 if thread_message.content == "!print":
#                     print("Print job started")
#                     # DM the original user that the print job has started
#                     await dm_channel.send("Your print job has now started")
#                     break



# # Function to handle the !complete command
# @bot.command()
# async def complete(ctx):
#     channel = ctx.channel
#     thread = channel.thread
#     if thread:
#         await thread.send("Print job completed")
#         job_id = int(thread.name.split("-")[-1])
#         update_print_job_status(job_id, "Completed")
#         await ctx.send(f"Print job {job_id} completed.")
#     else:
#         await ctx.send("This command can only be used in a thread.")
