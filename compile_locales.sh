#!/usr/bin/env bash

reference="ru.po"

cd locales
for i in *.po; do
  echo "Processing $i"
  changes=$(diff -u0 <(grep -e '^msgid' $reference) <(grep -e '^msgid' "$i") | grep 'msgid')
  if [ -n "$changes" ]; then
    echo "--------"
    echo "Translation file \"$i\" contains changes! Please fix."
    echo "$changes"
    echo "--------"
  fi
  folder="compiled/${i%%.*}/LC_MESSAGES/"
  mkdir -p "$folder"
  msgfmt "$i" -o "$folder/all.mo"
done

echo "All done."
