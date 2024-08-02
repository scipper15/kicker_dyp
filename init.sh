#!/bin/bash

# Generate a 32-byte (256-bit) secret key using openssl
SECRET_KEY=$(openssl rand -hex 32)
FLASK_ENV="prod"

# Create a .env file and write the SECRET_KEY to it
echo "SECRET_KEY=$SECRET_KEY" > .env
echo "FLASK_ENV=$FLASK_ENV" >> .env

# Output the result
echo ".env file created with environment variables."

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
