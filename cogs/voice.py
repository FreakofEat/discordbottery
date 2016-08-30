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
    def __init__(self, url, file_location):
        threading.Thread.__init__(self)
        self.url = url
        self.file_location = file_location

    def run(self):
        urllib.request.urlretrieve(self.url, self.file_location)


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
    invoked_channel = None

    def __init__(self, url, title, audio_id, sys_location, invoked_channel):
        self.url = url
        self.title = title
        self.audio_id = audio_id
        self.sys_location = sys_location
        self.invoked_channel = invoked_channel

    async def start_download(self):
        if not os.path.exists(self.sys_location):
            if self.url == "gpm":
                # print(self.audio_id)
                self.url = gpmapi.get_stream_url(
                    self.audio_id, str(os.environ['GPM_DEVICEID'])[2:])
            self.download_thread = UrlDownloader(self.url, self.sys_location)
            self.download_thread.start()
            while not os.path.exists(self.sys_location) or \
                    self.download_thread.is_alive():
                await asyncio.sleep(0.5)

    async def delete_item(self):
        if self.download_thread is not None:
            if self.download_thread == 'haha':
                return
            while self.download_thread.is_alive():
                self.download_thread.join(1)
                await asyncio.sleep(10)
            if os.path.exists(self.sys_location):
                os.remove(self.sys_location)

    def get_audio_info(self):
        return self.title

    def get_location(self):
        return self.sys_location

    def __eq__(self, other):
        return self.audio_id == other.audio_id

    def __del__(self):
        if os.path.exists(self.sys_location):
            os.remove(self.sys_location)


