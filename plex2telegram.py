import logging
import asyncio
import time
import os
import yaml
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie
from plexapi import utils


with open("config.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# Send the data to Telegram
async def send_to_telegram(plexvids):
    async with Bot(token=cfg["telegram"]["bot_token"]) as bot:
        for x in plexvids:
            logging.info(f"Sending {x} to Telegram")
            await bot.send_photo(chat_id=cfg["telegram"]["chat_id"],
                photo=open(x['image'], "rb"),
                caption=x['text'],
                parse_mode=ParseMode.HTML
                )
            time.sleep(5) # maybe avoids some flooding


# Gets all of the recent plex videos and their cover art
def get_recent_plex_vids(image_folder="/tmp/plexart"):
    plex = PlexServer(cfg["plex"]["url"], cfg["plex"]["token"])
    os.makedirs(image_folder, exist_ok=True)

    recent = []
    for section in cfg["plex"]["movie_libs"]:
        recent = recent + plex.library.section(section).recentlyAdded(libtype="movie")
    for section in cfg["plex"]["episode_libs"]:
        recent = recent + plex.library.section(section).recentlyAdded(libtype="episode")
    recent.sort(key=lambda x: x.addedAt)

    list = []
    for i in recent:
        guid = i.guid.split('/')[-1]

        if isinstance(i,Episode):
            title = f"{i.grandparentTitle} ({i.parentTitle})\nEpisode {i.index} - {i.title}"
        elif isinstance(i,Movie):
            title = f"{i.title} ({i.year})"

        time = i.addedAt
        text = f"<b>{title}</b>\nNow Available on Plex"

        imgfile = f"{guid}.jpg"
        if not os.path.isfile(f"{image_folder}/{imgfile}"):
            utils.download(cfg["plex"]["url"] + i.art, cfg["plex"]["token"], imgfile, image_folder)

        list.append({
            "text": text,
            "guid": guid,
            "image": f"{image_folder}/{imgfile}",
            "time": time
            })

    logging.info(f"Retrieved {len(list)} videos from Plex")
    return list


# Restore the last time we saw
last_time = datetime.now()
try:
    with open(cfg["lasttime_file"], 'r') as f:
        last_time = datetime.fromtimestamp(float(f.readline().rstrip()))
    logging.info(f"Loaded last time from {cfg['lasttime_file']}: {last_time}")
except:
    logging.info(f"Couldn't load {cfg['lasttime_file']}. Defaulting to now")


# Main loop
done = False
while not done:
    try:
        # look for new videos since previous checks
        new_lasttime = last_time
        newvids = []
        for vid in get_recent_plex_vids():
            if vid['time'] <= last_time:
                continue

            if vid['time'] > new_lasttime:
                new_lasttime = vid['time']
            newvids.append(vid)

        # if we have new results
        if len(newvids) > 0:
            asyncio.run(send_to_telegram(newvids))
            with open(cfg["lasttime_file"], "w") as f:
                f.write(f"{new_lasttime.timestamp()}")
            logging.info(f"Saved new last time to {cfg['lasttime_file']}: {new_lasttime}")
            last_time = new_lasttime

    except KeyboardInterrupt:
        logging.info("Exiting due to keyboard interrupt")
        done = True
        break

    time.sleep(cfg["poll_interval"])
