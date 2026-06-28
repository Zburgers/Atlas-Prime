# Media Fixtures

Keep this folder small and legal to commit.

The committed strategy is to generate a synthetic MP4 locally instead of checking in binary media:

```sh
make fixture
```

This writes `fixtures/media/sample-2s.mp4` using FFmpeg `lavfi` test sources. The generated file is ignored by git.
