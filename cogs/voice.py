from discord.ext import commands
import discord
from gmusicapi import Mobileclient
import os
import asyncio
import threading
import urllib.request
import youtube_dl
import shutil
from collections import deque

gpmapi = Mobileclient(debug_logging=False)


class UrlDownloader(threading.Thread):
    """ Represents a url to be downloaded in a seperate thread """
    def __init__(self, url, file_location):
        threading.Thread.__init__(self)
        self.url = url
        self.file_location = file_location

    def run(self):
        urllib.request.urlretrieve(self.url, self.file_location)

class ffmpegOption:
    """
    Represents an option to pass to ffmpeg
    """
    filter_name = ""
    filter_options = ""
    
    def __init__(self, filter_name, filter_options):
        self.filter_name = filter_name
        self.filter_options = filter_options
    

class AudioItem:
    """
    Object referring to an audio file/url
    AudioItems are equal (==) if ids are the same
    """
    url = ""
    title = ""
    audio_id = ""
    sys_location = ""
    download_thread = None
    player = None
    invoked_channel = None # channel that requested the item
    invoker = None # user that requested the item

    def __init__(self, url, title, audio_id, sys_location, invoked_channel,
                 invoker="", gpm_track_dict=None):
        self.url = url
        self.title = title
        self.audio_id = audio_id
        self.sys_location = sys_location
        self.invoked_channel = invoked_channel
        self.invoker = invoker
        self.gpm_track_dict = gpm_track_dict

    async def start_download(self):
        # Begin download of relevant audio
        if not os.path.exists(self.sys_location):
            if self.url == "gpm":
                # print(self.audio_id)
                self.url = gpmapi.get_stream_url(
                    self.audio_id, str(os.environ['GPM_DEVICEID'])[2:])
                '''
                if self.gpm_track_dict is not None and \
                        'id' in self.gpm_track_dict:
                    try:
                        gpmapi.increment_song_playcount(self.gpm_track_dict['id'])
                    except: # lol
                        pass
                '''
            self.download_thread = UrlDownloader(self.url, self.sys_location)
            self.download_thread.start()
            while not os.path.exists(self.sys_location) or \
                    self.download_thread.is_alive():
                await asyncio.sleep(0.5)

    async def delete_item(self):
        # Delete audio from filesystem
        if self.download_thread is not None:
            if self.download_thread == 'haha':
                return
            while self.download_thread.is_alive():
                self.download_thread.join(1)
                await asyncio.sleep(10)
            if os.path.exists(self.sys_location):
                os.remove(self.sys_location)

    async def thumb_up(self):
        # Thumb up song on google play (helps with radio)
        if self.audio_id[0] == 'T':
            song = gpmapi.get_track_info(self.audio_id)
            song['rating'] = '5'
            gpmapi.change_song_metadata(song)

    def get_audio_info(self):
        return self.title

    def get_location(self):
        return self.sys_location

    def get_invoker(self):
        return self.invoker
    
    def set_invoker(self, invoker):
        self.invoker = invoker

    def __eq__(self, other):
        return self.audio_id == other.audio_id

    def __del__(self):
        if os.path.exists(self.sys_location):
            os.remove(self.sys_location)


