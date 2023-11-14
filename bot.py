"""
To do:

Add shoe command for memes
"""

import discord
from discord.ext import commands, tasks
import csv
import pandas as pd
import numpy as np
import datetime
import matplotlib
import calplot
from table2ascii import table2ascii # to print out an ascii table in discord
import os # to create empty folders for users

""" Bot Info/Prelim. Commands"""
specified_token = '' # add a token in here if you wish to override the default token
if specified_token:
    TOKEN = specified_token
else:
    TOKEN = os.environ['DISCORD_GYM_BOT_TOKEN'] # use the default token

description = "Gym Scheduler Bot"
client = commands.Bot(command_prefix="!", description=description, intents=discord.Intents.all())

""" Universal Functions
general rules: 
return -1 means a "failed" function. ie something prevented it from executing fully (eg player not in db etc)
return -2 means a logical reason why it shouldn't execute (eg trying to 
look up last visit when you haven't been yet)
"""

# generic "access_db" function. used in all functions that require querying the database
def access_db(query_type=None, id=None):

    df = pd.read_csv('Data/Gym_User_List.csv',index_col='discord_id')  # check the user list
    print(df)

    if query_type == 'searching': # eg for display_users(), user_specified(), add_visit & last_visit()
        if id is None:  # if no user is specified:
            return df # return the entire dataframe
        else: # if user specified
            try:
                filtered_data = df.loc[id]
                return filtered_data
            except:
                return -1 # user not found

    elif query_type == 'add_user':
        try:
            filtered_data = df.loc[id]
            return -1  # return -1 if the user is found - we shouldn't add them if the user is already there
        except:
            return df  # return the whole df if the user isn't found - will append to this later

    else: # query_type is None or something else
        print("Error- query_type not specified - check code")
        return

def extract_id(message, user_id):

    # split_message = message.split()
    # command = split_message[0] # not useful atm but maybe in the future
    # print(split_message)

    try: # test to see if an id was specified
        split_message = message.split()
        id_to_extract = split_message[1]
        # print(id_to_extract)
    except IndexError: # if no id is specified
        # print("No id specified.")
        return user_id # no id was specified, therefore default to the id of the player who used the command

    if id_to_extract[0] == "<": # if they're pinging someone
        other_id = id_to_extract.split("@")[1] # not quite properly trimmed
        other_id = int(other_id[:len(other_id) - 1])  # fully trimmed, converted to an integer
    else: # if the user was not pinged (only the id was specified)
        other_id = int(id_to_extract)

    return other_id

def display_users(): # shows all current user data in a table 

    df = access_db('searching') # query the data, return a dataframe
    df.reset_index(inplace=True) # reset the index because access_db returns the df with discord_id as the index
    df_rearranged = df.loc[:, ["name", "discord_id", "gym_visits", "time_added"]]

    df_lists = df_rearranged.values.tolist() # makes each row into a list, and puts each list into a a list of lists

    for list in df_lists:
        list[3] = list[3][:10] # reducing each date string to yyyy-mm-dd

    """ ascii table that will be printed """
    data_table = table2ascii(
        header=['Name', 'Discord ID', 'Gym Visits', 'Tracked Since'],
        body=df_lists
    )

    return data_table

""" idk if i need this - could just use display_users()"""
def lookup_user(id, query_type, username): # data for a single user

    df = access_db('searching', id)
    print(f"User id: {id}")
    print("df returned:\n\n\n")
    print(df)
    
    try:
        df += 1 # if df returned -1, this will work, and hence indicate the user is already there
        if query_type == 'self':
            return "You are not in the database! Use **!addme** to add yourself."
        else: # ie query_type = 'other_user'
            return f"{username} is not in the database! They need to use **!addme** to add themselves."

    except:
        gym_visits = df.loc['gym_visits']

        if gym_visits > 2:
            if query_type == 'self':
                return f"You have been to the gym {gym_visits} times."
            else: # ie if the query_type is 'other_user'
                return f"{username} has been to the gym {gym_visits} times."
        elif gym_visits == 0:
            if query_type == 'self':
                return "You haven't been to the gym yet!"
            else: # ie if the query_type is 'other_user'
                return f"{username} hasn't been to the gym!"
        elif gym_visits == 2:
            if query_type == 'self':
                return "You have been to the gym twice."
            else: # ie if the query_type is 'other_user'
                return f"{username} has been to the gym twice."
        elif gym_visits == 1:
            if query_type == 'self':
                return "You have been to the gym once."
            else: # ie if the query_type is 'other_user'
                return f"{username} has been to the gym once."            

