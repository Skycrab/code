import sys

# START: split
def split(stream): # split stream into list of log entry components
    lines = [line for line in stream]          # get all lines from stdin
    logs = [line.split(' ') for line in lines] # split into list of lists
    return logs
# END: split

# START: count
def count(logs,i):
    entries = [entry[i] for entry in logs]     # get all elements at i
    uniq = {}                                  # build a dictionary
    for e in entries:                          # count unique IP address
        if e in uniq: uniq[e] += 1             # bump count
        else: uniq[e] = 1                      # first time seeing, count=1
    return uniq
# END: count

# START: histo
IP_COLUMN=0
uniq = count(split(sys.stdin),IP_COLUMN)       # get unique IP counts
# make histogram by sorting in reverse order by count
pairs = uniq.items()                           # get (IP,count) pairs
pairs.sort((lambda x,y : cmp(x[1],y[1])))      # sort, comparing count not IP
pairs.reverse()
for p in pairs:                                # dump histogram
   print p[1], p[0]
# END: histo
