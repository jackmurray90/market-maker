import requests
from decimal import Decimal
from os.path import isfile
from time import sleep
from math import floor

HOST = 'https://fryx.finance'

if not isfile('.apikey'):
  api_key = requests.get(HOST + '/new_user').json()['api_key']
  with open('.apikey', 'w') as f:
    f.write(api_key)

api_key = open('.apikey', 'r').read()

def request(url, params={}):
  params['api_key'] = api_key
  response = requests.get(HOST + url, params)
  sleep(0.5)
  return response.json()

def round_to_18_decimal_places(amount):
  return floor(amount * 10**18) / Decimal(10**18)

def get_mid_market_rate():
  response = requests.get('https://api.kraken.com/0/public/Depth?pair=XMRBTC').json()
  kraken_min_ask = min([Decimal(ask[0]) for ask in response['result']['XXMRXXBT']['asks']])
  kraken_max_bid = max([Decimal(bid[0]) for bid in response['result']['XXMRXXBT']['bids']])
  return round_to_18_decimal_places((kraken_min_ask + kraken_max_bid) / Decimal('2.0'))

while True:
  balances = request('/balances')
  if Decimal(balances['BTC']) == 0 and Decimal(balances['XMR']) == 0:
    print("Both balances are zero, deposit some XMR and BTC to the following addresses and then press enter:")
    print(request('/deposit', {'currency': 'BTC'})['address'])
    print(request('/deposit', {'currency': 'XMR'})['address'])
    input()
    continue
  mid_market_rate = get_mid_market_rate()
  print("Kraken mid market rate is", mid_market_rate, "updating orders")
  orders = request('/orders')
  for order in orders:
    request('/cancel', {'order_id': order['id']})
  buy_price = round_to_18_decimal_places(mid_market_rate * Decimal('0.98'))
  sell_price = round_to_18_decimal_places(mid_market_rate * Decimal('1.02'))
  request('/buy', {'amount': '%0.18f'%round_to_18_decimal_places(Decimal(balances['BTC']) / buy_price), 'price': '%0.18f'%buy_price})
  request('/sell', {'amount': '%0.18f'%Decimal(balances['XMR']), 'price': '%0.18f'%sell_price})
  sleep(60)
