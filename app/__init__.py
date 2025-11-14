"""
Flask application for miniflux-AI.
"""
from flask import Flask


def create_app() -> Flask:
    """
    Create a Flask application instance.
    """
    app = Flask(__name__)
    
    # Register blueprints
    from app.routes.webhook import webhook_bp
    from app.routes.digest import digest_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(digest_bp)
    
    return app