def add_me(id,username): # adds the user to the db if they aren't there already

    df = access_db('add_user', id) # will return the entire dataframe, index_col = discord_id

    try:
        df += 1 # if df returned -1, this will work, and hence indicate the user is already there
        return "You are already in the database."
    except:
        # this will indicate it is actually a df, and hence the user needs to be added
        df.reset_index(inplace=True)  # reset index so discord_id becomes one of the columns again
        curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # current exact time, which will be added

    """ 1 - Add to user list """
    new_user_df = pd.DataFrame([[id,username,curr_time,0]],columns=['discord_id','name','time_added','gym_visits'])
    df_new = pd.concat([df, new_user_df], ignore_index=True)
    df_new.to_csv('Data/Gym_User_List.csv',index=None) # save changes in an updated csv

    """ 2 - Create dates file for the user """
    with open(f"Data/Dates/{id} dates.csv", 'w', newline='') as write_dates_file:
        csv_writer = csv.writer(write_dates_file)
        csv_writer.writerow(["date"])

    return f"{username} added! Thanks <@{id}>."

def add_visit(id): # adds a sesh for the user

    df = access_db('searching') # will return the entire dataframe, index_col = discord_id
    print(f"User id: {id}")
    print("df returned:\n\n\n")
    print(df)

    try:
        """ 1 - Increment gym_visits in user list """
        df.loc[id, 'gym_visits'] += 1 # find the id by the discord_id (index) & increment the sesh count
        sessions = df.loc[id, 'gym_visits']
    except:
        # this will indicate it is not a df, and hence it should return an error message
        return "You are not in the database! Use **!addme** to add yourself."
    else:
        df.reset_index(inplace=True)  # reset index so discord_id becomes one of the columns again
        df.to_csv('Data/Gym_User_List.csv', index=None)  # save changes in an updated csv

        """ 2 - Add sesh date to dates file """
        curr_date = str(datetime.date.today()) # date in the format yyyy-mm-dd
        with open(f"Data/Dates/{id} dates.csv", 'a', newline='') as write_dates_file:
            csv_writer = csv.writer(write_dates_file)
            csv_writer.writerow([curr_date])

        if sessions > 2:
            return f"Session added! Thanks <@{id}>. You have now been to the gym {sessions} times."
        elif sessions == 2:
            return f"Session added! Thanks <@{id}>. You have now been to the gym twice."
        elif sessions == 1:
            return f"Session added! Thanks <@{id}>. You have now been to the gym once."
        else: # ie if 0 or not a number
            return "Uh, slight error. Ask Finah to fix me. :("

def last_visit(id, query_type, username): # says when the user last went to the gym (either self or specified user)
    
    df = access_db('searching', id)
    
    try:
        df += 1 # if df returned -1, this will work, and hence indicate the user is already there
        if query_type == 'self':
            return "You are not in the database! Use **!addme** to add yourself."
        else: # ie query_type = 'other_user'
            return f"{username} is not in the database! They need to use **!addme** to add themselves."

    except:
        # checking the dates file to find the last visit date"""
        #         
        gym_visits = df.loc['gym_visits']

        if gym_visits == 0:
            if query_type == 'self':
                return "You haven't been to the gym yet!"
            else: # ie if query_type = 'other_user'
                return f"{username}'s hasn't been to the gym yet!"

        else: # if gym_visits > 0
            with open(f"Data/Dates/{id} dates.csv", "r", encoding="utf-8", errors="ignore") as read_file:
                last_line = read_file.readlines()[-1] # should return a date
                if last_line != "date":
                    converted_date = datetime.datetime.strptime(last_line, "%Y-%m-%d\n") # convert date to the correct date format
                    readable_date = converted_date.strftime("%d %B %Y") # converting date object to string
                    if query_type == 'self':
                        return f"Your last gym visit was on {readable_date}."
                    else: # ie if query_type = 'other_user'
                        return f"{username}'s last gym visit was on {readable_date}"
                else: # if the last_line is date
                    if query_type == 'self':
                        return "You don't have any gym sesh dates recorded!"
                    else: # ie if query_type = 'other_user'
                        return f"{username}'s doesn't have any gym sesh dates recorded!"

def extract_dates(username, id): # extracts all the dates a user has been to the gym
        """ df is in the form ['name','time_added','gym_visits'] with index_col discord_id"""
        df = access_db('searching', id) # access the db for the specified user id

        start_date = df['time_added'] # date the user was added to the db
        start_date_dt64 = pd.to_datetime(start_date, format="%Y-%m-%d %H:%M:%S").to_numpy() # as a datetime64 object

        try:
            df += 1 # if df returned -1, this will work, and hence indicate the user is not there
            return -1
        except:
            # checking the dates file to find the last visit date"""

            with open(f"Data/Dates/{id} dates.csv", "r", encoding="utf-8", errors="ignore") as read_file:
                csv_reader = csv.reader(read_file)
                header = next(csv_reader) # skips the header

                # Check file as empty
                if header != None:
                    date_list = [] # will append to this
                    # Iterate over each row after the header in the csv
                    for row in csv_reader:
                        date_list.append(row)
                    # print(date_list)

                    # removing duplicate dates (so only max 1 per day for the calplot)
                    unique_dates_list = []
                    for date in date_list:
                        if date not in unique_dates_list:
                            unique_dates_list.append(date)
                    date_list = unique_dates_list

                    user_data = (username, date_list, start_date_dt64)
                    return user_data # tuple - will be used in the graph_data function
                else:
                    return -1 # error ting

