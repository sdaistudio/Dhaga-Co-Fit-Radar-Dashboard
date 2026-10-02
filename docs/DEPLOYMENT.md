# Deployment

## 1. GitHub

```bash
git init
git add .
git commit -m "Fit Radar MVP"
git branch -M main
git remote add origin https://github.com/<your-account>/fit-radar.git
git push -u origin main
```

`.env` and `runs/` are ignored by git. Check that no key is in any committed file before you push.

## 2. Hugging Face Spaces (the route the brief suggests)

1. Create a new Space. Choose **Docker** as the SDK. Make it public.
2. Push this repository to the Space (it is a git remote like any other), or link the Space to the GitHub repository.
3. In the Space's settings, under secrets, add `ANTHROPIC_API_KEY` (or the GPT settings). Leave it out to run on offline rules.
4. The Space builds from the `Dockerfile` and serves on port 7860, which the header at the top of `README.md` declares.

Without a key the Space opens on the saved demo run and works fully. With a key, a visitor pressing **Run** spends your money: about 2,000 comments a run. Set a spend limit on the key, or leave the key out of the public Space and show a live run from your own machine.

## 3. Any other host

Anything that runs a Docker image or `uvicorn server:app --host 0.0.0.0 --port $PORT` works (Render, Railway, Fly.io, a VM). Set the same environment variables.

## Before the demo

- Open the public link on a phone and on a machine that has never seen it.
- Confirm the header says which reader produced the run on screen.
- Decide whether **Run** will be pressed live. If so, test it on the public link that morning.
