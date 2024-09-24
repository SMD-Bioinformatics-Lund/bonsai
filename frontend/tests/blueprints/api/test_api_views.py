from flask import url_for


def test_add_to_group(app, user_obj):
    with app.test_client(user=user_obj) as client:
        client.get("/")
