import json
import os
import random
import aiohttp
import asyncio



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


class Louki:

	def __init__(self, acc):
		self.BASIC_IOS_HEADER = {
			'Authorization': NEW_SWITCH_AUTH,
			'User-Agent': USER_AGENT
		}

		self.acc = acc

	async def __aenter__(self):
		await self.Login()
		return self

	async def __aexit__(self, *exc):
		await self.Logout()

	def __enter__(self):
		# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		loop = asyncio.get_event_loop()
		loop.run_until_complete(self.Login())
		return self

	def __exit__(self, *exc):
		# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		loop = asyncio.get_event_loop()
		loop.run_until_complete(self.Logout())

	async def Login(self):
		# print("Logging in")
		if self.acc["secret"]:
			self.token = await self.GetFnTokenAuth()
	
		self.headers = {
			"Authorization": "bearer " + self.token,
			"User-Agent": USER_AGENT
		}

	async def Logout(self):
		url = "{}oauth/sessions/kill/{}".format(
			ACCOUNT_PUBLIC_ENDPOINT, self.token)
		async with aiohttp.ClientSession(headers=self.headers) as s:
			await s.delete(url, timeout=10)

	async def GetToken(self, login_data):
		url = "{}oauth/token".format(ACCOUNT_PUBLIC_ENDPOINT)
		async with aiohttp.ClientSession(headers=self.BASIC_IOS_HEADER) as s:
			async with s.post(url, data=login_data) as response:
				resp = await response.json()
		if "access_token" in resp:
			self.account_id = resp["account_id"]
			return resp["access_token"]
		else:
			if "errorMessage" in resp:
				resp["errorMessage"] = resp["errorMessage"].replace("'", "")
			raise Exception(resp)

	async def GetFnTokenAuth(self):
		login_data = {
			"grant_type": "device_auth",
			"secret": self.acc["secret"],
			"account_id": self.acc["account_id"],
			"device_id": self.acc["device_id"],
			"token_type": "eg1"
		}
		return await self.GetToken(login_data)

	async def QueryMCP(self, command, profile, body={}, rvn=-1):
		url = "{}profile/{}/client/{}?profileId={}&rvn={}".format(
			FORTNITE_PUBLIC_ENDPOINT, self.acc["account_id"], command, profile, rvn)
		if type(body) == str:
			body = json.loads(body)
		async with aiohttp.ClientSession(headers=self.headers) as s:
			async with s.post(url, json=body, timeout=20) as response:
				info = await response.json()
		if "errorMessage" in info:
			info["errorMessage"] = info["errorMessage"].replace("'", "")
			raise Exception(info)
		return info

	async def GetStats(self):
		info = await self.QueryMCP("QueryProfile", "campaign")
		if "profileChanges" in info and len(info["profileChanges"]) > 0:
			profile = info["profileChanges"][0]["profile"]
			if "stats" in profile and "attributes" in profile["stats"]:
				stats = profile["stats"]["attributes"]
				if "research_levels" in stats:
					return stats["research_levels"]
		return {}


	async def GetSTWDailyQuests(self):
		info = await self.QueryMCP("QueryProfile", "campaign")
		found = {}
		with open('DailyQuestsInfo.json', 'r') as file:
			quests_info = json.load(file)
			for item in info["profileChanges"][0]["profile"]["items"]:
				if info["profileChanges"][0]["profile"]["items"][item]["templateId"].split(":")[1] in quests_info.keys():
					if info["profileChanges"][0]["profile"]["items"][item]["attributes"]["quest_state"] == "Active":
						quests_info[info["profileChanges"][0]["profile"]["items"][item]["templateId"].split(":")[1]]["questId"] = item
						found[info["profileChanges"][0]["profile"]["items"][item]["templateId"].split(":")[1]] = quests_info[info["profileChanges"][0]["profile"]["items"][item]["templateId"].split(":")[1]]
		
		sorted_found = dict(sorted(found.items()))
		return sorted_found

	async def ReplaceSTWDailyQuest(self, templateId):
		data = {
			"questId": templateId
		}
		await self.QueryMCP("FortRerollDailyQuest", "campaign", data)

		return await self.GetSTWDailyQuests()

	async def ClaimDailyQuest(self, profileId):

		url = f"{FORTNITE_PUBLIC_ENDPOINT}profile/{self.acc["account_id"]}/client/ClientQuestLogin?profileId={profileId}&rvn=-1"
		headers = {
		'Authorization': 'bearer ' + self.token,
		'Content-Type': 'application/json',
		'User-Agent' : USER_AGENT
		}

		async with aiohttp.ClientSession(headers=self.headers) as r:
			async with r.post(url, data='{}', headers=headers, timeout=10) as response:
				info = await response.json()
		if profileId == "campaign" and "errorMessage" not in info:
    		# Get current daily quests
			quests = await self.GetSTWDailyQuests()
			
			# Filter quests with 80 vBucks reward
			vbucks_quests = []
			for quest in quests.values():
				if quest.get('reward', {}).get('vBucks', 0) == 80:
					vbucks_quests.append(quest)
			
			if not vbucks_quests:
				return quests  # No 80 vBucks quests to replace
			
			# Split quests into Eliminate and non-Eliminate
			eliminate_quests = []
			other_quests = []
			for quest in vbucks_quests:
				if 'Eliminate' in quest['description']:
					eliminate_quests.append(quest)
				else:
					other_quests.append(quest)
			
			# Determine which quest to replace
			if other_quests:
				quest_to_replace = other_quests[0]
			else:
				quest_to_replace = eliminate_quests[0]
			
			# Replace the selected quest using its questId
			await self.ReplaceSTWDailyQuest(quest_to_replace['questId'])
			print(f"Replaced {quest_to_replace['description']} quest for {self.acc['account_id']}.")

		if 'errorMessage' in info:
			await self.AccDB.update_one({"user": self.acc["user"], "account_id" : self.acc["account_id"]},{"$set": { "autodaily": False }})
			print("Error claiming quest for {} thus disabling auto daily claim for it.".format(self.acc["account_id"]))
		else:
			print(f"Claimed {profileId} quest successfuly for {self.acc["account_id"]}.")


	async def GetCollectors(self):
		info = await self.QueryMCP("QueryProfile", "campaign")

		collectorItems = []
		resource = ""
		amount = 0
		for each in info["profileChanges"][0]["profile"]["items"]:
			if info["profileChanges"][0]["profile"]["items"][each]["templateId"].startswith("CollectedResource"):
				collectorItems.append(each)

			elif info["profileChanges"][0]["profile"]["items"][each]["templateId"].startswith("Token:collectionresource"):
				resource = each
				amount = info["profileChanges"][0]["profile"]["items"][each]["quantity"]

		return info["profileChangesBaseRevision"], collectorItems, resource, amount

	async def SpendResearch(self, StatId):
		info = await self.QueryMCP("QueryProfile", "campaign")
		for each in info["profileChanges"][0]["profile"]["items"]:
			if info["profileChanges"][0]["profile"]["items"][each]["templateId"].startswith("Token:collectionresource"):
				resource = each
				break
		rvn = info["profileChangesBaseRevision"]
		data = {
			"statId": StatId
		}
		sinfo = await self.QueryMCP("PurchaseResearchStatUpgrade", "campaign", data, rvn)
		return sinfo, resource

	async def SetSaC(self, sacs):
		data = {
			"affiliateName": random.choice(sacs)
		}
		await self.QueryMCP("SetAffiliateName", "common_core", data)
		return True

	async def ClaimDaily(self):

		await self.ClaimDailyQuest("athena")
		await self.ClaimDailyQuest("campaign")
		Stats = {
			"fortitude": 0,
			"offense": 0,
			"resistance": 0,
			"technology": 0
		}
		Stats = {**Stats, **(await self.GetStats())}
		if Stats and Stats != {}:
			rvn, collectorItems, resource, amount = await self.GetCollectors()
			if collectorItems != []:
				body = {
					"collectorsToClaim": collectorItems
				}
				info = await self.QueryMCP("ClaimCollectedResources", "campaign", body, rvn)
				for modified in info["profileChanges"]:
					if "itemId" in modified:
						if modified["itemId"] == resource:
							print(f"Claimed {modified["quantity"]} resources for {self.acc["account_id"]}.")

			lowest_stat_key = min(Stats, key=Stats.get)
			if Stats[lowest_stat_key] < 120:
				info, resource = await self.SpendResearch(lowest_stat_key)
		chance = random.randrange(0, 100)
		if os.environ.get("SAC")!= "" and int(os.environ.get("CHANCE"))>= chance:
			sacs = os.environ.get("SAC").split(",")
			await self.SetSaC(sacs)