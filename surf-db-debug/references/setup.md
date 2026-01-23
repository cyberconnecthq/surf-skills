# Database Debug Tool Setup Guide

This guide helps you configure secure database access for AI-assisted debugging.

## Prerequisites

- SSH access to bastion hosts
- Database credentials (read-only recommended)
- `psql` (PostgreSQL) or `mysql` client installed
- Python3 (standard on macOS, json module is built-in)

## Step 1: Create Config Directory

```bash
mkdir -p ~/.config/surf-db
chmod 700 ~/.config/surf-db
```

## Step 2: Create Configuration File

```bash
touch ~/.config/surf-db/config.json
chmod 600 ~/.config/surf-db/config.json
```

Edit `~/.config/surf-db/config.json`:

```json
{
  "environments": {
    "stg": {
      "bastion": {
        "host": "bastion.staging.example.com",
        "port": 22,
        "user": "your-username",
        "key_path": "~/.ssh/your-staging-key"
      },
      "default_db": "main",
      "databases": {
        "main": {
          "type": "postgres",
          "host": "db-main.internal.staging",
          "port": 5432,
          "name": "myapp_staging",
          "user": "readonly_user",
          "password": "your-password"
        },
        "analytics": {
          "type": "postgres",
          "host": "db-analytics.internal.staging",
          "port": 5432,
          "name": "analytics_staging",
          "user": "readonly_user",
          "password_cmd": "pass show surf/stg-analytics-password"
        },
        "events": {
          "type": "mysql",
          "host": "db-events.internal.staging",
          "port": 3306,
          "name": "events_staging",
          "user": "readonly_user",
          "password": "your-password"
        }
      }
    },
    "prd": {
      "bastion": {
        "host": "bastion.prod.example.com",
        "port": 22,
        "user": "your-username",
        "key_path": "~/.ssh/your-prod-key"
      },
      "default_db": "main",
      "databases": {
        "main": {
          "type": "postgres",
          "host": "db-main.internal.prod",
          "port": 5432,
          "name": "myapp_production",
          "user": "readonly_user",
          "password_cmd": "pass show surf/prd-db-password"
        }
      }
    }
  }
}
```

### Configuration Notes

- **Multiple databases**: Each environment can have multiple databases under `databases`
- **default_db**: Specifies which database to use when `--env stg` is used without specifying a database
- **password vs password_cmd**: Use `password_cmd` to fetch from password managers (recommended)
- **tunnel_port** (optional): Add to a database config to use a specific local port

## Step 3: Configure SSH ControlMaster (Recommended)

This enables connection reuse for faster repeated queries.

Create socket directory:

```bash
mkdir -p ~/.ssh/sockets
chmod 700 ~/.ssh/sockets
```

Add to `~/.ssh/config`:

```ssh-config
# SSH ControlMaster for connection reuse
Host *
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 10m
```

## Step 4: Verify Setup

```bash
~/.claude/skills/surf-db-debug/scripts/surf-db-query --check-setup
```

Expected output:
```
✓ Config file exists: ~/.config/surf-db/config.json
✓ Config file permissions: 600
✓ Python3 available (json module built-in)
✓ PostgreSQL client (psql) found
✓ Environment 'stg' configured
✓   SSH key exists: ~/.ssh/your-staging-key
      Database: main (default)
      Database: analytics
      Database: events
✓ Environment 'prd' configured
✓   SSH key exists: ~/.ssh/your-prod-key
      Database: main (default)
✓ SSH socket directory exists: ~/.ssh/sockets

Setup complete!
```

## Step 5: Test Connection

```bash
# List databases for an environment
~/.claude/skills/surf-db-debug/scripts/surf-db-query --env stg --list-dbs

# Start tunnel for default database
~/.claude/skills/surf-db-debug/scripts/surf-db-query --env stg --tunnel start

# Or start tunnel for specific database
~/.claude/skills/surf-db-debug/scripts/surf-db-query --env stg:analytics --tunnel start

# Test query
~/.claude/skills/surf-db-debug/scripts/surf-db-query --env stg --sql "SELECT 1"

# Query specific database
~/.claude/skills/surf-db-debug/scripts/surf-db-query --env stg:analytics --sql "SELECT 1"
```

## Usage Examples

```bash
# Use default database for stg
surf-db-query --env stg --sql "SELECT * FROM users LIMIT 5"

# Use specific database
surf-db-query --env stg:analytics --sql "SELECT * FROM events LIMIT 5"
surf-db-query --env stg:events --sql "SHOW TABLES"

# Tunnel management per database
surf-db-query --env stg:main --tunnel start
surf-db-query --env stg:analytics --tunnel start
```

## Security Best Practices

1. **Use read-only database users** - Create dedicated users with SELECT-only permissions
2. **Use password manager** - Use `password_cmd` instead of plaintext passwords
3. **Rotate credentials** - Regularly update database passwords
4. **Never share config** - The config file contains sensitive credentials
5. **File permissions** - Keep config.json at 600

## Troubleshooting

### "Permission denied" on SSH
```bash
chmod 600 ~/.ssh/your-key
```

### "Connection refused" on database
- Check if tunnel is running: `surf-db-query --env stg --tunnel status`
- Verify database host/port in config
- Check security group/firewall rules

### Forgot to close tunnel?
No problem! Tunnels use `ControlPersist` and will auto-close after 10 minutes of inactivity. You can also manually stop:
```bash
surf-db-query --env stg --tunnel stop
```

### Password command fails
Test your password command directly:
```bash
pass show surf/stg-db-password
```
