#!/usr/bin/env python3
# send_cmd.py
import sys
import time
from scan_and_grab import *

# setup the klipper connection
k = KlipperAPI()

# send the command string passed by argument
cmd = " ".join(sys.argv[1:])

# get and print the response
response = k.move_and_wait(cmd)
print(f"<< {response}")

# close the klipper connection
k.close()