from AsyncFortniteAPI import *
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


if __name__ == "__main__":
    load_dotenv()
    client = AsyncIOMotorClient(GetDBinfo())
    db = client.get_default_database()
    AccDB = db['accounts']
    fClient = AsyncFortniteAPI(AccDB)
    fClient.ClaimAllDailies()