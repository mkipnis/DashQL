A Dash-based wrapper for QuantLib


To build and run:
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
gunicorn rates:server --bind 0.0.0.0:8050
```

To run in the docker:
```
docker build -t rates-app .
docker run -e DASH_HOST=0.0.0.0 -p 8050:8050 rates-app
```
