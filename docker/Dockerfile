# Single image shared by the pipeline, API, and dashboard services in
# docker-compose.yml -- which command runs is decided by each service's
# `command:` override, not by this file, so there's one dependency set to
# maintain instead of three near-duplicate images.
#
# NOT YET BUILT/TESTED: this build sandbox has no `docker` binary and no
# internet access, so this image has never actually been built or run. It
# follows standard, conservative patterns (slim base, no build-essential
# needed since pandas/scikit-learn ship wheels for this Python version), but
# you are the first to actually run `docker build` on it -- report back any
# errors.

FROM python:3.11-slim

WORKDIR /app

# Copy only the requirements file first so Docker can cache the pip install
# layer and skip reinstalling every dependency when only source code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command; overridden per-service in docker-compose.yml
CMD ["python", "src/ingestion/generate_synthetic_data.py"]
