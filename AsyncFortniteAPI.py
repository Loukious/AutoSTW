import aiohttp
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import traceback
import json
from time import strftime
from collections import deque, OrderedDict
import concurrent.futures
import math
import numpy
from functools import partial
import datetime


FORTNITE_PUBLIC_ENDPOINT = "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/"
ACCOUNT_PUBLIC_ENDPOINT = "https://account-public-service-prod.ol.epicgames.com/account/api/"
FRIENDS_ENDPOINT = "https://friends-public-service-prod.ol.epicgames.com/friends/api/v1/"
EULA_ENDPOINT= "https://eulatracking-public-service-prod-m.ol.epicgames.com/eulatracking/api/public/agreements/fn/"
CHANNELS_ENDPOINT = "https://channels-public-service-prod.ol.epicgames.com/api/v1/"
LAUNCHER_ENDPOINT = "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/"
EVENTS_PUBLIC_ENDPOINT = "https://events-public-service-live.ol.epicgames.com/api/v1/events/Fortnite/download/"
PORTRAIL_ENDPOINT = "https://cdn2.unrealengine.com/Kairos/portraits/"

SWITCH_AUTH = "basic NTIyOWRjZDNhYzM4NDUyMDhiNDk2NjQ5MDkyZjI1MWI6ZTNiZDJkM2UtYmY4Yy00ODU3LTllN2QtZjNkOTQ3ZDIyMGM3"
IOS_AUTH = "basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE="
USER_AGENT = ""
SWITCH_HEADER = {
	"Authorization": SWITCH_AUTH,
	"User-Agent": USER_AGENT
}


async def GetClientToken():
	url = ACCOUNT_PUBLIC_ENDPOINT + "oauth/token"
	login_data = {
	"grant_type" : "client_credentials",
	"token_type" : "eg1"
	}
	async with aiohttp.ClientSession() as s:
		async with s.post(url,data=login_data, headers=SWITCH_HEADER) as response:
			token = (await response.json())['access_token']
	return token


async def GetClientVersion():
	token = await GetClientToken()
	headers = {
	'Authorization': 'bearer ' + token,
	'User-Agent' : USER_AGENT
	}
	url = LAUNCHER_ENDPOINT + "public/assets/v2/platform/Windows/namespace/fn/catalogItem/4fe75bbc5a674f4f9b356b5c90567da5/app/Fortnite/label/Live"
	async with aiohttp.ClientSession() as s:
		async with s.get(url, headers=headers) as response:
			versioninfo = (await response.json())['elements'][0]['buildVersion']
	return "Fortnite/" + versioninfo[:-8] + " Windows/10.0.19042.1.256.64bit"





async def GetFnTokenAuth(device_id,accountId,secret):
	headers = {
	'Authorization': IOS_AUTH,
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




async def ClaimDaily(acc):
	global AccDB

	device_id = acc['device_id']
	accountId = acc['account_id']
	secret = acc['secret']
	resp = await GetFnTokenAuth(device_id,accountId,secret)
	try:
		token = resp['access_token']
		account_id = resp['account_id']
		logged = True
	except:
		logged = False
	if logged:
		url = FORTNITE_PUBLIC_ENDPOINT + "profile/" + account_id + "/client/ClaimLoginReward?profileId=campaign&rvn=-1"
		headers = {
		'Authorization': 'bearer ' + token,
		'Content-Type': 'application/json',
		'User-Agent' : USER_AGENT
		}
		async with aiohttp.ClientSession() as r:
			async with r.post(url, data='{}', headers=headers, timeout=10) as response:
				info = await response.json()
		await logout(token)
		
		if 'errorMessage' in info:
			await AccDB.update_one({"user": acc['user'], "account_id" : accountId},{"$set": { "autodaily": False }})
			print("Error claiming rewards for {} thus disabling auto daily claim for it.".format(acc['account_id']))
		else:
			print("Claimed reward successfuly for {}.".format(acc['account_id']))

	else:
		print("Couldn't log into {} thus deleting it from the DB.".format(acc['account_id']))
		AccDB.delete_one({"user": acc['user'], "account_id":acc['account_id']})



async def keepawake():
    url = "https://autostw.onrender.com"
    async with aiohttp.ClientSession() as r:
        await r.get(url, timeout=10)

			

async def ClaimAllDailies():
	global AccDB
	async for acc in AccDB.find({"autodaily": True}):
		print("Claiming rewards for {}".format(acc["account_id"]))
		await keepawake()
		try:
			await ClaimDaily(acc)
		except:
			print(traceback.format_exc())
			
	




async def GetFnTokenAuthCode(code):
	headers = {
	'Authorization': IOS_AUTH,
	'User-Agent': USER_AGENT
	}
	url = ACCOUNT_PUBLIC_ENDPOINT + "oauth/token"
	login_data = {
	"grant_type" : "authorization_code",
	"code" : code,
	"includePerms" : False,
	"token_type" : "eg1"
	}
	async with aiohttp.ClientSession() as s:
		async with s.post(url,data=login_data, headers=headers) as response:
			resp = await response.json()
	return resp


async def logout(token):
	url = ACCOUNT_PUBLIC_ENDPOINT + "oauth/sessions/kill/" + token
	headers = {
	'Authorization': 'bearer ' + token,
	'Content-Type': 'application/json',
	'User-Agent' : USER_AGENT
	}
	async with aiohttp.ClientSession() as r:
		await r.delete(url, headers=headers, timeout=10)







async def RemoveDevice(acc):
	global AccDB

	AccDB.delete_one({"user": acc['user'], "account_id":acc['account_id']})





def GetDBinfo():
	return os.environ.get("MONGODB_URI") + "?retryWrites=false"


client = AsyncIOMotorClient(GetDBinfo())
db = client.get_default_database()
AccDB = db['accounts']


loop = asyncio.get_event_loop()
USER_AGENT = loop.run_until_complete(GetClientVersion())
