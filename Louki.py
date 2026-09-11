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

ANDROID_AUTH = "basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU="
USER_AGENT = ""
ANDROID_HEADER = {
	"Authorization": ANDROID_AUTH,
	"User-Agent": USER_AGENT
}

# Quest categories users rank via /stwquestprefs (must match the Discord
# bot's QuestRankingView.CATEGORIES). 'quest_ranking' on an account is a
# list of these category names in preference order.
CATEGORIES = [
	("Destroy things", lambda k: k.startswith("daily_destroy")),
	("Discover locations", lambda k: k.startswith("daily_discovery")),
	("Eliminate Husks as class", lambda k: k.startswith("daily_huskextermination") and any(x in k for x in ("anyhero", "constructor", "ninja", "outlander", "soldier"))),
	("Eliminate Husks with weapon/traps", lambda k: k.startswith("daily_huskextermination") and not any(x in k for x in ("anyhero", "constructor", "ninja", "outlander", "soldier"))),
	("Complete missions", lambda k: k.startswith("daily_mission_specialist_anyhero")),
	("Complete missions as class", lambda k: k.startswith("daily_mission_specialist") and "anyhero" not in k),
	("Mission objectives", lambda k: k in ("daily_explorezones", "daily_mission_buildradar")),
	("Save survivors", lambda k: k in ("daily_high_priority", "daily_partyof50")),
	("Loot", lambda k: k in ("daily_safes", "daily_treasurechests"))
]


