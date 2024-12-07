# docker-compose-dev-win.ps1

# Load environment variables from .env.dev
Get-Content .env.dev | ForEach-Object {
    if ($_ -notlike '#*') {
        $var = $_.Split('=', 2)
        [Environment]::SetEnvironmentVariable($var[0], $var[1])
    }
}

# Run docker compose
docker compose -f docker-compose.yml up --build
