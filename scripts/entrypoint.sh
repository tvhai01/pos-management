#!/bin/bash
# =============================================================================
# Entrypoint script for the POS Management System Docker container.
#
# Responsibilities:
# 1. Wait for PostgreSQL to be ready.
# 2. Run database migrations.
# 3. Collect static files.
# 4. Start the application server.
# =============================================================================

set -o errexit
set -o pipefail
set -o nounset

# -----------------------------------------------------------------------------
# Wait for PostgreSQL
# -----------------------------------------------------------------------------
echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."

while ! python -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('${POSTGRES_HOST}', ${POSTGRES_PORT}))
sock.close()
exit(result)
" 2>/dev/null; do
    echo "PostgreSQL is not ready yet. Retrying in 2 seconds..."
    sleep 2
done

echo "PostgreSQL is ready!"

# -----------------------------------------------------------------------------
# Create logs directory if not exists
# -----------------------------------------------------------------------------
mkdir -p /app/logs

# -----------------------------------------------------------------------------
# Run Migrations
# -----------------------------------------------------------------------------
echo "Running database migrations..."
python manage.py migrate --noinput

# -----------------------------------------------------------------------------
# Collect Static Files
# -----------------------------------------------------------------------------
echo "Collecting static files..."
python manage.py collectstatic --noinput

# -----------------------------------------------------------------------------
# Start Server
# -----------------------------------------------------------------------------
echo "Starting server..."
exec "$@"
