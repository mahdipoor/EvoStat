from __future__ import print_function
import sys, os, time, socket, subprocess, re, traceback
from os  import popen
import glob
import base64, urllib2

from suppress_stdout_stderr import suppress_stdout_stderr
debug = False

# Tools to fenerate PROLOG terms from Python
# PROLOG: "f(a(1),b(2))."  FROM PYTHON:  "f"  and   { a:1, b:2 }

def termDict(f, d) :
    return f+"("+",".join([k+"("+str(d[k])+")" for k in d.keys()])+")."
    
def termInt(f,i) :
    return f+"("+str(i)+")."

def termIntList(f,l) :
    if (l == None ):
        plog("Failed to produce a complex term due to empty argument list: " + f)
        return f+"."
    return f+"("+", ".join([str(i) for i in l])+")."

def plog(str) :
    if (debug == True):
        print("      --"+str, file=sys.stderr)

def settings() :
    for root in sys.argv:  # See if anything on the command-line matches a .setting file
        file = root + ".settings"
        if os.path.isfile(file) :
            return(eval(open(file,'r').read()))

    file = socket.gethostname() + ".settings"
    if os.path.isfile(file) :
        return(eval(open(file, 'r').read()))

    plog("requires('" + sys.argv[0] +
         "', or(config_file('<hostname>.settings')," +
         "config_file('<evostatname>.settings')),'Create by modifying template.pl').")
    exit(0)

def nullImage(img, who) :
    if (img == None) :
        plog(who + " called with null image (None)")
        traceback.print_stack()
        return True
    return False

