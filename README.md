# InstaPull

InstaPull turns your Instagram saved posts into an AI-agent-readable memory layer. It exports saves into a local JSON index and can use vision models to describe images and videos, so agents can better understand what you collect, what you like, and what patterns show up across your saved posts.

The goal is not just to download data. The goal is to make saved Instagram posts usable as context for AI agents, personal search, taste analysis, question-answering, and future workflows that need structured memory about your interests.

## What It Does

- Reads your logged-in Instagram session from your browser cookies.
- Fetches posts you saved on Instagram.
- Saves everything into an `index.json` file with structured data for AI agents.
- Optionally asks an AI model to describe images and videos.

AI analysis is off by default. For image posts, InstaPull analyzes one image when a provider is selected. For video posts, it samples representative frames across the video and asks the AI provider for a video-specific description. Those descriptions are stored alongside the original Instagram metadata so an agent can search and reason over both the post content and the generated visual understanding.

## Install

From this repository:

```bash
pip install -e ".[gemini]"
```

Use `.[all]` to install every currently supported optional provider dependency. Right now, that means Gemini. Ollama support uses the core dependencies and expects Ollama itself to be installed separately on your machine.

## Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Then edit `.env` and add the credentials for the provider you want to use.

Important: do not publish your `.env` file. It can contain private API keys. The included `.gitignore` is configured to keep `.env` out of Git.

## Usage

Fetch 10 saved posts without AI analysis:

```bash
instapull sync --limit 10
```

Fetch 10 saved posts using Gemini:

```bash
instapull sync --provider gemini --limit 10
```

Fetch 10 saved posts using a local Ollama vision model:

```bash
instapull sync --provider ollama --limit 10
```

If your computer says `instapull` is not found, use this equivalent command:

```bash
python3 -m instapull.cli sync --provider gemini --limit 10
```

You can also choose Gemini in `.env`:

```bash
INSTAPULL_PROVIDER=gemini
```

Save to a custom folder:

```bash
instapull sync --output ~/Desktop/instapull-data
```

## AI Providers

InstaPull currently includes:

- `gemini`: Google Gemini Developer API, with optional Vertex AI mode.
- `ollama`: local vision models through an Ollama server running on your machine.
- `none`: no AI analysis.

The provider code lives in `instapull/providers/`. Each provider implements the same small interface, so new providers can be added without changing the rest of the export flow.

For Gemini, there are two paths:

- Gemini Developer API through Google AI Studio: uses `GEMINI_API_KEY`. Google documents this API-key path, but access can depend on your account, region, project permissions, and billing or quota setup.
- Vertex AI: uses `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and Google Cloud credentials on the machine. This is more setup, but some users may prefer it if they already use Google Cloud.

### Ollama Local Models

Local model files are not bundled with InstaPull. They can be several gigabytes, and users have different hardware. Instead, InstaPull talks to Ollama, which runs the model locally on the user's machine.

Basic setup:

```bash
ollama pull qwen2.5vl
instapull sync --provider ollama
```

By default, InstaPull expects:

```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5vl
```

You can change those in `.env`. The model must support vision input. A text-only local model will not be able to analyze images or video frames.

## Image And Video Analysis

Images and videos are handled differently.

For images:

- InstaPull downloads the image.
- It resizes the image before sending it to the AI provider.
- It asks for a concise image description.

For videos:

- InstaPull downloads the video to a temporary local file.
- It extracts frames across the duration of the video.
- It sends those frames together to the AI provider.
- It asks for a video summary that describes the sequence, not just separate images.
- It deletes the temporary video file after frame extraction.

Default video sampling:

- 0-2 seconds: 2 frames
- 2-5 seconds: 3 frames
- 5-10 seconds: 5 frames
- 10-15 seconds: 6 frames
- 15-20 seconds: 8 frames
- 20-30 seconds: 10 frames
- 30-45 seconds: 12 frames
- 45-60 seconds: 14 frames
- 60-90 seconds: 16 frames
- 90-120 seconds: 18 frames
- 120-180 seconds: 20 frames
- 180-300 seconds: 24 frames
- Longer than 300 seconds: about 1 frame every 2 seconds, capped by `INSTAPULL_VIDEO_MAX_FRAMES`

You can change these settings in `.env`:

```bash
INSTAPULL_VIDEO_SECONDS_PER_FRAME=2
INSTAPULL_VIDEO_MAX_FRAMES=24
INSTAPULL_MAX_VIDEO_MB=100
```

`INSTAPULL_MAX_VIDEO_MB` is a safety limit for temporary video downloads. The default is 100 MB so the tool does not unexpectedly download very large videos, use too much disk space, or send a much larger AI request than expected. You can raise it if your saved videos are larger.

## Output Data

InstaPull writes one file: `index.json`.

This file is intended to be easy for AI agents and scripts to read. Each entry keeps the source Instagram metadata, direct media URLs, and optional AI-generated visual analysis.

Each post entry includes:

- `post_id`
- `username`
- `post_url`
- `image_url`
- `video_url`
- `caption`
- `hashtags`
- `date`
- `post_type`
- `location`
- `ai_description`
- `ai_provider`
- `ai_model`
- `ai_media_type`
- `ai_frames_analyzed`

For videos, `image_url` is usually the preview image and `video_url` is the actual video file.

## Privacy And Security

InstaPull may send image data or sampled video frames to the AI provider you choose. If you do not choose a provider, no AI provider receives media. InstaPull does not send your Instagram password, but it does use your Instagram browser session to read your saved posts.

Do not share:

- `.env`
- API keys
- Instagram session IDs
- exported data if it contains private saves or captions

InstaPull uses browser-cookie login. A cookie is a small browser value that websites use to remember your login.

## Instagram Disclaimer

InstaPull is not affiliated with, authorized, maintained, sponsored, or endorsed by Instagram or Meta. Use it at your own risk.

## Current Limitations

- The export currently writes one `index.json` file, not one file per post.
- Carousel posts are currently analyzed using the main image only.
- Instagram can change its private behavior, which may affect saved-post fetching.
- AI descriptions can be incomplete or wrong. Treat them as generated notes, not facts.
- Video audio is not transcribed or analyzed yet.

## Development

Run a quick syntax check:

```bash
python3 -m compileall instapull
```

Run the lightweight test suite:

```bash
python3 -m unittest discover
```

Show the command-line help:

```bash
python3 -m instapull.cli --help
python3 -m instapull.cli sync --help
```
