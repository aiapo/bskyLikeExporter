# bskyLikeExporter
Export all your Bluesky likes to a simple HTML file, including local download of images and videos for archival using Python.

Designed for my personal use, so it was developed in a couple of hours and may have bugs.
I may add QOL features in the future to improve it but I currently am not using Bluesky at the moment.

## Running
### Install dependencies
```bash
pip install -r requirements.txt
```

### Fill out .env
Copy `.env.sample` to `.env` and fill out your handle and app password.

### Run
```bash
python main.py
```

### Export
The program will export to `likes.html`

## Potential Future Todos
- Database to maintain list of likes to only update new likes
- Better way to download videos
- More interactive
- Better error handling / rate limit checks