#!/usr/bin/env bash

reference="ru.po"

cd locales;
for i in *.po;
do
  changes=$(diff -u0  <(grep -e '^msgid' $reference|sort) <(grep -e '^msgid' $i|sort) | grep 'msgid');
  if [ ! -z "$changes" ];
  then
    echo "--------"
    echo "Translation file \"$i\" contains changes! Please fix."
    echo "$changes";
    echo "--------"
  fi
  folder="compiled/${i%%.*}/LC_MESSAGES/";
  mkdir -p $folder;
  msgfmt $i -o "$folder/all.mo";
done
