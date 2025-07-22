import json
import os
import random
import asyncio
import secrets
import uuid
from curl_cffi.requests import AsyncSession
import string


FORTNITE_PUBLIC_ENDPOINT = "https://mcp-gc.live.fngw.ol.epicgames.com/fortnite/api/game/v2/"
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

	def generate_id(self, prefix="FRONTEND"):
		random_hex = secrets.token_hex(16).upper()
		return f"{prefix}-{random_hex}"

	def random_string(self, length):
		alphabet = string.ascii_letters + string.digits
		return ''.join(secrets.choice(alphabet) for _ in range(length))

	def generate_custom_id(self):
		part1 = self.random_string(9)
		part2 = self.random_string(12)
		return f"FN-{part1}-{part2}"

	def generate_guid_with_braces(self):
		return "{" + str(uuid.uuid4()).upper() + "}"


	async def Login(self):
		# print("Logging in")
		if self.acc["secret"]:
			self.token = await self.GetFnTokenAuth()
	
		self.headers = {
			"Authorization": "bearer " + self.token,
			"User-Agent": USER_AGENT,
			"X-EpicGames-GameSessionId": self.generate_id(),
            "X-EpicGames-AnalyticsSessionId": self.generate_guid_with_braces()
		}

	async def Logout(self):
		url = "{}oauth/sessions/kill/{}".format(ACCOUNT_PUBLIC_ENDPOINT, self.token)
		self.headers.update({
			"X-Epic-Correlation-ID": self.generate_custom_id()
		})
		async with AsyncSession(headers=self.headers) as s:
			await s.delete(url, timeout=10)

	async def GetToken(self, login_data):
		url = "{}oauth/token".format(ACCOUNT_PUBLIC_ENDPOINT)
		self.BASIC_IOS_HEADER.update({
			"X-Epic-Correlation-ID": self.generate_custom_id()
		})
		async with AsyncSession(headers=self.BASIC_IOS_HEADER) as s:
			response = await s.post(url, data=login_data)
			resp = response.json()

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

		if isinstance(body, str):
			body = json.loads(body)

		self.headers.update({
			"X-Epic-Correlation-ID": self.generate_custom_id(),
			"X-EpicGames-ProfileRevisions": '[{"profileId":"' + profile + '","clientCommandRevision":'+ str(rvn) + '}]'
		})

		async with AsyncSession(headers=self.headers) as s:
			response = await s.post(url, json=body, timeout=20)
			info = response.json()

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
		url = f"{FORTNITE_PUBLIC_ENDPOINT}profile/{self.acc['account_id']}/client/ClientQuestLogin?profileId={profileId}&rvn=-1"
		self.headers.update({
			"X-Epic-Correlation-ID": self.generate_custom_id()
		})
		async with AsyncSession(headers=self.headers) as r:
			response = await r.post(url, json={}, timeout=10)
			info = response.json()

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
			print(f"Claimed {profileId} quest successfuly for {self.acc['account_id']}.")


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

		return info["profileCommandRevision"], collectorItems, resource, amount

	async def SpendResearch(self, StatId):
		info = await self.QueryMCP("QueryProfile", "campaign")
		for each in info["profileChanges"][0]["profile"]["items"]:
			if info["profileChanges"][0]["profile"]["items"][each]["templateId"].startswith("Token:collectionresource"):
				resource = each
				break
		rvn = info["profileCommandRevision"]
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
							print(f"Claimed {modified['quantity']} resources for {self.acc['account_id']}.")
			mods = {k: v % 10 for k, v in Stats.items()}

			if len(set(mods.values())) == 1:
				# All stats have the same mod 10 → level the lowest stat
				chosen_stat = min(Stats, key=Stats.get)
			else:
				# Choose the stat with the highest mod 10
				chosen_stat = max(mods, key=mods.get)

			if Stats[chosen_stat] < 120:
				info, resource = await self.SpendResearch(chosen_stat)
		chance = random.randrange(0, 100)
		if os.environ.get("SAC")!= "" and int(os.environ.get("CHANCE"))>= chance:
			sacs = os.environ.get("SAC").split(",")
			await self.SetSaC(sacs)


async def GetClientToken():
	url = "{}oauth/token".format(ACCOUNT_PUBLIC_ENDPOINT)
	login_data = {
		"grant_type": "client_credentials",
		"token_type": "eg1"
	}
	async with AsyncSession() as s:
		response = await s.post(url, data=login_data, headers=SWITCH_HEADER)
		token = response.json()['access_token']
	return token

async def GetClientVersion():
	global USER_AGENT
	token = await GetClientToken()
	headers = {
		'Authorization': 'bearer ' + token,
		'User-Agent': USER_AGENT
	}
	url = "{}public/assets/v2/platform/Windows/namespace/fn/catalogItem/4fe75bbc5a674f4f9b356b5c90567da5/app/Fortnite/label/Live".format(
		LAUNCHER_ENDPOINT)
	async with AsyncSession() as s:
		response = await s.get(url, headers=headers)
		versioninfo = response.json()['elements'][0]['buildVersion']
	USER_AGENT = "Fortnite/" + versioninfo[:-8] + " Windows/10.0.26100.1.256.64bit"
