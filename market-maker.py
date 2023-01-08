import requests
from decimal import Decimal
from os.path import isfile
from time import sleep
from math import floor, ceil
from kraken import kraken_request

HOST = 'https://fryx.finance'

THRESHOLD = Decimal('3.22')

if not isfile('.apikey'):
  api_key = requests.get(HOST + '/new_user').json()['api_key']
  with open('.apikey', 'w') as f:
    f.write(api_key)

api_key = open('.apikey', 'r').read()

def format_decimal(d, decimal_places):
  digit = Decimal('10')
  while digit <= d:
    digit *= 10
  result = ''
  while decimal_places:
    result += str(floor(d % digit * 10 / digit))
    digit /= 10
    if digit == 1:
      result += '.'
    if digit < 1:
      decimal_places -= 1
  return result

def round_xmr(amount):
  return floor(amount * 10**12) / Decimal(10**12)

def round_btc(amount):
  return floor(amount * 10**8) / Decimal(10**8)

def request(url, params={}):
  params['api_key'] = api_key
  response = requests.get(HOST + url, params)
  return response.json()

def round_to_18_decimal_places(amount):
  return floor(amount * 10**18) / Decimal(10**18)

def round_up_to_18_decimal_places(amount):
  return ceil(amount * 10**18) / Decimal(10**18)

def get_mid_market_rate():
  response = requests.get('https://api.kraken.com/0/public/Depth?pair=XMRBTC').json()
  kraken_min_ask = min([Decimal(ask[0]) for ask in response['result']['XXMRXXBT']['asks']])
  kraken_max_bid = max([Decimal(bid[0]) for bid in response['result']['XXMRXXBT']['bids']])
  return round_to_18_decimal_places((kraken_min_ask + kraken_max_bid) / Decimal('2.0'))

def get_kraken_btc_deposit_address():
  result = kraken_request('/0/private/DepositAddresses', {'asset': 'XBT', 'method': 'Bitcoin'})[0]['address']
  print("Getting kraken btc deposit address", result)
  return result

def get_kraken_xmr_deposit_address():
  result = kraken_request('/0/private/DepositAddresses', {'asset': 'XMR', 'method': 'Monero'})[0]['address']
  print("Getting kraken xmr deposit address", result)
  return result

def get_kraken_btc_balance():
  result = Decimal(kraken_request('/0/private/Balance').get('XXBT')  or 0)
  print("Getting kraken btc balance", result)
  return result

def get_kraken_xmr_balance():
  result = Decimal(kraken_request('/0/private/Balance').get('XXMR') or 0)
  print("Getting kraken xmr balance", result)
  return result

def sell_on_kraken(amount):
  print("Issuing sell for",amount,"on kraken")
  print(kraken_request('/0/private/AddOrder', {
    'ordertype': 'market',
    'type': 'sell',
    'volume': format_decimal(amount, 12),
    'pair': 'XXMRXXBT',
  }))

def buy_on_kraken(amount):
  print("Issuing buy for",amount,"on kraken")
  print(kraken_request('/0/private/AddOrder', {
    'ordertype': 'market',
    'type': 'buy',
    'volume': format_decimal(amount, 12),
    'pair': 'XXMRXXBT',
  }))

def withdraw_xmr_from_kraken(amount):
  print("Withdrawing",amount,"xmr from kraken")
  print(kraken_request('/0/private/Withdraw', {
    'asset': 'XMR',
    'key': 'fryx.finance monero',
    'amount': format_decimal(amount, 12),
  }))

def withdraw_btc_from_kraken(amount):
  print("Withdrawing",amount,"btc from kraken")
  print(kraken_request('/0/private/Withdraw', {
    'asset': 'XBT',
    'key': 'fryx.finance bitcoin',
    'amount': format_decimal(amount, 8),
  }))

print("Deposit some XMR and BTC to the following addresses and then press enter:")
print(request('/deposit', {'asset': 'BTC'})['address'])
print(request('/deposit', {'asset': 'XMR'})['address'])
input()

