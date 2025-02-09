import traceback
from Louki import *
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os

def GetDBinfo():
	return os.environ.get("MONGODB_URI") + "?retryWrites=false"

async def claim_all_dailies():
    load_dotenv()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(GetDBinfo())
    db = client.get_default_database()
    AccDB = db['accounts']

    # Loop through all accounts
    async for acc in AccDB.find({"autodaily": True}):
        try:
            async with Louki(acc) as L:
                await L.ClaimDaily()
        except:
            print(traceback.format_exc())

# Run the async function
if __name__ == "__main__":
    asyncio.run(claim_all_dailies())