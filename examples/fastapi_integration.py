"""cfx + FastAPI: application settings with runtime validation.

cfx handles the settings layer (database connection, server flags, env-var
overrides, CLI arguments).  pydantic handles request/response schemas — these
two roles do not overlap.

Run with:
    python fastapi_integration.py --db.port 5433 --debug
    DB_HOST=prod.db uvicorn fastapi_integration:app
"""

from cfx import Config, Field

#############################################################################
# Settings
#############################################################################


class DatabaseConfig(Config):
    confid = "db"

    host: str = Field("localhost", "Database host", env="DB_HOST")
    port: int = Field(
        5432, "Database port", minval=1, maxval=65535, env="DB_PORT"
    )
    name: str = Field("app", "Database name", env="DB_NAME")
    pool_size: int = Field(10, "Connection pool size", minval=1)


class AppSettings(Config):
    confid = "app"

    title: str = Field("My API", "API title")
    debug: bool = Field(False, "Enable debug mode")
    secret_key: str = Field("changeme", "Secret key", env="SECRET_KEY")

    def validate(self):
        if not self.debug and self.secret_key == "changeme":
            raise ValueError("secret_key must be changed in production")


# DatabaseConfig is a nested sub-config; each AppConfig instance gets its own
# independent DatabaseConfig instance (no shared state across instances).
class AppConfig(Config, components=[DatabaseConfig, AppSettings]):
    confid = "config"


#############################################################################
# Load config
#############################################################################

cfg = AppConfig()

# In __main__ context you can override from the command line:
#
#   if __name__ == "__main__":
#       import argparse
#       parser = argparse.ArgumentParser()
#       AppConfig.add_arguments(parser)
#       args = parser.parse_args()
#       cfg = AppConfig.from_argparse(args)


#############################################################################
# FastAPI app
#############################################################################

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    app = FastAPI(title=cfg.app.title, debug=cfg.app.debug)
    app.state.config = cfg

    # pydantic handles the request/response schema — cfx doesn't touch this.
    class ItemCreate(BaseModel):
        name: str
        price: float

    class ItemResponse(BaseModel):
        id: int
        name: str
        price: float

    @app.get("/")
    def root():
        return {"title": app.state.config.app.title}

    @app.get("/config")
    def get_config():
        """Return settings dict (only available in debug mode)."""
        if not app.state.config.app.debug:
            raise HTTPException(status_code=403, detail="Not in debug mode")
        return app.state.config.to_dict()

    @app.post("/items", response_model=ItemResponse)
    def create_item(item: ItemCreate):
        # pydantic validated item.name and item.price; cfx has no role here.
        return ItemResponse(id=1, name=item.name, price=item.price)

except ImportError:
    pass  # fastapi/pydantic not installed


#############################################################################
# Smoke test (no fastapi required)
#############################################################################

if __name__ == "__main__":
    import yaml

    cfg.db.host = "prod.example.com"
    cfg.db.port = 5433
    print(yaml.dump(cfg.to_dict(), default_flow_style=False))
