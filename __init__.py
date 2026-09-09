import sys

from os import path


db_dir = path.abspath('/pos/server/database/')
services_dir = path.abspath('/pos/server/services/')
utils_dir = path.abspath('/pos/server/utils/')
io_dir = path.abspath('/pos/server/io_services')
r_dir = path.abspath("/pos/server/r_services")


paths = [db_dir, services_dir, utils_dir, io_dir, r_dir]

count = 0
for p in paths:
    if paths.index(p) != count:
        count += paths.index(p)
    sys.path.insert(count, p)
