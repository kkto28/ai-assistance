# Troubleshooting Google Calendar

This guide covers Clawbot's Google Calendar skill, which uses the Google
Calendar API and OAuth credentials. The skill supports listing, creating,
updating, and deleting events.

## Start here

1. Confirm the Google Calendar API is enabled for the Google Cloud project
   associated with your OAuth client.
2. Check that the OAuth client ID, client secret, and refresh token are set in
   `clawbot/set_env.sh` or the environment used to start Clawbot.
3. Confirm the OAuth grant includes the Calendar scope:
   `https://www.googleapis.com/auth/calendar`.
4. Restart the Clawbot process after changing environment variables. Launchers
   load `clawbot/set_env.sh` at startup.
5. Try listing events from the `primary` calendar before troubleshooting a
   different calendar or a write operation.

Do not paste credentials, access tokens, refresh tokens, or the contents of
`set_env.sh` into logs, issues, or chat.

## Check and reset OAuth tokens

Use the checks below in order. A successful, read-only listing confirms that
the credential path being tested can access Calendar; an empty event list is
still a successful API response.

### Check `GOOGLE_CALENDAR_ACCESS_TOKEN`

1. Start Clawbot with `GOOGLE_CALENDAR_ACCESS_TOKEN` configured and ask it to
   list today's events. The skill uses this token directly when it is set.
   This performs a read-only
   [Calendar events.list request](https://developers.google.com/workspace/calendar/api/v3/reference/events/list).
   A successful response means Google accepted the token for this request.
2. If the response is `401`, the token is expired, revoked, or otherwise
   invalid. The skill cannot distinguish these cases. A `403` usually points
   instead to an API, scope, account, or calendar permission issue.
3. For more context, review Google's
   [OAuth token expiration and revocation guidance](https://developers.google.com/identity/protocols/oauth2#expiration).

Access tokens are short-lived. The simplest fix is to remove or comment out
`GOOGLE_CALENDAR_ACCESS_TOKEN` in `clawbot/set_env.sh` (and unset it from the
environment used to launch Clawbot, if set there), then restart Clawbot. With
the access-token override removed, Clawbot will use the refresh-token
settings to obtain a fresh access token automatically. If no valid refresh
token is configured, follow the refresh-token steps below.

### Check `GOOGLE_CALENDAR_REFRESH_TOKEN`

The access-token setting takes precedence, so first remove or comment out
`GOOGLE_CALENDAR_ACCESS_TOKEN` from `clawbot/set_env.sh` and unset it from the
launcher environment. Restart Clawbot, then ask it to list today's events.
This forces the skill to exchange the configured refresh token for an access
token and make a read-only Calendar request.

- If the listing succeeds, the refresh token and matching OAuth client
  credentials were accepted.
- If the response includes `invalid_grant` or a refresh-token error, Google
  rejected the refresh token. Check that the refresh token, client ID, and
  client secret came from the same OAuth client, and review Google's
  [refresh-token expiration rules](https://developers.google.com/identity/protocols/oauth2#expiration).
- If the response is `403`, check API enablement, granted scope, account
  access, and consent-screen test-user status before replacing the token.

### Reset or replace the refresh token

1. In the [Google Cloud API Library](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com),
   make sure Google Calendar API is enabled in the project for the OAuth
   client.
2. In [Google Cloud OAuth clients](https://console.cloud.google.com/auth/clients),
   identify the client whose ID and secret Clawbot uses. For a new client,
   configure the OAuth consent screen and add the Google account as a test
   user if the app is in testing. When using the OAuth Playground below, use
   an OAuth client that allows its redirect URI,
   `https://developers.google.com/oauthplayground`.
3. Open Google's [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
   Open its settings, enable **Use your own OAuth credentials**, and enter the
   client ID and secret for that same client. Set access type to **Offline**
   so the token exchange can return a refresh token. Treat the client values
   as secrets.
4. In Step 1, request the scope
   `https://www.googleapis.com/auth/calendar`, authorize with the Google
   account whose calendar Clawbot should access, and grant consent.
5. In Step 2, exchange the authorization code for tokens. Copy the returned
   **refresh token** into `GOOGLE_CALENDAR_REFRESH_TOKEN`. Do not put the
   short-lived access token in the long-term configuration.
6. Update `GOOGLE_CALENDAR_CLIENT_ID` and `GOOGLE_CALENDAR_CLIENT_SECRET` to
   match the client used to issue the new refresh token. Remove
   `GOOGLE_CALENDAR_ACCESS_TOKEN`, restart Clawbot, and verify by listing
   today's events.

If no refresh token is returned, confirm **Offline** access is selected, then
grant consent again. If the account already granted this client access, revoke
that app's access in [Google Account connections](https://myaccount.google.com/connections),
then repeat the Playground authorization and exchange. Revoking access
invalidates existing credentials for that app; only do this for the correct
application.

For an external OAuth consent screen left in **Testing**, Google issues
refresh tokens that expire after seven days (except when requesting only basic
identity scopes). For a personal Calendar integration that needs to keep
running, review the app's publishing status on the
[OAuth consent screen](https://console.cloud.google.com/auth/audience) and
move it to **In production** if appropriate. A newly issued token does not
extend the lifetime of an existing token; authorize again after changing the
publishing status. See Google's
[refresh-token expiration rules](https://developers.google.com/identity/protocols/oauth2#expiration).

## Common errors

### Credentials are not configured

The skill requires either a `GOOGLE_CALENDAR_ACCESS_TOKEN`, or all three of:

- `GOOGLE_CALENDAR_CLIENT_ID`
- `GOOGLE_CALENDAR_CLIENT_SECRET`
- `GOOGLE_CALENDAR_REFRESH_TOKEN`

The access token setting takes precedence over refresh-token authentication.
Access tokens expire, so remove an old `GOOGLE_CALENDAR_ACCESS_TOKEN` and
restart the process to use the refresh token instead.

Check that variables are actually available to the running launcher. If using
`clawbot/set_env.sh`, ensure the file is at that exact path and that the
launcher was restarted after editing it.

### `invalid_grant`, refresh failure, or token response has no access token

The refresh token may have been revoked, issued to a different OAuth client,
or invalidated by a change to the OAuth consent configuration. Re-authorize
the application and replace the refresh token along with the matching client
ID and secret. Confirm the authorization includes the Calendar scope.

If using an OAuth consent screen in testing mode, confirm the Google account
is listed as a test user. Do not solve this by switching to a short-lived
access token for normal use.

### `401` / unauthenticated or invalid credentials

Follow [Check and reset OAuth tokens](#check-and-reset-oauth-tokens) to
identify whether the access token or refresh-token flow is failing. The skill
uses a configured access token directly and does not refresh it.

### `403` / permission denied or API not enabled

Check that the Google Calendar API is enabled in the Google Cloud project
associated with the OAuth client. Verify that the account granted the
Calendar scope and has access to the requested calendar. For a shared
calendar, ensure the account used for OAuth has the necessary sharing
permissions. Re-authorize after changing scopes.

### `404` / calendar or event not found

Calendar IDs default to `primary`. If using another calendar, confirm its
calendar ID and that the authorized account can access it. When updating or
deleting an event, first list events and use the exact event ID returned by
Clawbot. An event ID from another calendar will not necessarily work with the
current calendar ID.

### Invalid date or time

Event start and end values must be ISO 8601 date-times, for example:

```text
2026-09-25T10:00:00
2026-09-25T10:00:00+01:00
```

When no offset is supplied, Clawbot uses `Europe/London`. You can provide a
timezone explicitly when creating or updating an event. Check that the end is
after the start and that the intended daylight-saving offset is correct.

For event listings, use a supported date phrase such as `today`, `tomorrow`,
`yesterday`, `day after tomorrow`, `2026-09-25`, or `25/09/2026`. A specific
date phrase cannot be combined with `time_min` or `time_max`. Listing a date
uses the UK calendar day (`Europe/London`).

### No events found, or an event appears at the wrong time

- Confirm the correct calendar is selected; the default is `primary`.
- Check the requested day in `Europe/London`. Date-only listing bounds follow
  that timezone, including daylight-saving changes.
- For a custom listing range, verify `time_min` and `time_max` include the
  event. A listing with no `time_min` starts at the current time, so past
  events will not appear.
- Check the event's timezone and offset in Google Calendar. An ISO date-time
  with an explicit offset represents an exact moment and may display on a
  different local time or date in another timezone.

### Network, timeout, or connection error

The Calendar skill needs outbound HTTPS access to Google's OAuth and Calendar
API endpoints. Check the network connection, proxy/firewall rules, DNS, and
Google service availability, then retry. The skill's HTTP requests time out
after 20 seconds.

## Safe recovery workflow

1. Test a read-only listing on `primary`.
2. Resolve authentication or access errors before trying writes.
3. For an update or deletion, list events first and verify the exact event ID
   and calendar.
4. After creating or updating an event, list the relevant date range to
   confirm the result.

Clawbot reports Google API errors in its tool response. Retain the error
message for diagnosis, but remove credentials and private event details before
sharing it.
