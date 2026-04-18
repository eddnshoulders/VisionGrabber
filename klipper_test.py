#!/usr/bin/python

from scan_and_grab import *
k = KlipperAPI()

# send a move request to see if an error is returned
ans = k.gcode("G0 X120 Y120")
print(ans)

# get the current position
pos = k.get_position()
print(pos)

# attempt to home the machine
k.gcode("G28")

# close the connection
k.close()
