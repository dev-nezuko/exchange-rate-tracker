from starlette import status


def test_health_endpoint(test_client):
    response = test_client.get('/')
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['message'] == 'System is up and running'


def test_exchange_rates(test_client):
    response = test_client.get('/exchange-rates/')
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['rates'] == []


def test_get_all_exchange_rates(test_client, test_db, test_exchange_rate):
    test_db.add(test_exchange_rate)
    test_db.commit()
    response = test_client.get('/exchange-rates/')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()['rates']) == 1
    assert response.json()['rates'][0]['rate'] == test_exchange_rate.rate


def test_rates_board_is_served_with_its_assets(test_client):
    page = test_client.get('/rates')
    assert page.status_code == status.HTTP_200_OK
    assert page.headers['content-type'].startswith('text/html')
    assert '<label for="filter">' in page.text
    for asset in ('/static/rates.css', '/static/rates.js'):
        assert asset in page.text
        assert test_client.get(asset).status_code == status.HTTP_200_OK
