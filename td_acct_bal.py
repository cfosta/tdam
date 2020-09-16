import _cred as c
import requests as re
import json
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
import functools
from premailer import transform

#credentials to send email and groups to send to
email_user = c.email_un
email_password = c.email_pw
email_send = ['your_email_rec', 'your_email_rec']
subject = 'Title For Your Email'

msg = MIMEMultipart()
msg['From'] = email_user
msg['To'] = ", ".join(email_send)
msg['Subject'] = subject

### this dict needs to be updated to refresh automatically, right now, obtain a refresh token manually through TD website
api_cred = {
  "access_token": "a_very_long_encrypted_str",
  "refresh_token": "a_very_long_encrypted_str",
  "scope": "PlaceTrades AccountAccess MoveMoney",
  "expires_in": 1800,
  "refresh_token_expires_in": 7776000,
  "token_type": "Bearer"
}

account = c.td_acctid
client_id = c.td_clientid
refresh_token = api_cred['refresh_token']  # this is good for 90 days 


def access_token(refresh_token, client_id):
    resp = re.post('https://api.tdameritrade.com/v1/oauth2/token',
                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                         data={'grant_type': 'refresh_token',
                               'refresh_token': refresh_token,
                               'client_id': client_id})
    if resp.status_code != 200:
        raise Exception('Could not authenticate!')
    return resp.json()

### call the function above to refresh the access token
ref_resp = access_token(refresh_token, client_id)
new_access_token = ref_resp['access_token']

acct_url = f'https://api.tdameritrade.com/v1/accounts/{account}'
api_headers = {'authorization': 'Bearer {0}'.format(new_access_token)}
api_parameters = {'fields':'positions'}

response = re.get(acct_url, headers = api_headers, params = api_parameters)
acct_json = response.json()


dict_filt = lambda x, y: dict([ (i,x[i]) for i in x if i in set(y) ])

bal = acct_json['securitiesAccount']['currentBalances']
keys = [
    'liquidationValue',
    'cashBalance',
    'availableFunds',
    'longMarketValue',
    'shortMarketValue',
    'equity',
    'longOptionMarketValue',
    'shortOptionMarketValue',
    'buyingPower',
    #'moneyMarketFund',
    #'savings',
    #'mutualFundValue',
    #'bondValue',
    'marginBalance',
    'maintenanceRequirement',
    'longMarginValue',
    'shortMarginValue',
    'maintenanceCall'
        ]
convert_keys = {
    'liquidationValue':'Liquidation_Val',
    'cashBalance':'Cash',
    'availableFunds':'Availble_Funds',
    'longMarketValue':'Long_Mkt_Val',
    'shortMarketValue':'Short_Mkt_Val',
    'equity':'Equity',
    'longOptionMarketValue':'Long_Options',
    'shortOptionMarketValue':'Short_Options',
    'buyingPower':'Buying_Power',
    # 'moneyMarketFund':'Money_Mkt_Funds',
    # 'savings':'Savings',
    # 'mutualFundValue':'Mutual_Funds',
    # 'bondValue':'Bonds',
    'marginBalance':'Margin_Bal',
    'maintenanceRequirement':'Mntnce_Req',
    'longMarginValue':'Long_Margin_Val',
    'shortMarginValue':'Short_Margin_Val',
    'maintenanceCall':'Mntnce_Call'
}
new_keys=[
    'Liquidation_Val',
    'Cash',
    'Availble_Funds',
    'Buying_Power',
    'Equity',
    'Long_Mkt_Val',
    'Long_Options',
    'Short_Mkt_Val',
    'Short_Options',
    # 'Money_Mkt_Funds',
    # 'Savings',
    # 'Mutual_Funds',
    # 'Bonds',
    'Margin_Bal',
    'Long_Margin_Val',
    'Short_Margin_Val',
    'Mntnce_Req',
    'Mntnce_Call'
]

bal_dict = dict_filt(bal, keys)
new_bal_dict = dict((convert_keys[key], value) for (key, value) in bal_dict.items())
new_bal = sorted(zip(new_bal_dict.keys(),new_bal_dict.values()), key=lambda x: new_keys.index(x[0]))

balances_df = pd.DataFrame(new_bal, columns=['Account', 'Balance'])

positions = [(p['instrument']['symbol'],
              p['longQuantity'],
              p['shortQuantity'],
              p['averagePrice'],
              p['marketValue'],
              p['currentDayProfitLoss'],
              p['currentDayProfitLossPercentage'],
              #p['settledLongQuantity'],
              #p['settledShortQuantity'],
              p['maintenanceRequirement'])
          for p in acct_json['securitiesAccount']['positions']
          ]

