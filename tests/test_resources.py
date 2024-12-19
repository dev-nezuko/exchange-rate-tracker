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
