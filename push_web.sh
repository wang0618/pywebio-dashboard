#!/usr/bin/env bash

# This script commit local change to `web` branch and push commit to origin repo.

last_commit_date=$(git log -1 --date=format:"%Y/%m/%d" --format="%ad")
today=$(date +"%Y/%m/%d")

git checkout web
git add .

if [[ today = last_commit_date ]]; then
  git commit --amend -m "Data update at `date`" || exit 0
else
  git commit -m "Data update at `date`" || exit 0
fi

git push -f -u origin || exit 0