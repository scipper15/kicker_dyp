import os


class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    QUALIFYING_FILENAME = 'qualifying-group-1.xml'
    TREE_1_FILENAME = 'elimination-KO-Baum 1.xml'
    TREE_2_FILENAME = 'elimination-KO-Baum 2.xml'


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
        os.path.join(Config.basedir, 'dev.db')
    SECRET_KEY = 'your-secret-key'
    SERVER_NAME = 'tablesoccer.rocks:5000'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
        os.path.join(Config.basedir, 'test.db')
    SECRET_KEY = 'your-secret-key'
    SERVER_NAME = 'tablesoccer.rocks:5000'


class ProdConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
        os.path.join(Config.basedir, 'prod.db')
    SERVER_NAME = 'tablesoccer.rocks'
    # secret key should come from .env file which is obviously not part of the repository
    # create the file to make it work (compare readme.md)


config = {
    'dev': DevConfig,
    'test': TestConfig,
    'prod': ProdConfig,
}
