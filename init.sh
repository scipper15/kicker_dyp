#!/bin/bash

flask init-db
if [ $? -eq 0 ]; then
    echo "Database initialized successfully."
else
    echo "Failed to initialize database."
    exit 1
fi

flask create-standard-user
if [ $? -eq 0 ]; then
    echo "Standard user created successfully."
else
    echo "Failed to create standard user."
    exit 1
fi