df = pd.DataFrame(positions, columns = ['Ticker', 'Long', 'Short', 'Avg Price', 'Mkt Value', 'Today $', 'Today %', 'Mtnce Req'])
df['Cost Basis'] = df['Avg Price'] * df['Long']
df['P/L'] = df['Mkt Value'] - df['Cost Basis']
df['Today %'] = df['Today %'] * 0.01
df = df.reindex(columns = ['Ticker', 'P/L', 'Mkt Value', 'Cost Basis', 'Avg Price', 'Long', 'Short', 'Today $', 'Today %', 'Mtnce Req'])
df = df.sort_values(by=['Ticker'], ascending=True)
#df.loc['Column_Total'] = df.iloc[:, 1:4].sum(numeric_only=True, axis=0)
df = df.reset_index(drop=True)

# Set CSS properties for th, tr, tc elements in all dataframes we are going to put in the email body
th_props = [
    #('width', '100%'),
    ('background-color', '#8dbdff'),
    ('color', 'white'),
    ('text-align', 'center'),
    ('font-size', '10pt'),
    ('font-family', 'Helvetica'),
    ('padding', '6px 10px 6px 10px')
    ]
tr_props = [
    #('width', '100%'),
    ('background-color', 'white'),
    ('color', '#333333'),
    ('text-align', 'center'),
    ('font-size', '10pt'),
    ('font-family', 'Helvetica'),
    ('padding', '0px 5px 0px 0px')
    ]
tc_props = [
     ('background-color', 'white'),
     ('color', '#333333'),
     ('text-align', 'left'),
     ('font-size', '15pt'),
     ('font-weight', 'bold'),
     ('font-family', 'Helvetica'),
     ('padding', '12px')
     ]
# Set table styles
styles = [
  dict(selector = "th", props = th_props),
  dict(selector = "tr", props = tr_props),
  dict(selector = "caption", props = tc_props)
  ]

def row_bander(data):
    indx = data.index % 2 != 0
    indx = pd.concat([pd.Series(indx)] * 10, axis=1) #10 or the n of cols u have
    band = pd.DataFrame(np.where(indx, 'background-color:#f2f2f2', ''),
                 index=data.index, columns=data.columns)
    return band

def row_bander_acct(data):
    indx = data.index % 2 != 0
    indx = pd.concat([pd.Series(indx)] * 2, axis=1) #10 or the n of cols u have
    band = pd.DataFrame(np.where(indx, 'background-color:#f2f2f2', ''),
                 index=data.index, columns=data.columns)
    return band

def color_negative_red(value):
    if value < 0:
        color = 'red'
    elif value > 0:
        color = 'green'
    else:
        color = '#333333'
    return 'color: %s' % color


bal_title = "Current Balances:"

html_bal = (
    balances_df.style
    .hide_index()
    .set_caption(bal_title)
    .apply(row_bander_acct, axis=None)
    .applymap(color_negative_red, subset=['Balance'])
    .set_properties(subset = ['Balance'], **{'padding': '0px 13px 0px 13px', 'width': '35px'})
    .set_properties(subset = ['Account'], **{'text-align':'left', 'padding': '0px 13px 0px 13px', 'width': '50px', 'font-weight': 'bold'})
    .format({'Balance':'${:,.0f}'})
    .set_table_styles(styles)\
    .render()
)

pos_title = "All Positions And Today's Movement:"

html_pos = (
    df.style
    .hide_index()
    .set_caption(pos_title)
    .apply(row_bander, axis=None)
    .applymap(color_negative_red, subset=['P/L','Today $','Today %'])
    .set_properties(subset = ['Ticker'], **{'text-align':'left', 'padding': '0px 13px 0px 13px', 'width': '35px', 'font-weight': 'bold'})
    .set_properties(subset = ['P/L'], **{'padding': '0px 13px 0px 13px', 'font-weight': 'bold'})
    .format({'P/L':'${:,.0f}', 'Cost Basis':'${:,.0f}', 'Mkt Value':'${:,.0f}', 'Avg Price':'${:,.1f}', 'Today $':'${:,.0f}', 'Today %':'{:.1%}', 'Mtnce Req':'${:,.0f}', 'Long':'{:,.0f}', 'Short': '{:,.0f}'})
    .set_table_styles(styles)\
    .render()
)

body = """
<html>
  <head></head>
  <body>
  <br>
  <table width="800" align="center">
  {1}{0}
  <br>
</body>
</html>
""".format(html_bal,html_pos)

# <br>{0}<br>
# <br>

post_transform_html = transform(body, pretty_print=True)

msg.attach(MIMEText(post_transform_html, 'html'))
text = msg.as_string()

server = smtplib.SMTP('smtp.gmail.com',587)
server.starttls()
server.login(email_user, email_password)
server.sendmail(email_user, email_send, text)
server.quit()
