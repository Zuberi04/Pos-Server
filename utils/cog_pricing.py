class EstimateCOG:
    def __init__(self):
        self.eff = {"max": 2.00, "min": 1.00}

    def parse_cog(self, cog: float, data: dict, x: float = 1.00):
        from math import sqrt

        if "price" and "stock" in data:
            while x < self.eff["max"]:
                if round(data["price"], 2) != round(cog * x, 2):
                    if not self.check_if_in_range(cog * x, data["price"]):
                        if data["price"] > (cog * x):
                            x += sqrt(sqrt(data["price"]) - sqrt(cog * x))
                            continue
                        return self.calculate_cog_from_r_price(data, cog * x)
                print("Data passed for pricing: \n", data)
                data["total"] = cog * data["stock"]
                return data
            return self.calculate_cog_from_r_price(data, cog * x)
        return data

    def calculate_cog_from_r_price(self, data: dict, cog: float = 0):
        if not "amount" in data:
            try:
                if cog and cog > data["price"]:
                    self.eff = self.calc_n_eff(cog, data["price"])
                    cog = 0
                for k in self.eff.keys():
                    cog += data["price"] / self.eff[k]
                cog *= 1 / len(self.eff)
                if cog >= data["price"]:
                    return self.calculate_cog_from_r_price(data, cog)
                return self.parse_cog(cog, data)
            except KeyError:
                return data

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
