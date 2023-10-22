import pytest

from mock import call
from nameko.exceptions import RemoteError

from orders.models import Order, OrderDetail
from orders.schemas import OrderSchema, OrderDetailSchema


@pytest.fixture
def order(db_session):
    order = Order()
    db_session.add(order)
    db_session.commit()
    return order

@pytest.fixture
def multiple_inserts(db_session, range_list = 3):
    order_list = []
    for _ in range(range_list):
        order_list.append(Order())
    db_session.add_all(order_list)
    db_session.commit()

@pytest.fixture
def heavy_multiple_inserts(db_session, range_list = 10):
    order_list = []
    for _ in range(range_list):
        order_list.append(Order())
    db_session.add_all(order_list)
    db_session.commit()


@pytest.fixture
def order_details(db_session, order):
    db_session.add_all([
        OrderDetail(
            order=order, product_id="the_odyssey", price=99.51, quantity=1
        ),
        OrderDetail(
            order=order, product_id="the_enigma", price=30.99, quantity=8
        )
    ])
    db_session.commit()
    return order_details


def test_get_order(orders_rpc, order):
    response = orders_rpc.get_order(1)
    assert response['id'] == order.id

def test_get_list_order_no_orders(orders_rpc, page = 1):

    with pytest.raises(RemoteError) as err:
        orders_rpc.get_list_order(page)
    assert err.value.value == 'No Orders were found'

def test_get_list_order_invalid_page(orders_rpc, page = 0):

    with pytest.raises(RemoteError) as err:
        orders_rpc.get_list_order(page)
    assert err.value.value == 'Invalid page number given'

@pytest.mark.usefixtures('multiple_inserts')
def test_get_list_order(orders_rpc, page = 1):
    response = orders_rpc.get_list_order(page)
    assert len(response) == 3
    assert response == [
        {'id': 1, 'order_details': []},
        {'id': 2, 'order_details': []},
        {'id': 3, 'order_details': []}
    ]
@pytest.mark.usefixtures('heavy_multiple_inserts')
def test_get_list_order_heavy_db(orders_rpc, page = 1):
    response = orders_rpc.get_list_order(page)
    assert len(response) == 5
    assert response == [
        {'id': 1, 'order_details': []},
        {'id': 2, 'order_details': []},
        {'id': 3, 'order_details': []},
        {'id': 4, 'order_details': []},
        {'id': 5, 'order_details': []}
    ]

@pytest.mark.usefixtures('db_session')
def test_will_raise_when_order_not_found(orders_rpc):
    with pytest.raises(RemoteError) as err:
        orders_rpc.get_order(1)
    assert err.value.value == 'Order with id 1 not found'


@pytest.mark.usefixtures('db_session')
def test_can_create_order(orders_service, orders_rpc):
    order_details = [
        {
            'product_id': "the_odyssey",
            'price': 99.99,
            'quantity': 1
        },
        {
            'product_id': "the_enigma",
            'price': 5.99,
            'quantity': 8
        }
    ]
    new_order = orders_rpc.create_order(
        OrderDetailSchema(many=True).dump(order_details).data
    )
    assert new_order['id'] > 0
    assert len(new_order['order_details']) == len(order_details)
    assert [call(
        'order_created', {'order': {
            'id': 1,
            'order_details': [
                {
                    'price': '99.99',
                    'product_id': "the_odyssey",
                    'id': 1,
                    'quantity': 1
                },
                {
                    'price': '5.99',
                    'product_id': "the_enigma",
                    'id': 2,
                    'quantity': 8
                }
            ]}}
    )] == orders_service.event_dispatcher.call_args_list


@pytest.mark.usefixtures('db_session', 'order_details')
def test_can_update_order(orders_rpc, order):
    order_payload = OrderSchema().dump(order).data
    for order_detail in order_payload['order_details']:
        order_detail['quantity'] += 1

    updated_order = orders_rpc.update_order(order_payload)

    assert updated_order['order_details'] == order_payload['order_details']


def test_can_delete_order(orders_rpc, order, db_session):
    orders_rpc.delete_order(order.id)
    assert not db_session.query(Order).filter_by(id=order.id).count()
