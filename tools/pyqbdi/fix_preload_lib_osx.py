#!/usr/bin/env python3

import os
import subprocess
import sys

def read_header(libpath):
    p = subprocess.run(["otool", "-l", libpath],
                       check=True,
                       capture_output=True)
    newCommand = False
    getRPath = False
    getDLib = False
    rpath = []
    dlib = []
    for l in p.stdout.decode("utf8").split("\n"):
        l = l.strip(' ')
        if l.startswith("Load command"):
            newCommand = True
            getRPath = False
            getDLib = False
            continue
        if newCommand and l.startswith("cmd"):
            newCommand = False
            getRPath = l.endswith("LC_RPATH")
            getDLib = l.endswith("LC_LOAD_DYLIB")
            continue
        if getRPath and l.startswith("path"):
            getRPath = False
            newPath = l.split(' ', 1)[1]
            if newPath[-1] == ")":
                newPath = newPath[:newPath.rindex(' (')]
            rpath.append(newPath)
        if getDLib and l.startswith("name"):
            getDLib = False
            newPath = l.split(' ', 1)[1]
            if newPath[-1] == ")":
                newPath = newPath[:newPath.rindex(' (')]
            dlib.append(newPath)
    return rpath, dlib

def setID(libname):
    print(f"= Set ID to {os.path.basename(libname)} =")
    subprocess.run(["install_name_tool", "-id", os.path.basename(libname), libname],
                   check=True)

def removeRpath(libname, path):
    print(f"= Remove rpath {path} =")
    subprocess.run(["install_name_tool", "-delete_rpath", path, libname],
                   check=True)

def movLib(libname, oldlib, newlib):
    print(f"= replace {oldlib} by {newlib} =")
    subprocess.run(["install_name_tool", "-change", oldlib, newlib, libname],
                   check=True)

def resign(libname):
    print("= Resign =")
    subprocess.run(["codesign", "--force", "--sign", "-", libname],
                   check=True)


def run():

    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <lib>")
        sys.exit(1)

    libpath = sys.argv[1]

    if not os.path.isfile(libpath):
        print(f"Invalid library {libpath}")
        sys.exit(1)

    print(f"== fix library {libpath} ==")
    rpath, dlib = read_header(libpath)

    setID(libpath)

    for lib in dlib:
        if 'Python' not in lib:
            continue
        # set python lib to libpythonX.Y.dylib
        # the path of libpython will be add to DYLD_LIBRARY_PATH
        # at runtime by pyqbdipreload.py
        targetlib = f"libpython{sys.version_info.major}.{sys.version_info.minor}.dylib"
        movLib(libpath, lib, targetlib)

    for r in rpath:
        removeRpath(libpath, r)

    resign(libpath)




if __name__ == "__main__":
    run()