def graph_data(graphing_type, username, id=None):

    extracted_dates = extract_dates(username, id)
        
    if extracted_dates == -1:
        if graphing_type == 'self':
            return "You are not in the database! Use **!addme** to add yourself."
        elif graphing_type == 'other_user':
            return f"{username} is not in the database. They will need to use **!addme** to add themselves!"

    else: # if extracted_dates is a date_list

        # setting a colourmap for the graphs -- red = no gym day, green = gym day
        colourmap = matplotlib.colors.ListedColormap(['red', 'green']) # colourmap when the person has attended the gym 2+ times
        """ I had to add this additional version below because the colormap was bugged when the person attended the gym on the same day they started"""
        colourmap_single = matplotlib.colors.ListedColormap(['green', 'red']) # colourmap when the person has attended the gym once

        (user_name, date_list, start_date_dt64) = extracted_dates # separating the output to 3 different variables
        date_list_fixed = [str(date).replace('[','').replace(']','').replace("'","") for date in date_list] # fixes the dates being lists etc

        # converting dates to np.datetime64 so they are compatible with the pd.date_range later
        date_list_dt64 = [pd.to_datetime(date, format="%Y-%m-%d").to_numpy() for date in date_list_fixed]

        curr_date = datetime.date.today() # current date as datetime object - used to name the graph file with the date it was made
        curr_date_dt64 = np.datetime64(curr_date) # current date as np.datetime64 object - used as the end date for the pd.date_range

        """ Normalising the start date """
        start_date_dt64 = pd.Timestamp(start_date_dt64) # convert to pd.Timestamp so I can normalise it
        start_date_dt64 = start_date_dt64.normalize() # normalise the datetime to midnight
        start_date_dt64 = np.datetime64(start_date_dt64) # convert back to np.datetime64 object

        # generates a list of dates with times set to 0:00:00 (24 hr incremements starting from a normalised start time)
        all_dates = pd.date_range(start=start_date_dt64, end=curr_date_dt64).to_list()

        """generating the series to use for the heatmap """
        # all dates in which the user went to the gym. assigned a value 1 so it appears on the heatmap
        # the dates are the index, the 1's are in the 'value' column
        events = pd.Series(1, index=date_list_dt64)

        # adding the extra dates in which the user did not attend the gym - assigning these values 0
        for date in all_dates:
            if date not in events.index: # if the date is not in the events Series
                events.at[date] = 0 # add it in and assign its value to 0

        events.sort_index(inplace=True) # sorting by index again [NOT NEEDED, but I'm OCD]
        print("full events list (and after sorted):")
        print(events)
    
        if events.size < 1: # ie no gym visits
            if graphing_type == 'self':
                return "You haven't been to the gym yet!"
            elif graphing_type == 'other_user':
                return f"{username} hasn't gone to the gym yet!"

        if events.size > 1: # if they have attended the gym 2+ times, use the relevant cmap
            fig, axes = calplot.calplot(events, cmap=colourmap, colorbar=False, dropzero=False, suptitle=f"{user_name}'s Gym Attendance", yearascending=True)

        else: # if they have attended the gym only once, use the other cmap
            fig, axes = calplot.calplot(events, cmap=colourmap_single, colorbar=False, dropzero=False, suptitle=f"{user_name}'s Gym Attendance", yearascending=True)

        """ creating the user directory in which to save the graph file """
        try:
            path = f'Data/Graphs/{id}'
            os.mkdir(path)
            # print(f"Directory {path} created.")
        except FileExistsError:
            # print(f"Directory {path} already exists.")
            pass

        """ creating and saving the file """
        file_path = f"Data/Graphs/{id}/{id} Attendance ({curr_date}).png"
        fig.savefig(file_path, bbox_inches='tight', pad_inches=0.3) # saves the figure to the Data/Graphs/{id} folder
    
        with open(file_path, 'rb') as image_file:
            picture = discord.File(image_file)

        return picture # discord picture file
    
""" ADMIN FUNCTIONS - accessed with !!! and only works if the user is me"""

def remove_user(): # removes a user from the db (has to be specified), probably needs a confirmation
    pass

def backup_data(): # backs up the current data
    pass

def fresh_data(): # creates a fresh data set. ideally should require a backup beforehand
    pass

