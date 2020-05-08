from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
# For using sleep function because selenium
# works only when the all the elemets of the
# page is loaded.
import time
import jdatetime

import configparser
import json
# Proxy Server
from browsermobproxy import Server

# Process Responce
from objectpath import *

import requests

import uuid 
from tehran_stocks import Stocks, db
# Reading Config
config = configparser.ConfigParser()  # 3
config.read('mofid.cfg')


def getAuthKey():
    username = config['Users']['username']
    password = config['Users']['password']
    proxyServerAddress = config['config']['proxyserverpath']

    # Creating Proxy server
    server = Server(proxyServerAddress)
    server.start()
    proxy = server.create_proxy()
    proxy.whitelist(regexp='*emofid.com*', status_code=123)
    proxy.new_har(title="mofid", options={
        'captureContent': False, 'captureBinaryContent': False, 'captureHeaders': True})

    # Creating browser
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument("--proxy-server={0}".format(proxy.proxy))
    browser = webdriver.Chrome(chrome_options=chrome_options)

    url = "https://account.emofid.com/Login?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Deasy2_client_pkce%26redirect_uri%3Dhttps%253A%252F%252Fd.easytrader.emofid.com%252Fauth-callback%26response_type%3Dcode%26scope%3Deasy2_api%2520openid%26state%3Df8ff796b1d994e0d8f6fa1f6e878f165%26code_challenge%3D7qf19ieakAg4BvrDkBTHbr5h7_A0BSvci7dtp-0ZUWY%26code_challenge_method%3DS256%26response_mode%3Dquery"
    browser.get(url)

    userFiled = browser.find_element_by_xpath('//*[@id="Username"]')
    userFiled.clear()
    userFiled.send_keys(username)

    passwordFiled = browser.find_element_by_xpath('//*[@id="Password"]')
    passwordFiled.clear()
    passwordFiled.send_keys(password, Keys.RETURN)

    element = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, "/html/body/app-root/d-release-notes/div/div/button"))
    )
    element.click()

    try:
        browser.find_element_by_xpath(
            '//*[@id="root"]/main/div[2]/div[1]/ul[2]/li[1]/span/i').click()
    except:
        print('Error')

    with open('data.json', 'w') as outfile:
        json.dump(proxy.har, outfile)

    server.stop()

    tree = Tree(proxy.har)
    authKey = ''
    result = tree.execute(
        "$.log.entries.request[@.url is 'https://d11.emofid.com/easy/api/account/checkuser'].headers")
    for entry in result:
        for e in entry:
            if e['name'] == 'Authorization':
                authKey = e["value"]
    return authKey


def getHeaders(authKey):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://d.easytrader.emofid.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36'
    }
    headers['Authorization'] = authKey


def getAccountRemaining(headers):
    url = 'https://d11.emofid.com/easy/api/Money/GetRemain'
    return requests.get(url, headers=headers, verify=False, timeout=(10, 20)).json()


def getSymbolPriceDetails(headers, symbol):
    url = f'https://d11.emofid.com/easy/api/MarketData/GetSymbolDetailsData/{symbol}/StockOrderData'
    return requests.get(url, headers=headers, verify=False, timeout=(10, 20)).json()


def getSymbolDetails(headers, symbol):
    url = f'https://d11.emofid.com/easy/api/MarketData/GetSymbolDetailsData/{symbol}/SymbolInfo'
    return requests.get(url, headers=headers, verify=False, timeout=(10, 20)).json()


def getTodayOHLC(headers, symbol):
    url = f'https://d11.emofid.com/easy/api/CandleChart/GetTodayTrend/{symbol}'
    return requests.get(url, headers=headers, verify=False, timeout=(10, 20)).json()


def sendOrder(headers, symbol, price, quantity, side):
    headers['Content-Type'] = 'application/json'
    sendOrderurl = 'https://d11.emofid.com/easy/api/OmsOrder'
    postData = {
        "easySource": 1,
        "financeId": 1,
        "isSplitOrder": "false",
        "isin": symbol,
        "price": price,
        "quantity": quantity,
        "referenceKey":str(uuid.uuid4()) ,
        "referenceKeys": [],
        "side": side,
        "validityDateJalali": jdatetime.date.today().strftime('%Y/%m/%d'),
        "validityType": 74
    }
    response = requests.post(sendOrderurl, data=json.dumps(postData), headers=headers, verify=False, timeout=(10, 20))
    return response

def getOrders(headers):
    url = 'https://d11.emofid.com/easy/api/Order'
    return requests.get(url, headers=headers, verify=False, timeout=(10, 20)).json()


stock = Stocks.query.filter_by(name='كگل')