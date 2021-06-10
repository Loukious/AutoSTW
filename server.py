import asyncio
import tornado.escape
import tornado.ioloop
import tornado.locks
import tornado.web
import os.path
import uuid
import aiocron
from AsyncFortniteAPI import *
from motor.motor_asyncio import AsyncIOMotorClient




async def webhook(msg):

    url = "https://discord.com/api/webhooks/852610375497285662/pCoohygNyds_po2BbACRDiEoEavz0PWbYiR7-35-1AB9T5X2FXiGDk2c3T-3QoH2Ubm7"

    data = {
        "username": "Auto STW rewards Claiming bot",
        "content" : msg
    }

    async with aiohttp.ClientSession() as r:
        await r.post(url, json=data, timeout=10)


@aiocron.crontab('14 18 * * *')
async def attime():
    await webhook("@here claiming STW rewards started..")
    print("Started claiming rewards..")
    await ClaimAllDailies()
    print("Done claiming rewards..")
    await webhook("@here claiming STW rewards done.")





class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write("You're not supposed to be here!")
        


if __name__ == "__main__":

    app = tornado.web.Application(
        [
            (r"/", MainHandler)
        ])
    app.listen(int(os.getenv('PORT', 80)))
    print("Server started!")
    asyncio.get_event_loop().run_forever()
    tornado.ioloop.IOLoop.current().start()