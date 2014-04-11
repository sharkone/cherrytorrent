#!/usr/bin/env sh
python cherrytorrent.py &
sleep 30
curl "http://localhost:8080/add?uri=magnet%3A%3Fxt%3Durn%3Abtih%3Ac39fe3eefbdb62da9c27eb6398ff4a7d2e26e7ab%26dn%3Dbig%2Bbuck%2Bbunny%2Bbdrip%2Bxvid%2Bmedic%26tr%3Dudp%253A%252F%252Ftracker.publicbt.com%253A80%252Fannounce%26tr%3Dudp%253A%252F%252Fopen.demonii.com%253A1337"
sleep 30
curl "http://localhost:8080/shutdown"
