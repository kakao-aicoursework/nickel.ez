import pynecone as pc

class AppnameConfig(pc.Config):
    pass

config = AppnameConfig(
    app_name="app_name",
    db_url="sqlite:///pynecone.db",
    env=pc.Env.DEV,
)