#!/bin/bash

REPOPATH=$1
CONFIG_FILE=$2
UPDATER='looker_toolz.py'

TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
BRANCHNAME="Update_Fields_${TIMESTAMP}"

echo "change directory to lookml repository: ${REPOPATH}"

cd ${REPOPATH}

echo "Creating a new branch ${BRANCHNAME}"

git pull
git checkout -b $BRANCHNAME

cd ..

#TODO: set destination basepath in config file to REPOPATH
python $UPDATER --update --config $CONFIG_FILE 

cd ${REPOPATH}

if [ -z $(git status --porcelain) ];
then
    echo "No changes were made"
else
    echo "Files were changed!"

    git add *.view.lkml

    git commit -m "modifications for lookml files at ${TIMESTAMP}"

    git push --set-upstream origin ${BRANCHNAME}
fi
