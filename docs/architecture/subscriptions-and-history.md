# Subscriptions And Watch History

Subscriptions are viewer-to-channel relationships. The subscription feed includes only public, ready, moderation-approved videos from followed channels.

Watch history is viewer-private. It is refreshed when an authenticated viewer emits a `play` event and stores the latest reported position. It is deliberately separate from counted views, which retain their five-second measurement semantics.

```txt
POST /channels/{channel_id}/subscribe
DELETE /channels/{channel_id}/subscribe
GET /feed/subscriptions
GET /library/history
```

History responses are scoped to the requesting viewer and may include that viewer's private video entries; another viewer receives no access through the history endpoint.
