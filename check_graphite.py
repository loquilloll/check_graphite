#!/usr/bin/env python
#############################################################################
#
# Copyright (C) 2014 NETWAYS GmbH
#                <support@netways.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# Or visit their web page on the internet at http://www.fsf.org.
#
# Link
# https://github.com/NETWAYS/check_graphite
#
# Changelog
# 2018-09-07 Improve check output, add verbose mode Christian Wirtz <doc@snowheaven.de>
#
#############################################################################

import urllib.request
import getopt
import sys
import getpass
import os
from decimal import Decimal
import base64
import requests
from requests.auth import HTTPBasicAuth

def main():
  #asigning defaults
  cars = {'w':None, 'c':None, 't':'24h', 'H':'http://localhost:80/','u':None,'p':None}
  #parse options
  try:
    opts, args = getopt.getopt(sys.argv[1:], 'g:w:c:H:hm:t:T:vu:p:', ['help'])
  except getopt.GetoptError as e:
    print(e)
    usage()
    sys.exit(3)
  for o, a in opts:
    if o == '-h':
      usage()
      sys.exit(3)
    if o == '--help':
      showVerboseHelp()
      sys.exit(3)
    cars[o[1]] = a

  if 'm' in cars:
    if cars['m'] == '1':
      if not 'T' in cars:
        die('Mode 1 requires argument -T')
  else:
    cars['m'] = '0'

  if not 'g' in cars:
    print("Missing argument '-g'")
    usage()
    sys.exit(3)
  


  # Get Graphite data
  data = getGraph(cars['g'], cars['H'], cars['t'], cars['u'], cars['p'])

  # Handle thresholds
  perfdata = ""
  if cars['m'] == '0':
    result = handleThreshold(data[0], cars['w'], cars['c'])

    if result == 'ERROR':
      die('Invalid thresholds')
    perfdata = '|time='+str(data[1])+';value='+str(data[0])

  elif cars['m'] == '1':
    result = handleOverThreshold(data[2], cars['c'], cars['w'], cars['T'])
    if result[0] == 'ERROR':
      die('Invalid thresholds')

    perfdata = '|count='+str(result[1])+';perc='+str(result[2])

  mmas = getMaxMinAvgSum(data[2])
  if cars['w'] != None:
    perfdata += ';w='+cars['w']
  if cars['c'] != None:
    perfdata += ';c='+cars['c']

  # Perfdata
  perfdata += ';max='+str(mmas[0])+';min='+str(mmas[1])+';avg='+str(mmas[2])+';sum='+str(mmas[3])+';from='+cars['t']
  #";max={mmas[0]!s};min={mmas[1]!s};avg={mmas[2]!s};sum={mmas[3]};from={cars['t']}"
  #2.4: no proper formatting

  # Create check output text and add threshold info
  if cars['w'] != None and cars['c'] != None:
    output = cars['g'] + " is " + str(data[0]) + " (warn/crit at " + str(cars['w']) + "/" + str(cars['c']) + "), time frame is " + cars['t']
  else:
    output = cars['g'] + " is " + str(data[0]) + ", time frame is " + cars['t']

  # Debug
  if 'v' in cars: print("time frame: " + cars['t'])
  if 'v' in cars: print("output    : " + output)
  if 'v' in cars: print("perfdata  : " + perfdata)
  if 'v' in cars: print("result    : " + result)
  if 'v' in cars: print("\n\n")

  # Output
  print(output + perfdata)

  if result == 'CRITICAL':
    sys.exit(2)
  if result == 'WARNING':
    sys.exit(1)
  else:
    sys.exit(0)


#get latest changed data, return (x,y,z)
def getGraph(name, url, time, _user, _passwd):
  #graphite wants full names
  try:
    int(time[:-1])
  except ValueError:
    die('Unknown time format')

  #no negatives please
  if time[0] == '-':
    time = time[1:]
  if time[-1] == 'd':
    time += 'ays'
  elif time[-1] == 'h':
    time += 'ours'
  elif time[-1] == 'm':
    time += 'inutes'
  else:
    die('Unknown time format')


  payload = {'target': f'{name}','format':'json','from':f'-{time}'}
  url = f'{url}/render'
  try:
    r = requests.get(url)   
    r.raise_for_status()
  except requests.exceptions.HTTPError as e:
    if e.response.status_code != 401:
      die(e)
    try:
      death = None #without this the exception would cath the sys.exit() exception and die again printing the exit status
      user = _user
      passwd = _passwd
      if (user == None) or (passwd == None):
        user = os.environ.get('GRAPHITE_ACCESS_USER')
        passwd = os.environ.get('GRAPHITE_ACCESS_PASS')
      elif (user == None) or (passwd == None):
        death = ('Server requires authentication, provide -u and -p or, set your env GRAPHITE_ACCESS_USER and GRAPHITE_ACCESS_PASS accordingly')
      print(user,passwd)
      r = requests.get(url,
                        params=payload,
                        auth=HTTPBasicAuth(user, passwd))

      r.raise_for_status()
    except requests.exceptions.HTTPError as e:
      if death == None:
        die(e)
      else:
        die(death)
  except Exception as e:
    die(e)

  json = r.json()[0]
  datapoints = json['datapoints']
  #Find latest entry
  #entry = (data,time,MaxMinAvgSum,status)
  entry = ()
  if len(datapoints) == 0:
    die('Data returned by Graphite not valid')
  
  try:
    last_entry = datapoints[len(datapoints)-1]
    ctime = last_entry[1] #Starting time
    entry = (last_entry[0],last_entry[1]) #Keep the lastest entry
  except ValueError:
    die('Data returned by Graphite not valid')

  #traverse, collect values
  vals = []
  for value in datapoints:
    if value[0] is not None:
      vals.append(value[0])
    elif vals:
      vals.append(vals[-1])
  
  if entry != ():
    return (entry[0], entry[1], vals)

  #if no entry is found return 0 as value und time of latest actualisiation
  return (0, ctime, (0, 0, 0, 0))