class VoiceConnection:
    """
    Handles playing audio to it's specified channel (discord.VoiceClient obj)
    """
    voice_client = None
    bot = None
    playlist = None
    cur_player = None
    radio_leftovers = []
    radio_queue = None
    radio_channel = None
    title_queue = None
    misc_audio = None
    folder_path = ""
    playlist_manager_lock = False
    next_song = None
    is_playing = False
    play_next_lock = False

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
        if os.path.exists(self.folder_path):
            shutil.rmtree(self.folder_path, ignore_errors=True)
        if not os.path.exists(start_path):
            os.mkdir(start_path)
        os.mkdir(self.folder_path)

    async def add_to_playlist(self, arguments, message):
        # TODO: youtube playlist support
        query = message.content.split(" ", 1)
        if len(query) > 1:
            query = query[1]
        else:
            query = ""
        # self.radio_leftovers = []
        audio_type, audio_item_list = await self.create_audio_item(
            arguments, query, message)
        if audio_type == 'gpm radio':
            self.radio_queue = deque()
        for audio_item in audio_item_list:
            if audio_item is None:
                await self.bot.send_message(message.channel,
                                            "got nothing for you")
            elif audio_type == 'gpm radio':
                if len(self.playlist) == 0:
                    self.playlist.append(audio_item)
                else:
                    self.radio_queue.append(audio_item)
            else:
                self.playlist.append(audio_item)
        if len(self.playlist) == 0:
            return
        if not self.is_playing:
            self.is_playing = True
            self.play_next_lock = False
            cur_song = self.playlist.popleft()
            await cur_song.start_download()
            cur_song.player = await self.play(cur_song)
            self.cur_player = cur_song.player
        if audio_type == 'gpm radio':
            print('adding some')
            await self._add_radio_leftovers(2)
            print('done')
        else:
            for audio_item in audio_item_list:
                await audio_item.start_download()

    async def force_play(self, arguments, query):
        this_audio = await self.create_audio_item(arguments, query)
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
        try:
            if self.play_next_lock:
                return
            self.play_next_lock = True
            if self.next_song is not None:
                cur_song = self.next_song
            elif len(self.playlist) > 0:
                cur_song = self.playlist.popleft()
            elif len(self.radio_queue) > 0:
                cur_song = self.radio_queue.popleft()
            elif len(self.radio_leftovers) > 0:
                radio_msg_content = 'adding to queue'
                radio_msg = await self.bot.send_message(
                    self.radio_channel, 'adding to queue')
                await self._add_radio_leftovers(
                    5, radio_msg=radio_msg, radio_msg_content=radio_msg_content)
                cur_song = self.radio_queue.popleft()
            else:
                self.is_playing = False
                self.play_next_lock = False
                return
            await cur_song.start_download()
            cur_song.player = await self.play(cur_song)
            await self.bot.send_message(
                cur_song.invoked_channel, "**Now Playing:** " + cur_song.title)
            self.next_song = None
            self.cur_player = cur_song.player
            self.play_next_lock = False
            if len(self.playlist) > 0:
                self.next_song = self.playlist.popleft()
                await self.next_song.start_download()
            elif len(self.radio_queue) < 5:
                await self._add_radio_leftovers(
                    5-len(self.radio_queue))
            if self.next_song is not None:
                await self.next_song.start_download()
        except Exception as e:
            print(repr(e))

    async def clean_up(self, audio_item):
        try:
            # if self.next_song is None or self.next_song != audio_item:
            await audio_item.delete_item()
            await self.play_next()
        except Exception as e:
            print(repr(e))

    def after_audio(self, audio_item):
        coro = self.clean_up(audio_item) # client.send_message(text_channel, 'fdsfsdf')
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result(timeout=0.1)
        except TimeoutError as e:  # gotta timeout apparently???
            print(repr(e))
            print('uh oh')
            pass

    async def play(self, audio_to_play):
        cur_player = self.voice_client.create_ffmpeg_player(
            audio_to_play.sys_location,
            after=lambda: self.after_audio(audio_to_play))
        cur_player.start()
        return cur_player

    async def _add_radio_leftovers(self, num_to_add, radio_msg=None,
                                   radio_msg_content=""):
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
        # this is it
        # the stuff happens here!!!
        if arguments[2] == 'website':
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
                try:
                    ydl_results = ydl.extract_info(query, download=False)
                except:
                    await self.bot.send_message(
                        message.channel,
                        'some error (video not found most likely)')
                    return
                if 'entries' in ydl_results:
                    await self.bot.send_message(
                        message.channel,
                        ydl_results['entries'][0]['webpage_url'])
                    items = []
                    for result in ydl_results['entries']:
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
                            message.channel))
                    return 'ydl playlist', items
                url = ydl_results['url']
                title = ydl_results['title'] + ' - ' + ydl_results['uploader']
                audio_id = ydl_results['id']
                system_location = self.folder_path + '/' + audio_id + \
                    '.' + ydl_results['ext']
                return 'ydl single', [AudioItem(
                    url, title, audio_id, system_location, message.channel)]
        elif arguments[2] == 'gpm':
            if not await check_gpm_auth(client_type=0):
                return 'auth fail', [None]
            if arguments[1] == "*CHECK_MESSAGERADIO*":
                if len(query) > 0:
                    title, station_id = await self._get_gpm_station(query)
                    if station_id is None:
                        return 'gpm radio no results', [None]
                    radio_msg_content = 'starting "' + title + '" radio'
                    radio_msg = await self.bot.send_message(message.channel,
                                                          radio_msg_content)
                    song_list = gpmapi.get_station_tracks(station_id,
                                                          num_tracks=125)
                    gpmapi.delete_stations([station_id])
                else:
                    song_list = gpmapi.get_station_tracks('IFL', num_tracks=125)
                    radio_msg_content = 'starting random radio'
                    radio_msg = await self.bot.send_message(message.channel,
                                                          radio_msg_content)
                self.radio_leftovers = song_list[1:]
                title, song_item = await self._get_gpm_song(song_list[0],
                                                            message.channel)
                self.radio_channel = message.channel
                return 'gpm radio', [song_item]
            elif arguments[1] == '*CHECK_MESSAGEALBUM*':
                search = gpmapi.search(query, max_results=1)
                if len(search['album_hits']) > 0:
                    album_dict = search['album_hits'][0]['album']
                    title = album_dict['name'] + ' - ' + \
                            album_dict['albumArtist']
                    await self.bot.send_message(message.channel, title)
                    song_list = gpmapi.get_album_info(
                        album_dict['albumId'])['tracks']
                    songs = []
                    for song in song_list:
                        title, song_item = await self._get_gpm_song(
                            song, message.channel)
                        songs.append(song_item)
                else:
                    return 'gpm album no results', [None]
                return 'gpm album', songs
            else:
                song_list = gpmapi.search(query, max_results=1)
                if len(song_list['song_hits']) > 0:
                    track_dict = song_list['song_hits'][0]['track']
                    title, song_item = await self._get_gpm_song(track_dict,
                                                                message.channel)
                    await self.bot.send_message(message.channel, title)
                    return 'gpm single', [song_item]
                else:
                    return 'gpm no results', [None]
        print('create failed')

    async def stop(self):
        if len(self.misc_audio) > 0:
            self.misc_audio.popleft().player.stop()
        elif self.cur_player is not None:
            self.cur_player.stop()
            self.cur_player = None
            # await self.clean_up()

    async def leave(self):
        await self.clear()
        if os.path.exists(self.folder_path):
            shutil.rmtree(self.folder_path, ignore_errors=True)
        await self.voice_client.disconnect()

    async def clear(self):
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
        print('ok')

    async def stop_radio(self):
        self.radio_queue = deque()
        self.radio_leftovers = []

    async def get_queue_string(self):
        queue = ""
        if self.next_song is not None:
            queue += 'Next: ' + self.next_song.title + '\n'
        for i in range(len(self.playlist)):
            queue += str(i+1) + ': ' + self.playlist[i].title + '\n'
        if len(self.radio_queue) > 0:
            queue += 'radio:\n'
        for i in range(len(self.radio_queue)):
            queue += str(i+1) + ': ' + self.radio_queue[i].title + '\n'
        return queue

    async def dequeue(self, value):
        if value >= len(self.playlist):
            await self.playlist.pop().delete_item()
        else:
            await self.playlist.pop(value).delete_item()

    async def _get_gpm_station(self, query):
        hits_list = gpmapi.search(query, max_results=1)
        if len(hits_list['song_hits']) > 0:
            track_dict = hits_list['song_hits'][0]['track']
            audio_id = track_dict['nid']
            title = track_dict['title'] + ' - ' + track_dict[
                'artist']
            station_id = gpmapi.create_station('discord radio',
                                               track_id=audio_id)
        elif len(hits_list['album_hits']) > 0:
            album_dict = hits_list['album_hits'][0]['album']
            audio_id = album_dict['albumId']
            title = album_dict['name'] + ' -- ' + album_dict[
                'artist']
            station_id = gpmapi.create_station('discord radio',
                                               album_id=audio_id)
        elif len(hits_list['artist_hits']) > 0:
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
        title = track_dict['title'] + ' - ' + track_dict['artist']
        if 'id' in track_dict:
            audio_id = track_dict['id']
            print('id in track_dict: ' + title)
        else:
            audio_id = track_dict['nid']
        system_location = self.folder_path + '/' + audio_id + '.mp3'
        #try:
        #url = gpmapi.get_stream_url(audio_id,
        #                            config['gpm']['DeviceID'][2:])
        song_item = AudioItem("gpm", title, audio_id, system_location,
                              channel)
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
        if os.path.exists('vendor'):
            discord.opus.load_opus('vendor/lib/libopus.so.0')
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

    @commands.command(name='radio', pass_context=True)
    async def play_music_radio(self, ctx):
        """starts a radio based on a search query
        songs are taken off google play
        will only play after the immediate queue is clear"""
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

    @commands.command(name='queue', aliases=['q'], pass_context=True)
    async def get_queue(self, ctx):
        """sends the current queue to the chat"""
        if ctx.message.server.id in self.voice_connections:
            queue_string = await self.voice_connections[
                ctx.message.server.id].get_queue_string()
            if len(queue_string) > 0:
                await self.bot.send_message(ctx.message.channel, queue_string)

    @commands.command(name='stopradio', aliases=['sradio'], pass_context=True)
    async def stop_radio(self, ctx):
        """stops the radio!!!"""
        if ctx.message.server.id in self.voice_connections:
            await self.voice_connections[ctx.message.server.id].stop_radio()

async def check_gpm_auth(client_type=0):
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
