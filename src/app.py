"""Simple Flask application that displays Hello World."""
from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    """Return Hello World message."""
    return "Hello, World!"


if __name__ == "__main__":
    app.run(debug=True)
