from app.core.config import settings
from app.main import app


def test_app_name_is_data_skill_marketplace():
    assert settings.app_name == "Data Skill Marketplace"
    assert app.title == "Data Skill Marketplace"