class VoiceConnection:
    """
    Handles playing audio to its specified channel (discord.VoiceClient obj)
    """
    voice_client = None # Current discordpy voice client object
    bot = None # Current bot object
    playlist = None # deque of current playlist
    cur_player = None # discordpy player object that is currently playing
    cur_song = None # AudioItem of current audio
    radio_leftovers = [] # Leftovers from the radio query that may be used
    radio_queue = None # deque of current radio queue
    radio_channel = None # channel that the radio was invoked in
    title_queue = None # deque of audio titles
    misc_audio = None # deque of misc AudioItems (from force_play)
    folder_path = "" # Path to temp folder
    playlist_manager_lock = False # Nothing atm
    next_song = None # The next queued AudioItem that has begun downloading
    is_playing = False # Is the voice_client playing audio atm?
    play_next_lock = False # If an item in the queue is about to begin
    audio_filters = list() # holds ffmpegOption objects
    ffmpeg_options = '' # A string of ffmpeg options to use

    def __init__(self, bot, voice_client):
        self.playlist = deque()
        self.radio_queue = deque()
        self.title_queue = deque()
        self.misc_audio = deque()
        self.bot = bot
        self.voice_client = voice_client
        start_path = 'data/' + self.voice_client.server.name + \
                     ' - ' + self.voice_client.server.id + '/Voice'
        self.folder_path = start_path + '/tempdownloads'
        if os.path.exists(self.folder_path): # remove existing temp folder
            shutil.rmtree(self.folder_path, ignore_errors=True)
        if not os.path.exists(start_path): # create temp folder
            os.mkdir(start_path)
        os.mkdir(self.folder_path)

    async def add_to_playlist(self, arguments, message):
        # TODO: youtube playlist support
        # If something was previously paused
        if self.cur_player is not None and not self.cur_player.is_playing():
            self.cur_player.resume()
        query = message.content.split(" ", 1)
        if len(query) > 1:
            query = query[1]
        else:
            query = ""
        # self.radio_leftovers = []
        # Attempts to create an AudioItem from the given query + arguments
        audio_type, audio_item_list = await self.create_audio_item(
            arguments, query, message)
        if audio_type == 'gpm radio':  # Reset radio queue if a new station 
            self.radio_queue = deque() # has been given
        for audio_item in audio_item_list: # A list is always (supposed to be)
                                           # returned
            # Suppress error message if only searching
            if audio_item is None and arguments[1] != '*CHECK_MESSAGESEARCH*':
                await self.bot.send_message(message.channel,
                                            "got nothing for you")
            elif audio_type == 'gpm radio':  
                if len(self.playlist) == 0:          
                    self.playlist.append(audio_item)
                else: # Radio songs always have lower priority than queries
                    self.radio_queue.append(audio_item)
            else: # Playlist is first populated with any new AudioItems
                self.playlist.append(audio_item)
        if len(self.playlist) == 0: # Certainly nothing was added
            return
        if not self.is_playing: # Playlist is not empty and currently inactive
            # Begin playing next song
            self.is_playing = True
            self.play_next_lock = False # Resets the variable in case of error
            self.cur_song = self.playlist.popleft()
            await self.cur_song.start_download()
            self.cur_song.player = await self.play(self.cur_song) # plays audio
            self.cur_player = self.cur_song.player # potentially unnecessary
        if audio_type == 'gpm radio': # populating the radio_queue
            print('adding some')
            await self._add_radio_leftovers(2)
            print('done')
        else:
            for audio_item in audio_item_list:
                await audio_item.start_download()

    async def force_play(self, arguments, query):
        """ forces another item to play at the same time for an effect """
        temp, this_audio = await self.create_audio_item(arguments, query)
        if this_audio is None:
            return
        this_audio = this_audio[0]
        await this_audio.start_download()
        this_audio.player = self.voice_client.create_ffmpeg_player(
            this_audio.get_location())
        self.misc_audio.append(this_audio)
        this_audio.player.start()
        while this_audio.player.is_playing():
            await asyncio.sleep(10)
        await this_audio.delete_item()

    async def play_next(self):
        """ plays the next available AudioItem """
        try:
            if self.voice_client is None: # is this possible?
                return
            if self.play_next_lock: # the next item is already beginning to play
                return
            self.play_next_lock = True # the next item is beginning to play
            if self.next_song is not None: # if the next item was already loaded
                self.cur_song = self.next_song
            elif len(self.playlist) > 0: # if something remains in the playlist
                self.cur_song = self.playlist.popleft()
            elif len(self.radio_queue) > 0: # else in the radio queue
                self.cur_song = self.radio_queue.popleft()
            elif len(self.radio_leftovers) > 0: # else in the radio leftovers
                # checking to see if the bot is alone (no need for audio)
                if len(self.voice_client.channel.voice_members) < 2:
                    return
                radio_msg_content = 'adding to queue'
                radio_msg = await self.bot.send_message(
                    self.radio_channel, 'adding to queue')
                await self._add_radio_leftovers(
                    5, radio_msg=radio_msg, radio_msg_content=radio_msg_content)
                self.cur_song = self.radio_queue.popleft()
            else: # no AudioItems left to play
                self.is_playing = False
                self.play_next_lock = False
                return
            # begin downloading item (a file can still be played by ffmpeg while
            # downloading if properly stored, as it is in this implementation)
            await self.cur_song.start_download()
            self.cur_song.player = await self.play(self.cur_song)
            await self.bot.send_message(
                self.cur_song.invoked_channel, "**Now Playing:** " + self.cur_song.title)
            self.next_song = None
            self.cur_player = self.cur_song.player
            self.play_next_lock = False
            # Attempt to preload the next AudioItem
            if len(self.playlist) > 0:
                self.next_song = self.playlist.popleft()
                await self.next_song.start_download()
            elif len(self.radio_queue) < 5: # try from radio queue
                if len(self.voice_client.channel.voice_members) > 1:
                    await self._add_radio_leftovers(5-len(self.radio_queue))
            if self.next_song is not None: # preload
                await self.next_song.start_download()
        except Exception as e:
            print(repr(e)) # sad

    async def clean_up(self, audio_item):
        """ removes the temp files and plays next item """
        try:
            # if self.next_song is None or self.next_song != audio_item:
            await audio_item.delete_item()
            await self.play_next()
        except Exception as e:
            print(repr(e))

    def after_audio(self, audio_item):
        """ called after a player is finished """
        self.cur_song = None
        coro = self.clean_up(audio_item) # client.send_message(text_channel, 'fdsfsdf')
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result(timeout=0.1)
        except TimeoutError as e:  # gotta timeout apparently???
            print(repr(e))
            print('uh oh')
            pass

    async def play(self, audio_to_play : AudioItem):
        """ plays the given AudioItem"""
        # discordpy function
        cur_player = self.voice_client.create_ffmpeg_player(
            audio_to_play.sys_location,
            options=self.ffmpeg_options,
            after=lambda: self.after_audio(audio_to_play))
        cur_player.start()
        return cur_player
    
    async def refresh_filters(self):
        """ refresh the ffrmpeg_options string """
        if len(self.audio_filters) > 0:
            self.ffmpeg_options = '-filter:a "'
            for filter in self.audio_filters:
                self.ffmpeg_options += filter.filter_name + \
                    filter.filter_options + ','
            self.ffmpeg_options = self.ffmpeg_options[:-1] + '"'
        else:
            self.ffmpeg_options = ''
        print(self.ffmpeg_options)

    async def _add_radio_leftovers(self, num_to_add, radio_msg=None,
                                   radio_msg_content=""):
        """ adds songs from initial radio query to the radio queue.
        All songs aren't added from the radio by initially since the
        initial query returns like 100 songs """
        # radio_msg_content = 'getting 5 more songs'
        # radio_msg = await client.send_message(self.radio_channel,
        #                                       radio_msg_content)
        if len(self.radio_leftovers) == 0:
            return
        leftovers_to_add = self.radio_leftovers[0:num_to_add]
        if len(self.radio_leftovers) > num_to_add:
            self.radio_leftovers = self.radio_leftovers[num_to_add:]
        else:
            self.radio_leftovers = []
            await self.bot.send_message(self.radio_channel,
                                      'radio is finished')
        await self._put_radio_songs(
            leftovers_to_add, radio_msg, radio_msg_content)

    async def _get_from_ydl_playlist(self, arguments, query, message=None):
        """ incomplete """
        with youtube_dl.YoutubeDL({
                'default_search': 'auto',
                'playlistend': 10,
                'prefer_ffmpeg': True,
                # 'ignoreerrors': True,
                'format': 'bestaudio/best',
                'outtmpl': self.folder_path + '%(id)s.%(ext)s',
                'nopart': True,
                'ratelimit': 4000000,
                # 'logger': curLog,
                'fixup': "warn"}) as ydl:
            ydl_results = ydl.extract_info(query, download=False)

    async def create_audio_item(self, arguments, query, message=None):
        """ creates an AudioItem object based on the query and arguments 
        query would represent a url to process through youtube-dl or
        a search query to be used by youtube-dl or gpm (depending on
        the arguments) or empty for a random radio from gpm
        
        always should return a tuple of type (str, list()) representing the 
        result of the function and the created AudioItems (if any)
        
        much of the confusion in this implementation & this entire class is due 
        to the fact that I decided to reuse code from a previous version of this
        bot over doing a full rewrite of this part. Mistake!"""
        # this is it
        # the stuff happens here!!!
        if arguments[2] == 'website': # use youtube-dl
            with youtube_dl.YoutubeDL({
                    'default_search': 'auto', # search if url is not detected
                    'playlistend': 10,
                    'prefer_ffmpeg': True,
                    # 'ignoreerrors': True,
                    'format': 'bestaudio/best', # prefer best audio only format
                    'outtmpl': self.folder_path + '%(id)s.%(ext)s', # save path
                    'nopart': True, # download + write into the output file
                    'ratelimit': 4000000, # download speed limit (very high)
                    # 'logger': curLog,
                    'fixup': "warn"}) as ydl:
                try:
                    ydl_results = ydl.extract_info(query, download=False)
                except Exception as e:
                    print(str(e))
                    await self.bot.send_message(
                        message.channel,
                        "some error, video not found or it's blocked in the US :(")
                    return 'error', [None]
                # Just a youtube search
                if arguments[1] == '*CHECK_MESSAGESEARCH*': # show found video
                    await self.bot.send_message(
                        message.channel,
                        ydl_results['entries'][0]['webpage_url'])
                    return 'search', [None]
                # Create and return AudioItems
                if 'entries' in ydl_results: # a playlist was given
                    await self.bot.send_message(
                        message.channel,
                        ydl_results['entries'][0]['webpage_url'])
                    items = []
                    for result in ydl_results['entries']:
                        # creates an AudioItem for the current result
                        url = result['url']
                        if 'uploader' in result:
                            title = result['title'] + ' - ' + result['uploader']
                        else:
                            title = result['title']
                        audio_id = result['id']
                        system_location = self.folder_path + '/' + audio_id + \
                            '.' + result['ext']
                        items.append(AudioItem(
                            url, title, audio_id, system_location,
                            message.channel, message.author.name))
                    return 'ydl playlist', items
                # a playlist was NOT given:
                # creates an AudioItem based off result
                url = ydl_results['url']
                # direct videos don't have these
                if 'title' in ydl_results and 'uploader' in ydl_results:
                    title = ydl_results['title'] + ' - ' + ydl_results['uploader']
                else:
                    title = ydl_results['id']
                audio_id = ydl_results['id']
                system_location = self.folder_path + '/' + audio_id + \
                    '.' + ydl_results['ext']
                return 'ydl single', [AudioItem(
                    url, title, audio_id, system_location, message.channel,
                    message.author.name)]
        elif arguments[2] == 'gpm': # something from google play music
            if not await check_gpm_auth(client_type=0): # login to account
                return 'auth fail', [None]
            if arguments[1] == "*CHECK_MESSAGERADIO*": # radio query
                if len(query) > 0: # if a radio seed of sorts was given
                    title, station_id = await self._get_gpm_station(query)
                    if station_id is None:
                        return 'gpm radio no results', [None]
                    print('{}'.format(station_id))
                    radio_msg_content = 'starting "' + title + '" radio'
                    radio_msg = await self.bot.send_message(message.channel,
                                                            radio_msg_content)
                    song_list = gpmapi.get_station_tracks(station_id,
                                                          num_tracks=50)
                    #gpmapi.delete_stations([station_id])
                else: # get a random radio station (IFL)
                    song_list = gpmapi.get_station_tracks('IFL', num_tracks=50)
                    radio_msg_content = 'starting random radio'
                    radio_msg = await self.bot.send_message(message.channel,
                                                            radio_msg_content)
                self.radio_leftovers = song_list[1:] # store leftovers
                # create AudioItem of first result
                title, song_item = await self._get_gpm_song(song_list[0],
                                                            message.channel)
                song_item.set_invoker(message.author.name) # who requested it
                self.radio_channel = message.channel
                return 'gpm radio', [song_item]
            elif arguments[1] == '*CHECK_MESSAGEALBUM*': # album query
                # check if a search index was given
                test_pos = query.rsplit(" ", 1)
                if test_pos[0].isdigit():
                    pos = int(test_pos[0]) - 1
                else:
                    pos = 0
                # perform search
                search = gpmapi.search(query, max_results=10)
                if len(search['album_hits']) > 0:
                    album_dict = search['album_hits'][pos]['album']
                    title = album_dict['name'] + ' - ' + \
                            album_dict['albumArtist']
                    await self.bot.send_message(message.channel, title)
                    song_list = gpmapi.get_album_info(
                        album_dict['albumId'])['tracks']
                    songs = []
                    for song in song_list: # make AudioItems of each song
                        title, song_item = await self._get_gpm_song(
                            song, message.channel)
                        song_item.set_invoker(message.author.name)
                        songs.append(song_item)
                else: # no albums found
                    return 'gpm album no results', [None]
                return 'gpm album', songs
            else: # regular song search
                song_list = gpmapi.search(query, max_results=1)
                if len(song_list['song_hits']) > 0:
                    track_dict = song_list['song_hits'][0]['track']
                    # create AudioItem of found song
                    title, song_item = await self._get_gpm_song(track_dict,
                                                                message.channel)
                    await self.bot.send_message(message.channel, title)
                    song_item.set_invoker(message.author.name)
                    return 'gpm single', [song_item]
                else:
                    return 'gpm no results', [None]
        print('create failed')

    async def stop(self):
        """ stops current AudioItem and tries to play next """
        if len(self.misc_audio) > 0:
            self.misc_audio.popleft().player.stop()
        elif self.cur_player is not None:
            self.cur_player.stop()
            self.cur_player = None
            # await self.clean_up()

    async def leave(self):
        """ clears queue and leaves the voice channel """
        await self.clear()
        if os.path.exists(self.folder_path): # remove temp files
            shutil.rmtree(self.folder_path, ignore_errors=True)
        await self.voice_client.disconnect()

    async def clear(self):
        """ resets all queues """
        try:
            self.radio_queue = deque()
            self.radio_leftovers = []
            self.playlist = deque()
            self.cur_player.stop()
            self.cur_player = None
        except Exception as e:
            print('clear error: ' + self.voice_client.server.name)
            print(repr(e))

    async def pause(self):
        """ pause audio """
        if self.cur_player is not None and self.cur_player.is_playing():
            self.cur_player.pause()

    async def resume(self):
        if self.cur_player is not None and not self.cur_player.is_playing():
            self.cur_player.resume()

    async def stop_radio(self):
        """ remove all queued radio songs """
        self.radio_queue = deque()
        self.radio_leftovers = []

    async def get_queue_string(self):
        """ string representation of the queue """
        queue = ''
        if self.cur_song is not None:
            queue += 'Now: {} ({})\n'.format(self.cur_song.title,
                                             self.cur_song.invoker)
        if self.next_song is not None:
            queue += 'Next: {} ({})\n'.format(self.next_song.title,
                                              self.next_song.invoker)
        for i in range(len(self.playlist)):
            queue += '{} : {} ({})\n'.format(i+1, self.playlist[i].title,
                                             self.playlist[i].invoker)
        if len(self.radio_queue) > 0:
            queue += 'radio:\n'
        for i in range(len(self.radio_queue)):
            queue += '{} : {}\n'.format(i+1, self.radio_queue[i].title)
        return queue

    async def dequeue(self, value):
        """ remove an AudioItem at a certain index """
        if value >= len(self.playlist):
            await self.playlist.pop().delete_item()
        else:
            await self.playlist.pop(value).delete_item()
            
    async def reset_filters(self):
        """ reset audio filters """
        self.audio_filters = list() # reset audio_filters
        await self.refresh_filters()

    async def add_filter(self, filter):
        """ add filter to audio filter list """
        self.audio_filters.append(filter)
        await self.refresh_filters()
        
    async def _get_gpm_station(self, query):
        """ searches for a gpm station based on the query 
        first finds a relevant seed based on query then creates the station """
        hits_list = gpmapi.search(query, max_results=1)
        if len(hits_list['station_hits']) > 0: # is a specific station found?
            station_dict = hits_list['station_hits'][0]['station']
            title = station_dict['name'] + " (Pre-made station)"
            if 'curatedStationId' in station_dict['seed']:
                # is a pre-made station by staff
                audio_id = station_dict['seed']['curatedStationId']
                station_id = gpmapi.create_station('discord radio',
                                                   curated_station_id=audio_id)
            elif 'genreId' in station_dict['seed']:
                # query is a genre
                audio_id = station_dict['seed']['genreId']
                station_id = gpmapi.create_station('discord radio',
                                                   genre_id=audio_id)
            else:
                station_id = None
            if station_id is not None: # station successfully made
                return title, station_id

        if len(hits_list['song_hits']) > 0: # is a related song found?
            track_dict = hits_list['song_hits'][0]['track']
            if 'id' in track_dict:
                audio_id = track_dict['id']
                print('id in track_dict: ' + title)
            elif 'storeId' in track_dict:
                audio_id = track_dict['storeId']
            else:
                audio_id = track_dict['nid']
                print('nid in track_dict: ' + title)
            title = track_dict['title'] + ' - ' + track_dict[
                'artist']
            station_id = gpmapi.create_station('discord radio',
                                               track_id=audio_id)
        elif len(hits_list['album_hits']) > 0: # is a related album found?
            album_dict = hits_list['album_hits'][0]['album']
            audio_id = album_dict['albumId']
            title = album_dict['name'] + ' -- ' + album_dict[
                'artist']
            station_id = gpmapi.create_station('discord radio',
                                               album_id=audio_id)
        elif len(hits_list['artist_hits']) > 0: # is a related artist found?
            artist_dict = hits_list['artist_hits'][0]['artist']
            audio_id = artist_dict['artistId']
            title = artist_dict['name'] + ' (artist)'
            station_id = gpmapi.create_station('discord radio',
                                               artist_id=audio_id)
        else:
            return 'no results', None
        return title, station_id

    async def _put_radio_songs(self, song_list, radio_msg=None,
                               radio_msg_content=""):
        """ creates AudioItems based on the song_list given from a previous
        gpm radio query """
        song_items = []
        for track_dict in song_list:
            title, song_item = await self._get_gpm_song(track_dict,
                                                        self.radio_channel)
            await song_item.start_download()
            self.radio_queue.append(song_item)
            if radio_msg is not None:
                radio_msg_content += '.'
                await self.bot.edit_message(radio_msg, radio_msg_content)
        return song_items

    async def _get_gpm_song(self, track_dict, channel):
        """ creates an AudioItem based on the given gpm track_dict """
        title = track_dict['title'] + ' - ' + track_dict['artist']
        if 'id' in track_dict:
            audio_id = track_dict['id']
            print('id in track_dict: ' + title)
        elif 'storeId' in track_dict:
            audio_id = track_dict['storeId']
        else:
            audio_id = track_dict['nid']
            print('nid in track_dict: ' + title)
        system_location = self.folder_path + '/' + audio_id + '.mp3'
        #try:
        #url = gpmapi.get_stream_url(audio_id,
        #                            config['gpm']['DeviceID'][2:])
        song_item = AudioItem("gpm", title, audio_id, system_location,
                              channel, gpm_track_dict=track_dict)
        # await song_item.start_download()
        '''except:
            global gpmMM_logged_in
            if not gpmMM_logged_in:
                print('gpmMM auth')
                self.gpmMM_logged_in = gpmMMapi.login()
            audio_id = track_dict['id']
            filename, song_bytestream = gpmMMapi.download_song(audio_id)
            url = self.folder_path + '/' + filename
            with open(url, 'wb') as f:
                f.write(song_bytestream)
            system_location = url
            song_item = AudioItem(url, title, audio_id, system_location,
                                  channel)
            song_item.download_thread = 'haha'
        '''
        return title, song_item

    def is_connected(self):
        return self.voice_client.is_connected()


