import logging

from nameko.events import event_handler
from nameko.rpc import rpc

from products import dependencies, schemas
from products.exceptions import InvalidArgument, NotFound

logger = logging.getLogger(__name__)


class ProductsService:

    name = 'products'

    storage = dependencies.Storage()

    @rpc
    def create(self, product):
        product = schemas.Product(strict=True).load(product).data
        self.storage.create(product)

    @rpc
    def get(self, product_id):
        product = self.storage.get(product_id)
        return schemas.Product().dump(product).data

    @rpc
    def list(self):
        products = self.storage.list()
        return schemas.Product(many=True).dump(products).data

    @rpc
    def delete_one(self, product_id):
        product = self.storage.get(product_id)
        if product is None:
            raise NotFound('Order with id {} not found'.format(product_id))
        self.storage.delete_one(product_id)
        return {"deleted_id": product_id}

    @event_handler('orders', 'order_created')
    def handle_order_created(self, payload):
        for product in payload['order']['order_details']:
            self.storage.decrement_stock(
                product['product_id'], product['quantity'])
