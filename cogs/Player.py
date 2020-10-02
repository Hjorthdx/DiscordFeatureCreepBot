import discord, os
from discord.ext import commands

class Player(commands.Cog):
    # Some documentation

    def __init__(self, bot):
        self.bot = bot
        self.basePath = "C:/Users/Sren/Documents/GitHub/DiscordKarmaBot/mp3-files/"
        self.queue = asyncio.Queue()
        self.ctxList = []
        self.next = asyncio.Event()
        self.bot.loop.create_task(self.audioPlayerTask())

    @commands.Cog.listener()
    async def on_ready(self):
        print("Player cog is loaded")

    async def audioPlayerTask(self):
        while True:
            self.next.clear()
            currentSong = await self.queue.get()
            ctx = self.ctxList.pop(0)
            async with ctx.typing():
                x = await YTDLSource.from_url(currentSong, loop=self.bot.loop, stream=True)
                ctx.voice_client.play(x, after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set))
            await ctx.send('Now playing: {}'.format(x.title), delete_after=x.duration)
            await self.next.wait()
       
    # Not changed to the queue system yet. So this will likely break if tried while bot is already playing something.
    @commands.command(brief="play slet dem. !available for list of all mp3's")
    async def play(self, ctx, *, userInput):
        mp3 = self.basePath + userInput + ".mp3"
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(mp3))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
        await ctx.message.delete()

    @commands.command(help="yt youtube link", aliases=['youtube'])
    async def yt(self, ctx, *, url):
        await self.queue.put(url)
        self.ctxList.append(ctx)
        await ctx.message.delete()

    @commands.command(help="Shows all the current mp3 files")
    async def available(self, ctx):
        availableMp3Files = "```"
        for filename in os.listdir('c:/Users/Sren/Documents/GitHub/DiscordKarmaBot/mp3-files'):
            if filename.endswith('.mp3'):
                availableMp3Files += f"{filename[:-4]}\n"
        availableMp3Files+="```"
        await ctx.send(availableMp3Files, delete_after=15)
        await ctx.message.delete()

    @commands.command(brief="Changes the volume the bot is playing", help="I.e. !volume 60 sets the volume to 60%", aliases=['v'])
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume), delete_after=15)
        await ctx.message.delete()

    @commands.command(help="Makes the bot join a desired voice channel")
    async def connect(self, ctx, *, channel: discord.VoiceChannel = None):
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
            await ctx.message.delete()
            return
        
        if channel is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                await ctx.message.delete()
                return
                
        await channel.connect()
        await ctx.message.delete()

    @commands.command(help="Makes the bot leave voice channel")
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()
        await ctx.message.delete()

    @commands.command(brief="Pauses the current song")
    async def pause(self, ctx):
        ctx.voice_client.pause()
        await ctx.send("Paused", delete_after=15)
        await ctx.message.delete()

    @commands.command(brief="Resumes the current song")
    async def resume(self, ctx):
        ctx.voice_client.resume()
        await ctx.send("Resumed", delete_after=15)
        await ctx.message.delete()
    
    @commands.command(help="Command for the Pomodoro cog to utilize", self_bot=True, hidden=True)
    async def PlayPomodoro(self, ctx):
        if ctx.voice_client.is_playing():
            print("Pausing song to play pomodoro timer")
            x = ctx.voice_client.source
            ctx.voice_client.pause()
            timerSound = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.basePath + "Lyt nu.mp3"))
            ctx.voice_client.play(timerSound, after=lambda e: print('Player error: %s' % e) if e else None)
            while ctx.voice_client.is_playing():
                await asyncio.sleep(1)
            print("Trying to replay song")
            ctx.voice_client.play(x, after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set))
        else:    
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.basePath + "Lyt nu.mp3"))
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

    @play.before_invoke
    @yt.before_invoke
    @PlayPomodoro.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")

def setup(bot):
    bot.add_cog(Player(bot))


import asyncio, youtube_dl

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

