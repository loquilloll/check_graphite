# check\_grapite.py


An Icinga 2 plugin to check graphite metrics.

# Installation

* Put the Script into your Pluginfolder designated by your constants.conf  
* Create a CheckCommand object for check_Graphite.py, remember including envs for authentication.
  * An example config is included and make sure that location is found by your icinga2.conf.  
* Create a Service object with all the arguments you in your hostfolder.    
  * An example config is included.  
* Done, now start icinga2.  

# Authentication
## Environment Variables:
```
GRAPHITE_ACCESS_USER
GRAPHITE_ACCESS_PASS
```

# Usage

```
  -g [graph name]
  Name of the graph as given by Graphite

  -H [URL]  
  URL to the page Graphite is running on, in the form of "http://url.top/"  
  Default is "http://localhost:80/"
                      
  -w [[u]Wthreshold]  
  Define warning threshold, use 'u' to warn if value goes below threshold

  -c [[u]Cthreshold]  
  Define critical threshold, use 'u' to warn if value goes below thrshold
  
  -t [time frame]  
  Get data for the last X [d]ays/[h]ours/[m]inutes.  
  Default is 24 hours.
  
  -m [mode]  
  Declare mode.  
  0: Default mode  
  1: Needs -T [threshold] option, counts the time the graph is over your threshold.  
  Can be combined with all other options  
   
  -h  
  Print usage

  --help  
  Display verbose help

  Example usage:  
  `./check_graphite -g carbon.agents.cpuUsage -H http://example.com/ -w 85.4 -c u0 -t 3d`  
  Poll the graph carbon.agents.cpuUsage on example.com for the last three days,  
  warning if it is over 85.4 and sending a critical if it is below 0.
```

# Output

The output will be formatted the following way:  

```
Mode 0: 
Status|most recent value;wThreshold;cThreshold;max;min;avg;sum;time   
Mode 1: 
Status|count over threshold;percentile over threshold;wThreshold;cThreshold;max;min;avg;sum;time  
```
