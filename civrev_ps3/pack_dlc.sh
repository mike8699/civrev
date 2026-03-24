#!/bin/bash

.venv/bin/python fpk.py repack ./Pak9/
mv Pak9.FPK ~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/Pak9.edat
