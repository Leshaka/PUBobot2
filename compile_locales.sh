#!/bin/sh

cd locales;
for i in *.po;
do
  folder="compiled/${i%%.*}/LC_MESSAGES/";
  mkdir -p $folder;
  msgfmt $i -o "$folder/all.mo";
done