#!/usr/bin/env bash

echo "OK lets do this"
while true; do
    read -r cmd
    echo "OK"
    if [ "$cmd" == "BYE" ] ; then
        exit
    fi
done
