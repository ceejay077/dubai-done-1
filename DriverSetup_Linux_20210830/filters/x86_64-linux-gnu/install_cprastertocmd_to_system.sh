#!/bin/sh

CURRENT_DIR=$(dirname "$0")

FILTER_NAME=cprastertocmd
FILTER_DIR=

if [ `uname` = Linux ]; then
	echo "Detected Linux Kernel"
	FILTER_DIR=/usr/lib/cups/filter
elif [ `uname` = Darwin ]; then
	echo "Detected Darwin Kernel"
	FILTER_DIR=/usr/libexec/cups/filter
else
	echo "Assumimg Linux Kernel"
	FILTER_DIR=/usr/lib/cups/filter
fi

echo "installing cprastertocmd to directory $FILTER_DIR"
cp "$CURRENT_DIR/$FILTER_NAME" "$FILTER_DIR/"
chmod a+x "$FILTER_DIR/$FILTER_NAME"
sync

