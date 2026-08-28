from app.db import get_db_engine


def get_db():
    db = get_db_engine().get_session()
    try:
        yield db
    finally:
        db.close()
