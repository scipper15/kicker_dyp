flask init-db
if ($LASTEXITCODE -eq 0) {
    Write-Host "Database initialized successfully."
} else {
    Write-Host "Failed to initialize database."
    exit 1
}

flask create-standard-user
if ($LASTEXITCODE -eq 0) {
    Write-Host "Standard user created successfully."
} else {
    Write-Host "Failed to create standard user."
    exit 1
}
