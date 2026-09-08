#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import socket, os, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect((os.environ.get('POSTGRES_HOST', 'db'), int(os.environ.get('POSTGRES_PORT', '5432'))))
except OSError:
    sys.exit(1)
finally:
    s.close()
" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL is up."

python manage.py migrate --noinput
python manage.py seed_demo_data

exec "$@"
