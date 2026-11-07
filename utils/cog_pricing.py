import time


class EstimateCOG:
    "C.O.G: assumption being that a p  makes a max profit of 200% of its 100% sale. Thus C.O.G can be calculated from its R.P"

    def __init__(self):
        self.eff = {"max": 2.00, "min": 1.00}

    def parse_cog(self, cog: float, data: dict, x: float = 1.00):
        from math import sqrt

        while x < self.eff["max"]:
            if round(data["price"], 2) != round(cog * x, 2):
                if not self.check_if_in_range(cog * x, data["price"]):
                    if data["price"] > (cog * x):
                        x += sqrt(sqrt(data["price"]) - sqrt(cog))
                        continue
                    return self.calculate_cog_from_r_price(data, cog * x)
            print("Data passed for pricing: \n", data)
            data["amount"] = cog * data["stock"]
            return data
        raise ArithmeticError(
            f"Failed in parsing cog with error val lack of equality check btw {data['price']} and {cog} at e of {x}"
        )

    def calculate_cog_from_r_price(self, data: dict, cog: float = 0):
        if not "price" or not "stock" in data or "amount" in data:
            return data
        elif cog and cog > data["price"]:
            self.eff = self.calc_n_eff(cog, data["price"])
        cog = 0
        for k in self.eff.keys():
            cog += data["price"] / self.eff[k]
        cog *= 1 / len(self.eff)
        print(f"Cog to price: {cog}: {data['price']}")
        if cog >= data["price"]:
            return self.calculate_cog_from_r_price(data, cog)
        return self.parse_cog(cog, data)

    def calc_n_eff(self, m: float, x: float):
        for e in self.eff.keys():
            self.eff[e] = m / x * self.eff[e]
        return self.eff

    @staticmethod
    def check_if_in_range(x: float, price: float):
        if price * 0.9 <= x <= price * 1.15:
            return True
        return False


est_price = EstimateCOG()
