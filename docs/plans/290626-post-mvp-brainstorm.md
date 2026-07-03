# Post-MVP Platform Evolution Ideas — Atlas Prime

*Generated: 29-06-2026*
*Status: Brainstorm / Research Phase*

---

## Current State (MVP Complete)

The platform currently supports:
- User authentication via Clerk
- Video upload → MinIO storage
- Background FFmpeg HLS transcoding (720p/360p)
- Authenticated HLS playback via API proxy
- Basic video library/list/watch pages
- Admin dashboard for operations/debugging
- Playback event telemetry

---

## Major Feature Themes

### 1. SOCIAL & ENGAGEMENT

#### Comments System
- Nested comment threads with reply support
- Comment likes/upvotes
- Comment pinning by video owner
- Basic markdown or rich text formatting
- Real-time updates via polling (SSE future)

#### Likes / Reactions
- Like/unlike buttons on videos
- View count tracking
- Social proof indicators (likes, views)
- API: `POST /videos/{id}/likes`

#### Subscriptions & Channels
- Creator profile pages
- Subscribe/unsubscribe flow
- Subscriber count visibility
- Channel branding (banners, avatars)

#### Notifications
- In-app notification center
- Email/SMS hooks for important events
- Notification preferences per user

---

### 2. DISCOVERY & SEARCH

#### Search Engine
- Full-text video title/description search
- Tags system for videos
- Search filters (date, duration, quality)
- Search suggestions/autocomplete

#### Categories & Tags
- Predefined video categories
- User-defined tags
- Tag-based browsing
- Category landing pages

#### Homepage Feed
- Personalized video feed
- Trending/recent videos
- "Watch next" suggestions
- Algorithm stub (simple recency/popularity)

---

### 3. CREATOR TOOLS & ANALYTICS

#### Advanced Dashboard
- Video performance analytics (views, watch time)
- Audience demographics
- Revenue/analytics (if monetization added later)
- A/B testing for thumbnails

#### Video Management
- Bulk video actions
- Scheduled publishing
- Video versioning/replacement
- Privacy scheduling (private → public on date)

#### Metadata Richness
- Custom thumbnails upload
- Video chapters/timestamps
- Multi-language support
- End screens / cards

---

### 4. PLAYBACK ENHANCEMENTS

#### Quality Selection
- Manual quality selector (360p, 480p, 720p, 1080p)
- Auto quality switching based on bandwidth
- Playback speed controls (0.5x, 1.25x, 1.5x, 2x)

#### Advanced Player Features
- Keyboard shortcuts
- Picture-in-picture support
- Theater mode / fullscreen enhancements
- Autoplay toggle
- Captions support (VTT files)

#### Shorts Format
- Vertical video support
- Shorts-specific discovery feed
- Duration limits (< 60s)

---

### 5. INFRASTRUCTURE & SCALABILITY

#### CDN Integration
- Cloudflare R2 / S3 for production
- Signed URL expiration
- Cache invalidation strategy
- Multi-region delivery

#### Advanced Transcoding
- 1080p/4K renditions
- AV1/H.265 codec support
- HDR/Dolby Vision
- Multiple audio tracks
- Subtitle generation (auto + upload)

#### Storage Lifecycle
- Automatic cleanup of drafts after N days
- Archive storage for inactive videos
- Transcoded version garbage collection

---

### 6. MODERATION & SAFETY

#### Content Moderation
- Report system (spam, abuse flags)
- Auto-moderation for titles/descriptions
- Moderation queue dashboard
- Age-restricted content flow

#### Comments Moderation
- Blocklist for banned words
- Comment hold for review
- Auto-collapse for low-quality comments

#### DMCA / Copyright
- Takedown request handling
- Content ID system stub
- Repeat infringer policy

---

### 7. MONETIZATION & PREMIUM

#### Creator Monetization
- Super Chat-style donations
- Channel memberships
- Creator revenue sharing
- Payout dashboard

#### Ads System
- Pre-roll/mid-roll ad slots
- Ad-free viewing (premium)
- Ad performance analytics

#### Subscriptions
- Premium tier (no ads, early access)
- Channel-specific subscriptions
- Free trial system

---

### 8. LIVE STREAMING (Major Addition)

- RTMP ingest endpoint
- Live transcoding pipeline
- Live chat (WebSocket-based)
- Stream recording to VOD
- Scheduled streams

---

### 9. MOBILE & APP ECOSYSTEM

#### Native Mobile Apps
- iOS/Android apps (React Native)
- Offline viewing (premium)
- Mobile upload from camera roll
- Push notifications

#### Smart TV Apps
- Apple TV, Android TV
- Remote-friendly UI
- 4K playback support

---

### 10. ADVANCED UX FEATURES

#### Playlists
- User-created playlists
- Auto-play next video
- Shuffle/repeat modes
- Playlist privacy settings

#### Watch History
- Watch later list
- Continue watching
- History management
- Clear history option

#### User Profiles
- Avatar upload
- Bio/description
- Social links
- Theme preferences

---

## Quick Wins (Implement Soon)

These are "low-hanging fruit" that build on existing infrastructure:

1. **Video Likes System** - Database table, API endpoint, UI component
2. **Custom Thumbnails** - Upload flow addition, MinIO storage
3. **View Count Tracking** - Increment on playback start
4. **Video Tags** - Simple string array on videos table
5. **Audio-only Playback** - Extract audio rendition option
6. **Export Transcript Hook** - Placeholder for future captions

---

## Moonshot Ideas

For when the platform matures:

1. **AI-Powered Features**
   - Auto-chapters generation from transcript
   - Smart blur/pixelate for faces
   - Duplicate detection across platform

2. **Creator Studio**
   - Stream deck integration
   - OBS plugin for direct streaming
   - Audio editing tools

3. **Community Features**
   - Live chat during premieres
   - Community posts (text updates)
   - Polls on videos

---

## Questions for Prioritization

1. Which social features matter most? (comments, likes, subscriptions)
2. Should we tackle discovery/search before creator tools?
3. Do you want mobile app planning now or focus on web?
4. Any features here that are explicitly NOT wanted?
5. What's your vision for the "crazy" part - what would surprise/delight users?