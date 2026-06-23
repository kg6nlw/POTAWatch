# POTA Discord Alerts

This is a simple GitHub Actions + Discord webhook setup that checks current POTA spots and posts matching activators or parks into a Discord channel as embedded messages.

## What it does

- Checks the POTA activator spot feed.
- Matches callsigns and/or park references from `config.json`.
- Posts clean Discord embeds through a webhook.
- Runs automatically every 5 minutes with GitHub Actions.
- Stores already-posted spots in `seen_spots.json` so it does not spam duplicates.

## 1. Create your Discord webhook

1. In Discord, create a channel such as `#pota-alerts`.
2. Right-click the channel or open channel settings.
3. Go to **Integrations**.
4. Choose **Webhooks**.
5. Create a new webhook.
6. Copy the webhook URL.

## 2. Put this folder in GitHub

Create a new GitHub repository and upload these files:

```text
.github/workflows/pota-discord-alerts.yml
config.json
pota_discord_alerts.py
requirements.txt
README.md
```

## 3. Add your Discord webhook as a GitHub secret

In your GitHub repo:

1. Go to **Settings**.
2. Go to **Secrets and variables**.
3. Choose **Actions**.
4. Click **New repository secret**.
5. Name it exactly:

```text
DISCORD_WEBHOOK_URL
```

6. Paste your Discord webhook URL as the value.

## 4. Edit `config.json`

Example:

```json
{
  "watch_callsigns": [
    "KG6NLW",
    "K6ARK"
  ],
  "watch_parks": [
    "US-0001"
  ],
  "watch_modes": [],
  "watch_bands": [],
  "role_id": "",
  "ping_role": false,
  "only_newer_than_minutes": 20
}
```

### Callsign alerts

To alert on specific activators:

```json
"watch_callsigns": ["KG6NLW", "K6ARK", "AA0Z", "AI7LK", "K0WHW", "K1DDN", "K5QBF", "K5YVY", "K6DJV", "K6YYL", "K7SPR", "K8MRD", "K9OL", "KC5HWB", "KD7DTS", "KE8LQR", "KE8UTX", "KG5AHJ", "KH2SR", "KH6WI", "KI2D", "KI6NAZ", "KJ5LXP", "KK6USY", "KM9G", "KT0ADS", "NB6GC", "NW9F", "R1BIG", "VA3SDO", "VA7BIX", "VE6LK", "VE9CF", "VK7HH", "W1FYG", "W2HRC", "W6VVR", "W7DLZ", "WB6NOA", "WE4DX", "WT1W", "WX6SWW"]
```

### Park alerts

To alert on specific parks:

```json
"watch_parks": ["US-1234", "US-5678"]
```

### Mode filters

Leave blank for all modes:

```json
"watch_modes": []
```

Or limit it:

```json
"watch_modes": ["SSB", "CW", "FT8"]
```

### Band filters

Leave blank for all bands:

```json
"watch_bands": []
```

Or limit it:

```json
"watch_bands": ["20m", "40m"]
```

## 5. Turn on GitHub Actions

Go to the **Actions** tab in your GitHub repo.

Run **POTA Discord Alerts** manually once using **Run workflow**.

After that, it runs automatically every 5 minutes.

## Optional: role ping

In Discord, enable Developer Mode, right-click the role, and copy the role ID.

Then edit `config.json`:

```json
"role_id": "123456789012345678",
"ping_role": true
```

The bot uses Discord `allowed_mentions` so it only pings the role ID you enter.

## Important notes

GitHub scheduled workflows are not instant. They are good for simple alerting, but not guaranteed to fire exactly on the minute.

If you want near-real-time alerts, run `pota_discord_alerts.py` on a Raspberry Pi, shack PC, or VPS every minute with cron instead.