""" Discord Bot Coroutines """

@client.event
async def on_ready(): # confirms that the bot is online
    print("We have logged in as {0.user}".format(client))

@client.event
async def on_message(message): # coroutine responsible for running commands based on user input

    """on_message user data"""
    server_id = message.guild.id
    server_name = message.guild.name
    username = str(message.author).split('#')[0] # discord username before the #0000 number
    user_id = message.author.id # unique discord ID of the user
    user_message = str(message.content) # content of the message
    channel = str(message.channel.name) # channel
    print(f"--- {server_name} --- {username}: {user_message} ({channel}) ---") # printed to the console

    if message.author == client.user: # ensuring the bot doesn't respond to itself
        return

    if user_message[0] != "!": # generally, commands require an !
        if "cle has claimed the souls of" in user_message or "dj-khaled-another-one-one-gif" in user_message:
            await message.channel.send("Thank you kind sir, Clay.")
        else:
            return
            
    if user_message[:4] =="!ban" and message.author.id == 542419880922578969:
        await message.channel.send("You ain't banning no one, fool <@542419880922578969>")

    # message data
    split_message = user_message.split() # message split into command + additional arguments (such as user id specified)
    print(split_message)
    user_command = split_message[0]

    try:
        other_arg = split_message[1]
    except:
        other_arg = None

    """ list of user text commands """

    if user_command.lower() == '!all':
        await message.channel.send(f"```{display_users()}```") # bot sends the ascii table in ```_``` so discord embeds it
        return

    elif user_command.lower() == '!sesh':
        await message.channel.send(add_visit(user_id))
        return

    elif user_command.lower() == '!addme':
        await message.channel.send(add_me(user_id,username))
        return

    elif user_command.lower() == '!graph':
        # extracting the id to query 
        lookup_id = extract_id(user_message, user_id)

        if lookup_id == user_id: # the user is querying their own id - graph of themselves
            output = graph_data('self',username,user_id)

            if type(output) != str and type(output) != int: # ie if the output is a discord picture file
                await message.channel.send(f"{username}'s Gym Attendance:")
                await message.channel.send(file=output)
            else:
                await message.channel.send(output)

        else: # else, graph the user specified
            user_specified = await client.fetch_user(lookup_id)
            lookup_name = user_specified.name # username of the person being looked up

            output = graph_data('other_user',lookup_name,lookup_id)

            if type(output) != str and type(output) != int: # ie if the output is a discord picture file
                await message.channel.send(f"{lookup_name}'s Gym Attendance:")
                await message.channel.send(file=output)
            else:
                await message.channel.send(output)

    elif user_command.lower() == '!lookup':
        # extracting the id to query 
        lookup_id = extract_id(user_message, user_id)

        if lookup_id == user_id: # the user is querying their own id - look themselves up
            await message.channel.send(lookup_user(user_id, 'self', username))

        else: # query the user specified
            user_specified = await client.fetch_user(lookup_id)
            lookup_name = user_specified.name # username of the person being looked up

            await message.channel.send(lookup_user(lookup_id, 'other_user', lookup_name))

    elif user_command.lower() == '!lastvisit':
        # extracting the id to query 
        lookup_id = extract_id(user_message, user_id)

        if lookup_id == user_id: # the user is querying their own id - check their own last visit
            await message.channel.send(last_visit(user_id, 'self', username))

        else: # query the user specified
            user_specified = await client.fetch_user(lookup_id)
            lookup_name = user_specified.name # username of the person being looked up

            await message.channel.send(last_visit(lookup_id, 'other_user', lookup_name))

    elif user_command.lower() == '!shoes':
        await message.channel.send("I may slightly have forgotten to implement a shoes command sorry guys!!!")

    # test function - DELETE AFTERWARDS
    elif user_command.lower() == '!!!extract':
        await message.channel.send(extract_id(user_message, user_id))

    elif user_message.lower() == "!helpme": # the 'help' command

        await message.channel.send("**List of commands:**\n\n"
                                   "**!addme** -- adds yourself to the database\n"
                                   "**!sesh** -- record a gym session for yourself in the database\n"
                                   "**!all** -- displays all user data\n"
                                   "**!graph** -- show your gym attendance on a calendar\n"
                                   "**!graph @person** -- show the specified person's gym attendance on a calendar\n"
                                   "**!lookup** -- look up how many times you have been to the gym\n"
                                   "**!lookup @person** -- look up how many times the specified person has gone to the gym\n"
                                   "**!lastvisit** -- look up when you last went to the gym\n"
                                   "**!lastvisit @person** -- look up the specified person's last visit to the gym\n")

    # list of ADMIN text commands

# @tasks.loop(seconds=2)
# async def test_schedule_func():
#     print("hi")

# @bot.command()
# async def repeat_thing():

client.run(TOKEN)
