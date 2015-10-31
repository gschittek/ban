import json
from functools import wraps


import pytest

from ban.core.tests.factories import (HouseNumberFactory, PositionFactory,
                                      StreetFactory, MunicipalityFactory)
from ban.http import views

pytestmark = pytest.mark.django_db


def log_in(func):
    @wraps(func)
    def inner(*args, **kwargs):
        # Subtly plug in authenticated user.
        return func(*args, **kwargs)
    return inner


@pytest.mark.xfail
@pytest.mark.parametrize('name,kwargs,expected', [
    ['api:position', {"ref": 1, "key": "id"}, '/api/position/id/1/'],
    ['api:position', {}, '/api/position/'],
    ['api:housenumber', {"ref": 1, "key": "id"}, '/api/housenumber/id/1/'],
    ['api:housenumber', {"ref": "93031_1491H_84_BIS", "key": "cia"}, '/api/housenumber/cia/93031_1491H_84_BIS/'],  # noqa
    ['api:housenumber', {}, '/api/housenumber/'],
    ['api:street', {"ref": 1, "key": "id"}, '/api/street/id/1/'],
    ['api:street', {"ref": "930310644M", "key": "fantoir"}, '/api/street/fantoir/930310644M/'],  # noqa
    ['api:street', {}, '/api/street/'],
    ['api:municipality', {"ref": 1, "key": "id"}, '/api/municipality/id/1/'],
    ['api:municipality', {"ref": "93031", "key": "insee"}, '/api/municipality/insee/93031/'],  # noqa
    ['api:municipality', {"ref": "93031321", "key": "siren"}, '/api/municipality/siren/93031321/'],  # noqa
    ['api:municipality', {}, '/api/municipality/'],
])
def test_api_url(name, kwargs, expected):
    assert reverse(name, kwargs=kwargs) == expected


def test_invalid_identifier_returns_400(get):
    resp = get('/position/invalid:22')
    assert resp.status == 400


def test_cors(get):
    street = StreetFactory(name="Rue des Boulets")
    resp = get('/street/id:' + str(street.id))
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert resp.headers["Access-Control-Allow-Headers"] == "X-Requested-With"


def test_get_housenumber(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url(views.Housenumber, id=housenumber.id, identifier="id"))
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['street']['name'] == housenumber.street.name


def test_get_housenumber_with_unknown_id_is_404(get, url):
    resp = get(url(views.Housenumber, id=22, identifier="id"))
    assert resp.status == 404


def test_get_housenumber_with_cia(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url(views.Housenumber, id=housenumber.cia, identifier="cia"))
    assert resp.json['number'] == "22"


