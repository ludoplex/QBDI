#!/usr/bin/env python3

# This file is part of pyQBDI (python binding for QBDI).
#
# Copyright 2017 - 2023 Quarkslab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import platform
import pyqbdi
from ctypes import util as ctypesutil
import sys
import os
import argparse

def run():

    parser = argparse.ArgumentParser()

    parser.add_argument("script", type=str, help="PyQBDI script")
    parser.add_argument("target", type=str, help="command to instrument")
    parser.add_argument("args", type=str, help="command arguments", nargs='*')

    args = parser.parse_args()

    script = args.script
    binary = args.target
    args = [args.target] + args.args
    environ = os.environ.copy()

    preloadlib = os.path.join(
            os.path.dirname(pyqbdi.__file__),
            os.path.basename(pyqbdi.__file__).replace("pyqbdi", "pyqbdipreloadlib"))

    if not os.path.isfile(preloadlib):
        print(f"Cannot found pyqbdi preload library : {preloadlib}")
        exit(1)

    # add LD_PRELOAD or DYLD_INSERT_LIBRARIES
    if platform.system() == 'Darwin':

        environ["DYLD_INSERT_LIBRARIES"] = preloadlib
        environ["DYLD_LIBRARY_PATH"] = os.path.join(sys.base_prefix, 'lib')
        environ["DYLD_BIND_AT_LAUNCH"] = "1"
    elif platform.system() == 'Linux':
        libpythonname = f"python{sys.version_info.major}.{sys.version_info.minor}"
        libpython = ctypesutil.find_library(libpythonname)
        if not libpython:
            libpythonname = f"python{sys.version_info.major}.{sys.version_info.minor}{sys.abiflags}"
            libpython = ctypesutil.find_library(libpythonname)
        if not libpython:
            print(f"PyQBDI in PRELOAD mode need lib{libpythonname}.so")
            exit(1)

        environ["LD_PRELOAD"] = os.pathsep.join([libpython, preloadlib])
        environ["LD_BIND_NOW"] = "1"
    else:
        print("PyQBDI in PRELOAD mode is not supported on this platform")
        exit(1)

    # add PYQBDI_TOOL
    if not os.path.isfile(script):
        print(f"Cannot find {script} script")
        exit(1)
    else:
        environ["PYQBDI_TOOL"] = script

    ## https://docs.python.org/3.8/library/os.html#os.execve:
    # "execve will not use the PATH variable to locate the executable; path must contain an appropriate absolute or relative path."
    # seach the binary path in PATH if needed
    binarypath = None
    if '/' in binary:
        # absolute or relative path
        binarypath = binary
    elif "PATH" in environ:
        for p in environ["PATH"].split(os.pathsep):
            if os.path.isfile(os.path.join(p, binary)):
                binarypath = os.path.join(p, binary)
                break

    if not binarypath or not os.path.isfile(binarypath):
        print(f"Cannot find binary {binary}")
        exit(1)

    os.execve(binarypath, args, environ)

    print("Fail execve")
    exit(1)

if __name__ == "__main__":
    run()
