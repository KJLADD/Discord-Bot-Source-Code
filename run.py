import discord
from discord.ext import commands
import random
import asyncio
import json
import datetime
import aiohttp
import requests
import logging
if not discord.opus.is_loaded():
 from .utils import config
from .utils import checks
import re
import pendulum
import rethinkdb as r

client = discord.client()
client_prefix= "b:"
client = commands.client(command_prefix=client_prefix)

@client.event
async def on_ready():
    print("Bolt is online!")
    print('Bolt is connected to '+str(len(client.servers))+' servers')
    #Extra 1
    await client.change_presence(game=discord.Game(name='b:help | '+str(len(client.servers))+' servers'))

# - General Commands 

#generalcommand
@client.command(pass_context = True)
async def serverinfo(ctx):
 server = ctx.message.server
roles = [x.name for x in server.role_hierarchy]
role_length = len(roles)

if role_length > 50: 
    roles = roles[:50]
    roles.append('>>>> [50/%s] Roles'%len(roles))

roles = ', '.join(roles);
channelz = len(server.channels);
time = str(server.created_at); time = time.split(' '); time= time[0];

join = discord.Embed(description= '%s '%(str(server)),title = 'Server Name', colour = 0xFFFF);
join.set_thumbnail(url = server.icon_url);
join.add_field(name = '__Owner__', value = str(server.owner) + '\n' + server.owner.id);
join.add_field(name = '__ID__', value = str(server.id))
join.add_field(name = '__Member Count__', value = str(server.member_count));
join.add_field(name = '__Text/Voice Channels__', value = str(channelz));
join.add_field(name = '__Roles (%s)__'%str(role_length), value = roles);
join.set_footer(text ='Created: %s'%time);

