# Playlists

Playlists are creator-owned collections with `private` as the default visibility. A public playlist is readable without a session; a private playlist is readable only by its owner and is indistinguishable from a missing playlist to other viewers.

Only public, ready, moderation-approved videos can be added. This keeps a public playlist from leaking private, processing, or removed media.

```txt
POST   /playlists
GET    /playlists/{playlist_id}
POST   /playlists/{playlist_id}/items
DELETE /playlists/{playlist_id}/items/{item_id}
```

`playlist_items.position` provides stable creator ordering. Each video can occur only once in a playlist.
