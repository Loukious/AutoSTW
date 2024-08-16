import asyncio
import tornado.escape
import tornado.ioloop
import tornado.locks
import tornado.web
import os.path
import aiocron
from AsyncFortniteAPI import *
from dotenv import load_dotenv



async def webhook(msg):

    url = "https://discord.com/api/webhooks/1012083072390418512/giO9hbpkeGkpGScAjgYjiVv3rWvsWZgrJ2upeIjhLeo_Tbtcm60ZVpVOBV8NMaljPkcr"

    data = {
        "username": "Auto STW rewards Claiming bot",
        "content" : msg
    }

    async with aiohttp.ClientSession() as r:
        await r.post(url, json=data, timeout=10)


@aiocron.crontab('1 0 */7 * *')
async def attime():
    # await webhook("<@&852445293974650900> claiming STW rewards started..")
    print("Started claiming rewards..")
    await fClient.ClaimAllDailies()
    print("Done claiming rewards..")
    # await webhook("<@&852445293974650900> claiming STW rewards done.")





class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write("You're not supposed to be here!")
        

class ClaimDailiesHandler(tornado.web.RequestHandler):
    async def post(self):
        print("Started claiming rewards..")
        await fClient.ClaimAllDailies()
        print("Done claiming rewards..")
        self.write("Claimed all dailies successfully!")


if __name__ == "__main__":
    load_dotenv()
    client = AsyncIOMotorClient(GetDBinfo())
    db = client.get_default_database()
    AccDB = db['accounts']
    fClient = AsyncFortniteAPI(AccDB)

    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/claim-dailies", ClaimDailiesHandler)
        ])

    port = int(os.getenv('PORT', 80))
    app.listen(port, address='0.0.0.0')
    print("Server started!")
    asyncio.get_event_loop().run_forever()
    tornado.ioloop.IOLoop.current().start()