class Louki:

	def __init__(self, acc, AccDB=None):
		self.BASIC_IOS_HEADER = {
			'Authorization': ANDROID_AUTH,
			'User-Agent': USER_AGENT
		}

		self.acc = acc
		self.AccDB = AccDB

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
		alphabet = string.ascii_letters + string.digits + "-_"
		return ''.join(secrets.choice(alphabet) for _ in range(length))

	def generate_custom_id(self):
		return f"FN-{self.random_string(22)}"

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

	async def AutoRotateQuest(self):
		"""Opt-in: spend the daily reroll on the account's least wanted active quest.

		'quest_ranking' is the account's category preference order (most
		wanted category first). Protected quests are never rerolled:
		- quests rewarding 150+ vBucks, and
		- quests belonging to one of the user's top 3 ranked categories
		  (or any ranked category, if the user ranked fewer than 3).
		Among the remaining candidates, a quest from a later (less
		wanted) category gets rerolled; unranked categories count as
		least wanted. If every active quest is protected, the reroll is
		skipped. Fortnite allows 1 reroll per day, so "Re-rolls
		exhausted" means today's reroll was already used.
		"""
		quests = await self.GetSTWDailyQuests()
		if not quests:
			return

		ranking = self.acc.get("quest_ranking") or []

		def preference(key):
			# Lower is more wanted; unranked quests rank below everything.
			return ranking.index(key) if key in ranking else len(ranking)

		def category_of(key):
			for category, match in CATEGORIES:
				if match(key):
					return category
			return None

		def is_protected(key):
			# Big reward: never give up 150 vBucks.
			if quests[key].get("reward", {}).get("vBucks", 0) >= 150:
				return True
			# Favourite categories: never touch the user's top 3.
			category = category_of(key)
			return category is not None and category in ranking[:3]

		candidates = [key for key in quests if not is_protected(key)]
		if not candidates:
			print(f"All active quests are protected (150 vB or top categories) for {self.acc['account_id']}; skipping rotation.")
			return

		def undesirability(key):
			# Sort key for "least wanted" among the non-protected
			# candidates: vBuck reward is the primary priority (a
			# cheaper quest goes first), then less preferred category,
			# then a stable key-name tiebreak.
			quest = quests[key]
			vb = quest.get("reward", {}).get("vBucks", 0)
			category = category_of(key)
			return (-vb, preference(category) if category else len(ranking), key)

		least_key = max(candidates, key=undesirability)
		least_quest = quests[least_key]
		try:
			await self.QueryMCP("FortRerollDailyQuest", "campaign", {"questId": least_quest["questId"]})
			print(f"Auto-rotated '{least_quest['description']}' for {self.acc['account_id']}.")
		except Exception as e:
			if "Re-rolls exhausted" in str(e):
				print(f"Daily reroll already used for {self.acc['account_id']}.")
			else:
				print(f"Failed to auto-rotate quest for {self.acc['account_id']}: {e}")

	async def ClaimDailyQuest(self, profileId):
		url = f"{FORTNITE_PUBLIC_ENDPOINT}profile/{self.acc['account_id']}/client/ClientQuestLogin?profileId={profileId}&rvn=-1"
		self.headers.update({
			"X-Epic-Correlation-ID": self.generate_custom_id()
		})
		async with AsyncSession(headers=self.headers) as r:
			response = await r.post(url, json={}, timeout=10)
			info = response.json()

		if profileId == "campaign" and "errorMessage" not in info:
			# Opt-in auto rotation replaces the least wanted quest once per day
			if self.acc.get("autorotate"):
				await self.AutoRotateQuest()

		if 'errorMessage' in info:
			if self.AccDB is not None:
				await self.AccDB.update_one({"user": self.acc["user"], "account_id" : self.acc["account_id"]},{"$set": { "autodaily": False }})
			print("Error claiming quest for {} thus disabling auto daily claim for it.".format(self.acc["account_id"]))
		else:
			print(f"Claimed {profileId} quest successfuly for {self.acc['account_id']}.")


	async def GetStorefront(self):
		url = "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/storefront/v2/catalog"
		self.headers.update({
			"X-Epic-Correlation-ID": self.generate_custom_id()
		})
		async with AsyncSession(headers=self.headers) as s:
			response = await s.get(url, timeout=20)
			store = response.json()
		return store

	async def ClaimFreeLlama(self):
		"""Claim the free llamas from the STW store (CardPackStorePreroll).

		Free llamas are 0-price offers that aren't one-time 'Always.' upgrade
		packs — they rotate in on some days and aren't always available. The
		server rejects the purchase with 'Preroll data is missing' until the
		store's x-ray preview exists for the account, so
		PopulatePrerolledOffers must run first. Only 0-price offers are ever
		purchased (expectedTotalPrice is always 0) — llamas that cost llama
		tickets or V-Bucks are never touched. Failures are logged and never
		propagate, so a llama problem can't break the daily claim flow.
		"""
		try:
			store = await self.GetStorefront()
			llama_store = next((f for f in store.get("storefronts", [])
								if f.get("name") == "CardPackStorePreroll"), None)
			if llama_store is None:
				return
			free = [e for e in llama_store.get("catalogEntries", [])
					if "always" not in e.get("devName", "").lower()
					and e.get("prices") and e["prices"][0].get("finalPrice") == 0]
			if not free:
				print(f"No free llamas in the store for {self.acc['account_id']}.")
				return

			# Roll the store's x-ray previews so the purchases are allowed.
			await self.QueryMCP("PopulatePrerolledOffers", "campaign")

			claimed = 0
			for offer in free:
				data = {
					"offerId": offer["offerId"],
					"purchaseQuantity": 1,
					"currency": "GameItem",
					"currencySubType": "AccountResource:currency_xrayllama",
					"expectedTotalPrice": 0,
					"gameContext": "fn"
				}
				# Some free offers allow several claims; keep buying until the
				# server says the limit is reached (same loop the game runs).
				for _ in range(10):
					try:
						info = await self.QueryMCP("PurchaseCatalogEntry", "common_core", data)
					except Exception as e:
						msg = str(e)
						if "limit of" in msg or "because fulfillment" in msg:
							# Already claimed today (or ever) — not an error.
							break
						if "catalog_out_of_date" in msg:
							# Only ever retry at 0; a changed nonzero price
							# means this offer is no longer free.
							print(f"Free llama offer changed price for {self.acc['account_id']}; skipping.")
							break
						raise e
					claimed += 1
					# Choice card packs the purchase left in the campaign
					# profile only pay out once an option is picked.
					for update in info.get("multiUpdate", []):
						if update.get("profileId") != "campaign":
							continue
						for change in update.get("profileChanges", []):
							item = change.get("item", {})
							if (change.get("changeType") == "itemAdded"
									and item.get("templateId", "").startswith("CardPack:")
									and item.get("attributes", {}).get("options")):
								await self.QueryMCP("OpenCardPack", "campaign",
									{"cardPackItemId": change["itemId"], "selectionIdx": 0})
			if claimed:
				print(f"Claimed {claimed} free llama(s) for {self.acc['account_id']}.")
			else:
				print(f"Free llamas already claimed for {self.acc['account_id']}.")
		except Exception as e:
			print(f"Failed to claim free llamas for {self.acc['account_id']}: {e}")

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
		await self.ClaimFreeLlama()
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
		response = await s.post(url, data=login_data, headers=ANDROID_HEADER)
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
