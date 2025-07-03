import json

import orjson
import asyncio
import os
import sqlite3
import sys

import discord
import math
import random
import time

import pytz
import yt_dlp.utils

from datetime import datetime

# Import classes from our files
from Player import Player
from Servers import Servers
from Song import Song

asyncio_tasks = set()

def pront(content, lvl="DEBUG", end="\n") -> None:
    """
    A custom logging method that acts as a wrapper for print().

    Parameters
    ----------
    content : `any`
        The value to print.
    lvl : `str`, optional
        The level to raise the value at.
        Accepted values and their respective colors are as follows:

        LOG : None,
        DEBUG : Pink,
        OKBLUE : Blue,
        OKCYAN : Cyan,
        OKGREEN : Green,
        WARNING : Yellow,
        ERROR : Red,
        NONE : Resets ANSI color sequences
    end : `str` = `\\n` (optional)
        The character(s) to end the statement with, passes to print().
    """
    colors = {
        "LOG": "",
        "DEBUG": "\033[1;95m",
        "OKBLUE": "\033[94m",
        "OKCYAN": "\033[96m",
        "OKGREEN": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "NONE": "\033[0m"
    }
    # if type(content) != str and type(content) != int and type(content) != float:
    #    content = sep.join(content)
    print(colors[lvl] + "{" + datetime.now().strftime("%x %X") +
          "} " + lvl + ": " + str(content) + colors["NONE"], end=end)  # sep.join(list())