class Voice:
    """voice related commands"""

    def __init__(self, bot: commands.Bot, v_c=None):
        self.bot = bot
        if os.path.exists('vendor'): # Required for discord voice
            discord.opus.load_opus('opus/lib/libopus.so.0')
        if v_c is not None:
            self.voice_connections = v_c
        else:
            self.voice_connections = {}

    @commands.command(name='youtube', aliases=['y', 'Y'], pass_context=True)
    async def play_youtube(self, ctx):
        """plays a given url (many sites work) or search query"""
        msg = ctx.message.content.split(" ", 1)
        if len(msg) == 1:
            return

        if self.voice_connections.get(ctx.message.server.id) is None:
            voice_channel = None
            if ctx.message.author.voice.voice_channel is None:
                for channel in ctx.message.server.channels:
                    if channel.type == discord.ChannelType.voice:
                        voice_channel = channel
            else:
                voice_channel = ctx.message.author.voice.voice_channel
            self.voice_connections[ctx.message.server.id] = \
                VoiceConnection(
                    self.bot, await self.bot.join_voice_channel(voice_channel))

        arguments = ['voice', '*CHECK_MESSAGEQ*', 'website', 'false']

        await self.voice_connections[ctx.message.server.id].add_to_playlist(
            arguments, ctx.message)
            
    @commands.command(name='youtubesearch', aliases=['ys', 'Ys'], pass_context=True)
    async def search_youtube(self, ctx):
        """searches for a query on youtube"""
        msg = ctx.message.content.split(" ", 1)
        if len(msg) == 1: # If no query was given
            ctx.message.content = '`youtubesearch ys joanna newsom'

        if self.voice_connections.get(ctx.message.server.id) is None:
            voice_channel = None
            if ctx.message.author.voice.voice_channel is None:
                for channel in ctx.message.server.channels:
                    if channel.type == discord.ChannelType.voice:
                        voice_channel = channel
            else:
                voice_channel = ctx.message.author.voice.voice_channel
            self.voice_connections[ctx.message.server.id] = \
                VoiceConnection(
                    self.bot, await self.bot.join_voice_channel(voice_channel))

        arguments = ['voice', '*CHECK_MESSAGESEARCH*', 'website', 'false']

        await self.voice_connections[ctx.message.server.id].add_to_playlist(
            arguments, ctx.message)

    @commands.command(name='music', aliases=['m', 'M'], pass_context=True)
    async def play_music(self, ctx):
        """plays a song off google play music"""
        msg = ctx.message.content.split(" ", 1)
        if len(msg) == 1:
            return

        if self.voice_connections.get(ctx.message.server.id) is None:
            voice_channel = None
            if ctx.message.author.voice.voice_channel is None:
                for channel in ctx.message.server.channels:
                    if channel.type == discord.ChannelType.voice:
                        voice_channel = channel
            else:
                voice_channel = ctx.message.author.voice.voice_channel
            self.voice_connections[ctx.message.server.id] = \
                VoiceConnection(
                    self.bot, await self.bot.join_voice_channel(voice_channel))

        arguments = ['voice', '*CHECK_MESSAGEQ*', 'gpm', 'false']

        await self.voice_connections[ctx.message.server.id].add_to_playlist(
            arguments, ctx.message)

    @commands.command(name='album', aliases=['a', 'A'], pass_context=True)
    async def play_music_album(self, ctx):
        """plays a song off google play music"""
        msg = ctx.message.content.split(" ", 1)
        if len(msg) == 1:
            return

        if self.voice_connections.get(ctx.message.server.id) is None:
            voice_channel = None
            if ctx.message.author.voice.voice_channel is None:
                for channel in ctx.message.server.channels:
                    if channel.type == discord.ChannelType.voice:
                        voice_channel = channel
            else:
                voice_channel = ctx.message.author.voice.voice_channel
            self.voice_connections[ctx.message.server.id] = \
                VoiceConnection(
                    self.bot, await self.bot.join_voice_channel(voice_channel))

        arguments = ['voice', '*CHECK_MESSAGEALBUM*', 'gpm', 'false']

        await self.voice_connections[ctx.message.server.id].add_to_playlist(
            arguments, ctx.message)

    @commands.command(name='radio', pass_context=True)
    async def play_music_radio(self, ctx):
        """starts a radio based on a search query
        songs are taken off google play
        will only play after the immediate queue is clear"""
        msg = ctx.message.content.split(" ", 1)

        if self.voice_connections.get(ctx.message.server.id) is None:
            voice_channel = None
            if ctx.message.author.voice.voice_channel is None:
                for channel in ctx.message.server.channels:
                    if channel.type == discord.ChannelType.voice:
                        voice_channel = channel
            else:
                voice_channel = ctx.message.author.voice.voice_channel
            self.voice_connections[ctx.message.server.id] = \
                VoiceConnection(
                    self.bot, await self.bot.join_voice_channel(voice_channel))
                    
        arguments = ['voice', '*CHECK_MESSAGERADIO*', 'gpm', 'false']

        await self.voice_connections[ctx.message.server.id].add_to_playlist(
            arguments, ctx.message)

    @commands.command(aliases=['stop'], pass_context=True)
    async def skip(self, ctx):
        """stops the current song and plays the next in queue"""
        if ctx.message.server.id in self.voice_connections:
            await self.voice_connections[ctx.message.server.id].stop()

    @commands.command(pass_context=True)
    async def leave(self, ctx):
        """leaves the voice channel and clears all queues"""
        if ctx.message.server.id in self.voice_connections:
            await self.voice_connections[ctx.message.server.id].leave()
            if self.voice_connections[ctx.message.server.id].is_connected():
                await self.voice_connections[
                    ctx.message.server.id].voice_client.disconnect()
            del self.voice_connections[ctx.message.server.id]

    '''
    @commands.command(pass_context=True)
    async def clear(self, ctx):
        """leaves the voice channel and clears all queues"""
        if ctx.message.server.id in self.voice_connections:
            await self.voice_connections[ctx.message.server.id].leave()
            if self.voice_connections[ctx.message.server.id].is_connected():
                await self.voice_connections[
                    ctx.message.server.id].voice_client.disconnect()
            del self.voice_connections[ctx.message.server.id]
    '''

    @commands.command(pass_context=True)
    async def pause(self, ctx):
        """pauses the current queue"""
        if ctx.message.server.id in self.voice_connections:
            await self.voice_connections[ctx.message.server.id].pause()

    @commands.command(pass_context=True)
    async def resume(self, ctx):
        """resumes the paused queue"""
        if ctx.message.server.id in self.voice_connections:
            await self.voice_connections[ctx.message.server.id].resume()

    @commands.command(name='queue', aliases=['q', 'Q'], pass_context=True)
    async def get_queue(self, ctx):
        """sends the current queue to the chat"""
        if ctx.message.server.id in self.voice_connections:
            queue_string = await self.voice_connections[
                ctx.message.server.id].get_queue_string()
            if len(queue_string) > 0:
                await self.bot.send_message(ctx.message.channel, queue_string)
    
    @commands.command(name='dequeue', aliases=['deq'], pass_context=True)
    async def remove_from_queue(self, ctx, index=1):
        """removes the audio file at index from the queue"""
        if ctx.message.server.id in self.voice_connections:
            queue_string = await self.voice_connections[
                ctx.message.server.id].dequeue(index)
    
    @commands.command(name='stopradio', aliases=['sradio'], pass_context=True)
    async def stop_radio(self, ctx):
        """stops the radio!!!"""
        if ctx.message.server.id in self.voice_connections:
            await self.voice_connections[ctx.message.server.id].stop_radio()

    @commands.command(name='vfix', pass_context=True)
    async def voice_fix(self, ctx):
        """sometimes things go wrong & ur just gonna have to `vfix"""
        # any general fixes go here
        if ctx.message.server.id in self.voice_connections:
            print('vfix 1-1')
            voice_channel = self.voice_connections[
                ctx.message.server.id].voice_client.channel
            old_vc = self.voice_connections[ctx.message.server.id].voice_client
            self.voice_connections[ctx.message.server.id].voice_client = None
            old_vc.disconnect()
            self.voice_connections[ctx.message.server.id].voice_client = \
                self.bot.join_voice_channel(voice_channel)
            if self.bot.voice_client_in(ctx.message.server) is None:
                print('vfix 1-2')
                voice_channel = None
                if ctx.message.author.voice.voice_channel is None:
                    for channel in ctx.message.server.channels:
                        if channel.type == discord.ChannelType.voice:
                            voice_channel = channel
                else:
                    voice_channel = ctx.message.author.voice.voice_channel
                self.voice_connections[ctx.message.server.id].voice_client = \
                    await self.bot.join_voice_channel(voice_channel)
            await self.voice_connections[ctx.message.server.id].play_next()
        else:
            print('vfix 2-1')
            if self.bot.voice_client_in(ctx.message.server) is None:
                voice_channel = None
                if ctx.message.author.voice.voice_channel is None:
                    for channel in ctx.message.server.channels:
                        if channel.type == discord.ChannelType.voice:
                            voice_channel = channel
                else:
                    voice_channel = ctx.message.author.voice.voice_channel
                self.voice_connections[ctx.message.server.id] = \
                    VoiceConnection(self.bot,
                        await self.bot.join_voice_channel(voice_channel))
    
    @commands.command(name='effect', pass_context=True)
    async def add_effect(self, ctx, *, effect=""):
        """ adds a given audio effect to the voice output
        '`effect (EFFECT)' to apply EFFECT
        These effects are additive (!!!!)
        also, the bot has to be in a voice channel
        
        possible effects: 
        reset - removes all filters currently applied
        bb - bass boost
        nc [sample rate] - time stretch (sample rate is 600000 if unspecified)
        pulse - apulsator (headache inducer!!!)
        
        more info: https://ffmpeg.org/ffmpeg-filters.html#Audio-Filters
        """
        if ctx.message.server.id in self.voice_connections:
            effect_split = effect.split()
            if effect_split[0] == 'reset': #remove all filters
                await self.voice_connections[
                    ctx.message.server.id].reset_filters()
            else: #add new ffmpegOption object to list
                new_filter = None
                if effect_split[0] == 'bb':
                    new_filter = ffmpegOption('bass=gain=', '10')
                elif effect_split[0] == 'nc':
                    if len(effect_split) > 1 and effect_split[1].is_digit():
                        new_filter = ffmpegOption('asetrate=', effect_split[1])
                    else:
                        new_filter = ffmpegOption('asetrate=', '60000')
                elif effect_split[0] == 'pulse':
                    new_filter = ffmpegOption('apulsator', '')
                if new_filter is not None:
                    await self.voice_connections[
                        ctx.message.server.id].add_filter(new_filter)

async def check_gpm_auth(client_type=0):
    """ check if gpm is logged in and is subbed"""
    # client_type=0: MobileClient()
    # TODO: client_type=1: MusicManager()
    if client_type == 0:
        if not gpmapi.is_authenticated():
            print('auth')
            gpm_logged_in = gpmapi.login(
                str(os.environ['GPM_EMAIL']), str(os.environ['GPM_PASS']),
                str(os.environ['GPM_DEVICEID']))
            if not gpm_logged_in:
                print("Failed GPM login")
                return False
        return True
