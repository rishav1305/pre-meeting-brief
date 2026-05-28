"""Brief distribution channels — calendar event attachment, Slack digest, etc.

For the POC the Google Calendar channel is wired as a mock: the payload that
a real Google Calendar Events.patch() call would carry is constructed and
persisted to pre_meeting_brief.distribution_log, but the HTTP call is not made.
The architectural seam is real; the OAuth and network call are deferred.
"""
