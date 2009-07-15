#!/bin/sh

TMP=$(mktemp -d)
cp -a tilecache $TMP
cp -a debian $TMP/tilecache
dpkg-source -b $TMP/tilecache
rm -fr $TMP
