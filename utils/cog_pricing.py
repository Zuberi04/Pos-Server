class EstimateCOG:
    "C.O.G: assumption being that a p  makes a max profit of 190% of its 100% sale. Thus C.O.G can be calculated from its R.P"

    def __init__(self):
        self.eff = {"max": 2.90, "min": 2.00}

    def parse_cog(self, cog: float, data: dict, x: float = 0):

        while x < self.eff["max"] + 0.1:
            p = cog * self.eff["min"] if not x else x
            if data["price"] != p:
                if p > data["price"]:
                    if p / data["price"] - 1 > 0.15:
                        return self.calculate_cog_from_r_price(
                            data, p, x - self.eff["min"] if x else p / cog
                        )
                elif 1 - p / data["price"] > 0.15:
                    if not x:
                        x = self.eff["min"] + cog / data["price"]
                    else:
                        x += cog / data["price"]
                    continue
            data["amount"] = cog
            return data
        print(
            f"Failed to find cog equality with amount {cog} and mov of {x} and price: {data['price']}"
        )
        return self.calculate_cog_from_r_price(data, cog, x - self.eff["min"])

    def calculate_cog_from_r_price(self, data: dict, cog: float = 0, x: float = 0):
        if not "price" in data or "amount" in data and not cog:
            return data
        elif cog:
            for k in self.eff.keys():
                self.eff[k] = self.calc_n_eff(self.eff[k], cog, data["price"], x)
            cog = 0
        for k in self.eff.keys():
            cog += data["price"] / self.eff[k]
        cog *= 1 / len(self.eff)
        print(f"Cog to price: {cog}: {data['price']}")
        if cog >= data["price"]:
            return self.calculate_cog_from_r_price(data, cog)
        return self.parse_cog(cog, data)

    @staticmethod
    def calc_n_eff(k: float, cog: float, price: float | int, x: float = 0):
        m = cog / price
        if k != m:
            if k > m:
                return k - m
            try:
                return k - m / x
            except ZeroDivisionError:
                return (m / k) - k
        return k


est_price = EstimateCOG()
