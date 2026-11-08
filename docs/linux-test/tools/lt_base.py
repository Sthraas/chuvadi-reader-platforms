import sys, os, time, json, subprocess, glob
sys.path.insert(0, "/home/claude/lx/tools/linux")
from uitest_lib import App
APP = "/home/claude/uitest-build"
EV = "/home/claude/evidence/lt"
def tabs(a): return a.js("return [...document.querySelectorAll('.rtab .rtab-name')].map(t=>t.textContent.trim())")
def toasts(a): return a.js("return [...document.querySelectorAll('[class*=toast]')].map(t=>t.innerText.trim()).filter(x=>x)")