#generalcommand
@client.command()
async def ping(ctx):
 client.send('Pong! :ping_pong: {0}'.format(round(client.latency, 1))

#generalcommand
@client.command()
async def uptime(ctx):
  client.wait_until_ready()
    global seconds seconds = 0
    global minutes minutes = 0
    global hours hours = 0
    global days days = 0
    global weeks weeks = 0
    while not client.is_closed: await asyncio.sleep(1) seconds += 1 if seconds==60: minutes += 1 seconds = 0 if minutes==60: hours += 1 minutes = 0 if hours==24: days += 1 hours = 0 if days==7: weeks += 1 days = 0

client.loop.create_task(get_uptime())
         
#generalcommand
@client.command(pass_context = True)
async def serverlists(ctx):
    x = '\n'.join([str(server) for server in client.servers])
    embed = discord.Embed(title = "Servers", description = x, color = 0xFFFFF)
    return await client.say(embed = embed)
                          
#generalcommand
@client.command(pass_context = True)
async def clientinfo(ctx):
    y =  "Connected to "+str(len(client.servers))+" servers. | The client invitation link is **https://discordapp.com/oauth2/authorize?client_id=421737816574132234&scope=client&permissions=536345743**. The server invitation link is https://discord.gg/Kckvz5H ." 
    embed = discord.Embed(title = "client information:", description = y, color = 0xFFFFF)
    return await client.say(embed = embed)


#generalcommand
@client.command()
async def roll(dice : str):
    """Rolls a dice in NdN format."""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await client.say('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await client.say(result)

#generalcommand
@client.command(pass_context = True)
async def say(ctx, *args):
    if ctx.message.author.server_permissions.mention_everyone or ctx.message.author.id == '227884796066529281':
      mesg = ' '.join(args)
      await client.delete_message(ctx.message)
      return await client.say(mesg)

# - Moderation Commands

#moderationcommand
@client.command(pass_context = True)
async def getbans(ctx):
    if ctx.message.author.server_permissions.mention_everyone or ctx.message.author.id == '227884796066529281':
    x = await client.get_bans(ctx.message.server)
    x = '\n'.join([y.name for y in x])
    embed = discord.Embed(title = "List of banned members", description = x, color = 0xFFFFF)
    return await client.say(embed = embed)

#moderationcommand
@client.command(pass_context = True)
async def ban(ctx, *, member : discord.Member = None):
    if not ctx.message.author.server_permissions.ban_members:
        return

    if not member:
        return await client.say(ctx.message.author.mention + " Specify a user to ban!")
    try:
        await client.ban(member)
    except Exception as e:
        if 'Privilege is too low' in str(e):
            return await client.say(":x: Denied! Your permissions are too low. :x:")

    embed = discord.Embed(description = "**%s** has been banned!"%member.name, color = 0xFF0000)
    return await client.say(embed = embed)

#moderationcommand
@client.command(pass_context = True)
async def unban(ctx, *, member : discord.Member = None):
    if not ctx.message.author.server_permissions.ban_members:
        return

    if not member:
        return await client.say(ctx.message.author.mention + " Specify a user to unban!")
    try:
        await client.unban(member)
    except Exception as e:
        if 'Privilege is too low' in str(e):
            return await client.say(":x: Denied! Your permissions are too low. :x:")

    embed = discord.Embed(description = "**%s** has been unbanned!"%member.name, color = 0xFF0000)
    return await client.say(embed = embed)

#moderationcommand
@client.command(pass_context = True)
async def kick(ctx, *, member : discord.Member = None):
    if not ctx.message.author.server_permissions.kick_members or ctx.message.author.id == '227884796066529281':
        return

    if not member:
        return await client.say(ctx.message.author.mention + " Specify a user to kick!")
    try:
        await client.kick(member)
    except Exception as e:
        if 'Privilege is too low' in str(e):
            return await client.say(":x: Denied! Your permissions are too low. :x:")

    embed = discord.Embed(description = "**%s** has been kicked!"%member.name, color = 0xFF0000)
    return await client.say(embed = embed)

#moderationcommand
@client.command(pass_context = True)
async def mute(ctx, member: discord.Member):
     if ctx.message.author.server_permissions.manage_messages or ctx.message.author.id == '227884796066529281':
        role = discord.utils.get(member.server.roles, name='Muted')
        await client.add_roles(member, role)
        embed=discord.Embed(title="User muted!", description="**{0}** was muted by **{1}**!".format(member, ctx.message.author), color=0xff00f6)
        await client.say(embed=embed)
     else:
        embed=discord.Embed(title=":x: Denied! Your permissions are too low. :x:", description=":x: You don't have permission to use this command.", color=0xff00f6)
        await client.say(embed=embed)

#moderationcommand
@client.command(pass_context = True)
async def unmute(ctx, member: discord.Member):
     if ctx.message.author.server_permissions.manage_messages or ctx.message.author.id == '227884796066529281':
        role = discord.utils.get(member.server.roles, name='Muted')
        await client.remove_roles(member, role)
        embed=discord.Embed(title="User unmuted!", description="**{0}** was unmuted by **{1}**!".format(member, ctx.message.author), color=0xff00f6)
        await client.say(embed=embed)
     else:
        embed=discord.Embed(title="Permission denied.", description=":x: You don't have permission to use this command.", color=0xff00f6)
        await client.say(embed=embed)



# - POLL SYSTEM
def setup(client):
    client.add_cog(Strawpoll(client))


getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```', re.DOTALL)


class Strawpoll:
    """This class is used to create new strawpoll """

    def __init__(self, client):
        self.client = client
        self.url = 'https://strawpoll.me/api/v2/polls'
        # In this class we'll only be sending POST requests when creating a poll
        # Strawpoll requires the content-type, so just add that to the default headers
        self.headers = {'User-Agent': 'Bonfire/1.0.0',
                        'Content-Type': 'application/json'}
        self.session = aiohttp.clientSession()

    @commands.group(aliases=['strawpoll', 'poll', 'polls'], pass_context=True, invoke_without_command=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def strawpolls(self, ctx, poll_id: str = None):
        """This command can be used to show a strawpoll setup on this server
        EXAMPLE: !strawpolls
        RESULT: A list of all polls setup on this server"""
        # Strawpolls cannot be 'deleted' so to handle whether a poll is running or not on a server
        # Just save the poll, which can then be removed when it should not be "running" anymore
        polls = await config.get_content('strawpolls', ctx.message.server.id)
        # Check if there are any polls setup on this server
        try:
            polls = polls[0]['polls']
        except TypeError:
            await self.client.say("There are currently no strawpolls running on this server!")
            return
        # Print all polls on this server if poll_id was not provided
        if poll_id is None:
            fmt = "\n".join(
                "{}: https://strawpoll.me/{}".format(data['title'], data['poll_id']) for data in polls)
            await self.client.say("```\n{}```".format(fmt))
        else:
            # Since strawpoll should never allow us to have more than one poll with the same ID
            # It's safe to assume there's only one result
            try:
                poll = [p for p in polls if p['poll_id'] == poll_id][0]
            except IndexError:
                await self.client.say("That poll does not exist on this server!")
                return

            async with self.session.get("{}/{}".format(self.url, poll_id),
                                        headers={'User-Agent': 'Bonfire/1.0.0'}) as response:
                data = await response.json()

            # The response for votes and options is provided as two separate lists
            # We are enumarting the list of options, to print r (the option)
            # And the votes to match it, based on the index of the option
            # The rest is simple formatting
            fmt_options = "\n\t".join(
                "{}: {}".format(result, data['votes'][i]) for i, result in enumerate(data['options']))
            author = discord.utils.get(ctx.message.server.members, id=poll['author'])
            created_ago = (pendulum.utcnow() - pendulum.parse(poll['date'])).in_words()
            link = "https://strawpoll.me/{}".format(poll_id)
            fmt = "Link: {}\nTitle: {}\nAuthor: {}\nCreated: {} ago\nOptions:\n\t{}".format(link, data['title'],
                                                                                            author.display_name,
                                                                                            created_ago, fmt_options)
            await self.client.say("```\n{}```".format(fmt))

    @strawpolls.command(name='create', aliases=['setup', 'add'], pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def create_strawpoll(self, ctx, title, *, options):
        """This command is used to setup a new strawpoll
        The format needs to be: poll create "title here" all options here
        Options need to be separated by using either one ` around each option
        Or use a code block (3 ` around the options), each option on it's own line"""
        # The following should use regex to search for the options inside of the two types of code blocks with `
        # We're using this instead of other things, to allow most used puncation inside the options
        match_single = getter.findall(options)
        match_multi = multi.findall(options)
        # Since match_single is already going to be a list, we just set
        # The options to match_single and remove any blank entries
        if match_single:
            options = match_single
            options = [option for option in options if option]
        # Otherwise, options need to be set based on the list, split by lines.
        # Then remove blank entries like the last one
        elif match_multi:
            options = match_multi[0].splitlines()
            options = [option for option in options if option]
        # If neither is found, then error out and let them know to use the help command, since this one is a bit finicky
        else:
            await self.client.say(
                "Please provide options for a new strawpoll! Use {}help {} if you do not know the format".format(
                    ctx.prefix, ctx.command.qualified_name))
            return
        # Make the post request to strawpoll, creating the poll, and returning the ID
        # The ID is all we really need from the returned data, as the rest we already sent/are not going to use ever
        payload = {'title': title,
                   'options': options}
        try:
            async with self.session.post(self.url, data=json.dumps(payload), headers=self.headers) as response:
                data = await response.json()
        except json.JSONDecodeError:
            await self.client.say("Sorry, I couldn't connect to strawpoll at the moment. Please try again later")
            return

        # Save this strawpoll in the list of running strawpolls for a server
        poll_id = str(data['id'])

        r_filter = {'server_id': ctx.message.server.id}
        sub_entry = {'poll_id': poll_id,
                     'author': ctx.message.author.id,
                     'date': str(pendulum.utcnow()),
                     'title': title}

        entry = {'server_id': ctx.message.server.id,
                 'polls': [sub_entry]}
        update = {'polls': r.row['polls'].append(sub_entry)}
        if not await config.update_content('strawpolls', update, r_filter):
            await config.add_content('strawpolls', entry, {'poll_id': poll_id})
        await self.client.say("Link for your new strawpoll: https://strawpoll.me/{}".format(poll_id))

    @strawpolls.command(name='delete', aliases=['remove', 'stop'], pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def remove_strawpoll(self, ctx, poll_id):
        """This command can be used to delete one of the existing strawpolls
        EXAMPLE: !strawpoll remove 5
        RESULT: No more strawpoll 5~"""
        r_filter = {'server_id': ctx.message.server.id}
        content = await config.get_content('strawpolls', r_filter)
        try:
            content = content[0]['polls']
        except TypeError:
            await self.client.say("There are no strawpolls setup on this server!")
            return

        polls = [poll for poll in content if poll['poll_id'] != poll_id]

        update = {'polls': polls}
        # Try to remove the poll based on the ID, if it doesn't exist, this will return false
        if await config.update_content('strawpolls', update, r_filter):
            await self.client.say("I have just removed the poll with the ID {}".format(poll_id))
        else:
            await self.client.say("There is no poll setup with that ID!")
             
client.run('NDIxNzM3ODE2NTc0MTMyMjM0.DYhMgQ.OTnE5TrxUg9jcu4BxR-AhgUeni4');
