class Config:
    QUALIFYING_FILENAME = 'qualifying-group-1.xml'
    TREE_1_FILENAME = 'elimination-KO-Baum 1.xml'
    TREE_2_FILENAME = 'elimination-KO-Baum 2.xml'


class DevConfig(Config):
    DEBUG = True
    SECRET_KEY = 'your-secret-key'
    SERVER_NAME = 'tablesoccer.rocks:5000'


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'your-secret-key'
    SERVER_NAME = 'tablesoccer.rocks:5000'


class ProdConfig(Config):
    DEBUG = False
    SERVER_NAME = 'tablesoccer.rocks'
    # secret key should come from .env file, create the file to make it work (compare readme.md)
    # SECRET_KEY = 'your-secret-key'


config = {
    'dev': DevConfig,
    'test': TestConfig,
    'prod': ProdConfig,
}
