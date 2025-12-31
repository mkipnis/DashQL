A Dash-based wrapper for QuantLib


To build:
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

To run in the docker:
```
docker build -t rates-app .
docker run -e DASH_HOST=0.0.0.0 -p 8050:8050 rates-app
```