def test_get_street(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url(views.Street, id=street.id, identifier="id"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_with_fantoir(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url(views.Street, id=street.fantoir, identifier="fantoir"))
    assert resp.json['name'] == "Rue des Boulets"


@log_in
def test_create_position(post):
    housenumber = HouseNumberFactory(number="22")
    url = '/position'
    data = {
        "version": 1,
        "center": "(3, 4)",
        "housenumber": housenumber.id,
    }
    resp = post(url, data)
    assert resp.status == 201
    assert resp.json['id']
    assert resp.json['center']['lon'] == 3
    assert resp.json['center']['lat'] == 4
    assert resp.json['housenumber']['id'] == housenumber.id


@log_in
def test_replace_position(put, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(views.Position, id=position.id, identifier="id")
    data = {
        "version": 2,
        "center": (3, 4),
        "housenumber": position.housenumber.id
    }
    resp = put(uri, body=json.dumps(data))
    assert resp.status == 200
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 2
    assert resp.json['center']['lon'] == 3
    assert resp.json['center']['lat'] == 4


@log_in
def test_replace_position_with_existing_version_fails(put, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(views.Position, id=position.id, identifier="id")
    data = {
        "version": 1,
        "center": (3, 4),
        "housenumber": position.housenumber.id
    }
    resp = put(uri, body=json.dumps(data))
    assert resp.status == 409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_replace_position_with_non_incremental_version_fails(put, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(views.Position, id=position.id, identifier="id")
    data = {
        "version": 18,
        "center": (3, 4),
        "housenumber": position.housenumber.id
    }
    resp = put(uri, body=json.dumps(data))
    assert resp.status == 409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_update_position(post, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(views.Position, id=position.id, identifier="id")
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = post(uri, data=data)
    assert resp.status == 200
    assert resp.json['id'] == position.id
    assert resp.json['center']['lon'] == 3.4
    assert resp.json['center']['lat'] == 5.678


@log_in
def test_update_position_with_existing_version_fails(post, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(views.Position, id=position.id, identifier="id")
    data = {
        "version": 1,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = post(uri, data=data)
    assert resp.status == 409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_update_position_with_non_incremental_version_fails(post, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(views.Position, id=position.id, identifier="id")
    data = {
        "version": 3,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = post(uri, data)
    assert resp.status == 409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_create_housenumber(post):
    street = StreetFactory(name="Rue de Bonbons")
    data = {
        "version": 1,
        "number": 20,
        "street": street.id,
    }
    resp = post('/housenumber', data)
    assert resp.status == 201
    assert resp.json['id']
    assert resp.json['number'] == '20'
    assert resp.json['ordinal'] == ''
    assert resp.json['street']['id'] == street.id


@log_in
def test_create_housenumber_does_not_use_version_field(post):
    street = StreetFactory(name="Rue de Bonbons")
    data = {
        "version": 3,
        "number": 20,
        "street": street.id,
    }
    resp = post('/housenumber', data=data)
    assert resp.status == 201
    assert resp.json['id']
    assert resp.json['version'] == 1


@log_in
def test_replace_housenumber(put, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    uri = url(views.Housenumber, id=housenumber.id, identifier="id")
    data = {
        "version": 2,
        "number": housenumber.number,
        "ordinal": 'bis',
        "street": housenumber.street.id,
    }
    resp = put(uri, body=json.dumps(data))
    assert resp.status == 200
    assert resp.json['id']
    assert resp.json['version'] == 2
    assert resp.json['number'] == '22'
    assert resp.json['ordinal'] == 'bis'
    assert resp.json['street']['id'] == housenumber.street.id


@log_in
def test_replace_housenumber_with_missing_field_fails(put, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    uri = url(views.Housenumber, id=housenumber.id, identifier="id")
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.street.id,
    }
    resp = put(uri, body=json.dumps(data))
    assert resp.status == 422
    assert 'errors' in resp.json


@log_in
def test_create_street(post):
    municipality = MunicipalityFactory(name="Cabour")
    data = {
        "version": 1,
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": municipality.id,
    }
    resp = post('/street', data)
    assert resp.status == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Rue de la Plage'
    assert resp.json['municipality']['id'] == municipality.id


def test_get_municipality(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url(views.Municipality, id=municipality.id, identifier="id")
    resp = get(uri)
    assert resp.status == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


def test_get_municipality_streets_collection(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    street = StreetFactory(municipality=municipality, name="Rue de la Plage")
    uri = url(views.Municipality, id=municipality.id, identifier="id",
              route="streets")
    resp = get(uri, query_string='pouet=ah')
    assert resp.status == 200
    assert resp.json['collection'][0] == street.as_resource
    assert resp.json['total'] == 1


def test_get_municipality_streets_collection_is_paginated(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    StreetFactory.create_batch(30, municipality=municipality)
    uri = url(views.Municipality, id=municipality.id, identifier="id",
              route="streets")
    resp = get(uri)
    page1 = json.loads(resp.body)
    assert len(page1['collection']) == 20
    assert page1['total'] == 30
    assert 'next' in page1
    assert 'previous' not in page1
    resp = get(page1['next'])
    page2 = json.loads(resp.body)
    assert len(page2['collection']) == 10
    assert page2['total'] == 30
    assert 'next' not in page2
    assert 'previous' in page2
    resp = get(page2['previous'])
    assert json.loads(resp.body) == page1


def test_get_municipality_versions(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    uri = url(views.Municipality, id=municipality.id, identifier="id",
              route="versions")
    resp = get(uri)
    assert resp.status == 200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['name'] == 'Cabour'
    assert resp.json['collection'][1]['name'] == 'Cabour2'


def test_get_municipality_version(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    uri = url(views.Municipality, id=municipality.id, identifier="id",
              route="versions", route_id=1)
    resp = get(uri)
    assert resp.status == 200
    assert resp.json['name'] == 'Cabour'
    assert resp.json['version'] == 1
    uri = url(views.Municipality, id=municipality.id, identifier="id",
              route="versions", route_id=2)
    resp = get(uri)
    assert resp.status == 200
    assert resp.json['name'] == 'Cabour2'
    assert resp.json['version'] == 2


def test_get_street_versions(get, url):
    street = StreetFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url(views.Street, id=street.id, identifier="id",
              route="versions")
    resp = get(uri)
    assert resp.status == 200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['name'] == 'Rue de la Paix'
    assert resp.json['collection'][1]['name'] == 'Rue de la Guerre'


def test_get_street_version(get, url):
    street = StreetFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url(views.Street, id=street.id, identifier="id",
              route="versions", route_id=1)
    resp = get(uri)
    assert resp.status == 200
    assert resp.json['name'] == 'Rue de la Paix'
    assert resp.json['version'] == 1
    uri = url(views.Street, id=street.id, identifier="id",
              route="versions", route_id=2)
    resp = get(uri)
    assert resp.status == 200
    assert resp.json['name'] == 'Rue de la Guerre'
    assert resp.json['version'] == 2


def test_invalid_route_is_not_found(get, url):
    resp = get(url(views.Street, id=1, identifier="id", route="invalid"))
    assert resp.status == 404
    resp = get(url(views.Street, id=1, identifier="id", route="save_object"))
    assert resp.status == 404