def handleThreshold(data, warn, crit):
  #test on critical first, in case critical <= warning
  #float just yields wrong compare values sometimes

  if crit != None:
    if crit[0] == 'u':
      try:
        crit = Decimal(crit[1:])
        if data < crit:
          return 'CRITICAL'
      except:
        return 'ERROR'
    else:
      try:
        crit = Decimal(crit)
        if data > crit:
          return 'CRITICAL'
      except:
        return 'ERROR'
  if warn != None:
    if warn[0] == 'u':
      try:
        warn = Decimal(warn[1:])
        if data < crit:
          return 'WARNING'
      except:
        return 'ERROR'
    else:
      try:
        warn = Decimal(warn)
        if data > warn:
          return 'WARNING'
      except:
        return 'ERROR'

  return 'OK'


def handleOverThreshold(data, crit, warn, threshold):
  res = 'OK'
  try:
    threshold = Decimal(threshold)
  except:
    res = 'ERROR'

  count = 0
  for word in data:
    if word > threshold:
      count += 1

  perc = 100*(Decimal(count)/len(data))
  cu = False
  wu = False

  try:
    if crit != None:
      if crit[0] == 'u':
        crit = crit[1:]
        cu = True
      if crit[-1] != '%':
        crit = Decimal(crit)
        if crit > count and not cu:
          return ('CRITICAL', count, perc)
        if crit < count:
          return ('CRITICAL', count, perc)
      crit = Decimal(crit[:-1])
      if crit > perc and not cu:
        return ('CRITICAL', count, perc)
      if crit < perc:
        return ('CRITICAL', count, perc)
    if warn != None:
      if warn[0] == 'u':
        warn = warn[1:]
        wu = True
      if warn[-1] != '%':
        warn = Decimal(warn)
        if warn > count and not wu:
          return ('WARNING', count, perc)
        if warn < count:
          return ('WARNING', count, perc)
      warn = Decimal(warn[:-1])
      if warn > perc and not wu:
        return ('WARNING', count, perc)
      if warn < perc:
        return ('WARNING', count, perc)
  except:
    res = 'ERROR'
  return (res, count, perc)


def getMaxMinAvgSum(data):
  #(max,min,avg,sum)
  return (max(data), min(data), sum(data)/len(data), sum(data))


def die(msg):
  print(msg)
  sys.exit(3)

def usage():
  print('Usage: \n'+sys.argv[0] + ' -g [Graph] -H [url] [-w [u][Wthreshold]] [-c [u][Cthreshold]] [-t [time frame]] [-u [username]] [-p [password]] [-h, --help]')


def showVerboseHelp():
  print('  '+sys.argv[0]+' - Help\n')
  print('''\
  -g [graph name]      Name of the graph as given by Graphite

  -H [URL]             URL to the page Graphite is running on,
                       in the form of "http://url.top/"
                       Default is "http://localhost:80/"

                       Uses the enviroment variables GRAPHITE_ACCESS_USER
                       and GRAPHITE_ACCESS_PASS for authorization

  -w [[u]Wthreshold]   Define warning threshold, only int or float
                       use 'u' to warn if value goes below threshold

  -c [[u]Cthreshold]   Define critical threshold, only int or float
                       use 'u' to warn if value goes below thrshold

  -t [time frame]      Get data for the last X [d]ays/[h]ours/[m]inutes
                       Default is 24 hours

  -m [mode]            Declare mode
                       0: Default mode
                       1: Needs -T [threshold] option, counts the time the
                          graph is over your threshold. Can be combined
                          with all other options

  -v                   Verbose mode

  -u                   Username. Alternative to GRAPHITE_ACCESS_USER

  -p                   Password. Alternative to GRAPHITE_ACCESS_PASS

  -h                   Print usage

  --help               Display this site

  Example usage:
  '''+sys.argv[0]+''' -g carbon.agents.cpuUsage -H http://example.com/ -w 85.4 -c u0 -t 3d
  Poll the graph carbon.agents.cpuUsage on example.com for the last three days,
  warning if it is over 85.4 and sending a critical if it is below 0.
  ''')

if __name__ == '__main__':
  main()
