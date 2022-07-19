import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from datetime import datetime

st.set_page_config(layout="wide")

c1,c2 = st.columns([1,6])

with c1:
  st.image('MO_mark_mono_neg.svg',width=200)
with c2:
  st.markdown('# Fencers')

st.subheader('Made by Wolf')
st.markdown('<br>')

def get_tournaments(from_date, to_date):
  url = f'https://fencingtimelive.com/tournaments/list/data?from={from_date}&to={to_date}'
  request = requests.get(url)
  tournaments = json.loads(request.content)
  return tournaments


def get_events(tournament):
  id = tournament['id']
  url = f'https://fencingtimelive.com/tournaments/eventSchedule/{id}'
  request = requests.get(url)
  soup = BeautifulSoup(request.content, 'lxml')

  #First find all days
  events = []
  dates = soup.find_all('h5')
  for date in dates:
    tbl = date.find_next_sibling()
    links = tbl.find_all('a')
    for link in links:
      if 'href' in link.attrs.keys():
        if 'events' in link.attrs['href']:
          id = link.attrs['href'].split('/')[-1]
          name = link.text.strip()
          event = {'event_id':id,'event_name':name,'event_date':date.text}
          event.update(tournament)
          events.append(event)
  return events


def get_competitors(event):
  id = event['event_id']
  url = f'https://fencingtimelive.com/events/competitors/download/{id}'
  request = requests.get(url)
  competitors_csv = [row.split(',') for row in request.text.split('\n')]
  header = ['competitor_'+i for i in competitors_csv[0]]
  rows = competitors_csv[1:]
  competitors_dict = []
  for comp in [dict(zip(header,r)) for r in rows]:
    temp = comp.copy()
    temp.update(event)
    competitors_dict.append(temp)
  return competitors_dict
  

def get_aus_fencers():
  fencer_comp_list = []
  tournaments = get_tournaments('2022-06-15','2022-07-13')
  aus_tournaments = [t for t in tournaments if 'AUS' in t['location']]

  print(f'Getting {len(aus_tournaments)} tournaments')
  for tournament in aus_tournaments:
    events = get_events(tournament)
    tname = tournament['name']

    print(f'Getting {len(events)} events from {tname}')
    for event in events:
      ename = event['event_name']
      competitors = get_competitors(event)
      fencer_comp_list = fencer_comp_list + competitors

      print(f'Fetched {len(competitors)} competitors from {ename}')
    

  df = pd.DataFrame(fencer_comp_list)
  df.to_csv('fencers.csv')



# First Choose Dates
sd = st.date_input('Select Start Date',value=datetime(2022,6,20))
ed = st.date_input('Select End Date',value=datetime(2022,7,30))

# Get Tournaments:
fencer_comp_list = []
tournaments = get_tournaments('2022-06-15','2022-07-13')
tnames = [t['name']+' | '+t['location']+' | '+t['dates'] for t in tournaments]

# Next pick tournaments
tpicked = st.multiselect('Choose Tournaments',tnames,[])

tids = []
events = []
for tname in tpicked:
  tid = [t for t in tournaments if t['name'] in tname and t['location'] in tname and t['dates'] in tname][0]
  tids.append(tid)
  event_list = get_events(tid)
  events += event_list

# Next pick Event
enames = [e['event_name'] + ' | ' + e['name'] for e in events]
epicked = st.multiselect('Choose Events',enames,[])

# Next display Fencers in a table
eids = []
fencers = []
for ename in epicked:
  eid = [e for e in events if e['name'] in ename and e['event_name'] in ename][0]
  eids.append(eid)
  f = get_competitors(eid)
  fencers += f

if len(fencers) > 0:
  df = pd.DataFrame(fencers)
  cols = ['name','location','event_date','event_name','competitor_Club(s)','competitor_Division','competitor_Country','competitor_Name','competitor_Status','competitor_Rank']
  cols = [c for c in cols if c in df.columns]
  df = df.loc[:,cols]
  df = df.rename(index=str,columns={'name':'Tournament', 'location':'Location','event_date':'Date','event_name':'Event',
    'competitor_Club(s)':'Club','competitor_Division':'Division','competitor_Country':'Country',
    'competitor_Name':'Name','competitor_Status':'Status','competitor_Rank':'Rank'})
  #df.columns = ['Tournament','Location','Date','Event','Club','Division','Country','Name','Status','Rank']

  # Filter to club
  if 'Club' in df.columns:
    df.Club = df.Club.fillna('')
    clubs = df.Club.unique()
    clubs = sorted(clubs)
    cpicked = st.multiselect('Filter by Club',clubs,[])

    mask = [True if i in set(cpicked) else False for i in df.Club]
    df2 = df.loc[mask].reset_index(drop=True)
  else:
    df2 = df

  st.table(df2)

  st.download_button('Download as CSV',df2.to_csv(),file_name='fencers.csv')

  df3 = df2.groupby('Date').count()['Name'].reset_index()
  if df3.shape[0]>0:
    st.table(df3)
    st.vega_lite_chart(df3, spec={
        "width": "container",
        "height": 200,
        "mark": {"type":"bar","color":"#0CF66A"},
        "encoding": {
          "x": {"field": "Date", "type": "nominal", "axis": {"labelAngle": 0}},
          "y": {"field": "Name", "type": "quantitative"}
        }
    })
