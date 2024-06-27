#!/bin/bash
# pip3 install aiofiles
# pip3 install websockets_proxy
# pip3 install loguru

mkdir -p logs
for i in {0..99}
do
    pm2 start --name "batch-$i" "python3 batch.py $i"
done

# kill -9 $(ps aux | grep "batch.py" | tr -s ' '| cut -d ' ' -f 2)
