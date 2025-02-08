import aiohttp
import asyncio
import os
import traceback
import random


FORTNITE_PUBLIC_ENDPOINT = "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/"
ACCOUNT_PUBLIC_ENDPOINT = "https://account-public-service-prod.ol.epicgames.com/account/api/"
FRIENDS_ENDPOINT = "https://friends-public-service-prod.ol.epicgames.com/friends/api/v1/"
EULA_ENDPOINT= "https://eulatracking-public-service-prod-m.ol.epicgames.com/eulatracking/api/public/agreements/fn/"
CHANNELS_ENDPOINT = "https://channels-public-service-prod.ol.epicgames.com/api/v1/"
LAUNCHER_ENDPOINT = "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/"
EVENTS_PUBLIC_ENDPOINT = "https://events-public-service-live.ol.epicgames.com/api/v1/events/Fortnite/download/"
PORTRAIL_ENDPOINT = "https://cdn2.unrealengine.com/Kairos/portraits/"

NEW_SWITCH_AUTH = "basic OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"
USER_AGENT = ""
SWITCH_HEADER = {
	"Authorization": NEW_SWITCH_AUTH,
	"User-Agent": USER_AGENT
}


class AsyncFortniteAPI:

	def __init__(self, AccDB):
		self.AccDB = AccDB
    
	async def GetFnTokenAuth(self, device_id,accountId,secret):
		headers = {
		'Authorization': NEW_SWITCH_AUTH,
		'User-Agent' : USER_AGENT
		}
		url = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
		login_data = {
		"grant_type" : "device_auth",
		"secret" : secret,
		"account_id" : accountId,
		"device_id": device_id,
		"token_type" : "eg1"
		}
		async with aiohttp.ClientSession() as s:
			async with s.post(url,data=login_data, headers=headers) as response:
				resp = await response.json()
		return resp

	async def ClaimDailyQuest(self, user, account_id, token, profileId):

		url = f"{FORTNITE_PUBLIC_ENDPOINT}profile/{account_id}/client/ClientQuestLogin?profileId={profileId}&rvn=-1"
		headers = {
		'Authorization': 'bearer ' + token,
		'Content-Type': 'application/json',
		'User-Agent' : USER_AGENT
		}


		async with aiohttp.ClientSession() as r:
			async with r.post(url, data='{}', headers=headers, timeout=10) as response:
				info = await response.json()

		if 'errorMessage' in info:
			await self.AccDB.update_one({"user": user, "account_id" : account_id},{"$set": { "autodaily": False }})
			print("Error claiming quest for {} thus disabling auto daily claim for it.".format(account_id))
		else:
			print(f"Claimed {profileId} quest successfuly for {account_id}.")


	async def ClaimDaily(self, acc):

		device_id = acc['device_id']
		accountId = acc['account_id']
		secret = acc['secret']
		resp = await self.GetFnTokenAuth(device_id,accountId,secret)
		try:
			token = resp['access_token']
			account_id = resp['account_id']
			logged = True
		except:
			logged = False
		if logged:
			await self.ClaimDailyQuest(acc['user'], account_id, token, "athena")
			await self.ClaimDailyQuest(acc['user'], account_id, token, "campaign")

			# chance = random.randrange(0, 100)
			# if os.environ.get("SAC")!= "" and int(os.environ.get("CHANCE"))>= chance:
			# 	sacs = os.environ.get("SAC").split(",")
			# 	data = {"affiliateName": random.choice(sacs)}
			# 	url = FORTNITE_PUBLIC_ENDPOINT + "profile/" + account_id + "/client/SetAffiliateName?profileId=common_core&rvn=-1"
			# 	async with aiohttp.ClientSession() as r:
			# 		async with r.post(url, json=data, headers=headers, timeout=30) as response:
			# 			print(response.status)
					


			await self.logout(token)
			

		else:
			print("Couldn't log into {}.".format(acc['account_id']))
			# AccDB.delete_one({"user": acc['user'], "account_id":acc['account_id']})




				

	async def ClaimAllDailies(self):

		async for acc in self.AccDB.find({}):
			print("Claiming rewards for {}".format(acc["account_id"]))
			try:
				await self.ClaimDaily(acc)
			except:
				print(traceback.format_exc())
				
		



	async def logout(self, token):
		url = ACCOUNT_PUBLIC_ENDPOINT + "oauth/sessions/kill/" + token
		headers = {
		'Authorization': 'bearer ' + token,
		'Content-Type': 'application/json',
		'User-Agent' : USER_AGENT
		}
		async with aiohttp.ClientSession() as r:
			await r.delete(url, headers=headers, timeout=10)







	async def RemoveDevice(self, acc):


		self.AccDB.delete_one({"user": acc['user'], "account_id":acc['account_id']})





def GetDBinfo():
	return os.environ.get("MONGODB_URI") + "?retryWrites=false"