def create_json_snapshot(player: Player):
    # with open(rf"player_snapshot_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")}.json", "wb") as f:
    #     f.write(orjson.dumps(player, option=orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY))

    # TODO see status of queue, see queue emptying and retrieve voice client information
    # TODO list server's dictionary

    voice_data = [{
        "timestamp": {
            "POSIX_timestamp": datetime.now().timestamp(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "player": {
            "queue": player.queue.__str__(),
            "song_title": player.song.title,
            "song_elapsed_time": str(player.song.get_elapsed_time()),
            "server_dictionary": Servers.__dict__.__str__()
        }
    }]

    with open(f"snapshots/player_snapshot_{datetime.now().strftime('%%Y-%%m-%%d %%H%%M%%S')}.json", "w") as f:
        json.dump(voice_data, f, indent=4)


# makes a ascii song progress bar
def get_progress_bar(song: Song) -> str:
    """
    Creates an ASCII progress bar from a provided Song.
    
    This is calculated from a time delta counted within the song.

    Parameters
    ----------
    song : `Song`
        The Song object to create the progress bar from.
    
    Returns
    -------
    str
        A string containing a visual representation of how far the song has played.
    """
    # if the song is None or the song has been has not been started ( - 100000 is an arbitrary number)
    if song is None or song.get_elapsed_time() > time.time() - 100000 or song.duration is None:
        return ''
    percent_duration = (song.get_elapsed_time() / song.duration)*100

    if percent_duration > 100:#percent duration cant be greater than 100
        return 'The player has stalled, please run /force-reset-player.'

    ret = f'{song.parse_duration_short_hand(math.floor(song.get_elapsed_time()))}/{song.parse_duration_short_hand(song.duration)}'
    ret += f' [{(math.floor(percent_duration / 4) * "▬")}{">" if percent_duration < 100 else ""}{((math.floor((100 - percent_duration) / 4)) * " ")}]'
    return ret

@DeprecationWarning
def progress_bar(begin: int, end: int, current_val: int) -> str:
    """
    A deprecated method for producing progress bars that only requires integers
    """
    percent_duration = (current_val / end) * 100

    if percent_duration > 100:#percent duration cant be greater than 100
        percent_duration = 100

    ret = f'{current_val}/{end}'
    ret += f' [{(math.floor(percent_duration / 4) * "▬")}{">" if percent_duration < 100 else ""}{((math.floor((100 - percent_duration) / 4)) * "    ")}]'
    return ret

# Returns a random hex code
def get_random_hex(seed = None) -> int:
    """
    Returns a random hexidecimal color code.
    
    Parameters
    ----------
    seed : `int` | `float` | `str` | `bytes` | `bytearray` (optional)
        The seed to generate the color from.
        None or no argument seeds from current time or from an operating system specific randomness source if available.

    Returns
    -------
    int
        The integer representing the hexidecimal code.
    """
    random.seed(seed)
    return random.randint(0, 16777215)


# Creates a standard Embed object
def get_embed(interaction, title='', content='', url=None, color='', progress: bool = True) -> discord.Embed:
    """
    Quick and easy method to create a discord.Embed that allows for easier keeping of a consistent style

    TODO change the content parameter to be named description to allow it to align easier with the standard discord.Embed() constructor.

    Parameters
    ----------
    interaction : `discord.Interaction`
        The Interaction to draw author information from.
    title : `str` (optional)
        The title of the embed. Can only be up to 256 characters.
    content : `str` (optional)
        The description of the embed. Can only be up to 4096 characters.
    url : `str` | `None` (optional)
        The URL of the embed.
    color : `int` (optional)
        The color of the embed.
    progress : `bool` = `True` (optional)
        Whether get_embed should try to automatically add the progress bar and now-playing information.

    Returns
    -------
    discord.Embed
        The embed generated by the parameters.
    """
    if color == '':
        color = get_random_hex(interaction.user.id)
    embed = discord.Embed(
        title=title,
        description=content,
        url=url,
        color=color
    )
    embed.set_author(name=interaction.user.display_name,
                     icon_url=interaction.user.display_avatar.url)

    # If the calling method wants the status bar
    if progress:
        player = Servers.get_player(interaction.guild_id)
        if player and player.is_playing():

            embed.set_footer(text= f'{"🔂 " if player.looping else ""}{"🔁 " if player.queue_looping else ""}{"♾ " if player.true_looping else ""}',
                             icon_url=player.song.thumbnail)
    return embed


# Creates and sends an Embed message
async def send(interaction: discord.Interaction, title='', content='', url='', color='', ephemeral: bool = False, progress: bool = True) -> None:
    """
    A convenient method to send a get_embed generated by its parameters.

    Parameters
    ----------
    interaction : `discord.Interaction`
        The Interaction to draw author information from.
    title : `str` (optional)
        The title of the embed. Can only be up to 256 characters.
    content : `str` (optional)
        The description of the embed. Can only be up to 4096 characters.
    url : `str` | `None` (optional)
        The URL of the embed.
    color : `int` (optional)
        The color of the embed.
    progress : `bool` = `True` (optional)
        Whether get_embed should try to automatically add the progress bar and now-playing information.
    ephemeral : `bool` = `False` (optional)
    """
    embed = get_embed(interaction, title, content, url, color, progress)
    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


def get_now_playing_embed(player: Player, progress: bool = False) -> discord.Embed:
    """
    Gets an embed for a now-playing messge.
    Used for consistency and neatness.

    Parameters
    ----------
    player : `Player`
        The player to gather states, etc. from.
    progress : `bool`, `False`, optional
        Whether the embed should generate with a progress bar.

    Returns
    -------
    `discord.Embed`:
        The now-playing embed.

    """
    # If the player isn't currently playing something
    if not player.is_playing():
        return discord.Embed(title='Nothing is playing.')
    title_message = f'Now Playing:\t{":repeat_one: " if player.looping else ""}{":repeat: " if player.queue_looping else ""}{":infinity: " if player.true_looping else ""}'
    embed = discord.Embed(
        title=title_message,
        url=player.song.original_url,
        description=f'{player.song.title} -- {player.song.uploader}',
        color=get_random_hex(player.song.id)
    )
    embed.add_field(name='Duration:', value=player.song.parse_duration(
        player.song.duration), inline=True)
    embed.add_field(name='Requested by:', value=player.song.requester.mention)
    if progress:
        embed.add_field(name='Timestamp:', value=f"`{get_progress_bar(player.song)}`", inline=False)
    embed.set_image(url=player.song.thumbnail)
    embed.set_author(name=player.song.requester.display_name,
                     icon_url=player.song.requester.display_avatar.url)
    
    return embed

def populate_song_list(songs: list[Song], guild_id: int) -> None:
    """
    Creates a task to populate a list of songs in parallel.
    Is cognizant of a player and will halt itself in the event of its expiry.
    
    Parameters
    ----------
    songs : `list[Song]`
        The list of songs to iterate over.
    guild_id : `int`
        The id of the guild that the player to watch belongs to.
    """

    async def __primary_loop(songs: list[Song], guild_id: int) -> None:
        """
        Iterates over a list of Songs and populates them while checking if the Player they belong to still exists.
        
        Parameters
        ----------
        songs : `list[Song]`
            The list of songs to iterate over.
        guild_id : `int`
            The id of the guild that the player to watch belongs to.
        """
        for i in range(len(songs)):
            if Servers.get_player(guild_id) is None:
                return
            pront(f"populating {songs[i].title}")
            try:
                await songs[i].populate()
            except yt_dlp.utils.ExtractorError:
                pront('raised ExtractorError', 'ERROR')
            except yt_dlp.utils.DownloadError:
                pront('raised DownloadError', 'ERROR')
            songs[i] = None

    task = asyncio.create_task(__primary_loop(songs, guild_id))
    asyncio_tasks.add(task)
    task.add_done_callback(asyncio_tasks.discard)

async def force_reset_player(player: Player) -> None:
    """Forcibly restarts a player without losing any of the queue information contained within.
    
    Parameters
    ----------
    player : `Player`
        The player to restart.
    """
    await player.clean()
    player.vc = await player.vc.channel.connect(self_deaf=True)
    player = Player.from_player(player)
    # TODO i hate getting the guild id like this...
    Servers.set_player(player.vc.guild.id, player)

# Moved the logic for skip into here to be used by NowPlayingView and PlayerManagement
async def skip_logic(player: Player, interaction: discord.Interaction):
    """
    Performs all of the complex logic for permitting or denying skips.
    
    Placed here for use in both PlaybackManagement and NowPlayingView
    
    Parameters
    ----------
    player : `Player`
        The player the song belongs to.
    interaction : `discord.Interaction`
        The message Interaction.

    """
    # Get a complex embed for votes
    async def skip_msg(title: str = '', content: str = '', present_tense: bool = True, ephemeral: bool = False) -> None:

        embed = get_embed(interaction, title, content,
                          color=get_random_hex(player.song.id),
                          progress=present_tense)
        embed.set_thumbnail(url=player.song.thumbnail)

        users = ''
        for user in player.song.vote.get():
            users = f'{user.name}, {users}'
        users = users[:-2]
        if present_tense:
            # != 1 because if for whatever reason len(skip_vote) == 0 it will still make sense
            voter_message = f"User{'s who have' if len(player.song.vote) != 1 else ' who has'} voted to skip:"
            song_message = "Song being voted on:"
        else:
            voter_message = f"Vote passed by:"
            song_message = "Song that was voted on:"

        embed.add_field(name="Initiated by:",
                        value=player.song.vote.initiator.mention)
        embed.add_field(name=song_message,
                        value=player.song.title, inline=True)
        embed.add_field(name=voter_message, value=users, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # If there's not enough people for it to make sense to call a vote in the first place
    # or if this user has authority
    if len(player.vc.channel.members) <= 3 or Pretests.has_song_authority(interaction, player.song):
        player.vc.stop()
        await send(interaction, "Skipped!", ":white_check_mark:")
        return

    votes_required = len(player.vc.channel.members) // 2

    if player.song.vote is None:
        # Create new Vote
        player.song.create_vote(interaction.user)
        await skip_msg("Vote added.", f"{votes_required - len(player.song.vote)}/{votes_required} votes to skip.")
        return

    # If user has already voted to skip
    if interaction.user in player.song.vote.get():
        await skip_msg("You have already voted to skip!", ":octagonal_sign:", ephemeral=True)
        return

    # Add vote
    player.song.vote.add(interaction.user)

    # If vote succeeds
    if len(player.song.vote) >= votes_required:
        await skip_msg("Skip vote succeeded! :tada:", present_tense=False)
        player.song.vote = None
        player.vc.stop()
        return

    await skip_msg("Vote added.", f"{votes_required - len(player.song.vote)}/{votes_required} votes to skip.")


# Makes things more organized by being able to access Utils.Pretests.[name of pretest]
class Pretests:
    """
    A static class containing methods for pre-run state tests.

    ...

    Methods
    -------
    has_discretionary_authority(interaction: `discord.Interaction`):
        Checks if the interaction.user has discretionary authority in the current scenario.
    has_song_authority(interaction: `discord.Interaction`, song: `Song`):
        Checks if the interaction.user has authority over the given song.
    voice_channel(interaction: `discord.Interaction`):
        Checks if all voice channel states are correct.
    player_exists(interaction: `discord.Interaction`):
        Checks if there is a Player registered for the current guild and if voice channel states are correct.
    playing_audio(interaction: `discord.Interaction`):
        Checks if audio is playing in a player for that guild and voice channel states are correct.
    check_perms(interaction: `discord.Interaction`):
        Checks if the bot is set up with the correct permissions to function properly.
    update_libraries():
        Updates all libraries required to make the bot function correctly.
    """
    # To be used with control over the Player as a whole
    def has_discretionary_authority(interaction: discord.Interaction) -> bool:
        """
        Checks if the interaction.user has discretionary authority in the current scenario.
        
        Parameters
        ----------
        interaction : `discord.Interaction`
            The interaction to pull interaction.user from.

        Returns
        -------
        bool
            Whether the interaction.user should have discretionary authority.
        """

        if interaction.user.voice and len(interaction.user.voice.channel.members) <= 3:
            return True
        for role in interaction.user.roles:
            if role.name.lower() == 'dj':
                return True
            if role.permissions.manage_channels or role.permissions.administrator:
                return True
        # Force discretionary authority for developers
        if interaction.user.id == 369999044023549962 or interaction.user.id == 311659410109759488 or interaction.user.id == 670821194550870016:
            return True
        return False

    # To be used for control over a specific song
    def has_song_authority(interaction: discord.Interaction, song: Song) -> bool:
        """
        Checks if the interaction.user has authority over the given song.
        
        Parameters
        ----------
        interaction : `discord.Interaction`
            The interaction to pull interaction.user from.
        song : `Song`
            The song to compare interaction.user to.

        Returns
        -------
        bool
            Whether the interaction.user should have authority over the song.
        """
        if song.requester == interaction.user:
            return True

        return Pretests.has_discretionary_authority(interaction)

    # Checks if voice channel states are right
    async def voice_channel(interaction: discord.Interaction) -> bool:
        """
        Checks if all voice channel states are correct.

        Specifically, this checks if MaBalls is in a voice channel and if the person executing the command is in the same channel.
        
        Parameters
        ----------
        interaction : `discord.Interaction`
            The interaction to check and respond in.

        Returns
        -------
        bool
            Will return true in the event that all checks pass. Otherwise, Will return false in the event one or more
            checks fail, this will also use interaction.response to send a response to the message.
        """
        if interaction.guild.voice_client is None:
            await interaction.response.send_message("MaBalls is not in a voice channel", ephemeral=True)
            return False

        if interaction.user.voice.channel != interaction.guild.voice_client.channel:
            await interaction.response.send_message("You must be connected to the same voice channel as MaBalls", ephemeral=True)
            return False
        return True

    # Expanded test for if a Player exists
    async def player_exists(interaction: discord.Interaction) -> bool:
        """
        Checks if there is a Player registered for the current guild and if voice channel states are correct.

        Specifically, this checks if voice_channel returns True then checks if the Player exists for that guild.
        
        Parameters
        ----------
        interaction : `discord.Interaction`
            The interaction to check and respond in.

        Returns
        -------
        bool
            Will return true in the event that all checks pass. Otherwise, Will return false in the event one or more
            checks fail, this will also use interaction.response to send a response to the message.
        """
        if not await Pretests.voice_channel(interaction):
            return False
        if Servers.get_player(interaction.guild_id) is None:
            await interaction.response.send_message("This command can only be used while a queue exists", ephemeral=True)
            return False
        return True

    # Expanded test for if audio is currently playing from a Player
    async def playing_audio(interaction: discord.Interaction) -> bool:
        """
        Checks if audio is playing in a player for that guild and voice channel states are correct.

        Specifically, this checks if player_exists and subsequently voice_channel returns True then checks if player.is_playing is True.
        
        Parameters
        ----------
        interaction : `discord.Interaction`
            The interaction to check and respond in.

        Returns
        -------
        bool
            Will return true in the event that all checks pass. Otherwise, False will be returned in the event
            one or more checks fail, this will also use interaction.response to send a response to the message.
        """
        if not await Pretests.player_exists(interaction):
            return False
        if not Servers.get_player(interaction.guild_id).is_playing():
            await interaction.response.send_message("This command can only be used while a song is playing.")
            return False
        return True


    async def check_perms(interaction: discord.Interaction) -> str | None:
        """
        Checks if the bot is set up with the correct permissions to function properly.

        Returns any required permissions that are not set to True in a formatted string, returns None otherwise.

        Parameters
        ----------
        interaction : `discord.Interaction`
            The interaction to check and respond in.

        Returns
        -------
        permissions : str or None
            If any required permissions are not set, they will be returned as a formatted string.
            Otherwise, None will be returned
        """

        perms = interaction.channel.permissions_for(interaction.guild.me)

        # makeshift enum
        required = {
            "CONNECT": perms.connect,
            "SPEAK": perms.speak
        }

        # if one or more permissions are false, return the false permissions
        missing = [perm for perm, value in required.items() if not value]

        if len(missing) > 0:
            return ", ".join(missing)
        else:
            return None

    # FIXME unimplemented
    async def update_libraries(self: discord.Interaction = None) -> bool:
        """
        Event-based updating utility that requires linux to function, kills the bot and starts a new one in a new tmux session.

        Needs requirements.txt to function.

        Returns
        -------
        successful : bool
            False if unsuccessful
        """

        if os.name == 'nt':
            pront("Attempted to update libraries, this option is only available for linux operating systems", lvl="WARNING")
            return False

        try:
            db = sqlite3.connect('settings.db')
            cursor = db.cursor()

            cursor.execute("""
                SELECT update_day FROM Updates;
            """)

            update_day = cursor.fetchone()[0]
        except Exception as e:
            pront(e, lvl="ERROR")
            return False

        ### explanation pseudocode
        # play triggered
        # past 12 A.M.? update is due, day is set
        # play triggered again
        # still past 5 A.M. and same day? update is not due
        # play triggered again
        # past 12 A.M and next day? update is due, day is set

        d: datetime = datetime.now(pytz.timezone("America/New_York")) # set as EST

        if d.hour >= 0 and d.day != update_day:
            pront("Update detected, installing")
            update_day = datetime.today().day

            # create a new subprocess that runs the update, starts a new session then kills the bot
            p0 = await asyncio.create_subprocess_exec('python', '-m', 'pip', 'install', '-r', 'requirements.txt')
            await p0.wait()
            await launch_tmux_bot()

            try:
                cursor.execute(f"""
                        UPDATE Updates SET update_day = {update_day}
                """)
                db.commit()
            except sqlite3.OperationalError as e:
                pront(e, lvl="ERROR")
                return False
            finally:
                db.close()

            pront("Update successful, this bot session will be terminated. \nA new tmux session has been created under the name of SlashDiscordMusicBot", lvl="OKBLUE")
            sys.exit(0) # kill the bot and let the new session take over
        else:
            db.close()
            pront("No updates detected, skipping")
            return False


    # temporary solution to required yt-dlp updates, unimplemented
    async def update_libraries_yt_dlp(self: discord.Interaction = None) -> int:
        """
                Event-based updating utility for yt-dlp.

                Returns
                -------
                successful : bool
                    False if unsuccessful
        """

        try:
            db = sqlite3.connect('settings.db')
            cursor = db.cursor()

            cursor.execute("""
                SELECT update_day FROM Updates;
            """)

            update_day = cursor.fetchone()[0]
        except Exception as e:
            pront(e, lvl="ERROR")
            return 0

        d: datetime = datetime.now(pytz.timezone("America/New_York"))  # set as EST

        if d.hour >= 0 and d.day != update_day:
            pront("Update detected, installing")
            update_day = datetime.today().day

            p0 = await asyncio.create_subprocess_exec('.venv/Scripts/python', '-m', 'pip', 'install', '--upgrade', 'pip', 'yt-dlp')
            await p0.wait()

            try:
                cursor.execute(f"""
                                UPDATE Updates SET update_day = {update_day}
                        """)
                db.commit()
            except sqlite3.OperationalError as e:
                pront(e, lvl="ERROR")
                return 0
            finally:
                db.close()

            pront("Update successful", lvl="OKBLUE")
            return 1 # success, notify
        else:
            db.close()
            pront("No updates detected, skipping")
            return -1 # success, ignore

        # d: datetime = datetime.now(pytz.timezone("America/New_York"))  # set as EST
        #
        # try:
        #     db = sqlite3.connect('settings.db')
        #     cursor = db.cursor()
        #
        #     cursor.execute("""
        #         SELECT update_day FROM Updates;
        #     """)
        #
        #     update_day = cursor.fetchone()[0]
        # except Exception as e:
        #     pront(e, lvl="ERROR")
        #     return False
        #
        # if d.hour >= 0 and d.day != update_day:
        #     p0 = await asyncio.create_subprocess_exec('python', '-m', 'pip', 'install', '--upgrade', 'yt-dlp')
        #     await p0.wait()
        #
        #     if p0.returncode != 0:
        #         pront("YT-DLP update error code " + str(p0.returncode), lvl="ERROR")
        #         return False


async def launch_tmux_bot():
    session_name = "SlashDiscordMusicBot"
    cwd = os.getcwd() # current working directory
    shell_command = (
        f'cd {cwd} && '
        f'python3 -m venv venv && '
        f'source venv/bin/activate && '
        f'pip install --upgrade pip && '
        f'python3 musS_D.py'
    )

    # Kill the tmux session if it already exists
    await asyncio.create_subprocess_exec(
        'tmux', 'kill-session', '-t', session_name,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

    try:
        await asyncio.create_subprocess_exec(
            'tmux', 'new-session', '-d', '-s', session_name, shell_command
        )
    except Exception as e:
        pront(e, lvl="ERROR")