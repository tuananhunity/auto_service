from src import create_app

app = create_app()


if __name__ == "__main__":
    from src.extensions import socketio

    socketio.run(
        app,
        host="0.0.0.0",
        port=5500,
        debug=False,
        allow_unsafe_werkzeug=True,
    )
