from nameko.events import EventDispatcher
from nameko.rpc import rpc
from nameko_sqlalchemy import DatabaseSession

from orders.exceptions import NotFound
from orders.models import DeclarativeBase, Order, OrderDetail
from orders.schemas import OrderSchema


class OrdersService:
    name = 'orders'

    db = DatabaseSession(DeclarativeBase)
    event_dispatcher = EventDispatcher()

    @rpc
    def get_order(self, order_id):
        order = self.db.query(Order).get(order_id)

        if not order:
            raise NotFound('Order with id {} not found'.format(order_id))

        return OrderSchema().dump(order).data
    
    @rpc
    def get_list_order(self, page_number):
        if page_number < 1:
            raise  ValueError('Invalid page number given')
        order_list = self.db.query(Order).limit(5).offset((page_number-1)*5).all()
        order_list_response = []

        if len(order_list) == 0:
            raise NotFound('No Orders were found')
        
        for order in order_list:
            order_list_response.append(OrderSchema().dump(order).data)
        
        return order_list_response

    @rpc
    def create_order(self, order_details):
        order = Order(
            order_details=[
                OrderDetail(
                    product_id=order_detail['product_id'],
                    price=order_detail['price'],
                    quantity=order_detail['quantity']
                )
                for order_detail in order_details
            ]
        )
        self.db.add(order)
        self.db.commit()

        order = OrderSchema().dump(order).data

        self.event_dispatcher('order_created', {
            'order': order,
        })

        return order

    @rpc
    def update_order(self, order):
        order_details = {
            order_details['id']: order_details
            for order_details in order['order_details']
        }

        order = self.db.query(Order).get(order['id'])

        for order_detail in order.order_details:
            order_detail.price = order_details[order_detail.id]['price']
            order_detail.quantity = order_details[order_detail.id]['quantity']

        self.db.commit()
        return OrderSchema().dump(order).data

    @rpc
    def delete_order(self, order_id):
        order = self.db.query(Order).get(order_id)
        self.db.delete(order)
        self.db.commit()
