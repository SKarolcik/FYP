#!/bin/bash

if [ -z "$GPIO_SET" ]; then
    export GPIO_SET=1
    sudo pigpiod
fi
python qttrial.py