while True:
  balances = request('/balances')
  mid_market_rate = get_mid_market_rate()
  print("Kraken mid market rate is", mid_market_rate, "updating orders")
  orders = request('/orders', {'market': 'XMRBTC'})
  for order in orders:
    request('/cancel', {'order_id': order['id']})
  balances = request('/balances')
  buy_price = round_to_18_decimal_places(mid_market_rate * Decimal('0.99'))
  sell_price = round_up_to_18_decimal_places(mid_market_rate * Decimal('1.01'))
  buy_amount = round_to_18_decimal_places(Decimal(balances['BTC']) / buy_price)
  sell_amount = Decimal(balances['XMR'])
  if buy_amount > 0:
    request('/buy', {'market': 'XMRBTC', 'amount': str(buy_amount), 'price': str(buy_price)})
  if sell_amount > 0:
    request('/sell', {'market': 'XMRBTC', 'amount': str(sell_amount), 'price': str(sell_price)})
  if buy_amount < THRESHOLD:
    orders = request('/orders', {'market': 'XMRBTC'})
    for order in orders:
      request('/cancel', {'order_id': order['id']})
    # need to get some more BTC on this exchange
    # how much xmr do we need to sell, in order for buy and sell to be balanced?
    # sell_amount - x == buy_amount + x
    # x = (sell_amount - buy_amount) / 2
    amount_to_move_to_kraken = round_xmr((sell_amount - buy_amount) / 2)
    print("amount to move to kraken is", amount_to_move_to_kraken, "XMR")
    print(request('/withdraw', {'asset': 'XMR', 'amount': str(amount_to_move_to_kraken), 'address': get_kraken_xmr_deposit_address()}))
    balances = request('/balances')
    buy_price = round_to_18_decimal_places(mid_market_rate * Decimal('0.99'))
    sell_price = round_up_to_18_decimal_places(mid_market_rate * Decimal('1.01'))
    buy_amount = round_to_18_decimal_places(Decimal(balances['BTC']) / buy_price)
    sell_amount = Decimal(balances['XMR'])
    if buy_amount > 0:
      request('/buy', {'market': 'XMRBTC', 'amount': str(buy_amount), 'price': str(buy_price)})
    if sell_amount > 0:
      request('/sell', {'market': 'XMRBTC', 'amount': str(sell_amount), 'price': str(sell_price)})
    while get_kraken_xmr_balance() < amount_to_move_to_kraken * Decimal('0.95'):
      sleep(60)
    sell_on_kraken(amount_to_move_to_kraken)
    sleep(60)
    amount_of_btc_to_move_from_kraken = get_kraken_btc_balance()
    withdraw_btc_from_kraken(amount_of_btc_to_move_from_kraken)
    while Decimal(request('/balances')['BTC']) < amount_of_btc_to_move_from_kraken * Decimal('0.95'):
      sleep(60)
    print("And the funds have arrived locally")
  elif sell_amount < THRESHOLD:
    orders = request('/orders', {'market': 'XMRBTC'})
    for order in orders:
      request('/cancel', {'order_id': order['id']})
    # need to get some more XMR on this exchange
    # how much btc do we need to move, in order for buy and sell to be balanced?
    # sell_amount * mid_market_rate + x == buy_amount * mid_market_rate - x
    # 2 * x = mid_market_rate * (buy_amount - sell_amount)
    # x = (buy_amount - sell_amount) * mid_market_rate / 2
    amount_to_move_to_kraken = round_btc((buy_amount - sell_amount) * mid_market_rate / (Decimal(2)))
    print("amount to move to kraken is", amount_to_move_to_kraken, "BTC")
    print(request('/withdraw', {'asset': 'BTC', 'amount': str(amount_to_move_to_kraken), 'address': get_kraken_btc_deposit_address()}))
    balances = request('/balances')
    buy_price = round_to_18_decimal_places(mid_market_rate * Decimal('0.99'))
    sell_price = round_up_to_18_decimal_places(mid_market_rate * Decimal('1.01'))
    buy_amount = round_to_18_decimal_places(Decimal(balances['BTC']) / buy_price)
    sell_amount = Decimal(balances['XMR'])
    if buy_amount > 0:
      request('/buy', {'market': 'XMRBTC', 'amount': str(buy_amount), 'price': str(buy_price)})
    if sell_amount > 0:
      request('/sell', {'market': 'XMRBTC', 'amount': str(sell_amount), 'price': str(sell_price)})
    while get_kraken_btc_balance() < amount_to_move_to_kraken * Decimal('0.95'):
      sleep(60)
    amount_to_buy_on_kraken = amount_to_move_to_kraken / mid_market_rate * Decimal('0.98')
    buy_on_kraken(amount_to_buy_on_kraken)
    sleep(60)
    amount_to_move_from_kraken = get_kraken_xmr_balance()
    withdraw_xmr_from_kraken(amount_to_move_from_kraken)
    while Decimal(request('/balances')['XMR']) < amount_to_move_from_kraken * Decimal('0.95'):
      sleep(60)
    print("and the funds have arrived locally")
  else:
    sleep(60*5)
