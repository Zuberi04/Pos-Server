from utils.stmt import read_stmt
from database.models import Inventory, Catalog

class FilterInventory:
    def __init__(self):
        pass

    async def collect_inventory_data(self):
        inventory = read_stmt.read_stmt(Inventory)
        if inventory is None:
            return None
        res = []
        for record in inventory:
            if len(res) > 0:
                if record['id'] in res:
                    continue

            data = read_stmt.read_stmt(Catalog, record['id'])
            if data:
                update = self.check_if_inventory_matches_catalog(record, data)
                if update is None:
                    continue
                if update not in res:
                    res.append(update['id'])
                continue
            continue
        return res

    def check_if_inventory_matches_catalog(self, inv:dict, catalog: list | dict):
        data = self.total_stock_price_of_catalog(catalog)
        up = False
        if inv['stock'] != data['stock']:
            inv['stock'] = data['stock']
            up = True
        if inv['amount'] != data['amount']:
            inv['amount'] = data['amount']
            up = True
        if up:
            return read_stmt.write_items_to_db(Inventory, inv)
        return None
        
        
    @staticmethod
    def total_stock_price_of_catalog(catalog: list | dict):
        stock = 0
        amount = 0
        if isinstance(catalog, dict):
            return {'stock': catalog['stock'], 'amount': catalog['amount']}
        for record in catalog:
            if not 'stock' in record or not 'price' in record:
                continue
            stock += record['stock']
            amount += record['price']
            continue
        return {'stock': stock, 'amount': amount}


filter_catalog = FilterInventory()

