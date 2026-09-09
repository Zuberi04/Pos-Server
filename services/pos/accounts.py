from services.pos.fetch import q_fetch
from services.analysis.graph import gen_graph


class Accounts:

    def __init__(self):
        pass

    async def collect_data_to_process(self, data: dict):
        if not 'name' in data:
            data["name"] = "inventory"
        inventory = await q_fetch.fetch_data(data)
        if not inventory:
            return {'error': 'No records to balance your pos accounts!!'}
        elif isinstance(inventory, dict):
            return {'error': 'Records held to few for any relevant calculations!!'}

        proc = []
        for record in inventory:
            if not record:
                continue
            q = {'name': 'catalog', 'q': record['id'], 'relshp': 'sales'}
            results = q_fetch.collect_query(q)
            if not results:
                raise ValueError(f'Error, failed getting query for inv record with id: {record['id']}')
            elif not 'sales' in results:
                continue
            record['rels'] = results
            if not record in proc:
                proc.append(record)
            continue
        if not proc:
            return {'error': 'Not enough sales made for calculation and analysis!!'}
        return self.balance_accounts(proc, data['id'])

    def balance_accounts(self, data: list, id: str):
        gp = 0
        for record in data:
            if not record:
                continue
            rec = {'stock': record['stock'], 'amount': record['amount']}
            if isinstance(record['rels'], dict):
                rec["product"] = record['rels']['stock']
                rec["quantity"] = record['rels']['sales']['quantity']
                i = data.index(record)
                cos = self.calculate_price_of_good_sold(rec)
                record['rels']['cog'] = cos
                gp += self.trading_account(record['rels']['amount'], cos)
                data[i] = record
                continue

            for recs in record['rels']:
                if 'sales' in recs:
                    rec['product'] = recs['stock']
                    rec['quantity'] = recs['sales']['quantity']
                    i = record['rels'].index(recs)
                    cos = self.calculate_price_of_good_sold(rec)
                    recs['price'] = cos
                    record['rels'][i] = recs
                    gp += self.trading_account(recs['sales']["amount"], cos)
                continue

        np = self.profit_loss_account(gp, id)
        return self.create_balance_sheet(np, data, id)

    @staticmethod
    def trading_account(sales: float, cos: float):
        """G.P = Sales - C.O.G sold"""
        return sales - cos

    @staticmethod
    def calculate_price_of_good_sold(data: dict):
        total = (data["product"] / data["stock"]) * data["amount"]
        if not total:
            raise ValueError("Error, failed calculating totals for product passed!!")
        return (data["quantity"] / data["product"]) * total

    def profit_loss_account(self, gp: float, id: str):
        """N.p = G.P - E"""
        expense = self.fetch_and_calculate_expenses(id)
        return gp - expense

    def create_balance_sheet(self, np: float, data: list, id: str):
        """A = C + L"""
        (res, acc) = self.balance_sheet(data)
        a = acc['assets'] + np
        c =  acc['credits'] + acc['liability']
        if a != c:
            return self.create_balance_sheet(np, data)
        res['total'] = a
        res['assets'].append({'profit': np})
        return self.clean_balance_sheet_data(res, id)

    def balance_sheet(self, inventory: list):
        """A = C + L"""
        print('Length of inventory passed: ', len(inventory))
        res = {'capital': 0, 'assets': 0, 'liability': 0}
        resp: dict = {'assets': [], 'credits': []}
        for record in inventory:
            if not 'flag' in record:
                raise ValueError('Malformed data pased or missing values passed!!')
            if record['flag'] != 'non-assets':
                if record not in resp['assets']:
                    resp['assets'].append(record)
                    res['assets'] += record['amount']
                    debtor = self.fetch_extras({'name': 'creditors', 'q': record['id']})
                    if debtor:
                        if debtor not in resp['credits']:
                            resp["credits"].append(debtor)
                            res['liability'] += debtor['amount']
                        continue
                    continue
                continue
            elif not isinstance(record['rels'], list):
                if record['rels'] not in resp['credits']:
                    resp['credits'].append(record['rels'])
                    res['assets'] += record['rels']['price']
                    resp["assets"].append({"stock": record["rels"]["price"]})
                    res['capital'] += self.calculate_total_for_record(record['rels'])
                    debtor = self.fetch_extras({"name": "creditors", "q": record["id"]})
                    if debtor:
                        if debtor['p_id'] != record['rels']['id']:
                            continue
                        elif debtor not in resp['credits']:
                            resp['credits'].append(debtor)
                            res['liability'] += debtor['amount']
                        continue
                    continue
                continue
            for rec in record['rels']:
                if rec not in resp['credits']:
                    resp['credits'].append(rec)
                    res['assets'] += rec['price']
                    res['capital'] += self.calculate_total_for_record(rec)
                    debtor = self.fetch_extras({"name": "creditors", "q": record["id"]})
                    if debtor:
                        if debtor['p_id'] != rec['id']:
                            continue
                        elif debtor not in resp['credits']:
                            resp['credits'].append(debtor)
                            res['liability'] += debtor['amount']
                        continue
                    continue
                continue
            continue
        return (resp, res)

    def calculate_total_for_record(data: dict):
        return data['cog']

    @staticmethod
    def fetch_extras(name: str, q: dict = None):
        if q:
            return q_fetch.collect_query(q)
        return q_fetch.fetch_data(name)

    @staticmethod
    def fetch_and_calculate_expenses(id: str):
        expenses = q_fetch.fetch_data({'name': "operationexpenses", 'id': id})
        if not expenses:
            return 0
        if not isinstance(expenses, list):
            if "error" in expenses:
                return 0
            return expenses["amount"]
        e = 0
        for expense in expenses:
            e += expense["amount"]
            continue
        return e

    @staticmethod
    def clean_balance_sheet_data(data: dict, id: str):
        result = {'assets': [], 'credits': [], 'total': 0}
        result['total'] = data['total']
        for k, v in data.items():
            if k != 'assets':
                if k != 'credits':
                    continue
                for item in v:
                    if 'brand' in item:
                        item['name'] = item['brand']
                        del item['brand']
                        if item not in result['credits']:
                            result['credits'].append(item)
                        continue
                    continue
                continue
            for item in v:
                if 'category' in item:
                    item['name'] = item['category']
                    del item['category']
                    if item not in result['assets']:
                        result['assets'].append(item)
                    continue
                continue
            continue

        return{'accounts': result, 'analysis': gen_graph.collect_req_data_for_graph({'id': id}) }


accounts = Accounts()
