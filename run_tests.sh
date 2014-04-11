#!/usr/bin/env sh
python cherrytorrent.py &
sleep 5
curl "http://localhost:8080/add?uri=magnet%3A%3Fxt%3Durn%3Abtih%3A95731CE3C5EA065766F6EB92C9A426A58ADA56FE%26dn%3Dgravity%2B2013%2B1080p%2Bbrrip%2Bx264%2Byify%26tr%3Dudp%253A%252F%252Fopen.demonii.com%253A1337%252Fannounce"
sleep 30
curl "http://localhost:8080/shutdown"
