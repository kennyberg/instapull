# Security Policy

## Reporting A Security Issue

If you find a security issue, please open a private report if the repository host supports it. If private reporting is not available yet, avoid posting secrets or exploit details publicly.

## Secrets

Never commit private credentials to this repository.

Examples of secrets:

- `.env` files
- API keys
- Instagram session IDs
- Google Cloud credential files
- private keys

The `.gitignore` file is configured to ignore common secret files, but you should still review changes before publishing.

## Data Sent To AI Providers

When AI analysis is enabled, InstaPull sends image data or sampled video frames to the selected AI provider. Captions may be included as context in the prompt. Do not use AI analysis on content you do not want sent to that provider. If no provider is selected, media is not sent to an AI provider.

## Instagram Session Data

InstaPull reads browser cookies to access saved posts for the account you are already logged into. A cookie is a small browser value that websites use to remember your login. Treat Instagram session cookies as private login material.
